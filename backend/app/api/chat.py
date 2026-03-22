from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import asyncio
import logging
from app.core.database import get_db
from app.models.models import Agent, Message, Task, TaskStatus, AgentLog
from app.services.llm_service import llm_service
from app.services.workspace_manager import workspace_manager
from app.services.openclaw_gateway import openclaw

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    content: str
    is_from_user: bool = True


class ChatMessageResponse(BaseModel):
    id: int
    agent_id: int
    sender: str
    content: str
    is_from_user: bool
    created_at: datetime

    class Config:
        from_attributes = True


async def sync_openclaw_messages(
    agent_id: int, agent_name: str, db: AsyncSession, max_wait: int = 60
):
    """Sync messages from OpenClaw session to local DB"""
    session_key = f"agent:{agent_name.lower()}:main"
    logger.info(f"Starting to sync messages for {session_key}")

    for attempt in range(max_wait):
        await asyncio.sleep(1)
        try:
            history = await openclaw.get_chat_history(session_key, limit=50)
            logger.info(f"Attempt {attempt}: Fetched {type(history)} from OpenClaw")

            if history is None:
                logger.info("History is None")
                continue
            elif not isinstance(history, dict):
                logger.info(f"History is not a dict: {type(history)}")
                continue

            logger.info(f"History keys: {history.keys()}")

            messages = history.get("messages", [])
            logger.info(f"Found {len(messages)} messages in history")

            if len(messages) > 0:
                logger.info(
                    f"First message role: {messages[0].get('role')}, content: {str(messages[0].get('content', []))[:100]}"
                )

            if messages and len(messages) > 0:
                synced_count = 0
                new_agent_texts = []
                for msg_data in messages:
                    if not isinstance(msg_data, dict):
                        continue

                    role = msg_data.get("role", "")
                    content_list = msg_data.get("content", [])
                    sender_label = msg_data.get("senderLabel", "")

                    # Extract text content from content array
                    text_content = ""
                    for item in content_list:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                text_content = item.get("text", "")
                                break
                            elif item.get("type") == "toolCall":
                                tool_name = item.get("name", "unknown")
                                args_str = str(item.get("arguments", {}))[:100]
                                text_content = (
                                    f"[Tool Call: {tool_name} - {args_str}...]"
                                )
                                break
                            elif item.get("type") == "toolResult":
                                result_text = item.get("content", "")
                                if (
                                    isinstance(result_text, list)
                                    and len(result_text) > 0
                                ):
                                    result_text = result_text[0].get("text", "")[:100]
                                text_content = (
                                    f"[Tool Result: {str(result_text)[:100]}...]"
                                )
                                break

                    if not text_content:
                        continue

                    # Determine sender and is_from_user
                    if role == "user":
                        sender = sender_label or "user"
                        is_from_user = True
                    else:
                        sender = agent_name
                        is_from_user = False
                        if text_content:
                            new_agent_texts.append(text_content)

                    existing = await db.execute(
                        select(Message).where(
                            Message.agent_id == agent_id,
                            Message.content == text_content,
                        )
                    )
                    existing_msg = existing.first()
                    if not existing_msg:
                        new_msg = Message(
                            agent_id=agent_id,
                            sender=str(sender),
                            content=text_content,
                            is_from_user=bool(is_from_user),
                        )
                        db.add(new_msg)
                        synced_count += 1
                        logger.info(
                            f"Adding message from {sender}: {text_content[:50]}..."
                        )

                if synced_count > 0:
                    await db.commit()
                    logger.info(
                        f"Synced {synced_count} new messages from OpenClaw for {agent_name}"
                    )

                    # Check task completion after syncing new messages
                    if new_agent_texts:
                        await check_task_completion_for_agent(
                            agent_id, agent_name, db, new_agent_texts
                        )

                    return True
        except Exception as e:
            logger.error(f"Error syncing OpenClaw messages: {e}")
            import traceback

            traceback.print_exc()

    return False


async def check_task_completion_for_agent(
    agent_id: int, agent_name: str, db: AsyncSession, new_messages: list[str]
):
    """Check if any IN_PROGRESS tasks should be moved to REVIEW based on new agent messages"""
    try:
        from app.models.models import Task, TaskStatus, AgentLog

        completion_keywords = [
            "task completed",
            "task complete",
            "completed successfully",
            "done!",
            "done.",
            "finished!",
            "finished.",
            "all done",
            "completed!",
            "ready!",
            "successfully",
            "task done",
            "execution complete",
            "executed perfectly",
            "completed the task",
            "finished the task",
            "the task is complete",
            "task is done",
            "no further action",
            "no more tasks",
            "nothing else",
        ]

        messages_text = "\n\n".join(new_messages[-5:])
        messages_lower = messages_text.lower()

        tasks_result = await db.execute(
            select(Task).where(
                Task.agent_id == agent_id, Task.status == TaskStatus.IN_PROGRESS
            )
        )
        tasks = tasks_result.scalars().all()

        for task in tasks:
            task_keywords = task.title.lower().split()[:3]
            task_context = " ".join(task_keywords)

            keyword_found = any(kw in messages_lower for kw in completion_keywords)

            if keyword_found:
                print(f"Completion keyword found for task {task.id}: {task.title}")

                result = await llm_service.generate(
                    [
                        {
                            "role": "user",
                            "content": f"""Task: {task.title}
Description: {task.description or "None"}
Agent messages:
{messages_text}

Did the agent complete this task? Respond: YES or NO and brief reason""",
                        }
                    ],
                    system_prompt="You are a task completion checker. Answer YES if the task is complete, NO if not.",
                    temperature=0.1,
                    max_tokens=100,
                )

                if result and result.strip().upper().startswith("YES"):
                    task.status = TaskStatus.REVIEW
                    log = AgentLog(
                        agent_id=agent_id,
                        action="TASK_AUTO_REVIEW",
                        details=f"Task '{task.title}' auto-moved to review from chat sync",
                    )
                    db.add(log)
                    await db.commit()
                    print(f"Task {task.id} auto-moved to REVIEW from chat sync")

                    # Update TASKS.md
                    from app.api.tasks import _update_agent_tasks_md

                    asyncio.create_task(_update_agent_tasks_md(agent_id, None))

    except Exception as e:
        print(f"Error in check_task_completion_for_agent: {e}")
        import traceback

        traceback.print_exc()


@router.get("/{agent_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    agent_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    sync: bool = False,
):
    """Get chat messages for an agent. Optionally sync from OpenClaw first (non-blocking)."""
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = agent_result.scalar_one_or_none()

    if sync and agent:
        asyncio.create_task(sync_openclaw_messages(agent_id, str(agent.name), db))

    result = await db.execute(
        select(Message)
        .where(Message.agent_id == agent_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return list(reversed(messages))


@router.post("/{agent_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    agent_id: int, message: ChatMessage, db: AsyncSession = Depends(get_db)
):
    """Send a message to an agent via OpenClaw Gateway"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Save user message to local DB for UI display
    user_message = Message(
        agent_id=agent_id,
        sender="user",
        content=message.content,
        is_from_user=True,
    )
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    # Send message to OpenClaw agent
    openclaw_result = await openclaw.send_chat_message(
        agent_id=str(agent.name),
        message=message.content,
        is_from_user=True,
    )

    log = AgentLog(
        agent_id=agent_id,
        action="CHAT_MESSAGE",
        details=f"User: {message.content[:50]}... | Sent to OpenClaw agent",
    )
    db.add(log)
    await db.commit()

    # Sync messages from OpenClaw in background
    asyncio.create_task(sync_openclaw_messages(agent_id, str(agent.name), db))

    await db.refresh(user_message)
    return user_message


@router.delete("/{agent_id}/messages")
async def clear_chat(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Clear all chat messages for an agent"""
    result = await db.execute(select(Message).where(Message.agent_id == agent_id))
    messages = result.scalars().all()
    for msg in messages:
        await db.delete(msg)
    await db.commit()
    return {"message": "Chat cleared"}


@router.get("/{agent_id}/status")
async def get_agent_chat_status(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Get chat status for an agent including unread count and last message"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    messages_result = await db.execute(
        select(Message)
        .where(Message.agent_id == agent_id)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    last_message = messages_result.scalar_one_or_none()

    total_messages = await db.execute(
        select(Message).where(Message.agent_id == agent_id)
    )
    message_count = len(total_messages.scalars().all())

    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "message_count": message_count,
        "last_message": {
            "content": last_message.content[:100] if last_message else None,
            "sender": last_message.sender if last_message else None,
            "created_at": last_message.created_at if last_message else None,
        },
    }
