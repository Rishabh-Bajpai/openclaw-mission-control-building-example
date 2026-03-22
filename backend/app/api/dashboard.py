from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.core.database import get_db
from app.models.models import Agent, AgentStatus, Task, TaskStatus, Team
from app.models.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    agents_result = await db.execute(select(func.count(Agent.id)))
    total_agents = agents_result.scalar() or 0

    active_result = await db.execute(
        select(func.count(Agent.id)).where(Agent.status == AgentStatus.ACTIVE)
    )
    active_agents = active_result.scalar() or 0

    idle_result = await db.execute(
        select(func.count(Agent.id)).where(Agent.status == AgentStatus.IDLE)
    )
    idle_agents = idle_result.scalar() or 0

    overheated_result = await db.execute(
        select(func.count(Agent.id)).where(Agent.status == AgentStatus.OVERHEATED)
    )
    overheated_agents = overheated_result.scalar() or 0

    tasks_result = await db.execute(select(func.count(Task.id)))
    total_tasks = tasks_result.scalar() or 0

    backlog_result = await db.execute(
        select(func.count(Task.id)).where(
            or_(Task.status == None, Task.status == TaskStatus.BACKLOG)
        )
    )
    backlog_tasks = backlog_result.scalar() or 0

    in_progress_result = await db.execute(
        select(func.count(Task.id)).where(Task.status == TaskStatus.IN_PROGRESS)
    )
    in_progress_tasks = in_progress_result.scalar() or 0

    review_result = await db.execute(
        select(func.count(Task.id)).where(Task.status == TaskStatus.REVIEW)
    )
    review_tasks = review_result.scalar() or 0

    done_result = await db.execute(
        select(func.count(Task.id)).where(Task.status == TaskStatus.DONE)
    )
    done_tasks = done_result.scalar() or 0

    teams_result = await db.execute(select(func.count(Team.id)))
    total_teams = teams_result.scalar() or 0

    return DashboardStats(
        total_agents=total_agents,
        active_agents=active_agents,
        idle_agents=idle_agents,
        overheated_agents=overheated_agents,
        total_tasks=total_tasks,
        backlog_tasks=backlog_tasks,
        in_progress_tasks=in_progress_tasks,
        review_tasks=review_tasks,
        done_tasks=done_tasks,
        total_teams=total_teams,
    )
