"""
SQLAlchemy ORM Models for OpenClaw Mission Control

This module defines all database tables and their relationships using SQLAlchemy 2.0.
Each class represents a table, with columns defined as class attributes.

Database Design Principles:
---------------------------
1. Async Support: All models use SQLAlchemy 2.0 async patterns
2. Type Safety: Type hints on all columns and relationships
3. Relationships: Explicit relationship definitions with back_populates
4. Timestamps: Automatic created_at/updated_at on all models
5. Constraints: Unique constraints where appropriate (e.g., agent names)

Model Overview:
---------------
- Team: Agent teams/groups
- Agent: AI agents with hierarchy support
- Task: Work items with status tracking
- Goal: High-level objectives
- Message: Chat messages
- Meeting: Standup meetings
- AgentLog: Audit log of agent actions
- Settings: Key-value configuration storage

Relationships:
--------------
- Team <-> Agent: One-to-Many (team has many agents)
- Agent <-> Task: One-to-Many (agent has many tasks)
- Agent <-> Agent: Self-referential (chief/subordinate hierarchy)
- Task <-> Goal: Many-to-One (tasks belong to goals)
- Agent <-> Message: One-to-Many (agent has many messages)
- Agent <-> AgentLog: One-to-Many (agent has many logs)

Extension Points:
-----------------
To add new models:

1. Create class inheriting from Base
2. Define __tablename__
3. Add columns with appropriate types
4. Define relationships with foreign keys
5. Import in database.py for table creation

Example:
    class Project(Base):
        __tablename__ = "projects"

        id = Column(Integer, primary_key=True)
        name = Column(String(100), nullable=False)
        description = Column(Text)

        # Relationships
        tasks = relationship("Task", back_populates="project")

To add fields to existing models:
1. Add column to model class
2. Create migration (or let tables auto-create in dev)
3. Update Pydantic schemas
4. Update API endpoints

See Also:
---------
- app/core/database.py - Database connection and table creation
- app/models/schemas.py - Pydantic schemas for validation
- https://docs.sqlalchemy.org/en/20/orm/
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class AgentStatus(str, enum.Enum):
    """
    Agent operational status.

    Agents cycle through these states during their lifecycle:
    - ACTIVE: Heartbeat enabled, agent periodically checks tasks
    - IDLE: Heartbeat disabled, agent dormant
    - OVERHEATED: Agent encountered errors, needs reset
    - OFFLINE: Agent unreachable (future: heartbeat monitoring)

    State Transitions:
        Created -> Idle (default)
        Idle -> Active (on start)
        Active -> Idle (on stop)
        Any -> Overheated (on error)
        Overheated -> Idle (on reset)

    Example:
        >>> agent = Agent(name="CEO", status=AgentStatus.ACTIVE)
        >>> print(agent.status)
        'active'
    """

    ACTIVE = "active"
    """Agent is running and processing tasks."""

    IDLE = "idle"
    """Agent is stopped, waiting for activation."""

    OVERHEATED = "overheated"
    """Agent encountered errors, needs manual reset."""

    OFFLINE = "offline"
    """Agent is unreachable (not currently used)."""


class TaskStatus(str, enum.Enum):
    """
    Task workflow status.

    Tasks follow a Kanban-style workflow:
    - BACKLOG: Task waiting to be started
    - IN_PROGRESS: Agent actively working on task
    - REVIEW: Task completed, awaiting approval
    - DONE: Task approved and complete

    State Transitions:
        BACKLOG -> IN_PROGRESS (auto on heartbeat or manual)
        IN_PROGRESS -> REVIEW (auto after timeout or manual)
        REVIEW -> DONE (manual approval only)
        Any -> BACKLOG (on unassign)

    Example:
        >>> task = Task(title="Build API", status=TaskStatus.BACKLOG)
        >>> task.status = TaskStatus.IN_PROGRESS
    """

    BACKLOG = "backlog"
    """Task waiting in backlog."""

    IN_PROGRESS = "in_progress"
    """Task currently being worked on."""

    REVIEW = "review"
    """Task completed, awaiting review."""

    DONE = "done"
    """Task approved and complete."""


class Team(Base):
    """
    Represents a team of agents.

    Teams provide organizational structure and can be used to:
    - Group related agents (e.g., Engineering, Design)
    - Assign colors for visual distinction
    - Filter views in the UI
    - Broadcast messages to all team members

    Attributes:
        id: Primary key
        name: Unique team name (displayed in UI)
        description: Optional team description
        color: Hex color code for UI styling (e.g., "#4ade80")
        created_at: Timestamp when team was created
        updated_at: Timestamp of last update
        agents: Relationship to agents in this team

    Example:
        >>> team = Team(
        ...     name="Engineering",
        ...     description="Backend development team",
        ...     color="#3b82f6"
        ... )

    Database Schema:
        Table: teams
        - id: INTEGER PRIMARY KEY
        - name: VARCHAR(100) UNIQUE NOT NULL
        - description: TEXT
        - color: VARCHAR(7)
        - created_at: DATETIME
        - updated_at: DATETIME
    """

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    """Primary key, auto-incremented."""

    name = Column(String(100), unique=True, nullable=False)
    """Team name, must be unique. Max 100 characters."""

    description = Column(Text, nullable=True)
    """Optional team description. Can be long text."""

    color = Column(String(7), nullable=True)
    """
    Hex color code for UI styling.
    
    Format: #RRGGBB (e.g., "#4ade80" for green)
    Used for team badges, borders, and visual distinction.
    """

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    """UTC timestamp when team was created. Auto-set on creation."""

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    """UTC timestamp of last update. Auto-updated on changes."""

    agents = relationship("Agent", back_populates="team")
    """
    Relationship to agents belonging to this team.
    
    Access: team.agents -> List[Agent]
    """


class Agent(Base):
    """
    Represents an AI agent in the system.

    Agents are the core entity, representing autonomous workers that can:
    - Execute tasks
    - Send/receive messages
    - Report to other agents (hierarchy)
    - Spawn sub-agents (if enabled)
    - Run on a schedule (heartbeat)

    Key Features:
    - Hierarchical: Agents can report to other agents via chief_id
    - Team-based: Agents belong to teams
    - Scheduled: Heartbeat frequency controls activation
    - Stateful: Tracks status, failure count, working hours
    - Configurable: Can spawn sub-agents, active hours, etc.

    Attributes:
        id: Primary key
        name: Unique agent identifier (also used by OpenClaw)
        role: Job title/function
        chief_id: ID of manager (self-reference for hierarchy)
        team_id: ID of team membership
        model: LLM model used by agent
        status: Current operational status
        heartbeat_frequency: Minutes between heartbeats (0 = disabled)
        active_hours_start/end: Daily working window
        can_spawn_subagents: Permission to create sub-agents
        failure_count: Consecutive task failures
        tasks: Relationship to assigned tasks
        messages: Relationship to chat messages
        logs: Relationship to activity logs

    Example:
        >>> agent = Agent(
        ...     name="Developer",
        ...     role="Senior Developer",
        ...     team_id=1,
        ...     chief_id=1,  # Reports to CEO
        ...     heartbeat_frequency=15,
        ...     can_spawn_subagents=False
        ... )

    Database Schema:
        Table: agents
        - id: INTEGER PRIMARY KEY
        - name: VARCHAR(100) UNIQUE NOT NULL
        - role: VARCHAR(100) NOT NULL
        - chief_id: INTEGER FOREIGN KEY (agents.id)
        - team_id: INTEGER FOREIGN KEY (teams.id)
        - model: VARCHAR(100)
        - status: VARCHAR(20) DEFAULT 'idle'
        - heartbeat_frequency: INTEGER DEFAULT 15
        - active_hours_start: VARCHAR(10) DEFAULT '00:00'
        - active_hours_end: VARCHAR(10) DEFAULT '23:59'
        - can_spawn_subagents: BOOLEAN DEFAULT FALSE
        - failure_count: INTEGER DEFAULT 0
        - created_at: DATETIME
        - updated_at: DATETIME
    """

    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    """Primary key, auto-incremented."""

    name = Column(String(100), unique=True, nullable=False)
    """
    Unique agent name.
    
    IMPORTANT: This is used as the identifier in OpenClaw Gateway.
    Cannot be changed after creation (would break OpenClaw references).
    
    Best practices:
    - Use clear, descriptive names (e.g., "API_Developer")
    - No spaces (use underscores)
    - Keep under 50 characters
    """

    role = Column(String(100), nullable=False)
    """
    Job title or function.
    
    Examples: "CEO", "Developer", "Designer", "QA Engineer"
    Used in IDENTITY.md generation and UI displays.
    """

    chief_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    """
    ID of manager/supervisor (self-referential foreign key).
    
    Creates agent hierarchy (CEO -> CTO -> Developer -> Junior Dev).
    Null means top-level (no manager).
    
    Access: agent.chief -> Agent (manager)
           agent.subordinates -> List[Agent] (reports)
    """

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    """Team membership. Null means unassigned."""

    model = Column(String(100), nullable=True)
    """
    LLM model used by this agent.
    
    Examples: "gpt-4", "gpt-3.5-turbo", "claude-3"
    Can override default model from settings.
    """

    status = Column(SQLEnum(AgentStatus), default=AgentStatus.IDLE)
    """Current operational status (active, idle, overheated, offline)."""

    heartbeat_frequency = Column(Integer, default=15)
    """
    Minutes between heartbeats.
    
    Heartbeats trigger task checking:
    - 0 = Disabled (manual activation only)
    - 15 = Every 15 minutes (default)
    - 60 = Every hour
    
    Set via agent start/stop actions.
    """

    active_hours_start = Column(String(10), default="00:00")
    """
    Daily active hours start time.
    
    Format: "HH:MM" in 24-hour format.
    Example: "09:00" for 9 AM start.
    
    Currently informational (future: restrict heartbeat to active hours).
    """

    active_hours_end = Column(String(10), default="23:59")
    """
    Daily active hours end time.
    
    Format: "HH:MM" in 24-hour format.
    Example: "17:00" for 5 PM end.
    """

    can_spawn_subagents = Column(Boolean, default=False)
    """
    Permission to create sub-agents.
    
    If True, agent can create child agents via OpenClaw.
    Used for hierarchical agent management.
    """

    failure_count = Column(Integer, default=0)
    """
    Consecutive task failures.
    
    Incremented on task failures, reset on success.
    If exceeds threshold (e.g., 3), agent status set to OVERHEATED.
    """

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    """UTC timestamp when agent was created."""

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    """UTC timestamp of last update."""

    # Relationships
    team = relationship("Team", back_populates="agents")
    """Team this agent belongs to."""

    chief = relationship("Agent", remote_side=[id], back_populates="subordinates")
    """Manager/supervisor of this agent."""

    subordinates = relationship("Agent", back_populates="chief")
    """Agents that report to this agent."""

    tasks = relationship("Task", back_populates="agent", foreign_keys="Task.agent_id")
    """Tasks assigned to this agent."""

    messages = relationship("Message", back_populates="agent")
    """Chat messages sent/received by this agent."""

    logs = relationship("AgentLog", back_populates="agent")
    """Activity logs for this agent."""


class Task(Base):
    """
    Represents a work item or assignment.

    Tasks are the primary unit of work in the system. They:
    - Track status through workflow (backlog → in_progress → review → done)
    - Can be assigned to agents
    - Belong to goals for organization
    - Have priority levels
    - Track move reasons for audit

    Workflow:
    ---------
    1. Created in BACKLOG status
    2. Automatically moved to IN_PROGRESS on heartbeat
    3. Agent works on task
    4. Moved to REVIEW on completion or timeout
    5. Human reviews and moves to DONE

    Attributes:
        id: Primary key
        title: Task name/display
        description: Detailed requirements
        goal_id: Parent goal (optional)
        agent_id: Assigned agent (optional)
        status: Current workflow status
        priority: 1-5 (1 = highest)
        move_reason: Why status changed (audit)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        completed_at: When moved to DONE

    Example:
        >>> task = Task(
        ...     title="Build API endpoint",
        ...     description="Create FastAPI endpoint for users",
        ...     agent_id=1,
        ...     priority=2
        ... )

    Database Schema:
        Table: tasks
        - id: INTEGER PRIMARY KEY
        - title: VARCHAR(200) NOT NULL
        - description: TEXT
        - goal_id: INTEGER FOREIGN KEY (goals.id)
        - agent_id: INTEGER FOREIGN KEY (agents.id)
        - status: VARCHAR(20) DEFAULT 'backlog'
        - priority: INTEGER DEFAULT 1
        - move_reason: TEXT
        - created_at: DATETIME
        - updated_at: DATETIME
        - completed_at: DATETIME
    """

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    """Primary key, auto-incremented."""

    title = Column(String(200), nullable=False)
    """Task title. Max 200 characters."""

    description = Column(Text, nullable=True)
    """Detailed task description. Can include requirements, acceptance criteria."""

    goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
    """Parent goal. Null means unassigned to any goal."""

    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    """Assigned agent. Null means unassigned (in backlog)."""

    status = Column(SQLEnum(TaskStatus), default=TaskStatus.BACKLOG)
    """Current status in workflow."""

    priority = Column(Integer, default=1)
    """
    Task priority 1-5.
    
    1 = Highest (Critical)
    2 = High
    3 = Medium (default)
    4 = Low
    5 = Lowest
    
    Used for task ordering in UI.
    """

    move_reason = Column(Text, nullable=True)
    """
    Reason for last status change.
    
    Examples: "Starting work", "Completed successfully", "Needs review"
    Used for audit trail and understanding workflow.
    """

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    """UTC timestamp when task was created."""

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    """UTC timestamp of last update."""

    completed_at = Column(DateTime, nullable=True)
    """UTC timestamp when task moved to DONE status."""

    agent = relationship("Agent", back_populates="tasks", foreign_keys=[agent_id])
    """Agent assigned to this task."""

    goal = relationship("Goal", back_populates="tasks")
    """Goal this task belongs to."""


class Goal(Base):
    """
    Represents a high-level objective or milestone.

    Goals help organize tasks into larger initiatives.
    Only one goal can be "main" at a time.

    Attributes:
        id: Primary key
        title: Goal name
        description: Detailed description
        is_main_goal: Whether this is the current main goal
        tasks: Relationship to tasks

    Example:
        >>> goal = Goal(
        ...     title="Q1 Product Launch",
        ...     description="Complete product MVP for Q1 launch",
        ...     is_main_goal=True
        ... )

    Database Schema:
        Table: goals
        - id: INTEGER PRIMARY KEY
        - title: VARCHAR(200) NOT NULL
        - description: TEXT
        - is_main_goal: BOOLEAN DEFAULT FALSE
        - created_at: DATETIME
        - updated_at: DATETIME
    """

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    """Primary key, auto-incremented."""

    title = Column(String(200), nullable=False)
    """Goal title. Max 200 characters."""

    description = Column(Text, nullable=True)
    """Detailed description of the goal."""

    is_main_goal = Column(Boolean, default=False)
    """
    Whether this is the current main goal.
    
    Only one goal should be main at a time.
    Setting a new main goal automatically unsets previous.
    Used for priority/focus in UI.
    """

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    """UTC timestamp when goal was created."""

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    """UTC timestamp of last update."""

    tasks = relationship("Task", back_populates="goal")
    """Tasks associated with this goal."""


class Message(Base):
    """
    Represents a chat message.

    Messages can be:
    - From user to agent
    - From agent to user (response)
    - System messages (notifications)
    - Agent-to-agent messages (if messaging extension added)

    Attributes:
        id: Primary key
        agent_id: Agent in conversation
        sender: Display name of sender
        content: Message text
        is_from_user: Whether message is from human user
        created_at: Timestamp

    Example:
        >>> msg = Message(
        ...     agent_id=1,
        ...     sender="user",
        ...     content="Hello!",
        ...     is_from_user=True
        ... )

    Database Schema:
        Table: messages
        - id: INTEGER PRIMARY KEY
        - agent_id: INTEGER FOREIGN KEY (agents.id) NOT NULL
        - sender: VARCHAR(50) NOT NULL
        - content: TEXT NOT NULL
        - is_from_user: BOOLEAN DEFAULT FALSE
        - created_at: DATETIME
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    """Primary key, auto-incremented."""

    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    """Agent this message is associated with."""

    sender = Column(String(50), nullable=False)
    """Display name of sender (e.g., "user", "CEO", "system")."""

    content = Column(Text, nullable=False)
    """Message content. Can be long text."""

    is_from_user = Column(Boolean, default=False)
    """
    Whether message is from human user.
    
    True = From user via UI
    False = From agent or system
    """

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    """UTC timestamp when message was sent."""

    agent = relationship("Agent")
    """Agent in this conversation."""


class Meeting(Base):
    """
    Represents a meeting or standup.

    Meetings are AI-generated conversations between agents.
    Currently supports standup meetings.

    Attributes:
        id: Primary key
        title: Meeting title
        meeting_type: Type (standup, etc.)
        transcript: Full conversation text
        briefing: Executive summary
        audio_url: TTS audio file URL (future)
        duration_minutes: Meeting length
        created_at: Timestamp

    Example:
        >>> meeting = Meeting(
        ...     title="Daily Standup - Jan 15",
        ...     meeting_type="standup",
        ...     transcript="CEO: Good morning...",
        ...     briefing="All projects on track",
        ...     duration_minutes=15
        ... )

    Database Schema:
        Table: meetings
        - id: INTEGER PRIMARY KEY
        - title: VARCHAR(200) NOT NULL
        - meeting_type: VARCHAR(50) DEFAULT 'standup'
        - transcript: TEXT
        - briefing: TEXT
        - audio_url: VARCHAR(500)
        - duration_minutes: INTEGER
        - created_at: DATETIME
    """

    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    """Primary key, auto-incremented."""

    title = Column(String(200), nullable=False)
    """Meeting title."""

    meeting_type = Column(String(50), default="standup")
    """Type of meeting (standup, sprint_review, etc.)."""

    transcript = Column(Text, nullable=True)
    """Full conversation transcript."""

    briefing = Column(Text, nullable=True)
    """Executive summary of meeting."""

    audio_url = Column(String(500), nullable=True)
    """URL to TTS audio file (future feature)."""

    duration_minutes = Column(Integer, nullable=True)
    """Meeting duration in minutes."""

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    """UTC timestamp when meeting was created."""


class AgentLog(Base):
    """
    Audit log of agent actions.

    Tracks all significant events for agents:
    - Created, started, stopped, deleted
    - Task assignments and completions
    - Heartbeats and auto-assignments
    - Errors and rate limits

    This provides an audit trail for debugging and monitoring.

    Attributes:
        id: Primary key
        agent_id: Agent involved (null for system events)
        action: Action type (CREATED, STARTED, etc.)
        details: Additional information
        created_at: Timestamp

    Example:
        >>> log = AgentLog(
        ...     agent_id=1,
        ...     action="TASK_COMPLETED",
        ...     details="Task 'Build API' completed in 30 minutes"
        ... )

    Database Schema:
        Table: agent_logs
        - id: INTEGER PRIMARY KEY
        - agent_id: INTEGER FOREIGN KEY (agents.id)
        - action: VARCHAR(100) NOT NULL
        - details: TEXT
        - created_at: DATETIME
    """

    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    """Primary key, auto-incremented."""

    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    """
    Agent involved in this action.
    
    Null for system-wide events (e.g., scheduler errors).
    """

    action = Column(String(100), nullable=False)
    """
    Action type.
    
    Common actions:
    - CREATED: Agent created
    - STARTED: Agent started
    - STOPPED: Agent stopped
    - RESET: Agent reset
    - DELETED: Agent deleted
    - TASK_STARTED: Task execution began
    - TASK_COMPLETED: Task finished
    - HEARTBEAT_AUTO_ASSIGN: Tasks auto-assigned
    - RATE_LIMITED: Rate limit hit
    """

    details = Column(Text, nullable=True)
    """Additional details about the action."""

    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    """UTC timestamp when action occurred."""

    agent = relationship("Agent")
    """Agent this log entry is for."""


class Settings(Base):
    """
    Key-value configuration storage.

    Simple settings system for storing configuration values
    that need to persist but don't warrant a full column.

    Attributes:
        id: Primary key
        key: Setting name (unique)
        value: Setting value
        updated_at: Last update timestamp

    Example:
        >>> setting = Settings(
        ...     key="theme",
        ...     value="dark"
        ... )

    Database Schema:
        Table: settings
        - id: INTEGER PRIMARY KEY
        - key: VARCHAR(100) UNIQUE NOT NULL
        - value: TEXT
        - updated_at: DATETIME
    """

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    """Primary key, auto-incremented."""

    key = Column(String(100), unique=True, nullable=False)
    """Setting key/name. Must be unique."""

    value = Column(Text, nullable=True)
    """Setting value. Can be any text (JSON, string, etc.)."""

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    """UTC timestamp of last update."""
