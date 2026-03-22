# 🚀 OpenClaw Mission Control - Building Example

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://typescriptlang.org)

> **A comprehensive tutorial project for building an AI Agent Mission Control Dashboard**

Learn how to build a production-ready dashboard for orchestrating autonomous AI agents with FastAPI, Next.js, and WebSocket real-time communication.
> **Note:** Some documentation describes aspirational or planned features that haven't been implemented yet. These are marked where applicable.

## 📚 Table of Contents

- [What You'll Learn](#what-youll-learn)
- [Architecture Overview](#architecture-overview)
- [Quick Start (5 minutes)](#quick-start-5-minutes)
- [Tutorial](#tutorial)
- [Extension Ideas](#extension-ideas)
- [API Reference](#api-reference)
- [Contributing](#contributing)

## 🎯 What You'll Learn

This tutorial teaches you to build:

### Backend Skills
- **FastAPI async patterns** - Non-blocking API endpoints
- **SQLAlchemy 2.0** - Modern async ORM with type hints
- **WebSocket communication** - Real-time log streaming
- **APScheduler** - Background job scheduling
- **Service-oriented architecture** - Clean separation of concerns

### Frontend Skills
- **Next.js 16 App Router** - Modern React framework
- **TypeScript** - Type-safe development
- **Tailwind CSS v4** - Utility-first styling
- **Custom React hooks** - State management patterns
- **WebSocket clients** - Real-time UI updates

### AI/Agent Concepts
- **Agent orchestration** - Managing AI agent fleets
- **Heartbeat scheduling** - Periodic agent activation
- **Task management** - Kanban-style workflows
- **Workspace files** - Agent personality & memory
- **Rate limiting** - Handling API constraints

### DevOps Skills
- **Environment configuration** - Secure secret management
- **Database migrations** - Schema evolution
- **Production deployment** - Docker, cloud platforms

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Dashboard   │  │  Agent UI    │  │  Kanban      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                 │                │               │
│         └─────────────────┼────────────────┘               │
│                           │                                 │
│              WebSocket / REST API                         │
└───────────────────────────┼─────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                      Backend (FastAPI)                     │
│         ┌─────────────────┴────────────────┐               │
│         │         API Routes                │               │
│  ┌──────┴──┐ ┌──────┴──┐ ┌──────┴──┐ ┌────┴────┐          │
│  │  Agents │ │  Tasks  │ │  Teams  │ │  Chat   │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│                                                             │
│         ┌──────────────────────────────────┐               │
│         │         Services Layer            │               │
│  ┌──────┴──────────┐  ┌───────────────────┐ │               │
│  │ OpenClaw Gateway│  │ Workspace Manager│ │               │
│  └──────────────────┘  └───────────────────┘ │               │
│  ┌──────────────────┐  ┌───────────────────┐               │
│  │  Task Executor   │  │   LLM Service    │               │
│  └──────────────────┘  └───────────────────┘               │
│                                                             │
│         ┌──────────────────────────────────┐               │
│         │         Core Layer              │               │
│  ┌──────┴──┐ ┌──────┴──┐ ┌──────┴──┐ ┌───┴────┐          │
│  │ Database│ │Scheduler│ │  Config │ │ Logger │          │
│  └─────────┘ └─────────┘ └─────────┘ └────────┘          │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ WebSocket RPC
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                    OpenClaw Gateway                        │
│              (External AI Agent Platform)                 │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User** interacts with **Frontend** (Next.js)
2. **Frontend** makes **REST API** calls to **Backend** (FastAPI)
3. **Backend** stores data in **Database** (SQLite/PostgreSQL)
4. **Backend** communicates with **OpenClaw Gateway** via **WebSocket RPC**
5. **Background jobs** (scheduler) run periodic tasks
6. **WebSocket** streams real-time logs to frontend

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### 1. Clone & Setup

```bash
git clone https://github.com/Rishabh-Bajpai/openclaw-mission-control-building-example.git
cd openclaw-mission-control-building-example
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OpenClaw token and LLM API key

# Run backend
uvicorn app.main:app --reload --port 8002
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local if your backend runs on different port

# Run frontend
npm run dev
```

### 4. Access the App

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8002
- **API Docs**: http://localhost:8002/docs

### 5. Create Your First Agent

1. Navigate to "Agent Studio" in the sidebar
2. Click "Create Agent"
3. Fill in:
   - Name: "CEO"
   - Role: "Chief Executive Officer"
   - Heartbeat: 15 minutes
4. Click "Start" to activate

🎉 **Success!** You've created your first AI agent!

---

## 📖 Tutorial

### Part 1: Understanding the Architecture (15 min)

#### 1.1 Project Structure

```
openclaw-mission-control/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/               # REST API endpoints
│   │   │   ├── agents.py     # Agent CRUD + lifecycle
│   │   │   ├── tasks.py      # Task management
│   │   │   └── ...
│   │   ├── core/             # Infrastructure
│   │   │   ├── database.py   # SQLAlchemy setup
│   │   │   ├── scheduler.py  # Background jobs
│   │   │   └── config.py     # Settings
│   │   ├── models/           # Data layer
│   │   │   ├── models.py     # SQLAlchemy models
│   │   │   └── schemas.py    # Pydantic schemas
│   │   └── services/         # Business logic
│   │       ├── openclaw_gateway.py  # OpenClaw integration
│   │       ├── workspace_manager.py # File operations
│   │       └── task_executor.py     # Task automation
│   └── requirements.txt
├── frontend/                   # Next.js application
│   ├── src/
│   │   ├── app/             # Next.js App Router
│   │   │   ├── agents/      # Agent Studio page
│   │   │   ├── kanban/      # Task board page
│   │   │   └── ...
│   │   ├── components/     # React components
│   │   └── lib/            # Utilities & API client
│   └── package.json
└── docs/                    # Documentation
```

**Key Pattern**: The codebase follows **Clean Architecture**:
- **API Layer**: Handles HTTP requests/responses
- **Service Layer**: Contains business logic
- **Model Layer**: Defines data structures
- **Core Layer**: Infrastructure (DB, scheduler, config)

#### 1.2 Backend Architecture

**FastAPI Application** (`backend/app/main.py`):

```python
# Simplified view of how the app starts
app = FastAPI(lifespan=lifespan)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    configure_logging()      # Setup logging
    await init_db()          # Create database tables
    start_scheduler()        # Start background jobs
    yield
    # SHUTDOWN
    stop_scheduler()         # Stop background jobs
```

**Database** (`backend/app/core/database.py`):

```python
# Async SQLAlchemy setup
engine = create_async_engine(settings.DATABASE_URL)
async_session = async_sessionmaker(engine, class_=AsyncSession)

# Usage in API endpoints
@app.get("/items/")
async def get_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item))
    return result.scalars().all()
```

**Key Concepts**:
- Uses **async/await** for non-blocking operations
- **Dependency Injection** with FastAPI's `Depends()`
- **SQLAlchemy 2.0** for type-safe ORM

#### 1.3 Frontend Architecture

**Next.js App Router** (`frontend/src/app/`):

```typescript
// Page component structure
export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  
  useEffect(() => {
    api.agents.list().then(setAgents);
  }, []);
  
  return (
    <div>
      {agents.map(agent => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  );
}
```

**API Client** (`frontend/src/lib/api.ts`):

```typescript
// Centralized API client with TypeScript types
export const api = {
  agents: {
    list: () => fetchJSON<Agent[]>('/agents/'),
    create: (data) => fetchJSON<Agent>('/agents/', { method: 'POST', body: JSON.stringify(data) }),
    // ...
  }
};
```

**Key Concepts**:
- **App Router** for file-based routing
- **Server Components** by default (can fetch data directly)
- **Client Components** for interactivity ('use client')
- **TypeScript** for type safety

### Part 2: Creating Your First Agent (20 min)

#### 2.1 Agent Creation Flow

When you create an agent, here's what happens:

**Step 1: API Endpoint Receives Request**

```python
# backend/app/api/agents.py

@router.post("/", status_code=201)
async def create_agent(agent: AgentCreate, db: AsyncSession = Depends(get_db)):
    # 1. Validate input
    if not agent.name or not agent.role:
        raise HTTPException(status_code=400, detail="Name and role required")
    
    # 2. Check for duplicates
    existing = await db.execute(select(Agent).where(Agent.name == agent.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Agent name already exists")
    
    # 3. Create database record
    db_agent = Agent(name=agent.name, role=agent.role, ...)
    db.add(db_agent)
    await db.commit()
    
    # 4. Create workspace files (SOUL.md, IDENTITY.md, etc.)
    await workspace_manager.create_agent_workspace(agent.name, agent.role, team_name)
    
    # 5. Register with OpenClaw Gateway
    await openclaw.create_agent(agent.name, workspace_path)
    
    # 6. Log the action
    await create_agent_log(db, db_agent.id, "CREATED", f"Agent {agent.name} created")
    
    return db_agent
```

**Step 2: Workspace Files Created**

Agent workspace includes personality and memory files:

```
~/.openclaw/agents/{agent_name}/workspace/
├── SOUL.md          # Personality & values
├── IDENTITY.md      # Role & team
├── AGENTS.md        # Governance rules
├── MEMORY.md        # Long-term memory
├── USER.md          # Human boss context
├── HEARTBEAT.md     # Activation instructions
└── TASKS.md         # Current tasks
```

**Example SOUL.md**:
```markdown
# SOUL - Core Values & Personality

## Role
You are a Chief Executive Officer responsible for strategic decisions.

## Values
- Innovation over tradition
- Data-driven decisions
- Transparency and accountability

## Communication Style
Clear, direct, and encouraging. Focus on outcomes, not activities.
```

#### 2.2 Code Walkthrough

Let's trace through the actual code:

**1. Frontend Agent Form** (`frontend/src/app/agents/page.tsx`):

```typescript
// Simplified form submission
const handleCreateAgent = async (formData) => {
  try {
    const agent = await api.agents.create({
      name: formData.name,
      role: formData.role,
      team_id: formData.team_id,
      chief_id: formData.chief_id,
      heartbeat_frequency: parseInt(formData.heartbeat),
    });
    
    // Show success message
    toast.success(`Agent ${agent.name} created!`);
    
    // Refresh agent list
    loadAgents();
  } catch (error) {
    toast.error(error.message);
  }
};
```

**2. API Route** (`backend/app/api/agents.py`):

See the full implementation above. Key points:
- Uses Pydantic for input validation
- Async database operations
- Error handling with HTTP exceptions
- Logging for audit trail

**3. Workspace Manager** (`backend/app/services/workspace_manager.py`):

```python
class WorkspaceManager:
    def create_agent_workspace(self, agent_name: str, role: str, team: str = None):
        """Create default files for new agent"""
        safe_name = agent_name.lower().replace(" ", "_")
        agent_dir = Path.home() / ".openclaw" / "agents" / safe_name / "workspace"
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Create each file with default content
        files = {
            "SOUL.md": self._generate_soul_content(role),
            "IDENTITY.md": self._generate_identity_content(agent_name, role, team),
            # ... other files
        }
        
        for filename, content in files.items():
            (agent_dir / filename).write_text(content)
```

#### 2.3 Hands-On Exercise

**Exercise**: Create an agent programmatically using curl:

```bash
# Create an agent
curl -X POST http://localhost:8002/agents/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyFirstAgent",
    "role": "Developer",
    "heartbeat_frequency": 15
  }'

# List all agents
curl http://localhost:8002/agents/

# Check workspace files
cat ~/.openclaw/agents/myfirstagent/workspace/IDENTITY.md
```

**Challenge**: Modify the agent creation to:
1. Add a custom field (e.g., `specialization`)
2. Create an additional workspace file (e.g., `SKILLS.md`)

### Part 3: Task Management & Workflows (25 min)

#### 3.1 Task Lifecycle

Tasks move through 4 states:

```
┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌────────┐
│  BACKLOG │───▶│ IN_PROGRESS  │───▶│  REVIEW  │───▶│  DONE  │
└──────────┘    └──────────────┘    └──────────┘    └────────┘
     │                  │
     │                  │
     ▼                  ▼
   Scheduler        Heartbeat
   auto-assign      triggers
```

**State Transitions**:
1. **BACKLOG → IN_PROGRESS**: When agent heartbeat runs
2. **IN_PROGRESS → REVIEW**: After 10 min timeout (auto) or agent moves
3. **REVIEW → DONE**: Human approves via UI
4. **Any → BACKLOG**: Task unassigned

#### 3.2 Heartbeat Mechanism

The heartbeat is the core of agent activation:

```python
# backend/app/core/scheduler.py

def run_agent_heartbeat():
    """Run heartbeat for all agents - assigns BACKLOG tasks to IN_PROGRESS"""
    agents = db.query(Agent).filter(
        Agent.heartbeat_frequency > 0,
        Agent.status != AgentStatus.OVERHEATED
    ).all()
    
    for agent in agents:
        # 1. Get pending tasks
        pending_tasks = db.query(Task).filter(
            Task.agent_id == agent.id,
            Task.status == TaskStatus.BACKLOG
        ).all()
        
        if pending_tasks:
            # 2. Move tasks to IN_PROGRESS
            for task in pending_tasks:
                task.status = TaskStatus.IN_PROGRESS
            
            # 3. Trigger OpenClaw agent
            openclaw.run_agent(agent.name, "Execute your assigned tasks")
            
            # 4. Log action
            log_action(agent.id, "HEARTBEAT_AUTO_ASSIGN", ...)
```

**How it works**:
1. Scheduler runs every minute (configurable)
2. Finds agents with `heartbeat_frequency > 0`
3. Checks for BACKLOG tasks assigned to agent
4. Moves them to IN_PROGRESS
5. Sends message to OpenClaw agent via WebSocket

#### 3.3 TASKS.md Synchronization

Tasks sync bidirectionally between DB and markdown files:

**DB → Markdown** (every minute):

```python
def sync_all_agent_tasks_md():
    """Sync TASKS.md for all agents (DB → TASKS.md)"""
    for agent in db.query(Agent).all():
        tasks = db.query(Task).filter(Task.agent_id == agent.id).all()
        
        # Generate markdown content
        content = f"""# Task Board

## My Tasks

### Backlog
{format_tasks([t for t in tasks if t.status == "backlog"])}

### In Progress
{format_tasks([t for t in tasks if t.status == "in_progress"])}

### Review
{format_tasks([t for t in tasks if t.status == "review"])}

### Done
{format_tasks([t for t in tasks if t.status == "done"])}
"""
        
        # Write to file
        workspace_manager.write_file(agent.name, "TASKS.md", content)
```

**Why markdown?**
- Agents can read it as part of their context
- Human-readable for debugging
- Version control friendly
- Easy to parse

#### 3.4 Hands-On Exercise

**Exercise**: Create and manage tasks:

```bash
# Create a task
curl -X POST http://localhost:8002/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Build landing page",
    "description": "Create HTML/CSS for new landing page",
    "agent_id": 1,
    "priority": 3
  }'

# Assign to agent (moves to IN_PROGRESS)
curl -X PUT http://localhost:8002/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress", "move_reason": "Starting work"}'

# Check TASKS.md
cat ~/.openclaw/agents/myfirstagent/workspace/TASKS.md
```

**Challenge**: Add a task dependency system:
1. Add `depends_on` field to Task model
2. Prevent task from starting until dependencies are done
3. Show dependency chain in UI

### Part 4: Building Custom Features (30 min)

See [EXTENSIONS_GUIDE.md](EXTENSIONS_GUIDE.md) for detailed tutorials on:
- Adding task dependencies
- Enabling agent-to-agent messaging
- Tracking agent performance metrics

Quick overview of where to add features:

**New Database Field**:
```python
# backend/app/models/models.py

class Task(Base):
    # ... existing fields ...
    
    # New field
    depends_on = Column(Integer, ForeignKey("tasks.id"), nullable=True)
```

**New API Endpoint**:
```python
# backend/app/api/tasks.py

@router.get("/{task_id}/dependencies")
async def get_task_dependencies(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if task.depends_on:
        dependency = await db.get(Task, task.depends_on)
        return dependency
    return None
```

**New Frontend Page**:
```typescript
// frontend/src/app/dependencies/page.tsx
'use client';

export default function DependenciesPage() {
  // Your component logic
  return <div>Task Dependencies</div>;
}
```

---

## 🛠️ Extension Ideas

Here are 15 ways to extend this project:

### 🔴 Easy Extensions (Start here!)

1. **Task Dependencies** - Block tasks until prerequisites complete
2. **Agent-to-Agent Messaging** - Direct communication between agents
3. **Task Categories/Tags** - Organize tasks with labels
4. **Agent Performance Metrics** - Track completion rates, time per task
5. **Task Attachments** - Upload files to tasks

### 🟡 Medium Extensions

6. **Agent Skills** - Assign specific competencies to agents
7. **Recurring Tasks** - Daily/weekly repeating tasks
8. **Task Comments** - Discussion threads on tasks
9. **Agent Availability Calendar** - Schedule vacations/busy times
10. **Task Time Tracking** - Log hours spent on each task

### 🟢 Advanced Extensions

11. **Multi-Agent Collaboration** - Multiple agents on one task
12. **Automated Task Estimation** - LLM estimates task complexity
13. **Workflow Automation Rules** - "When X happens, do Y"
14. **External Integrations** - Slack, Discord, Email notifications
15. **Agent Learning** - Agents improve based on past performance

For implementation guides on the first 3 extensions, see [EXTENSIONS_GUIDE.md](EXTENSIONS_GUIDE.md).

---

## 📚 API Reference

See [API_REFERENCE.md](API_REFERENCE.md) for complete API documentation.

Quick reference:

```
GET    /agents/           - List all agents
POST   /agents/           - Create new agent
GET    /agents/{id}       - Get agent details
PUT    /agents/{id}       - Update agent
DELETE /agents/{id}       - Delete agent
POST   /agents/{id}/start - Start agent heartbeat
POST   /agents/{id}/stop  - Stop agent heartbeat

GET    /tasks/            - List all tasks
POST   /tasks/            - Create task
PUT    /tasks/{id}        - Update task status
DELETE /tasks/{id}        - Delete task

WS     /ws/logs          - Real-time log stream
```

---

## 🤝 Contributing

Contributions welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

Quick guidelines:
- Follow existing code style
- Add tests for new features
- Update documentation
- One feature per PR

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---


**Built with ❤️ for the OpenClaw Community**


