from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    OVERHEATED = "overheated"
    OFFLINE = "offline"


class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class AgentCreate(BaseModel):
    name: str
    role: str
    chief_id: Optional[int] = None
    team_id: Optional[int] = None
    model: Optional[str] = None
    heartbeat_frequency: int = 15
    active_hours_start: str = "00:00"
    active_hours_end: str = "23:59"
    can_spawn_subagents: bool = False


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    chief_id: Optional[int] = None
    team_id: Optional[int] = None
    model: Optional[str] = None
    status: Optional[AgentStatus] = None
    heartbeat_frequency: Optional[int] = None
    active_hours_start: Optional[str] = None
    active_hours_end: Optional[str] = None
    can_spawn_subagents: Optional[bool] = None
    failure_count: Optional[int] = None


class AgentResponse(BaseModel):
    id: int
    name: str
    role: str
    chief_id: Optional[int]
    team_id: Optional[int]
    model: Optional[str]
    status: AgentStatus
    heartbeat_frequency: int
    active_hours_start: str
    active_hours_end: str
    can_spawn_subagents: bool
    failure_count: int
    tasks_completed: int
    tasks_failed: int
    total_working_time_minutes: int
    created_at: datetime
    updated_at: datetime
    warnings: Optional[List[str]] = None
    rate_limited: Optional[bool] = None
    retry_seconds: Optional[int] = None

    class Config:
        from_attributes = True


class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class TeamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    color: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    goal_id: Optional[int] = None
    agent_id: Optional[int] = None
    priority: int = 1
    depends_on: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    agent_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    priority: Optional[int] = None
    move_reason: Optional[str] = None
    depends_on: Optional[int] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    goal_id: Optional[int]
    agent_id: Optional[int]
    status: TaskStatus
    priority: int
    move_reason: Optional[str]
    depends_on: Optional[int]
    dependency_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    is_main_goal: bool = False


class GoalResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    is_main_goal: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    sender_id: int
    receiver_id: Optional[int] = None
    content: str
    action_type: Optional[str] = None
    sender_agent_id: Optional[int] = None
    recipient_agent_id: Optional[int] = None


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


class MeetingResponse(BaseModel):
    id: int
    title: str
    meeting_type: str
    transcript: Optional[str]
    briefing: Optional[str]
    audio_url: Optional[str]
    created_at: datetime
    duration_minutes: Optional[int]

    class Config:
        from_attributes = True


class AgentLogResponse(BaseModel):
    id: int
    agent_id: Optional[int]
    action: str
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_agents: int
    active_agents: int
    idle_agents: int
    overheated_agents: int
    total_tasks: int
    backlog_tasks: int
    in_progress_tasks: int
    review_tasks: int
    done_tasks: int
    total_teams: int


class FiveFileContent(BaseModel):
    soul: str
    identity: str
    agents: str
    memory: str
    user: str
    heartbeat: str = ""
