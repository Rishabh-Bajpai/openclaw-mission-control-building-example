from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.models import Team
from app.models.schemas import TeamCreate, TeamUpdate, TeamResponse

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/", response_model=List[TeamResponse])
async def list_teams(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).order_by(Team.name))
    teams = result.scalars().all()
    return teams


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(team_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.post("/", response_model=TeamResponse, status_code=201)
async def create_team(team: TeamCreate, db: AsyncSession = Depends(get_db)):
    db_team = Team(name=team.name, description=team.description, color=team.color)
    db.add(db_team)
    await db.commit()
    await db.refresh(db_team)
    return db_team


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int, team_update: TeamUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Team).where(Team.id == team_id))
    db_team = result.scalar_one_or_none()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team_update.name is not None:
        db_team.name = team_update.name
    if team_update.description is not None:
        db_team.description = team_update.description
    if team_update.color is not None:
        db_team.color = team_update.color

    await db.commit()
    await db.refresh(db_team)
    return db_team


@router.delete("/{team_id}", status_code=204)
async def delete_team(team_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team).where(Team.id == team_id))
    db_team = result.scalar_one_or_none()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    await db.delete(db_team)
    await db.commit()
