from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.core.database import get_db
from app.models.models import Meeting, Agent, Task
from app.models.schemas import MeetingResponse
from app.services.llm_service import llm_service
from app.services.workspace_manager import workspace_manager
from datetime import datetime, timezone

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("/", response_model=List[MeetingResponse])
async def list_meetings(
    meeting_type: str = None, limit: int = 50, db: AsyncSession = Depends(get_db)
):
    query = select(Meeting)
    if meeting_type:
        query = query.where(Meeting.meeting_type == meeting_type)
    query = query.order_by(Meeting.created_at.desc()).limit(limit)

    result = await db.execute(query)
    meetings = result.scalars().all()
    return meetings


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.post("/standup", response_model=MeetingResponse, status_code=201)
async def run_standup(db: AsyncSession = Depends(get_db)):
    agents_result = await db.execute(
        select(Agent).where(Agent.role.in_(["COO", "CFO", "CTO", "CMO", "Chief"]))
    )
    agents = agents_result.scalars().all()

    if not agents:
        raise HTTPException(
            status_code=400, detail="No C-suite agents found for standup"
        )

    standup_prompt = """You are participating in a daily executive standup. Each agent shares:
1. What they accomplished yesterday
2. What they're working on today
3. Any blockers they face

Generate a brief standup report for each agent role."""

    agent_reports = []
    for agent in agents:
        five_files = workspace_manager.read_all(agent.name)
        if five_files:
            system_prompt = five_files.soul + "\n\n" + five_files.agents
            response = await llm_service.generate(
                messages=[{"role": "user", "content": standup_prompt}],
                system_prompt=system_prompt,
            )
            agent_reports.append(
                f"## {agent.role}: {agent.name}\n{response or 'No report'}"
            )

    transcript = "\n\n".join(agent_reports)

    briefing_prompt = """Summarize the following standup into a concise briefing for the CEO:
What are the top priorities?
What are the main blockers?
What decisions need to be made?"""

    briefing = await llm_service.generate(
        messages=[{"role": "user", "content": transcript + "\n\n" + briefing_prompt}]
    )

    db_meeting = Meeting(
        title=f"Daily Standup - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        meeting_type="standup",
        transcript=transcript,
        briefing=briefing,
    )
    db.add(db_meeting)
    await db.commit()
    await db.refresh(db_meeting)

    return db_meeting


@router.get("/{meeting_id}/transcript")
async def get_transcript(meeting_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"transcript": meeting.transcript, "briefing": meeting.briefing}
