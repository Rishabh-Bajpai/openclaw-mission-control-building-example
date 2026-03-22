from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.models.models import Message, Agent, AgentLog

router = APIRouter(prefix="/messages", tags=["messages"])


class MessageCreate(BaseModel):
    agent_id: int
    sender: str
    content: str


class MessageResponse(BaseModel):
    id: int
    agent_id: int
    sender: str
    content: str
    is_from_user: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[MessageResponse])
async def list_messages(
    agent_id: Optional[int] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    query = select(Message)
    if agent_id:
        query = query.where(Message.agent_id == agent_id)
    query = query.order_by(Message.created_at.desc()).limit(limit)

    result = await db.execute(query)
    messages = result.scalars().all()
    return list(reversed(messages))


@router.post("/", response_model=MessageResponse, status_code=201)
async def send_message(message_data: MessageCreate, db: AsyncSession = Depends(get_db)):
    agent_result = await db.execute(
        select(Agent).where(Agent.id == message_data.agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=400, detail="Agent not found")

    db_message = Message(
        agent_id=message_data.agent_id,
        sender=message_data.sender,
        content=message_data.content,
        is_from_user=False,
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)

    return db_message
