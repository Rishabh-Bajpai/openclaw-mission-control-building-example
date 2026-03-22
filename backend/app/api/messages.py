from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
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
    sender_agent_id: Optional[int] = None
    recipient_agent_id: Optional[int] = None
    message_type: str = "direct"


class MessageResponse(BaseModel):
    id: int
    agent_id: int
    sender: str
    content: str
    is_from_user: bool
    sender_agent_id: Optional[int] = None
    recipient_agent_id: Optional[int] = None
    message_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AgentMessageCreate(BaseModel):
    content: str
    message_type: str = "direct"


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
        sender_agent_id=message_data.sender_agent_id,
        recipient_agent_id=message_data.recipient_agent_id,
        message_type=message_data.message_type,
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)

    return db_message


@router.post(
    "/agent/{sender_agent_id}/to/{recipient_agent_id}",
    response_model=MessageResponse,
    status_code=201,
)
async def send_agent_message(
    sender_agent_id: int,
    recipient_agent_id: int,
    message_data: AgentMessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a direct message from one agent to another.
    """
    sender_result = await db.execute(select(Agent).where(Agent.id == sender_agent_id))
    sender = sender_result.scalar_one_or_none()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender agent not found")

    recipient_result = await db.execute(
        select(Agent).where(Agent.id == recipient_agent_id)
    )
    recipient = recipient_result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient agent not found")

    db_message = Message(
        agent_id=recipient_agent_id,
        sender=sender.name,
        content=message_data.content,
        is_from_user=False,
        sender_agent_id=sender_agent_id,
        recipient_agent_id=recipient_agent_id,
        message_type=message_data.message_type,
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)

    return db_message


@router.get("/agent/{agent_id}", response_model=List[MessageResponse])
async def get_agent_messages(
    agent_id: int,
    include_sent: bool = True,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all messages for an agent (received + optionally sent).
    """
    if include_sent:
        query = select(Message).where(
            or_(
                Message.recipient_agent_id == agent_id,
                Message.sender_agent_id == agent_id,
            )
        )
    else:
        query = select(Message).where(Message.recipient_agent_id == agent_id)

    query = query.order_by(Message.created_at.desc()).limit(limit)
    result = await db.execute(query)
    messages = result.scalars().all()
    return list(reversed(messages))


@router.get(
    "/conversation/{agent1_id}/{agent2_id}", response_model=List[MessageResponse]
)
async def get_conversation(
    agent1_id: int,
    agent2_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Get conversation between two agents.
    """
    query = (
        select(Message)
        .where(
            or_(
                and_(
                    Message.sender_agent_id == agent1_id,
                    Message.recipient_agent_id == agent2_id,
                ),
                and_(
                    Message.sender_agent_id == agent2_id,
                    Message.recipient_agent_id == agent1_id,
                ),
            )
        )
        .order_by(Message.created_at)
        .limit(limit)
    )

    result = await db.execute(query)
    messages = result.scalars().all()
    return list(reversed(messages))
