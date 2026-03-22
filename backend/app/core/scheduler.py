from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.models import Agent, AgentStatus, Task, TaskStatus, AgentLog
import logging
import threading
import time
import asyncio
import re
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Create synchronous database engine for scheduler
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

scheduler = BackgroundScheduler()


def run_agent_heartbeat():
    """Run heartbeat for all agents - assigns BACKLOG tasks to IN_PROGRESS"""
    db = SessionLocal()
    try:
        agents = (
            db.query(Agent)
            .filter(
                Agent.heartbeat_frequency > 0, Agent.status != AgentStatus.OVERHEATED
            )
            .all()
        )

        for agent in agents:
            pending_tasks = (
                db.query(Task)
                .filter(Task.agent_id == agent.id, Task.status == TaskStatus.BACKLOG)
                .all()
            )

            if pending_tasks:
                for task in pending_tasks:
                    task.status = TaskStatus.IN_PROGRESS

                db.commit()

                log = AgentLog(
                    agent_id=agent.id,
                    action="HEARTBEAT_AUTO_ASSIGN",
                    details=f"Auto-assigned {len(pending_tasks)} tasks from heartbeat",
                )
                db.add(log)
                db.commit()

                logger.info(
                    f"Auto-assigned {len(pending_tasks)} tasks for agent {agent.name}"
                )
    except Exception as e:
        logger.error(f"Error in agent heartbeat: {e}")
        db.rollback()
    finally:
        db.close()


def sync_all_agent_tasks_md():
    """Sync TASKS.md for all agents (DB → TASKS.md)"""
    db = SessionLocal()
    try:
        agents = db.query(Agent).all()
        for agent in agents:
            try:
                # Import and call the async function
                from app.api.tasks import _update_agent_tasks_md

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_update_agent_tasks_md(agent.id, None))
                loop.close()
            except Exception as e:
                logger.error(f"Error syncing TASKS.md for agent {agent.name}: {e}")
    except Exception as e:
        logger.error(f"Error in TASKS.md sync: {e}")
    finally:
        db.close()


def sync_tasks_md_to_db():
    """Sync TASKS.md changes back to DB (TASKS.md → DB)"""
    db = SessionLocal()
    try:
        # Import workspace manager
        from app.services.workspace_manager import workspace_manager

        agents = db.query(Agent).all()

        for agent in agents:
            try:
                safe_name = agent.name.lower().replace(" ", "_")
                tasks_md = workspace_manager.read_file(
                    safe_name, "TASKS.md", in_workspace=True
                )

                if not tasks_md:
                    continue

                # Parse TASKS.md to extract task status changes
                changes_made = False

                # Parse "## My Tasks" section
                my_tasks_match = re.search(
                    r"## My Tasks\s*\n(.*?)(?=\n## |$)", tasks_md, re.DOTALL
                )
                if my_tasks_match:
                    my_tasks_content = my_tasks_match.group(1)

                    # Extract tasks by status from markdown format
                    # Format: - **[STATUS]** Task Title (ID: X)

                    # Find all status changes by parsing the markdown
                    # Status patterns: [BACKLOG], [IN_PROGRESS], [REVIEW], [DONE]
                    status_pattern = (
                        r"\*\*\[([A-Z_]+)\]\*\*\s+(.+?)(?:\s+\(ID:\s*(\d+)\))?"
                    )

                    # This is a simplified parser - it looks for status markers in the text
                    # More sophisticated parsing would need to track task IDs

                    # For now, we'll check if tasks need status updates based on markers
                    # The actual sync is handled when tasks are created/updated

                logger.info(
                    f"Checked TASKS.md for agent {agent.name} - no automatic DB updates needed (UI is source of truth)"
                )

            except Exception as e:
                logger.error(
                    f"Error syncing TASKS.md to DB for agent {agent.name}: {e}"
                )

    except Exception as e:
        logger.error(f"Error in TASKS.md to DB sync: {e}")
    finally:
        db.close()


def check_task_completion():
    """Check if any IN_PROGRESS tasks should be moved to REVIEW based on timeout"""
    db = SessionLocal()
    try:
        in_progress_tasks = (
            db.query(Task).filter(Task.status == TaskStatus.IN_PROGRESS).all()
        )

        for task in in_progress_tasks:
            if not task.agent_id:
                continue

            try:
                if task.updated_at:
                    updated = task.updated_at
                    if updated.tzinfo is None:
                        updated = updated.replace(tzinfo=timezone.utc)
                    time_in_progress = datetime.now(timezone.utc) - updated
                    if time_in_progress > timedelta(
                        minutes=10
                    ):  # If >10 minutes in progress
                        task.status = TaskStatus.REVIEW
                        db.commit()

                        log = AgentLog(
                            agent_id=task.agent_id,
                            action="TASK_AUTO_REVIEW",
                            details=f"Task '{task.title}' auto-moved to review (timeout)",
                        )
                        db.add(log)
                        db.commit()

                        logger.info(
                            f"Task {task.id} auto-moved to REVIEW: {task.title} (timeout)"
                        )

            except Exception as e:
                logger.error(f"Error checking task completion for task {task.id}: {e}")
                db.rollback()
    except Exception as e:
        logger.error(f"Error in task completion check: {e}")
    finally:
        db.close()


def schedule_agent_heartbeats():
    """Schedule individual heartbeat for each agent based on their frequency"""
    db = SessionLocal()
    try:
        agents = (
            db.query(Agent)
            .filter(
                Agent.heartbeat_frequency > 0, Agent.status != AgentStatus.OVERHEATED
            )
            .all()
        )

        for agent in agents:
            job_id = f"agent_heartbeat_{agent.id}"

            # Remove existing job if any
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

            # Add new job
            scheduler.add_job(
                run_agent_heartbeat,
                trigger="interval",
                minutes=agent.heartbeat_frequency,
                id=job_id,
                name=f"Heartbeat for {agent.name}",
            )

        logger.info(f"Scheduled heartbeats for {len(agents)} agents")
    except Exception as e:
        logger.error(f"Error scheduling agent heartbeats: {e}")
    finally:
        db.close()


def setup_periodic_tasks_sync():
    """Set up periodic TASKS.md sync (every 1 minute)"""
    # Remove existing job if any
    if scheduler.get_job("tasks_md_sync"):
        scheduler.remove_job("tasks_md_sync")

    scheduler.add_job(
        sync_all_agent_tasks_md,
        trigger="interval",
        minutes=1,
        id="tasks_md_sync",
        name="Sync all agent TASKS.md files",
    )


def sync_openclaw_heartbeats_to_db():
    """Sync all agent heartbeats from OpenClaw config to our DB. Runs every 60 seconds to catch external changes."""
    db = SessionLocal()
    try:
        from app.services.openclaw_gateway import OpenClawGateway

        gateway = OpenClawGateway()
        agents = db.query(Agent).all()
        synced = 0
        errors = 0

        for agent in agents:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                actual_hb = loop.run_until_complete(
                    gateway.get_agent_heartbeat(str(agent.name))
                )
                loop.close()

                db_hb = (
                    int(agent.heartbeat_frequency) if agent.heartbeat_frequency else 0
                )
                if actual_hb != db_hb:
                    logger.info(
                        f"[HeartbeatSync] {agent.name}: DB={db_hb}m, OpenClaw={actual_hb}m -> syncing to {actual_hb}m"
                    )
                    agent.heartbeat_frequency = actual_hb
                    db.commit()
                    synced += 1
            except Exception as e:
                errors += 1
                logger.debug(f"[HeartbeatSync] {agent.name}: {e}")

        if synced > 0 or errors > 0:
            logger.info(f"[HeartbeatSync] Synced {synced} agents, {errors} errors")
    except Exception as e:
        logger.error(f"Error in OpenClaw heartbeat sync: {e}")
    finally:
        db.close()


def setup_openclaw_heartbeat_sync():
    """Set up periodic OpenClaw heartbeat sync (every 60 seconds)"""
    if scheduler.get_job("openclaw_heartbeat_sync"):
        scheduler.remove_job("openclaw_heartbeat_sync")

    scheduler.add_job(
        sync_openclaw_heartbeats_to_db,
        trigger="interval",
        seconds=60,
        id="openclaw_heartbeat_sync",
        name="Sync OpenClaw heartbeats to DB",
    )


def setup_task_completion_check():
    """Set up periodic task completion check (every 2 minutes)"""
    if scheduler.get_job("task_completion_check"):
        scheduler.remove_job("task_completion_check")

    scheduler.add_job(
        check_task_completion,
        trigger="interval",
        minutes=2,
        id="task_completion_check",
        name="Check task completion status",
    )


def start_scheduler():
    scheduler.start()
    schedule_agent_heartbeats()
    setup_periodic_tasks_sync()
    setup_task_completion_check()
    setup_openclaw_heartbeat_sync()
    logger.info("Scheduler started")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
