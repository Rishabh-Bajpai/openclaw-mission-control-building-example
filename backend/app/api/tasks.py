from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timezone
import asyncio
from app.core.database import get_db
from app.models.models import Task, TaskStatus, Goal, Agent, AgentLog, Message
from app.models.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    GoalCreate,
    GoalResponse,
)
from app.services.task_executor import task_executor
from app.services.workspace_manager import workspace_manager

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    agent_id: Optional[int] = None,
    goal_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Task)
    if status:
        query = query.where(Task.status == status)
    if agent_id is not None:
        query = query.where(Task.agent_id == agent_id)
    if goal_id is not None:
        query = query.where(Task.goal_id == goal_id)
    query = query.order_by(Task.priority.desc(), Task.created_at.desc())

    result = await db.execute(query)
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(task_data: TaskCreate, db: AsyncSession = Depends(get_db)):
    if task_data.agent_id:
        agent_result = await db.execute(
            select(Agent).where(Agent.id == task_data.agent_id)
        )
        if not agent_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Agent not found")

    db_task = Task(
        title=task_data.title,
        description=task_data.description,
        goal_id=task_data.goal_id,
        agent_id=task_data.agent_id,
        priority=task_data.priority,
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)

    task_id = int(db_task.id)
    agent_id = int(task_data.agent_id) if task_data.agent_id else None

    if agent_id:
        log = AgentLog(
            agent_id=agent_id,
            action="TASK_ASSIGNED",
            details=f"Task '{db_task.title}' assigned to agent",
        )
        db.add(log)
        await db.commit()

        message = Message(
            agent_id=agent_id,
            sender="system",
            content=f"📋 **New Task Assigned:** {db_task.title}\n\n{db_task.description or 'No description'}",
            is_from_user=False,
        )
        db.add(message)
        await db.commit()

        asyncio.create_task(task_executor.execute_task(task_id, agent_id))
        asyncio.create_task(_update_agent_tasks_md(agent_id, None))

    return db_task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int, task_update: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = db_task.status
    old_agent_id = db_task.agent_id

    update_data = task_update.model_dump(exclude_unset=True)
    new_agent_id = update_data.get("agent_id")
    agent_just_assigned = new_agent_id is not None and old_agent_id is None

    for key, value in update_data.items():
        setattr(db_task, key, value)

    if task_update.status == TaskStatus.DONE:
        db_task.completed_at = datetime.now(timezone.utc)
    elif old_status == TaskStatus.DONE and task_update.status != TaskStatus.DONE:
        db_task.completed_at = None

    await db.commit()
    await db.refresh(db_task)

    current_agent_id = db_task.agent_id
    if str(old_status) != str(db_task.status) or agent_just_assigned:
        log = AgentLog(
            agent_id=int(current_agent_id) if current_agent_id else None,
            action="TASK_MOVED",
            details=f"Task {db_task.id} moved from {old_status} to {db_task.status}. Reason: {task_update.move_reason or 'Not specified'}",
        )
        db.add(log)
        await db.commit()

        # Sync TASKS.md for affected agents when status changes
        affected_agents = set()
        if old_agent_id:
            affected_agents.add(old_agent_id)
        if current_agent_id:
            affected_agents.add(current_agent_id)

        for agent_id in affected_agents:
            asyncio.create_task(_update_agent_tasks_md(int(agent_id), None))

    # Trigger agent to pick up task if just assigned
    if agent_just_assigned and new_agent_id:
        log = AgentLog(
            agent_id=new_agent_id,
            action="TASK_ASSIGNED",
            details=f"Task '{db_task.title}' assigned via update",
        )
        db.add(log)
        await db.commit()

        asyncio.create_task(task_executor.execute_task(int(db_task.id), new_agent_id))

    return db_task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(db_task)
    await db.commit()


@router.post("/{task_id}/unassign", response_model=TaskResponse)
async def unassign_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Unassign an agent from a task, moving it back to backlog"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    db_task = result.scalar_one_or_none()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_agent_id = db_task.agent_id
    if old_agent_id is None:
        raise HTTPException(status_code=400, detail="Task is not assigned to any agent")

    db_task.agent_id = None
    db_task.status = TaskStatus.BACKLOG
    db_task.completed_at = None

    await db.commit()
    await db.refresh(db_task)

    log = AgentLog(
        agent_id=int(old_agent_id),
        action="TASK_UNASSIGNED",
        details=f"Task '{db_task.title}' unassigned from agent",
    )
    db.add(log)
    await db.commit()

    asyncio.create_task(_update_agent_tasks_md(int(old_agent_id), None))

    return db_task


# Agent-facing endpoints (for OpenClaw agents)
agent_router = APIRouter(prefix="/agent/tasks", tags=["agent-tasks"])


@agent_router.get("/my-tasks/{agent_id}")
async def get_my_tasks(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Get all tasks assigned to a specific agent (for OpenClaw agent heartbeat)"""
    result = await db.execute(
        select(Task, Agent.name)
        .join(Agent, Task.agent_id == Agent.id)
        .where(Task.agent_id == agent_id)
        .order_by(Task.status, Task.priority.desc())
    )
    rows = result.all()

    tasks_by_status = {
        "BACKLOG": [],
        "IN_PROGRESS": [],
        "REVIEW": [],
        "DONE": [],
    }

    for row in rows:
        task = row[0]
        agent_name = row[1]
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value
            if hasattr(task.status, "value")
            else task.status,
            "priority": task.priority,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat()
            if task.completed_at
            else None,
        }
        status_key = (
            task.status.value.upper()
            if hasattr(task.status, "value")
            else str(task.status).upper()
        )
        if status_key in tasks_by_status:
            tasks_by_status[status_key].append(task_dict)

    return {
        "agent_id": agent_id,
        "tasks": tasks_by_status,
        "total": len(rows),
        "markdown": _tasks_to_markdown(tasks_by_status),
    }


@agent_router.get("/team-tasks/{agent_id}")
async def get_team_tasks(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Get all tasks for agents on the same team (team-scoped view)"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    team_id = agent.team_id

    if team_id:
        team_agents_result = await db.execute(
            select(Agent).where(Agent.team_id == team_id)
        )
        team_agent_ids = [a.id for a in team_agents_result.scalars().all()]
    else:
        team_agent_ids = [agent_id]

    result = await db.execute(
        select(Task, Agent.name)
        .join(Agent, Task.agent_id == Agent.id)
        .where(Task.agent_id.in_(team_agent_ids))
        .order_by(Task.status, Task.priority.desc())
    )
    rows = result.all()

    tasks_by_status = {
        "BACKLOG": [],
        "IN_PROGRESS": [],
        "REVIEW": [],
        "DONE": [],
    }

    for row in rows:
        task = row[0]
        agent_name = row[1]
        task_dict = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value
            if hasattr(task.status, "value")
            else task.status,
            "priority": task.priority,
            "assigned_to": agent_name,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat()
            if task.completed_at
            else None,
        }
        status_key = (
            task.status.value.upper()
            if hasattr(task.status, "value")
            else str(task.status).upper()
        )
        if status_key in tasks_by_status:
            tasks_by_status[status_key].append(task_dict)

    return {
        "team_id": team_id,
        "team_agent_ids": team_agent_ids,
        "tasks": tasks_by_status,
        "total": len(rows),
        "markdown": _tasks_to_markdown(tasks_by_status, show_agent=True),
    }


@agent_router.put("/{task_id}/status")
async def update_task_status_by_agent(
    task_id: int, status: str, db: AsyncSession = Depends(get_db)
):
    """Update task status (for OpenClaw agents)"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        new_status = TaskStatus(status.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: backlog, in_progress, review, done",
        )

    old_status = task.status
    task.status = new_status

    if new_status == TaskStatus.DONE:
        task.completed_at = datetime.now(timezone.utc)
    elif old_status == TaskStatus.DONE and new_status != TaskStatus.DONE:
        task.completed_at = None

    await db.commit()
    await db.refresh(task)

    if task.agent_id:
        asyncio.create_task(_update_agent_tasks_md(int(task.agent_id), db))

    return {
        "success": True,
        "task_id": task_id,
        "old_status": str(old_status),
        "new_status": str(new_status),
    }


def _tasks_to_markdown(tasks_by_status: dict, show_agent: bool = False) -> str:
    """Convert tasks dict to Markdown format for TASKS.md"""
    lines = ["# Task Board", ""]

    for status in ["BACKLOG", "IN_PROGRESS", "REVIEW", "DONE"]:
        task_list = tasks_by_status.get(status, [])
        status_icon = {
            "BACKLOG": "📋",
            "IN_PROGRESS": "🔄",
            "REVIEW": "👀",
            "DONE": "✅",
        }.get(status, "📌")

        lines.append(f"## {status_icon} {status.replace('_', ' ')}")

        if not task_list:
            lines.append("- No tasks")
        else:
            for task in task_list:
                priority = (
                    "🔴"
                    if task.get("priority", 0) >= 3
                    else ("🟡" if task.get("priority", 0) >= 2 else "🟢")
                )
                agent_info = (
                    f" (Assigned to: {task.get('assigned_to', 'Unknown')})"
                    if show_agent
                    else ""
                )
                lines.append(f"- {priority} [{task['id']}] {task['title']}{agent_info}")
        lines.append("")

    return "\n".join(lines)


async def _update_agent_tasks_md(agent_id: int, db: AsyncSession | None) -> bool:
    """Update TASKS.md file for an agent when their tasks change"""
    from app.core.database import async_session as get_new_session

    async def _do_work(session: AsyncSession) -> bool:
        try:
            agent_result = await session.execute(
                select(Agent).where(Agent.id == agent_id)
            )
            agent = agent_result.scalar_one_or_none()
            if not agent:
                return False

            agent_name = str(agent.name)

            my_tasks_result = await session.execute(
                select(Task)
                .where(Task.agent_id == agent_id)
                .order_by(Task.priority.desc())
            )
            my_tasks = my_tasks_result.scalars().all()

            team_id = agent.team_id
            if team_id:
                team_agents_result = await session.execute(
                    select(Agent).where(Agent.team_id == team_id)
                )
                team_agent_ids = [int(a.id) for a in team_agents_result.scalars().all()]
            else:
                team_agent_ids = [agent_id]

            team_tasks_result = await session.execute(
                select(Task, Agent.name)
                .join(Agent, Task.agent_id == Agent.id)
                .where(Task.agent_id.in_(team_agent_ids))
                .order_by(Task.priority.desc())
            )
            team_rows = team_tasks_result.all()

            my_tasks_by_status = {
                "BACKLOG": [],
                "IN_PROGRESS": [],
                "REVIEW": [],
                "DONE": [],
            }
            for task in my_tasks:
                task_dict = {
                    "id": int(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status.value
                    if hasattr(task.status, "value")
                    else task.status,
                    "priority": task.priority,
                }
                status_key = (
                    task.status.value.upper()
                    if hasattr(task.status, "value")
                    else str(task.status).upper()
                )
                if status_key in my_tasks_by_status:
                    my_tasks_by_status[status_key].append(task_dict)

            team_tasks_by_status = {
                "BACKLOG": [],
                "IN_PROGRESS": [],
                "REVIEW": [],
                "DONE": [],
            }
            for row in team_rows:
                task = row[0]
                agent_name_for_task = row[1]
                task_dict = {
                    "id": int(task.id),
                    "title": task.title,
                    "description": task.description,
                    "status": task.status.value
                    if hasattr(task.status, "value")
                    else task.status,
                    "priority": task.priority,
                    "assigned_to": agent_name_for_task,
                }
                status_key = (
                    task.status.value.upper()
                    if hasattr(task.status, "value")
                    else str(task.status).upper()
                )
                if status_key in team_tasks_by_status:
                    team_tasks_by_status[status_key].append(task_dict)

            my_md = _tasks_to_markdown(my_tasks_by_status, show_agent=False)
            team_md = _tasks_to_markdown(team_tasks_by_status, show_agent=True)

            full_content = f"""# TASKS.md - Task Board for {agent_name}

## My Tasks
{my_md}

## Team Tasks
{team_md}
"""

            return workspace_manager.update_tasks_md(str(agent.name), full_content)
        except Exception as e:
            print(f"Error updating TASKS.md for agent {agent_id}: {e}")
            return False

    if db is not None:
        return await _do_work(db)
    else:
        async with get_new_session() as new_db:
            return await _do_work(new_db)


goals_router = APIRouter(prefix="/goals", tags=["goals"])


@goals_router.get("/", response_model=List[GoalResponse])
async def list_goals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).order_by(Goal.created_at.desc()))
    goals = result.scalars().all()
    return goals


@goals_router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(goal_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@goals_router.post("/", response_model=GoalResponse, status_code=201)
async def create_goal(goal_data: GoalCreate, db: AsyncSession = Depends(get_db)):
    if goal_data.is_main_goal:
        result = await db.execute(select(Goal).where(Goal.is_main_goal == True))
        existing_main = result.scalar_one_or_none()
        if existing_main:
            existing_main.is_main_goal = False

    db_goal = Goal(
        title=goal_data.title,
        description=goal_data.description,
        is_main_goal=goal_data.is_main_goal,
    )
    db.add(db_goal)
    await db.commit()
    await db.refresh(db_goal)
    return db_goal


@goals_router.delete("/{goal_id}", status_code=204)
async def delete_goal(goal_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    db_goal = result.scalar_one_or_none()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    await db.delete(db_goal)
    await db.commit()
