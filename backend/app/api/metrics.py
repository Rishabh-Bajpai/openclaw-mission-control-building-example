from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from pydantic import BaseModel
from app.core.database import get_db
from app.models.models import Agent, Task, TaskStatus

router = APIRouter(prefix="/metrics", tags=["metrics"])


class AgentMetrics(BaseModel):
    agent_id: int
    agent_name: str
    tasks_completed: int
    tasks_in_progress: int
    tasks_failed: int
    total_working_time_minutes: int
    success_rate: float

    class Config:
        from_attributes = True


class TeamMetrics(BaseModel):
    team_id: int
    agents: List[AgentMetrics]


@router.get("/agent/{agent_id}", response_model=AgentMetrics)
async def get_agent_metrics(agent_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get performance metrics for a specific agent.
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    tasks_result = await db.execute(
        select(
            func.count(Task.id).filter(Task.status == TaskStatus.DONE),
            func.count(Task.id).filter(Task.status == TaskStatus.IN_PROGRESS),
        ).where(Task.agent_id == agent_id)
    )
    completed, in_progress = tasks_result.first()

    total_attempted = agent.tasks_completed + agent.tasks_failed
    success_rate = (
        (agent.tasks_completed / total_attempted * 100) if total_attempted > 0 else 0.0
    )

    return AgentMetrics(
        agent_id=agent.id,
        agent_name=agent.name,
        tasks_completed=agent.tasks_completed or 0,
        tasks_in_progress=in_progress or 0,
        tasks_failed=agent.tasks_failed or 0,
        total_working_time_minutes=agent.total_working_time_minutes or 0,
        success_rate=round(success_rate, 1),
    )


@router.get("/leaderboard", response_model=List[AgentMetrics])
async def get_leaderboard(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """
    Get top performing agents sorted by tasks completed.
    """
    result = await db.execute(
        select(Agent).order_by(Agent.tasks_completed.desc()).limit(limit)
    )
    agents = result.scalars().all()

    metrics = []
    for agent in agents:
        total_attempted = agent.tasks_completed + agent.tasks_failed
        success_rate = (
            (agent.tasks_completed / total_attempted * 100)
            if total_attempted > 0
            else 0.0
        )

        tasks_result = await db.execute(
            select(
                func.count(Task.id).filter(Task.status == TaskStatus.IN_PROGRESS)
            ).where(Task.agent_id == agent.id)
        )
        in_progress = tasks_result.scalar() or 0

        metrics.append(
            AgentMetrics(
                agent_id=agent.id,
                agent_name=agent.name,
                tasks_completed=agent.tasks_completed or 0,
                tasks_in_progress=in_progress,
                tasks_failed=agent.tasks_failed or 0,
                total_working_time_minutes=agent.total_working_time_minutes or 0,
                success_rate=round(success_rate, 1),
            )
        )

    return metrics
