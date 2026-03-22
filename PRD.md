# Product Requirement Document (PRD): OpenClaw Mission Control

## 1. Project Overview

**Project Name:** OpenClaw Mission Control (Muddy OS)  
**Objective:** A centralized command-and-control dashboard for managing autonomous AI agents integrated with OpenClaw Gateway. The system provides a complete solution for creating, orchestrating, and monitoring AI agents through a WebSocket-enabled API with a cyber-luxury themed UI.

**Target Users:** Human CEOs managing AI agent workforces

---

## 2. System Architecture

### 2.1 Backend Architecture

**Framework:** FastAPI with async/await support  
**Database:** PostgreSQL with SQLAlchemy ORM (configurable to SQLite)  
**Scheduler:** APScheduler for background tasks  
**WebSocket:** Real-time log streaming via `/ws/logs`  
**Authentication:** Device identity with Ed25519 cryptographic signatures

### 2.2 Frontend Architecture

**Framework:** Next.js 16 with App Router  
**Language:** TypeScript  
**Styling:** Tailwind CSS with "Cyber-Luxury" theme

### 2.3 OpenClaw Gateway Integration

**Protocol:** WebSocket RPC via `ws://127.0.0.1:18789`  
**Authentication:** Token-based + Device identity with Ed25519 signatures  
**Key RPC Methods:** `agents.create`, `agents.delete`, `config.get`, `config.apply`, `health`, `sessions.send`, `chat.send`, `chat.history`

---

## 3. Database Schema

### 3.1 Core Models

#### Agent
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `name` | String(100) | Unique identifier, cannot be changed after creation |
| `role` | String(100) | Job title/function |
| `chief_id` | Integer | Self-referential FK for hierarchy (CEO → COO → Chiefs → Specialists) |
| `team_id` | Integer | FK to Team |
| `model` | String(100) | LLM model used by agent |
| `status` | Enum | active, idle, overheated, offline |
| `heartbeat_frequency` | Integer | Minutes between heartbeats (0 = disabled) |
| `active_hours_start` | String(10) | Daily active window start (HH:MM) |
| `active_hours_end` | String(10) | Daily active window end (HH:MM) |
| `can_spawn_subagents` | Boolean | Permission to create sub-agents |
| `failure_count` | Integer | Consecutive task failures |
| `created_at`, `updated_at` | DateTime | Timestamps (timezone-aware UTC) |

#### Team
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `name` | String(100) | Unique team name |
| `description` | Text | Team purpose/description |
| `color` | String(7) | Hex color code (e.g., #FF5733) |
| `created_at`, `updated_at` | DateTime | Timestamps |

#### Task
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `title` | String(200) | Task title |
| `description` | Text | Task details |
| `goal_id` | Integer | FK to Goal (optional) |
| `agent_id` | Integer | FK to assigned Agent |
| `status` | Enum | backlog, in_progress, review, done |
| `priority` | Integer | Task priority (1-5) |
| `move_reason` | Text | Why task was moved (for audit) |
| `created_at`, `updated_at`, `completed_at` | DateTime | Timestamps |

#### Goal
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `title` | String(200) | Goal title |
| `description` | Text | Goal description |
| `is_main_goal` | Boolean | Only one main goal at a time |
| `created_at`, `updated_at` | DateTime | Timestamps |

#### Message
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `agent_id` | Integer | FK to Agent |
| `sender` | String(50) | Message sender |
| `content` | Text | Message content |
| `is_from_user` | Boolean | From human user vs agent |
| `created_at` | DateTime | Timestamp |

#### Meeting
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `title` | String(200) | Meeting title |
| `meeting_type` | String(50) | Type (standup, etc.) |
| `transcript` | Text | Full conversation |
| `briefing` | Text | Executive summary |
| `audio_url` | String(500) | TTS audio file URL |
| `duration_minutes` | Integer | Meeting duration |
| `created_at` | DateTime | Timestamp |

#### AgentLog
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `agent_id` | Integer | FK to Agent (nullable for system logs) |
| `action` | String(100) | Action type (CREATED, STARTED, STOPPED, etc.) |
| `details` | Text | Additional details |
| `created_at` | DateTime | Timestamp |

#### Settings
| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `key` | String(100) | Setting key (unique) |
| `value` | Text | Setting value |
| `updated_at` | DateTime | Timestamp |

### 3.2 Relationships

- **Agent Hierarchy:** Self-referential `chief_id` (CEO → COO → Chiefs → Specialists)
- **Agent-Team:** Many-to-one
- **Task-Agent:** Many-to-one
- **Task-Goal:** Many-to-one
- **Agent-Message:** One-to-many
- **Agent-Task:** One-to-many

---

## 4. Agent Workspace Framework

Each agent has a workspace directory at `~/.openclaw/agents/{agent_name}/workspace/` containing:

### 4.1 Workspace Files

**SOUL.md** - Personality & Voice
- Core values and beliefs
- Personality traits
- Communication style
- Decision-making framework

**IDENTITY.md** - Identity & Role
- Name and role
- Team affiliation
- Reporting structure
- Specific responsibilities
- Active hours

**AGENTS.md** - Governance & Protocols
- Startup sequence
- Task completion rules
- Sub-agent spawning rules
- Safety protocols
- Escalation procedures

**MEMORY.md** - Long-term Memory
- Past decisions and outcomes
- Learned patterns
- Relationship notes
- Project history

**USER.md** - Human Context
- Information about the human "Boss"
- User preferences
- Communication style
- Authority levels

**HEARTBEAT.md** - Heartbeat Instructions
- What to do on each heartbeat
- Task checking procedures
- Auto-assignment logic

**TASKS.md** - Current Task Board
- My Tasks section (by status)
- Team Tasks section
- Auto-synced from database

**models.json** - Configuration
- LLM model settings
- API endpoints
- Timeout configurations

### 4.2 File Management
- Files created automatically on agent creation
- Files updated when agent edited
- Identity.md reflects current team/chief assignments
- TASKS.md synced bidirectionally with database

---

## 5. Backend API Endpoints

### 5.1 Agents API (`/api/agents.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /agents/` | List | All agents with OpenClaw heartbeat sync |
| `GET /agents/hierarchy` | List | Agent hierarchy tree with team/chief names |
| `GET /agents/{id}` | Get | Single agent details |
| `GET /agents/{id}/subordinates` | Get | Direct reports for an agent |
| `POST /agents/` | Create | New agent (DB + OpenClaw + config.apply) |
| `PUT /agents/{id}` | Update | Agent fields (name locked) |
| `DELETE /agents/{id}` | Delete | Remove agent + cascade delete |
| `POST /agents/{id}/start` | Action | Enable heartbeat, trigger initial run |
| `POST /agents/{id}/stop` | Action | Disable heartbeat |
| `POST /agents/{id}/reset` | Action | Clear failure count, set idle |
| `GET /agents/{id}/files` | Get | Agent workspace markdown files |
| `PUT /agents/{id}/files` | Update | Edit agent workspace files |
| `GET /agents/{id}/logs` | Get | Agent activity logs |
| `POST /agents/sync-from-openclaw` | Sync | Import agents from OpenClaw config |

### 5.2 Teams API (`/api/teams.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /teams/` | List | All teams |
| `GET /teams/{id}` | Get | Single team |
| `POST /teams/` | Create | New team |
| `PUT /teams/{id}` | Update | Team details |
| `DELETE /teams/{id}` | Delete | Remove team |

### 5.3 Tasks API (`/api/tasks.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /tasks/` | List | All tasks (filterable by status, agent_id, goal_id) |
| `GET /tasks/{id}` | Get | Single task |
| `POST /tasks/` | Create | New task |
| `PUT /tasks/{id}` | Update | Task status, agent, title, description |
| `DELETE /tasks/{id}` | Delete | Remove task |
| `POST /tasks/{id}/unassign` | Action | Move back to backlog, clear agent |

**Agent-Facing Task Endpoints:**
| Endpoint | Description |
|----------|-------------|
| `GET /agent/tasks/my-tasks/{agent_id}` | Agent's own tasks by status |
| `GET /agent/tasks/team-tasks/{agent_id}` | Team tasks for agent |
| `PUT /agent/tasks/{task_id}/status` | Agent updates task status |

### 5.4 Goals API (`/api/tasks.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /goals/` | List | All goals |
| `GET /goals/{id}` | Get | Single goal |
| `POST /goals/` | Create | New goal (marks existing main_goal=false) |
| `DELETE /goals/{id}` | Delete | Remove goal |

### 5.5 Chat API (`/api/chat.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /chat/{agent_id}/messages` | Get | Chat messages (optional sync from OpenClaw) |
| `POST /chat/{agent_id}/messages` | Send | Message to agent via OpenClaw |
| `DELETE /chat/{agent_id}/messages` | Clear | Clear chat history |
| `GET /chat/{agent_id}/status` | Get | Chat status + last message |

### 5.6 Messages API (`/api/messages.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /messages/` | List | System messages (filterable by sender_id, receiver_id) |
| `POST /messages/` | Create | Send system message |

### 5.7 Meetings API (`/api/meetings.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /meetings/` | List | All meetings |
| `GET /meetings/{id}` | Get | Single meeting |
| `POST /meetings/standup` | Create | Run AI standup meeting |
| `GET /meetings/{id}/transcript` | Get | Meeting transcript + briefing |

### 5.8 Logs API (`/api/logs.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /logs/` | List | Agent logs (filterable by agent_id, action, limit) |

### 5.9 Dashboard API (`/api/dashboard.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /dashboard/stats` | Get | Dashboard statistics |

### 5.10 Settings API (`/api/settings.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /settings/` | Get | System settings + OpenClaw status |
| `GET /settings/llm` | Get | LLM configuration |
| `PUT /settings/llm` | Update | Update LLM settings |
| `GET /settings/openclaw` | Get | OpenClaw connection status |
| `POST /settings/openclaw/test` | Test | Test gateway connection |

### 5.11 WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `WS /ws/logs` | Real-time backend log streaming |

---

## 6. Core Services

### 6.1 OpenClaw Gateway Service (`services/openclaw_gateway.py`)

**Purpose:** WebSocket RPC client for OpenClaw integration

**Key Methods:**
```python
async def create_agent(name, workspace) -> dict
async def delete_agent(agent_id) -> bool
async def set_agent_heartbeat(name, minutes, workspace) -> HeartbeatResult
async def get_agent_heartbeat(name) -> int  # Returns minutes or 0
async def run_agent(agent_id, message) -> dict
async def send_chat_message(agent_id, message) -> dict
async def get_chat_history(agent_id) -> dict
async def health_check() -> dict
async def get_config() -> dict
async def list_agents() -> list
```

**Rate Limit Handling:**
- Returns `HeartbeatResult` with `rate_limited`, `retry_seconds`, `error_message`
- Pattern matching for rate limit errors
- Structured error propagation to frontend

### 6.2 Workspace Manager (`services/workspace_manager.py`)

**Purpose:** Manages agent workspace files in `~/.openclaw/agents/`

**Key Methods:**
```python
def create_agent_workspace(agent_name)
def read_file(agent_name, filename)
def write_file(agent_name, filename, content)
def update_identity(agent_name, role, team, chief)
def create_default_files(agent_name, role, team)
def get_tasks_md(agent_name) -> str
def update_tasks_md(agent_name, tasks_md)
def delete_agent_workspace(agent_name)
```

**Workspace Structure:**
```
~/.openclaw/agents/{agent_name}/
├── workspace/
│   ├── SOUL.md
│   ├── IDENTITY.md
│   ├── AGENTS.md
│   ├── MEMORY.md
│   ├── USER.md
│   ├── HEARTBEAT.md
│   ├── TASKS.md
│   └── models.json
```

### 6.3 Task Executor (`services/task_executor.py`)

**Purpose:** Triggers OpenClaw agent runs when tasks are assigned

**Key Methods:**
```python
async def execute_task(db, task_id, agent_id)
async def check_and_complete_tasks(db, agent_id)
```

### 6.4 LLM Service (`services/llm_service.py`)

**Purpose:** Generic LLM client for standup generation, task analysis

**Key Methods:**
```python
async def generate(messages, temperature=0.7, max_tokens=1000)
async def generate_with_stream(messages)
def parse_actions(llm_response) -> list
```

**Configuration:**
- OpenAI-compatible API
- Configurable model, temperature, max_tokens
- Streaming support

### 6.5 OpenClaw RPC Layer (`services/openclaw/`)

**gateway_rpc.py:**
- Low-level WebSocket RPC with protocol version 3
- Methods: `openclaw_call`, `send_message`, `ensure_session`, `get_chat_history`
- Ed25519 device identity authentication
- Auto-retry on connection failures

**device_identity.py:**
- Ed25519 key generation
- Device identity management
- Token-based authentication

---

## 7. Core Infrastructure

### 7.1 Scheduler (`core/scheduler.py`)

**Background Jobs (APScheduler):**

| Job | Frequency | Purpose |
|-----|-----------|---------|
| `run_agent_heartbeat` | Per-agent frequency | Auto-assign BACKLOG → IN_PROGRESS tasks |
| `sync_all_agent_tasks_md` | 1 minute | Sync DB tasks → TASKS.md files |
| `sync_openclaw_heartbeats_to_db` | 60 seconds | Sync OpenClaw heartbeat → DB status |
| `check_task_completion` | 2 minutes | Auto-move IN_PROGRESS → REVIEW after timeout |

**Key Functions:**
```python
def run_agent_heartbeat()
def sync_all_agent_tasks_md()
def sync_tasks_md_to_db()
def check_task_completion()
def sync_openclaw_heartbeats_to_db()
def schedule_agent_heartbeats()
def setup_periodic_tasks_sync()
def setup_task_completion_check()
def start_scheduler()
def stop_scheduler()
```

### 7.2 Rate Limit Handling (`core/rate_limit.py`)

**Rate Limit Patterns:**
- "rate_limit_error"
- "429"
- "too_many_requests"
- "exceeded.*rate limit"
- "retry\s*after"

**Key Functions:**
```python
def is_rate_limit_error(error_message: str) -> bool
def extract_retry_seconds(error_message: str) -> int
def get_rate_limit_info(error_message: str) -> RateLimitInfo
```

**Default Retry:** 60 seconds

### 7.3 Log Streaming (`core/log_stream.py`)

**BufferedHandler:**
- Captures all Python logs
- Circular buffer: 500 entries
- Thread-safe with locking

**WebSocket Endpoint:**
```python
async def log_ws_endpoint(websocket: WebSocket)
```

**Log Format:**
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "level": "INFO",
  "logger": "app.api.agents",
  "message": "Agent created: CEO"
}
```

### 7.4 Database (`core/database.py`)

**Setup:**
- Async SQLAlchemy engine
- Session management via `async_sessionmaker`
- Connection pooling
- Auto-commit disabled for explicit transaction control

### 7.5 Configuration (`core/config.py`)

**Environment Variables:**
```python
DATABASE_URL
OPENCLAW_GATEWAY_URL
OPENCLAW_GATEWAY_TOKEN
LLM_API_URL
LLM_API_KEY
LLM_MODEL
```

---

## 8. Frontend Architecture

### 8.1 Pages

| Page | Path | Description |
|------|------|-------------|
| **Dashboard** | `/dashboard` | Live stats, system status, quick actions |
| **Agent Studio** | `/agents` | Create/edit/delete agents, teams, start/stop with rate limit handling |
| **Kanban Board** | `/kanban` | 4-column drag-and-drop task management |
| **Org Chart** | `/orgchart` | Hierarchical visualization of agent reporting |
| **Chat** | `/chat` | Agent chat interface with OpenClaw sync |
| **Standup** | `/standup` | Run and view AI standup meetings |
| **Terminal** | `/terminal` | Full-screen agent activity log viewer |

### 8.2 Components

**Sidebar (`components/Sidebar.tsx`):**
- Navigation links
- User profile: "The Boss"
- Collapsible sections

**LogTerminal (`components/LogTerminal.tsx`):**
- Collapsible bottom panel
- Size presets: S/M/L/XL (200/300/400/600px)
- Source filter: All, Backend, Agent
- Action filter: CREATED, DELETED, FAILED, RUN, MOVED, etc.
- Agent filter dropdown
- Auto-scroll toggle
- WebSocket connection for real-time logs
- Color-coded entries:
  - RATE_LIMITED: Orange
  - CREATED/STARTED: Green
  - DELETED/FAILED: Red
  - RUN: Blue
  - MOVED: Yellow
  - STOPPED: Orange
  - UPDATED: Purple

### 8.3 Custom Hooks

**useRateLimit (`lib/useRateLimit.ts`):**
```typescript
function useRateLimit() {
  limits: Map<number, RateLimitEntry>
  setRateLimit(agentId, retrySeconds): void
  getRemainingSeconds(agentId): number
  isLimited(agentId): boolean
}
```

### 8.4 API Client (`lib/api.ts`)

**Custom Error Classes:**
```typescript
class RateLimitError extends Error {
  retrySeconds: number
  agentId: number | null
}

class GatewayRestartError extends Error {
  retrySeconds: number
  agentId: number | null
}
```

**API Methods:**
```typescript
export const api = {
  dashboard: { stats: () => ... },
  teams: { list, get, create, update, delete },
  agents: { list, hierarchy, get, create, update, delete, start, stop, reset, getFiles, updateFiles, getLogs },
  tasks: { list, get, create, update, delete },
  goals: { list, get, create, delete },
  chat: { messages, send, status, clear },
  meetings: { list, runStandup },
  logs: { list },
}
```

### 8.5 TypeScript Interfaces

```typescript
interface Agent {
  id: number
  name: string
  role: string
  chief_id: number | null
  team_id: number | null
  model: string | null
  status: 'active' | 'idle' | 'overheated' | 'offline'
  heartbeat_frequency: number
  active_hours_start: string
  active_hours_end: string
  can_spawn_subagents: boolean
  failure_count: number
  created_at: string
  updated_at: string
  warnings?: string[] | null
  rate_limited?: boolean | null
  retry_seconds?: number | null
}

interface Team {
  id: number
  name: string
  description: string | null
  color: string | null
}

interface Task {
  id: number
  title: string
  description: string | null
  goal_id: number | null
  agent_id: number | null
  status: 'backlog' | 'in_progress' | 'review' | 'done'
  priority: number
  move_reason: string | null
  created_at: string
  updated_at: string
}

interface Goal {
  id: number
  title: string
  description: string | null
  is_main_goal: boolean
}

interface DashboardStats {
  total_agents: number
  active_agents: number
  idle_agents: number
  overheated_agents: number
  total_tasks: number
  backlog_tasks: number
  in_progress_tasks: number
  review_tasks: number
  done_tasks: number
  total_teams: number
}
```

---

## 9. Theme & UI Specifications

### 9.1 Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| **Deep Black** | `#000000` | Primary background |
| **Gold** | `#FBC02D` | Accent, buttons, highlights |
| **White** | `#ffffff` | Primary text |
| **Gray** | `#888888` | Secondary text |
| **Dark Gray** | `#666666` | Muted text |
| **Card BG** | `#111111` | Card backgrounds |
| **Card BG Alt** | `#1a1a1a` | Input backgrounds |
| **Border** | `#333333` | Card borders |
| **Success** | `#4ade80` | Active status, success |
| **Warning** | `#fbbf24` | Warning, overheated, rate limit |
| **Error** | `#ef4444` | Errors, failures |
| **Info** | `#3b82f6` | Info, blue accents |

### 9.2 Component Classes

**Cards:**
```css
.card-cyber {
  background-color: #111;
  border: 1px solid #333;
  border-radius: 0.5rem;
  transition: border-color 0.2s;
}
.card-cyber:hover {
  border-color: #FBC02D;
}
```

**Buttons:**
```css
.btn-gold {
  background: linear-gradient(to right, #FBC02D, #f9a825);
  color: #000;
  font-weight: 600;
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
}
.btn-ghost {
  background: transparent;
  border: 1px solid #333;
  color: #888;
  padding: 0.5rem 1rem;
}
```

**Status Badges:**
```css
.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}
.status-active { background: rgba(74, 222, 128, 0.2); color: #4ade80; }
.status-idle { background: rgba(136, 136, 136, 0.2); color: #888; }
.status-overheated { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
```

### 9.3 Typography

- **Font Family:** System sans-serif stack
- **Heading Sizes:** text-3xl (h1), text-2xl (h2), text-xl (h3)
- **Body:** text-base (16px)
- **Small:** text-sm (14px), text-xs (12px)

---

## 10. Key Features & Patterns

### 10.1 Agent Creation (Two-Step Process)

1. **Create in Database:**
   - Validate name (unique, not empty)
   - Create Agent record
   - Create default workspace files
   - Log CREATED action

2. **Create in OpenClaw:**
   - Call `agents.create` RPC
   - Call `config.get` to get current config
   - Wait 0.5 seconds
   - Call `config.apply` with new agent entry
   - Set heartbeat if frequency > 0

### 10.2 Heartbeat Synchronization

**OpenClaw is Source of Truth:**
- Agent status determined by `heartbeat_frequency` from OpenClaw
- DB mirrors OpenClaw state via periodic sync
- UI uses `heartbeat_frequency > 0` for active state

**Sync Strategy:**
- `sync_openclaw_heartbeats_to_db()` runs every 60 seconds
- Compares DB heartbeat vs OpenClaw heartbeat
- Updates DB when they differ
- Logs HEARTBEAT_SYNC action

### 10.3 Rate Limit Handling

**Detection:**
- Pattern matching on error messages
- HTTP 429 status code
- Keywords: "rate_limit_error", "429", "retry after"

**UI Behavior:**
- Button shows countdown: "Wait 45s..."
- Orange background during countdown
- Button disabled during countdown
- Auto-enables after countdown expires
- Global error message at top of page

**Backend Behavior:**
- Returns structured error with `retry_seconds`
- Frontend stores in `useRateLimit` hook
- Countdown handled via `setInterval`

### 10.4 Gateway Restart Handling

**Health Check:**
- Call `health_check()` before start/stop/edit
- HTTP 503 means gateway restarting

**UI Behavior:**
- Show "Gateway restarting. Retry in 5s."
- Button disabled with countdown
- Auto-retry after 5 seconds

### 10.5 Task Management

**Kanban Board:**
- 4 columns: Backlog, In Progress, Review, Done
- Drag-and-drop (future enhancement)
- Task assignment to agents
- Priority levels (1-5)
- Move reasons for audit trail

**Auto-Assignment:**
- Heartbeat moves BACKLOG → IN_PROGRESS
- Scheduler runs per-agent based on frequency
- Task Executor triggers OpenClaw agent run

**Auto-Review:**
- Tasks in IN_PROGRESS for >10 minutes → REVIEW
- Scheduler checks every 2 minutes
- Logs TASK_AUTO_REVIEW action

**TASKS.md Sync:**
- DB → Markdown: Every 1 minute via scheduler
- Format includes My Tasks and Team Tasks sections
- Status changes reflected in agent workspace

### 10.6 Chat System

**Features:**
- Per-agent chat interface
- Message sync from OpenClaw
- Send messages to agents
- Clear chat history
- View chat status

**Integration:**
- Uses `sessions.send` RPC to OpenClaw
- Fetches history via `chat.history`
- Stores messages in database
- Syncs on demand via `?sync=true` param

### 10.7 Standup Meetings

**Generation:**
- C-suite agents participate
- LLM generates debate (3 rounds)
- Produces transcript and executive briefing
- Stored in Meeting table

**Future:**
- TTS for audio playback
- Telegram/Discord notifications
- Scheduled standups

### 10.8 Agent Hierarchy

**Structure:**
- Self-referential `chief_id` on Agent
- CEO node is synthetic (Boss/CEO)
- Visualized in Org Chart page
- Filtered views (e.g., only show team)

**Permissions:**
- `can_spawn_subagents` boolean
- Sub-agents inherit parent USER.md
- Get unique IDENTITY.md

---

## 11. Configuration

### 11.1 Backend Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/openclaw_mc
# Or SQLite: sqlite:///./openclaw_mc.db

# OpenClaw Gateway
OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18789
OPENCLAW_GATEWAY_TOKEN=your_token_here

# LLM API
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=your_openai_key
LLM_MODEL=gpt-4
```

### 11.2 Frontend Environment Variables

```bash
NEXT_PUBLIC_API_URL=http://localhost:8002
```

### 11.3 Agent Workspace Path

```
~/.openclaw/agents/{agent_name}/
```

---

## 12. Error Handling

### 12.1 Backend Error Types

```python
class RateLimitError(Exception):
    """OpenClaw rate limit exceeded"""
    retry_seconds: int

class GatewayRestartError(Exception):
    """OpenClaw gateway restarting"""
    retry_seconds: int

class OpenClawGatewayError(Exception):
    """General OpenClaw error"""
```

### 12.2 HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | - |
| 429 | Rate Limited | Retry after `retry_seconds` |
| 503 | Gateway Restarting | Retry after 5 seconds |
| 500 | Server Error | Log and alert |

### 12.3 Frontend Error Display

- Global error toast at bottom of screen
- Rate limit countdown on buttons
- Gateway restart countdown with auto-retry
- Console logging for debugging
- Error boundaries for component crashes

---

## 13. Security Considerations

### 13.1 Configuration Security
- Store OpenClaw token in environment variables
- Never commit credentials to repository
- Use `.env` files in `.gitignore`

### 13.2 API Security
- CORS configured for frontend origin
- Input validation on all endpoints
- SQL injection prevention via SQLAlchemy ORM
- Path traversal prevention in workspace manager

### 13.3 Authentication
- OpenClaw uses Ed25519 device identity
- Token-based authentication for gateway
- No user authentication (single-user system)

---

## 14. Deployment

### 14.1 Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

### 14.2 Frontend
```bash
cd frontend
npm install
npm run dev  # Development
npm run build  # Production build
```

### 14.3 Database
```bash
# Create database
createdb openclaw_mc

# Tables auto-created on startup
```

---

## 15. Testing

### 15.1 Backend Tests
```bash
cd backend
pytest tests/ -v
```

### 15.2 Frontend Tests
```bash
cd frontend
npm test
```

---

## 16. Implementation Roadmap

### Phase 1: Foundation ✅
- [x] FastAPI backend with PostgreSQL
- [x] Database schema for all entities
- [x] OpenClaw Gateway WebSocket RPC integration
- [x] Basic CRUD operations
- [x] Agent workspace file management

### Phase 2: Agent Lifecycle ✅
- [x] Two-step agent creation (DB + OpenClaw)
- [x] Start/Stop with heartbeat management
- [x] Rate limit detection and handling
- [x] Gateway restart handling
- [x] Heartbeat synchronization

### Phase 3: Task Management ✅
- [x] Kanban board UI
- [x] Task CRUD operations
- [x] Auto-assignment from heartbeat
- [x] TASKS.md bidirectional sync
- [x] Task filtering and assignment

### Phase 4: Real-Time Features ✅
- [x] WebSocket log streaming
- [x] Log terminal component
- [x] Real-time backend log capture
- [x] Agent activity logging

### Phase 5: Chat & Communication ✅
- [x] Agent chat interface
- [x] OpenClaw chat sync
- [x] Message history
- [x] Send messages to agents

### Phase 6: Meetings & Automation ✅
- [x] Standup meeting generation
- [x] LLM integration for debates
- [x] Meeting transcripts and briefings

### Phase 7: UI/UX Polish ✅
- [x] Cyber-Luxury theme
- [x] Rate limit countdown UI
- [x] Gateway status indicators
- [x] Timezone-aware timestamps
- [x] Error handling and user feedback

### Phase 8: Advanced Features (Planned)
- [ ] Daily standup automation (scheduled)
- [ ] TTS for meeting transcripts
- [ ] Telegram/Discord notifications
- [ ] Human-in-the-loop toggle
- [ ] Voice integration
- [ ] Task drag-and-drop
- [ ] Agent performance metrics
- [ ] Task completion analytics

---

## 17. Key Discoveries & Lessons Learned

### 17.1 OpenClaw Gateway Behavior
- Gateway restarts frequently during config changes
- Always check health before operations
- Use 5s retry delay when HTTP 503 received
- `config.apply` has ~60s cooldown between calls

### 17.2 Rate Limit Patterns
- Error messages contain: "rate_limit_error", "429", "retry after N seconds"
- Must extract retry seconds from error text
- Default retry is 60 seconds

### 17.3 Heartbeat Sync Strategy
- OpenClaw is source of truth for heartbeat state
- DB mirrors OpenClaw state via periodic sync
- UI uses `heartbeat_frequency > 0` to determine active status

### 17.4 Agent Naming
- Never rename agents after creation
- OpenClaw uses name as identifier
- Changing names breaks config references

### 17.5 Workspace Files
- Markdown files provide agent personality
- TASKS.md synced bidirectionally with DB
- Files auto-created on agent creation
- Updated when agent edited

---

## 18. File Structure

```
/home/rishabh/github_others/my-mission-control/
├── PRD.md                          # This document
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI route handlers
│   │   │   ├── __init__.py
│   │   │   ├── agents.py           # Agent CRUD + lifecycle
│   │   │   ├── chat.py             # Chat endpoints
│   │   │   ├── dashboard.py        # Dashboard stats
│   │   │   ├── logs.py             # Activity logs
│   │   │   ├── meetings.py         # Standup meetings
│   │   │   ├── messages.py         # System messages
│   │   │   ├── settings.py         # System settings
│   │   │   ├── tasks.py            # Tasks + Goals
│   │   │   └── teams.py            # Teams
│   │   ├── core/                   # Infrastructure
│   │   │   ├── config.py           # Settings
│   │   │   ├── database.py         # SQLAlchemy setup
│   │   │   ├── log_stream.py       # WebSocket logging
│   │   │   ├── rate_limit.py       # Rate limit utils
│   │   │   └── scheduler.py        # Background jobs
│   │   ├── models/                 # Data layer
│   │   │   ├── models.py           # SQLAlchemy models
│   │   │   └── schemas.py          # Pydantic schemas
│   │   ├── services/               # Business logic
│   │   │   ├── openclaw/           # OpenClaw RPC layer
│   │   │   │   ├── device_identity.py
│   │   │   │   ├── gateway_rpc.py
│   │   │   │   └── session_service.py
│   │   │   ├── llm_service.py      # LLM integration
│   │   │   ├── openclaw_gateway.py # Gateway client
│   │   │   ├── task_executor.py    # Task automation
│   │   │   └── workspace_manager.py # File management
│   │   └── main.py                 # FastAPI app entry
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js pages
│   │   │   ├── agents/             # Agent Studio
│   │   │   │   └── page.tsx
│   │   │   ├── chat/               # Chat interface
│   │   │   │   └── page.tsx
│   │   │   ├── dashboard/          # Dashboard
│   │   │   │   └── page.tsx
│   │   │   ├── kanban/             # Kanban board
│   │   │   │   └── page.tsx
│   │   │   ├── orgchart/           # Org chart
│   │   │   │   └── page.tsx
│   │   │   ├── standup/            # Standup meetings
│   │   │   │   └── page.tsx
│   │   │   ├── terminal/           # Full terminal
│   │   │   │   └── page.tsx
│   │   │   ├── globals.css         # Global styles
│   │   │   ├── layout.tsx          # Root layout
│   │   │   └── page.tsx            # Home redirect
│   │   ├── components/             # React components
│   │   │   ├── LogTerminal.tsx     # Log terminal
│   │   │   └── Sidebar.tsx         # Navigation
│   │   └── lib/                    # Utilities
│   │       ├── api.ts              # API client
│   │       └── useRateLimit.ts     # Rate limit hook
│   └── package.json
```

---

**End of PRD**

This document reflects the current state of OpenClaw Mission Control implementation.

**Last Updated:** 2024  
**Version:** 1.0
