import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Task, TaskStatus, Agent, Message
from app.core.database import async_session
from app.services.openclaw_gateway import openclaw

logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    Handles agent task execution lifecycle:
    1. Task assignment triggers execution
    2. Agent executes steps
    3. On completion, task moves to In Review
    """

    def __init__(self):
        self.active_executions: Dict[int, Dict[str, Any]] = {}

    async def execute_task(self, task_id: int, agent_id: int) -> Dict[str, Any]:
        """Execute a task for an agent"""

        if task_id in self.active_executions:
            return {
                "status": "already_running",
                "message": f"Task {task_id} is already being executed",
            }

        self.active_executions[task_id] = {
            "agent_id": agent_id,
            "started_at": datetime.now(timezone.utc),
            "status": "planning",
        }

        try:
            async with async_session() as db:
                await self._execute_task_internal(task_id, agent_id, db)
                return {"status": "completed", "task_id": task_id, "agent_id": agent_id}
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            import traceback

            traceback.print_exc()
            return {"status": "error", "message": str(e)}
        finally:
            self.active_executions.pop(task_id, None)

    async def _execute_task_internal(
        self, task_id: int, agent_id: int, db: AsyncSession
    ):
        """Execute the task via OpenClaw agent"""

        task_result = await db.execute(select(Task).where(Task.id == task_id))
        task = task_result.scalar_one_or_none()
        if not task:
            return

        agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = agent_result.scalar_one_or_none()
        if not agent:
            return

        logger.info(f"Executing task {task_id} for agent {agent.name}")

        msg = Message(
            agent_id=int(agent.id),
            sender="system",
            content=f"Starting execution of: {task.title}",
            is_from_user=False,
        )
        db.add(msg)

        task.status = TaskStatus.IN_PROGRESS
        await db.commit()

        logger.info(f"Triggering OpenClaw agent {agent.name} to execute task {task_id}")

        openclaw_result = await openclaw.run_agent(
            agent_id=str(agent.name),
            message=f"Execute task: {task.title}. Description: {task.description or 'No description'}",
        )

        if openclaw_result:
            logger.info(f"OpenClaw agent triggered successfully for task {task_id}")
            msg2 = Message(
                agent_id=int(agent.id),
                sender="system",
                content=f"Task '{task.title}' is being executed by OpenClaw agent",
                is_from_user=False,
            )
        else:
            logger.warning(f"OpenClaw agent trigger failed")
            msg2 = Message(
                agent_id=int(agent.id),
                sender="system",
                content=f"OpenClaw unavailable - task will be retried",
                is_from_user=False,
            )

        db.add(msg2)
        await db.commit()

        logger.info(f"Task {task_id} is now in progress - waiting for agent completion")

    def is_task_executing(self, task_id: int) -> bool:
        return task_id in self.active_executions


task_executor = TaskExecutor()
