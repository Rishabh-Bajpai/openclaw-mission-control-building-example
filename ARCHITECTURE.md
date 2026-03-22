# System Architecture

This document provides a deep dive into the OpenClaw Mission Control architecture, explaining design decisions, data flows, and component interactions.

## Table of Contents

- [Overview](#overview)
- [System Components](#system-components)
- [Data Flow](#data-flow)
- [Database Design](#database-design)
- [Agent Lifecycle](#agent-lifecycle)
- [Task Management Flow](#task-management-flow)
- [WebSocket Communication](#websocket-communication)
- [Extension Points](#extension-points)

## Overview

OpenClaw Mission Control is a **distributed system** consisting of:

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Browser                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   React UI   │  │  Real-time   │  │   State      │     │
│  │  Components  │  │   Updates    │  │ Management   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                FastAPI Backend                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  REST API Endpoints  │  WebSocket  │  Background Jobs  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Service Layer (Business Logic)               │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │ │
│  │  │ OpenClaw │ │ Workspace│ │  Task    │ │   LLM    │ │ │
│  │  │ Gateway  │ │ Manager  │ │Executor  │ │ Service  │ │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Data Layer (SQLAlchemy ORM)                  │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │ SQL/WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              External Services                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Database    │  │ OpenClaw     │  │   LLM API    │     │
│  │ (SQLite/PG)  │  │  Gateway     │  │  (OpenAI)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## System Components

### Frontend (Next.js 16)

**Architecture Pattern**: Client-Side Rendering with Server Components

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx         # Root layout (Server Component)
│   │   ├── page.tsx           # Home redirect
│   │   ├── agents/            # Agent Studio (Client Component)
│   │   ├── kanban/            # Task board (Client Component)
│   │   ├── chat/              # Chat interface (Client Component)
│   │   └── ...                # Other pages
│   ├── components/            # Shared components
│   │   ├── Sidebar.tsx        # Navigation
│   │   └── LogTerminal.tsx    # Real-time logs
│   └── lib/                   # Utilities
│       ├── api.ts            # API client
│       └── useRateLimit.ts   # Custom hook
```

**Key Design Decisions**:

1. **Client Components** (`'use client'`): Pages with user interaction (forms, drag-and-drop, WebSocket connections)
2. **Server Components** (default): Static pages, layouts, data fetching at build time
3. **State Management**: React hooks (useState, useEffect) + Context API where needed
4. **Styling**: Tailwind CSS v4 for utility-first CSS
5. **Type Safety**: Full TypeScript coverage with interfaces defined in `api.ts`

**Component Communication**:

```typescript
// Parent (Page) -> Child (Component)
<AgentCard 
  agent={agent}                    // Props down
  onStatusChange={handleStatus}  // Callbacks up
/>

// Global State (via API client)
const [agents, setAgents] = useState<Agent[]>([]);
useEffect(() => {
  api.agents.list().then(setAgents);  // Fetch from backend
}, []);
```

### Backend (FastAPI)

**Architecture Pattern**: Layered Architecture with Dependency Injection

```
backend/
├── app/
│   ├── main.py               # Application entry point
│   ├── api/                  # REST API layer
│   │   ├── agents.py        # Agent endpoints
│   │   ├── tasks.py         # Task endpoints
│   │   └── ...              # Other endpoints
│   ├── core/                 # Infrastructure
│   │   ├── database.py      # Database setup
│   │   ├── scheduler.py     # Background jobs
│   │   └── config.py        # Configuration
│   ├── models/               # Data layer
│   │   ├── models.py        # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   └── services/             # Business logic
│       ├── openclaw_gateway.py
│       ├── workspace_manager.py
│       └── ...
```

**Layer Responsibilities**:

1. **API Layer**: HTTP request handling, input validation, output serialization
2. **Service Layer**: Business logic, external integrations, complex operations
3. **Data Layer**: Database models, queries, relationships
4. **Core Layer**: Infrastructure (database connections, scheduler, logging)

**Example Flow**:

```python
# API Layer: Validate input, delegate to service
def create_agent(agent_data: AgentCreate, db: AsyncSession = Depends(get_db)):
    return await agent_service.create(db, agent_data)

# Service Layer: Business logic, multiple operations
def create(self, db, data):
    # 1. Create DB record
    db_agent = Agent(**data)
    db.add(db_agent)
    
    # 2. Create workspace files
    await workspace_manager.create_files(db_agent.name)
    
    # 3. Register with OpenClaw
    await openclaw.create_agent(db_agent.name)
    
    return db_agent
```

### External Integrations

#### OpenClaw Gateway

**Protocol**: WebSocket RPC (Remote Procedure Calls)

```
Mission Control              OpenClaw Gateway
     │                             │
     │  ┌───────────────────────┐  │
     │  │ 1. Connect WebSocket  │  │
     │  │    ws://localhost:18789│ │
     │  └───────────────────────┘  │
     │ ◄─────────────────────────── │
     │                             │
     │  ┌───────────────────────┐  │
     │  │ 2. Send RPC Request     │  │
     │  │ {                     │  │
     │  │   "method": "agents.create",
     │  │   "params": {...}      │  │
     │  │ }                      │  │
     │  └───────────────────────┘  │
     │ ───────────────────────────► │
     │                             │
     │  ┌───────────────────────┐  │
     │  │ 3. Receive Response   │  │
     │  │ {                     │  │
     │  │   "result": {...}      │  │
     │  │ }                      │  │
     │  └───────────────────────┘  │
     │ ◄─────────────────────────── │
```

**Key RPC Methods**:
- `agents.create` - Register new agent
- `agents.delete` - Remove agent
- `sessions.send` - Send message to agent
- `chat.history` - Get conversation history
- `config.apply` - Update agent configuration

#### LLM Service

**Protocol**: HTTP REST API (OpenAI-compatible)

```
Mission Control              LLM API (OpenAI)
     │                             │
     │  POST /v1/chat/completions  │
     │  {                         │
     │    "model": "gpt-4",       │
     │    "messages": [...]        │
     │  }                         │
     │ ───────────────────────────►│
     │                             │
     │  {                         │
     │    "choices": [{          │
     │      "message": {          │
     │        "content": "..."    │
     │      }                     │
     │    }]                      │
     │  }                         │
     │◄─────────────────────────── │
```

Used for:
- Generating agent personality files
- Creating standup meeting transcripts
- Parsing task instructions

## Data Flow

### 1. Agent Creation Flow

```
User (Frontend)              Backend              Database          OpenClaw
      │                         │                    │                  │
      │  1. POST /agents/       │                    │                  │
      │  {name, role, ...}      │                    │                  │
      │ ───────────────────────►│                    │                  │
      │                         │                    │                  │
      │                         │  2. Validate       │                  │
      │                         │  (Pydantic)        │                  │
      │                         │                    │                  │
      │                         │  3. INSERT         │                  │
      │                         │  ────────────────► │                  │
      │                         │                    │                  │
      │                         │◄───────────────────│                  │
      │                         │                    │                  │
      │                         │  4. Create         │                  │
      │                         │     Workspace      │                  │
      │                         │  (SOUL.md, etc)    │                  │
      │                         │                    │                  │
      │                         │  5. Register       │                  │
      │                         │  ────────────────────────────────────►
      │                         │                    │                  │
      │                         │◄───────────────────────────────────────│
      │                         │                    │                  │
      │◄────────────────────────│                    │                  │
      │  6. Return Agent        │                    │                  │
      │  {id, name, status, ...}│                    │                  │
```

**Key Points**:
- Frontend sends POST request with agent details
- Backend validates using Pydantic schemas
- Database stores agent record
- Workspace files created on filesystem
- OpenClaw registers agent for execution
- Success response includes full agent object

### 2. Task Assignment Flow

```
Scheduler (Background)         Database           OpenClaw
      │                            │                  │
      │  1. Heartbeat Trigger      │                  │
      │  (Every N minutes)         │                  │
      │                            │                  │
      │  2. SELECT agents          │                  │
      │     WHERE heartbeat > 0    │                  │
      │  ────────────────────────►│                  │
      │                            │                  │
      │◄───────────────────────────│                  │
      │                            │                  │
      │  3. SELECT tasks           │                  │
      │     WHERE status=BACKLOG   │                  │
      │  ────────────────────────►│                  │
      │                            │                  │
      │◄───────────────────────────│                  │
      │                            │                  │
      │  4. UPDATE tasks           │                  │
      │     SET status=IN_PROGRESS│                 │
      │  ────────────────────────►│                  │
      │                            │                  │
      │  5. Send message to        │                  │
      │     OpenClaw agent         │                  │
      │  ──────────────────────────────────────────────►
      │                            │                  │
      │                            │  6. Agent wakes  │
      │                            │     up and      │
      │                            │     processes    │
      │                            │                  │
```

**Key Points**:
- APScheduler triggers heartbeat every N minutes
- Finds agents with pending tasks
- Moves tasks from BACKLOG to IN_PROGRESS
- Notifies OpenClaw agent via WebSocket
- Agent executes task and reports back

### 3. Real-Time Log Streaming

```
Backend Logger              WebSocket Server         Frontend
      │                            │                    │
      │  1. Log Message            │                    │
      │  logger.info("...")        │                    │
      │                            │                    │
      │  2. BufferedHandler        │                    │
      │     captures log           │                    │
      │                            │                    │
      │  ─────────────────────────►│                    │
      │                            │                    │
      │                            │  3. Broadcast        │
      │                            │     to all clients │
      │                            │                    │
      │                            │  ──────────────────►│
      │                            │     WebSocket       │
      │                            │     message         │
      │                            │                    │
      │                            │                    │  4. Update
      │                            │                    │     UI LogTerminal
```

**Key Points**:
- All Python logs captured by BufferedHandler
- WebSocket server maintains connections
- Logs broadcast to all connected clients
- Frontend displays in real-time
- Supports filtering by level, source, agent

## Database Design

### Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    Team      │       │    Agent     │       │    Task      │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │──┐    │ id (PK)      │◄──────│ id (PK)      │
│ name         │  │    │ name (UQ)    │  │    │ title        │
│ description  │  │    │ role         │  │    │ description  │
│ color        │  └────│ team_id (FK) │  │    │ status       │
└──────────────┘       │ chief_id(FK)│───┘    │ agent_id(FK)│
       │               │ status       │        │ goal_id (FK) │
       │               │ heartbeat    │        │ priority     │
       │               │ can_spawn   │        │ move_reason  │
       │               └──────────────┘        └──────────────┘
       │                       │                      │
       │                       │                      │
       └──────────┐            │                      │
                  │            │                      │
┌──────────────┐  │     ┌──────────────┐       ┌──────────────┐
│   Message    │  │     │    Goal      │       │  AgentLog    │
├──────────────┤  │     ├──────────────┤       ├──────────────┤
│ id (PK)      │  └─────│ id (PK)      │       │ id (PK)      │
│ agent_id(FK) │─────────│ title        │       │ agent_id(FK) │
│ sender       │         │ description  │       │ action       │
│ content      │         │ is_main     │       │ details      │
│ is_from_user │         └──────────────┘       │ created_at   │
└──────────────┘                                └──────────────┘
```

### Relationships

**One-to-Many**:
- Team → Agents (one team has many agents)
- Agent → Tasks (one agent has many tasks)
- Agent → Messages (one agent has many messages)
- Goal → Tasks (one goal has many tasks)

**Self-Referential**:
- Agent → Agent (chief/subordinate hierarchy)
- Task → Task (dependencies, if implemented)

**Many-to-Many**:
- (Implicit through join table for extensions)

### Key Design Decisions

1. **Agent Name as Unique**: Used as identifier in OpenClaw
2. **Status Enums**: Typed as strings in DB, validated by Python enums
3. **Timezone Awareness**: All timestamps use timezone.utc
4. **Soft Deletes**: Not implemented (hard delete for now)
5. **Audit Logs**: Separate AgentLog table for all actions

## Agent Lifecycle

```
                    ┌─────────────┐
                    │   Created   │
                    │  (Database)   │
                    └──────┬──────┘
                           │
                           │ POST /agents/
                           │
                    ┌──────▼──────┐
                    │    Idle     │
                    │  (Created)  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌─────────┐ ┌─────────┐ ┌──────────┐
        │ Started │ │  Edit   │ │ Deleted  │
        │(Heartbeat)│ (Update) │ │ (Remove) │
        └────┬────┘ └────┬────┘ └────┬─────┘
             │           │           │
             ▼           │           ▼
        ┌─────────┐      │      ┌──────────┐
        │ Active  │◄─────┴─────►│  Over-   │
        │(Running)│              │ heated   │
        └────┬────┘              └──────────┘
             │
             │ Heartbeat disabled
             │
             ▼
        ┌─────────┐
        │  Stopped │
        │  (Idle)  │
        └─────────┘
```

**States**:
- **Created**: Agent exists in database, no OpenClaw registration yet
- **Idle**: Agent registered, heartbeat disabled
- **Active**: Heartbeat enabled, agent periodically wakes up
- **Overheated**: Agent encountered errors, needs reset
- **Stopped**: Heartbeat disabled manually
- **Deleted**: Agent removed from database and OpenClaw

## Task Management Flow

```
┌──────────┐
│  BACKLOG │  ← New tasks start here
└────┬─────┘
     │
     │ Heartbeat finds task
     │ assigned to agent
     ▼
┌──────────────┐
│ IN_PROGRESS  │  ← Agent working on task
└────┬─────────┘
     │
     │ Agent completes work
     │ or timeout (10 min)
     ▼
┌──────────┐
│  REVIEW  │  ← Ready for human review
└────┬─────┘
     │
     │ Human approves
     ▼
┌──────────┐
│   DONE   │  ← Completed
└──────────┘
```

**Transitions**:
- BACKLOG → IN_PROGRESS: Automatic (heartbeat) or manual (UI)
- IN_PROGRESS → REVIEW: Automatic after timeout or manual
- REVIEW → DONE: Manual approval only
- Any → BACKLOG: Manual unassign

## WebSocket Communication

### Connection Management

```python
# backend/app/core/log_stream.py

class BufferedHandler(logging.Handler):
    """
    Captures all Python logs and stores in a circular buffer.
    WebSocket connections read from this buffer.
    """
    
    def __init__(self, capacity=500):
        self.buffer = deque(maxlen=capacity)  # Circular buffer
        self.connections = []  # Active WebSocket connections
        
    def emit(self, record):
        log_entry = self.format(record)
        self.buffer.append(log_entry)
        
        # Broadcast to all connected clients
        for ws in self.connections:
            asyncio.create_task(ws.send_json(log_entry))
```

### Client Connection

```javascript
// frontend/src/components/LogTerminal.tsx

const LogTerminal = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  
  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket('ws://localhost:8002/ws/logs');
    wsRef.current = ws;
    
    ws.onmessage = (event) => {
      const log = JSON.parse(event.data);
      setLogs(prev => [...prev, log]);
    };
    
    return () => ws.close();  // Cleanup on unmount
  }, []);
  
  return <LogViewer logs={logs} />;
};
```

## Extension Points

### Where to Add New Features

**1. New Database Field**:
```python
# backend/app/models/models.py
class Task(Base):
    # ... existing fields ...
    your_new_field = Column(String(100), nullable=True)
```

**2. New API Endpoint**:
```python
# backend/app/api/your_feature.py
@router.get("/new-endpoint")
async def your_endpoint(db: AsyncSession = Depends(get_db)):
    # Your logic here
    return {"result": "success"}

# backend/app/main.py
app.include_router(your_feature.router)
```

**3. New Frontend Page**:
```typescript
// frontend/src/app/your-page/page.tsx
export default function YourPage() {
  return <div>Your content</div>;
}

// Add to sidebar in components/Sidebar.tsx
{ name: "Your Page", path: "/your-page", icon: "🚀" }
```

**4. New Background Job**:
```python
# backend/app/core/scheduler.py

def your_background_job():
    """Runs periodically"""
    db = SessionLocal()
    try:
        # Your logic here
        pass
    finally:
        db.close()

# In start_scheduler():
scheduler.add_job(
    your_background_job,
    trigger="interval",
    minutes=5,
    id="your_job"
)
```

**5. New Service**:
```python
# backend/app/services/your_service.py

class YourService:
    async def do_something(self, db: AsyncSession):
        # Business logic
        pass

your_service = YourService()
```

### Extension Patterns

**Pattern 1: Database Extension**
```
Model → Schema → Migration → API → Frontend
```

**Pattern 2: Service Extension**
```
Service → API → Frontend
```

**Pattern 3: Frontend-Only Extension**
```
Component → API Integration → State Management
```

## Performance Considerations

### Database
- ✅ Use `selectinload()` for eager loading relationships
- ✅ Add indexes for frequently queried columns
- ✅ Use async sessions for non-blocking operations
- ⚠️ Avoid N+1 queries (always use joined/selectin loading)

### Backend
- ✅ Cache OpenClaw gateway responses when appropriate
- ✅ Use connection pooling for database
- ✅ Rate limit external API calls
- ⚠️ Don't block the event loop (always use await)

### Frontend
- ✅ Use React.memo() for expensive components
- ✅ Virtualize long lists (if needed)
- ✅ Debounce rapid API calls
- ⚠️ Don't fetch data in render (use useEffect)

## Security Considerations

### Authentication
- Currently: No authentication (single-user system)
- Future: Add JWT or session-based auth

### Authorization
- Currently: No role-based access
- Future: Add admin/user roles

### Data Validation
- ✅ Pydantic schemas validate all inputs
- ✅ SQLAlchemy prevents SQL injection
- ✅ Path traversal prevented in workspace manager

### Secrets Management
- ✅ API keys in environment variables
- ✅ .env files in .gitignore
- ⚠️ Rotate tokens regularly

## Monitoring & Observability

### Logging
- All actions logged to AgentLog table
- Structured JSON logs via WebSocket
- Log levels: DEBUG, INFO, WARNING, ERROR

### Metrics (Future)
- Request latency
- Database query time
- OpenClaw connection status
- Active WebSocket connections

### Health Checks
- `/health` - Basic service health
- `/` - Service info and version
- Add deep health check for database and OpenClaw

## Deployment Architecture

### Development
```
Single Machine
├── Backend (localhost:8002)
├── Frontend (localhost:3000)
├── SQLite Database
└── OpenClaw Gateway (localhost:18789)
```

### Production
```
┌─────────────────────────────────────────┐
│           Load Balancer                 │
│            (Nginx/ALB)                  │
└─────────────────────────────────────────┘
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
┌──────────────┐      ┌──────────────┐
│   Frontend   │      │   Backend    │
│   (Next.js)  │      │  (FastAPI)   │
│              │      │              │
└──────────────┘      └──────┬───────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
            ┌──────────────┐  ┌──────────────┐
            │ PostgreSQL   │  │  Redis       │
            │  Database    │  │  (Cache)     │
            └──────────────┘  └──────────────┘
```

---

**See Also**:
- [API Reference](API_REFERENCE.md) - Complete endpoint documentation
- [Extensions Guide](EXTENSIONS_GUIDE.md) - How to add features
- [Deployment Guide](DEPLOYMENT.md) - Production setup
