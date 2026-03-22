from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.models import AgentLog
from app.models.schemas import AgentLogResponse

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=List[AgentLogResponse])
async def list_logs(
    agent_id: int = None,
    action: str = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    query = select(AgentLog)
    if agent_id:
        query = query.where(AgentLog.agent_id == agent_id)
    if action:
        query = query.where(AgentLog.action == action)
    query = query.order_by(AgentLog.created_at.desc()).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()
    return logs
