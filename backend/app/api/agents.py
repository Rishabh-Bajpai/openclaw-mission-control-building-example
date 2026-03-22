from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging
from app.core.database import get_db
from app.models.models import (
    Agent,
    AgentStatus,
    AgentLog,
    Task,
    TaskStatus,
    Team,
    Message,
)
from app.models.schemas import AgentCreate, AgentUpdate, AgentResponse, AgentLogResponse
from app.services.workspace_manager import workspace_manager
from app.services.openclaw_gateway import openclaw

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.name))
    agents = result.scalars().all()

    for agent in agents:
        actual_hb = await openclaw.get_agent_heartbeat(str(agent.name))
        db_hb = int(agent.heartbeat_frequency) if agent.heartbeat_frequency else 0
        if actual_hb != db_hb:
            logger.info(
                f"[ListSync] {agent.name}: DB={db_hb}m, OpenClaw={actual_hb}m -> syncing to {actual_hb}m"
            )
            agent.heartbeat_frequency = actual_hb

        # Sync status based on heartbeat - heartbeat is source of truth for activity
        if actual_hb > 0 and agent.status == AgentStatus.IDLE:
            logger.info(
                f"[ListSync] {agent.name}: status {agent.status} -> ACTIVE (heartbeat={actual_hb}m)"
            )
            agent.status = AgentStatus.ACTIVE
        elif actual_hb == 0 and agent.status == AgentStatus.ACTIVE:
            logger.info(
                f"[ListSync] {agent.name}: status {agent.status} -> IDLE (heartbeat=0)"
            )
            agent.status = AgentStatus.IDLE

    await db.commit()
    await db.refresh(agents[0]) if agents else None
    return agents


@router.get("/hierarchy")
async def get_agents_hierarchy(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(Agent.name))
    agents = result.scalars().all()

    agents_data = []
    for agent in agents:
        team_name = None
        chief_name = None
        if agent.team_id:
            team_result = await db.execute(select(Team).where(Team.id == agent.team_id))
            team = team_result.scalar_one_or_none()
            if team:
                team_name = team.name
        if agent.chief_id:
            chief_result = await db.execute(
                select(Agent).where(Agent.id == agent.chief_id)
            )
            chief = chief_result.scalar_one_or_none()
            if chief:
                chief_name = chief.name

        agents_data.append(
            {
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "status": agent.status.value
                if hasattr(agent.status, "value")
                else agent.status,
                "chief_id": agent.chief_id,
                "chief_name": chief_name,
                "team_id": agent.team_id,
                "team_name": team_name,
                "model": agent.model,
                "heartbeat_frequency": agent.heartbeat_frequency,
                "active_hours_start": agent.active_hours_start,
                "active_hours_end": agent.active_hours_end,
                "can_spawn_subagents": agent.can_spawn_subagents,
                "failure_count": agent.failure_count,
            }
        )

    return agents_data


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/subordinates", response_model=List[AgentResponse])
async def get_subordinates(agent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Agent).where(Agent.chief_id == agent_id).order_by(Agent.name)
    )
    subordinates = result.scalars().all()
    return subordinates


import os
import uuid


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(agent_data: AgentCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Agent).where(Agent.name == agent_data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Agent with this name already exists"
        )

    team_name = None

    if agent_data.team_id:
        team_result = await db.execute(
            select(Team).where(Team.id == agent_data.team_id)
        )
        team = team_result.scalar_one_or_none()
        if team:
            team_name = team.name

    # Default heartbeat to 10 minutes if not specified
    heartbeat_freq = (
        agent_data.heartbeat_frequency if agent_data.heartbeat_frequency > 0 else 10
    )

    db_agent = Agent(
        name=agent_data.name,
        role=agent_data.role,
        chief_id=agent_data.chief_id,
        team_id=agent_data.team_id,
        model=agent_data.model,
        heartbeat_frequency=heartbeat_freq,
        status=AgentStatus.ACTIVE,  # Start as active
        active_hours_start=agent_data.active_hours_start,
        active_hours_end=agent_data.active_hours_end,
        can_spawn_subagents=agent_data.can_spawn_subagents,
    )
    db.add(db_agent)
    await db.commit()
    await db.refresh(db_agent)

    agent_name_str = str(db_agent.name)
    workspace = workspace_manager.get_agent_workspace(agent_name_str)

    # Ensure workspace directory exists
    import os

    os.makedirs(workspace, exist_ok=True)

    workspace_manager.create_default_files(agent_name_str, agent_data.role, team_name)

    # Step 1: Check OpenClaw gateway health first
    health = await openclaw.health_check()
    if not health.get("connected"):
        raise HTTPException(
            status_code=503,
            detail={
                "message": "OpenClaw Gateway is restarting. Retry in 5 seconds.",
                "retry_seconds": 5,
                "agent_id": db_agent.id,
            },
        )

    # Step 2: Create agent in OpenClaw config (without heartbeat first)
    agent_added = await openclaw.add_agent_to_config(
        agent_name=agent_name_str,
        workspace=workspace,
    )

    # Small delay to ensure gateway processes the agent creation
    import asyncio

    await asyncio.sleep(0.5)

    # Step 2: Add heartbeat with default 10 minutes
    heartbeat_result = await openclaw.set_agent_heartbeat(
        agent_name=agent_name_str,
        heartbeat_minutes=int(db_agent.heartbeat_frequency),
        workspace=workspace,
    )

    if heartbeat_result["rate_limited"]:
        logger.warning(
            f"RATE_LIMITED: {agent_name_str} creation heartbeat blocked - wait {heartbeat_result['retry_seconds']}s"
        )
        db_agent.heartbeat_frequency = 0
        await db.commit()
        await db.refresh(db_agent)
        response = AgentResponse.model_validate(db_agent)
        response.rate_limited = True
        response.retry_seconds = heartbeat_result["retry_seconds"]
        response.warnings = [
            f"Heartbeat rate limited, retry in {heartbeat_result['retry_seconds']}s"
        ]
        raise HTTPException(
            status_code=429,
            detail={
                "message": f"Agent created but heartbeat rate limited. Retry in {heartbeat_result['retry_seconds']} seconds.",
                "retry_seconds": heartbeat_result["retry_seconds"],
                "agent_id": db_agent.id,
            },
        )

    if not heartbeat_result["success"]:
        logger.warning(
            f"Failed to set heartbeat for new agent {agent_name_str}: {heartbeat_result.get('error_message', 'Unknown error')}"
        )

    # Create agent session in OpenClaw via ensure_session
    session_key = f"agent:{agent_name_str.lower()}:main"
    session_created = False
    try:
        from app.services.openclaw.gateway_rpc import ensure_session, GatewayConfig

        config = GatewayConfig(
            url=openclaw.ws_url,
            token=openclaw.token,
            disable_device_pairing=False,
        )
        await ensure_session(
            session_key,
            config=config,
            label=f"Agent {agent_name_str} session",
        )
        session_created = True
        log_details = f"Created agent: {db_agent.name} | Session: {session_key}"
    except Exception as e:
        import traceback

        traceback.print_exc()
        log_details = f"Created agent: {db_agent.name} | Session failed: {e}"

    if agent_added:
        log_details += " | OpenClaw: Added"
    else:
        log_details += " | OpenClaw: Failed to add"

    if heartbeat_result["rate_limited"]:
        log_details += f" | Heartbeat: Rate limited (retry in {heartbeat_result['retry_seconds']}s)"
    elif heartbeat_result["success"]:
        log_details += f" | Heartbeat: {db_agent.heartbeat_frequency}m"
    else:
        log_details += " | Heartbeat: Not set"

    log = AgentLog(
        agent_id=db_agent.id,
        action="AGENT_CREATED",
        details=log_details,
    )
    db.add(log)
    await db.commit()

    return db_agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int, agent_update: AgentUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = agent_update.model_dump(exclude_unset=True)
    old_heartbeat = db_agent.heartbeat_frequency

    # Prevent name changes (not recommended by OpenClaw)
    if "name" in update_data:
        del update_data["name"]

    for key, value in update_data.items():
        setattr(db_agent, key, value)

    if agent_update.status == AgentStatus.OVERHEATED:
        db_agent.failure_count = 0

    await db.commit()
    await db.refresh(db_agent)

    agent_name_str = str(db_agent.name)

    # Update OpenClaw config if heartbeat_frequency changed
    if (
        agent_update.heartbeat_frequency is not None
        and agent_update.heartbeat_frequency != old_heartbeat
    ):
        # Check OpenClaw gateway health first
        health = await openclaw.health_check()
        if not health.get("connected"):
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "OpenClaw Gateway is restarting. Retry in 5 seconds.",
                    "retry_seconds": 5,
                    "agent_id": db_agent.id,
                },
            )

        workspace = workspace_manager.get_agent_workspace(agent_name_str)
        heartbeat_result = await openclaw.set_agent_heartbeat(
            agent_name=agent_name_str,
            heartbeat_minutes=int(agent_update.heartbeat_frequency),
            workspace=workspace,
        )

        if heartbeat_result["rate_limited"]:
            logger.warning(
                f"RATE_LIMITED: {agent_name_str} heartbeat update blocked - wait {heartbeat_result['retry_seconds']}s"
            )
            log = AgentLog(
                agent_id=db_agent.id,
                action="RATE_LIMITED",
                details=f"Agent heartbeat update rate limited, retry in {heartbeat_result['retry_seconds']}s",
            )
            db.add(log)
            await db.commit()
            response = AgentResponse.model_validate(db_agent)
            response.rate_limited = True
            response.retry_seconds = heartbeat_result["retry_seconds"]
            response.warnings = [
                f"Rate limited. Retry in {heartbeat_result['retry_seconds']}s"
            ]
            raise HTTPException(
                status_code=429,
                detail={
                    "message": f"Rate limited. Retry in {heartbeat_result['retry_seconds']} seconds.",
                    "retry_seconds": heartbeat_result["retry_seconds"],
                    "agent_id": db_agent.id,
                },
            )

        if heartbeat_result["success"]:
            logger.info(
                f"Updated heartbeat for {agent_name_str}: {agent_update.heartbeat_frequency}m"
            )
        else:
            actual_hb = await openclaw.get_agent_heartbeat(agent_name_str)
            db_agent.heartbeat_frequency = actual_hb
            logger.warning(
                f"Failed to update heartbeat for {agent_name_str}: synced to {actual_hb}m from OpenClaw"
            )

    # Update IDENTITY.md if role or team changed
    needs_identity_update = (
        agent_update.role is not None or agent_update.team_id is not None
    )

    if needs_identity_update:
        team_name = None
        if db_agent.team_id:
            team_result = await db.execute(
                select(Team).where(Team.id == db_agent.team_id)
            )
            team = team_result.scalar_one_or_none()
            if team:
                team_name = team.name

        workspace_manager.update_identity(
            agent_name_str,
            name=str(db_agent.name),
            role=str(db_agent.role),
            team=team_name,
        )
        logger.info(f"Updated IDENTITY.md for {agent_name_str}")

    log = AgentLog(
        agent_id=db_agent.id,
        action="AGENT_UPDATED",
        details=f"Updated fields: {list(update_data.keys())}",
    )
    db.add(log)
    await db.commit()

    return db_agent


@router.post("/{agent_id}/reset", response_model=AgentResponse)
async def reset_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    db_agent.status = AgentStatus.IDLE
    db_agent.failure_count = 0
    await db.commit()
    await db.refresh(db_agent)

    log = AgentLog(
        agent_id=db_agent.id, action="AGENT_RESET", details="Agent status reset to IDLE"
    )
    db.add(log)
    await db.commit()

    return db_agent


@router.post("/{agent_id}/start", response_model=AgentResponse)
async def start_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Start an agent: enable heartbeat, set status active, trigger run"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check OpenClaw gateway health first
    health = await openclaw.health_check()
    if not health.get("connected"):
        raise HTTPException(
            status_code=503,
            detail={
                "message": "OpenClaw Gateway is restarting. Retry in 5 seconds.",
                "retry_seconds": 5,
                "agent_id": agent_id,
            },
        )

    agent_name_str = str(db_agent.name)
    workspace = workspace_manager.get_agent_workspace(agent_name_str)
    warnings = []
    rate_limited = False
    retry_seconds = 0

    # Enable heartbeat with default 10 minutes if not set
    heartbeat_minutes = (
        int(db_agent.heartbeat_frequency) if db_agent.heartbeat_frequency > 0 else 10
    )
    heartbeat_result = await openclaw.set_agent_heartbeat(
        agent_name=agent_name_str,
        heartbeat_minutes=heartbeat_minutes,
        workspace=workspace,
    )

    if heartbeat_result["rate_limited"]:
        rate_limited = True
        retry_seconds = heartbeat_result["retry_seconds"]
        logger.warning(
            f"RATE_LIMITED: {agent_name_str} start blocked - wait {retry_seconds}s"
        )
        log = AgentLog(
            agent_id=db_agent.id,
            action="RATE_LIMITED",
            details=f"Agent start rate limited, retry in {retry_seconds}s",
        )
        db.add(log)
        await db.commit()

        response = AgentResponse.model_validate(db_agent)
        response.rate_limited = True
        response.retry_seconds = retry_seconds
        response.warnings = [f"Rate limited. Retry in {retry_seconds}s"]
        raise HTTPException(
            status_code=429,
            detail={
                "message": f"Rate limited. Retry in {retry_seconds} seconds.",
                "retry_seconds": retry_seconds,
                "agent_id": agent_id,
            },
        )

    if heartbeat_result["success"]:
        db_agent.heartbeat_frequency = heartbeat_minutes
    else:
        actual_hb = await openclaw.get_agent_heartbeat(agent_name_str)
        db_agent.heartbeat_frequency = actual_hb
        if actual_hb > 0:
            warnings.append(
                f"Heartbeat synced from OpenClaw: {actual_hb}m (config.apply failed)"
            )
        else:
            warnings.append(
                f"Failed to set heartbeat in OpenClaw: {heartbeat_result.get('error_message', 'Unknown error')}"
            )

    # Set status to active
    db_agent.status = AgentStatus.ACTIVE

    # Trigger agent run
    try:
        await openclaw.run_agent(
            agent_id=agent_name_str, message="Start working on your assigned tasks"
        )
    except Exception as e:
        logger.error(f"Failed to trigger run for {agent_name_str}: {e}")
        warnings.append(f"Failed to trigger agent run: {str(e)}")

    await db.commit()
    await db.refresh(db_agent)

    log = AgentLog(
        agent_id=db_agent.id,
        action="AGENT_STARTED",
        details=f"Agent started with heartbeat: {heartbeat_minutes}m"
        + (f" | Warnings: {', '.join(warnings)}" if warnings else ""),
    )
    db.add(log)
    await db.commit()

    # Return with warnings
    response = AgentResponse.model_validate(db_agent)
    response.warnings = warnings if warnings else None
    return response


@router.post("/{agent_id}/stop", response_model=AgentResponse)
async def stop_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Stop an agent: disable heartbeat, set status idle"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check OpenClaw gateway health first
    health = await openclaw.health_check()
    if not health.get("connected"):
        raise HTTPException(
            status_code=503,
            detail={
                "message": "OpenClaw Gateway is restarting. Retry in 5 seconds.",
                "retry_seconds": 5,
                "agent_id": agent_id,
            },
        )

    agent_name_str = str(db_agent.name)
    workspace = workspace_manager.get_agent_workspace(agent_name_str)
    warnings = []

    # Disable heartbeat
    heartbeat_result = await openclaw.set_agent_heartbeat(
        agent_name=agent_name_str,
        heartbeat_minutes=0,
        workspace=workspace,
    )

    if heartbeat_result["rate_limited"]:
        logger.warning(
            f"RATE_LIMITED: {agent_name_str} stop blocked - wait {heartbeat_result['retry_seconds']}s"
        )
        log = AgentLog(
            agent_id=db_agent.id,
            action="RATE_LIMITED",
            details=f"Agent stop rate limited, retry in {heartbeat_result['retry_seconds']}s",
        )
        db.add(log)
        await db.commit()

        response = AgentResponse.model_validate(db_agent)
        response.rate_limited = True
        response.retry_seconds = heartbeat_result["retry_seconds"]
        response.warnings = [
            f"Rate limited. Retry in {heartbeat_result['retry_seconds']}s"
        ]
        raise HTTPException(
            status_code=429,
            detail={
                "message": f"Rate limited. Retry in {heartbeat_result['retry_seconds']} seconds.",
                "retry_seconds": heartbeat_result["retry_seconds"],
                "agent_id": agent_id,
            },
        )

    if heartbeat_result["success"]:
        db_agent.heartbeat_frequency = 0
    else:
        actual_hb = await openclaw.get_agent_heartbeat(agent_name_str)
        db_agent.heartbeat_frequency = actual_hb
        if actual_hb > 0:
            warnings.append(
                f"Heartbeat synced from OpenClaw: {actual_hb}m (config.apply failed)"
            )
        else:
            warnings.append(
                f"Failed to disable heartbeat in OpenClaw: {heartbeat_result.get('error_message', 'Unknown error')}"
            )

    # Set status to idle
    db_agent.status = AgentStatus.IDLE

    await db.commit()
    await db.refresh(db_agent)

    log = AgentLog(
        agent_id=db_agent.id,
        action="AGENT_STOPPED",
        details="Agent stopped (heartbeat disabled)"
        + (f" | Warnings: {', '.join(warnings)}" if warnings else ""),
    )
    db.add(log)
    await db.commit()

    # Return with warnings
    response = AgentResponse.model_validate(db_agent)
    response.warnings = warnings if warnings else None
    return response


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    db_agent = result.scalar_one_or_none()
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent_name_str = str(db_agent.name)
    workspace_manager.delete_agent_files(agent_name_str)

    try:
        await openclaw.delete_agent(agent_name_str)
    except Exception as e:
        pass

    messages_result = await db.execute(
        select(Message).where(Message.agent_id == agent_id)
    )
    messages = messages_result.scalars().all()
    for msg in messages:
        await db.delete(msg)

    tasks_result = await db.execute(select(Task).where(Task.agent_id == agent_id))
    tasks = tasks_result.scalars().all()
    for task in tasks:
        await db.delete(task)

    logs_result = await db.execute(
        select(AgentLog).where(AgentLog.agent_id == agent_id)
    )
    logs = logs_result.scalars().all()
    for log in logs:
        await db.delete(log)

    log_entry = AgentLog(
        agent_id=agent_id,
        action="AGENT_DELETED",
        details=f"Deleted agent: {agent_name_str}",
    )
    db.add(log_entry)

    await db.delete(db_agent)
    await db.commit()


@router.get("/{agent_id}/files")
async def get_agent_files(agent_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    files = workspace_manager.read_all(agent.name)
    if not files:
        return {"error": "Agent files not found"}
    return files.model_dump()


@router.put("/{agent_id}/files")
async def update_agent_files(
    agent_id: int, files_data: dict, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    for filename, content in files_data.items():
        workspace_manager.save_file(agent.name, filename, content)

    return {"message": "Files updated successfully"}


@router.get("/{agent_id}/logs", response_model=List[AgentLogResponse])
async def get_agent_logs(
    agent_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AgentLog)
        .where(AgentLog.agent_id == agent_id)
        .order_by(AgentLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return logs


@router.post("/sync-from-openclaw")
async def sync_agents_from_openclaw(db: AsyncSession = Depends(get_db)):
    """Sync agents from OpenClaw config to Mission Control database"""
    try:
        config = await openclaw.get_config()
        if not config:
            raise HTTPException(status_code=500, detail="Failed to get OpenClaw config")

        # Extract actual config from nested structure
        actual_config = config.get("config", config)
        agents_list = actual_config.get("agents", {}).get("list", [])
        synced = 0
        created = 0
        updated = 0

        for agent_config in agents_list:
            agent_name = agent_config.get("name") or agent_config.get("id")
            if not agent_name:
                continue

            # Check if agent exists in our DB
            result = await db.execute(select(Agent).where(Agent.name == agent_name))
            existing = result.scalar_one_or_none()

            # Get heartbeat info
            heartbeat_config = agent_config.get("heartbeat", {})
            heartbeat_interval = 0
            if heartbeat_config:
                every = heartbeat_config.get("every", "0m")
                if every.endswith("m"):
                    try:
                        heartbeat_interval = int(every[:-1])
                    except ValueError:
                        heartbeat_interval = 0

            if existing:
                # Update existing agent
                existing.heartbeat_frequency = heartbeat_interval
                existing.status = AgentStatus.IDLE
                updated += 1
            else:
                # Create new agent
                new_agent = Agent(
                    name=agent_name,
                    role=agent_config.get("identity", {}).get("theme", "agent"),
                    status=AgentStatus.IDLE,
                    heartbeat_frequency=heartbeat_interval,
                )
                db.add(new_agent)
                created += 1

            synced += 1

        await db.commit()

        return {
            "synced": synced,
            "created": created,
            "updated": updated,
            "message": f"Synced {synced} agents from OpenClaw ({created} created, {updated} updated)",
        }
    except Exception as e:
        logger.error(f"Error syncing agents from OpenClaw: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
