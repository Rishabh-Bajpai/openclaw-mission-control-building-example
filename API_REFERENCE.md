# API Reference

Complete reference for all REST API endpoints in OpenClaw Mission Control.

## Base URL

```
Development: http://localhost:8002
Production: https://your-domain.com/api
```

## Authentication

Currently, the API does not require authentication. All endpoints are open.

> **Note**: For production use, add authentication middleware to protect sensitive endpoints.

## Response Format

All responses are JSON with the following structure:

### Success Response

```json
{
  "data": { /* response data */ },
  "status": "success"
}
```

### Error Response

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

## HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request succeeded, no body |
| 400 | Bad Request | Invalid request data |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Pydantic validation failed |
| 429 | Rate Limited | Too many requests |
| 503 | Service Unavailable | Gateway restarting |
| 500 | Server Error | Internal server error |

## Endpoints

### Agents

#### List All Agents

```http
GET /agents/
```

**Response**: Array of Agent objects

```json
[
  {
    "id": 1,
    "name": "CEO",
    "role": "Chief Executive Officer",
    "status": "active",
    "team_id": 1,
    "chief_id": null,
    "heartbeat_frequency": 15,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

#### Get Agent Hierarchy

```http
GET /agents/hierarchy
```

Returns agents with team and chief names for org chart display.

**Response**:
```json
[
  {
    "id": 1,
    "name": "CEO",
    "role": "Chief Executive Officer",
    "team_name": "Leadership",
    "chief_name": null,
    "status": "active",
    "subordinate_count": 3
  }
]
```

#### Get Single Agent

```http
GET /agents/{agent_id}
```

**Parameters**:
- `agent_id` (path): Agent ID

**Response**: Agent object

```json
{
  "id": 1,
  "name": "CEO",
  "role": "Chief Executive Officer",
  "status": "active",
  "team_id": 1,
  "chief_id": null,
  "model": "gpt-4",
  "heartbeat_frequency": 15,
  "active_hours_start": "00:00",
  "active_hours_end": "23:59",
  "can_spawn_subagents": true,
  "failure_count": 0,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Create Agent

```http
POST /agents/
```

**Request Body**:
```json
{
  "name": "Developer",
  "role": "Senior Developer",
  "team_id": 1,
  "chief_id": 1,
  "heartbeat_frequency": 15,
  "can_spawn_subagents": false
}
```

**Required Fields**:
- `name`: Unique agent name (max 100 chars)
- `role`: Agent's job title (max 100 chars)

**Optional Fields**:
- `team_id`: Team assignment
- `chief_id`: Reporting manager (self-reference)
- `heartbeat_frequency`: Minutes between heartbeats (default: 15)
- `can_spawn_subagents`: Permission to create sub-agents (default: false)

**Response**: Created agent (201)

#### Update Agent

```http
PUT /agents/{agent_id}
```

**Request Body**:
```json
{
  "role": "Lead Developer",
  "team_id": 2,
  "heartbeat_frequency": 30
}
```

> **Note**: Agent name cannot be changed after creation.

**Response**: Updated agent

#### Delete Agent

```http
DELETE /agents/{agent_id}
```

**Response**: 204 No Content

#### Start Agent

```http
POST /agents/{agent_id}/start
```

Enables heartbeat and triggers initial task check.

**Response**:
```json
{
  "id": 1,
  "name": "CEO",
  "status": "active",
  "message": "Agent started successfully"
}
```

#### Stop Agent

```http
POST /agents/{agent_id}/stop
```

Disables heartbeat.

**Response**:
```json
{
  "id": 1,
  "name": "CEO",
  "status": "idle",
  "message": "Agent stopped"
}
```

#### Reset Agent

```http
POST /agents/{agent_id}/reset
```

Clears failure count and sets status to idle.

**Response**:
```json
{
  "id": 1,
  "name": "CEO",
  "status": "idle",
  "failure_count": 0,
  "message": "Agent reset"
}
```

#### Get Agent Files

```http
GET /agents/{agent_id}/files
```

Returns agent workspace files (SOUL.md, IDENTITY.md, etc.)

**Response**:
```json
{
  "SOUL.md": "# Core Values...",
  "IDENTITY.md": "# Identity...",
  "TASKS.md": "# Task Board...",
  "AGENTS.md": "# Governance...",
  "MEMORY.md": "# Memory...",
  "USER.md": "# User Context...",
  "HEARTBEAT.md": "# Heartbeat Instructions...",
  "models.json": "{...}"
}
```

#### Update Agent Files

```http
PUT /agents/{agent_id}/files
```

**Request Body**:
```json
{
  "SOUL.md": "# Updated values...",
  "MEMORY.md": "# New memory entry..."
}
```

**Response**:
```json
{
  "message": "Files updated successfully"
}
```

#### Get Agent Logs

```http
GET /agents/{agent_id}/logs?limit=50
```

**Query Parameters**:
- `limit` (optional): Number of logs to return (default: 50, max: 500)

**Response**:
```json
[
  {
    "id": 1,
    "agent_id": 1,
    "action": "CREATED",
    "details": "Agent CEO created",
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "agent_id": 1,
    "action": "HEARTBEAT_AUTO_ASSIGN",
    "details": "Auto-assigned 2 tasks",
    "created_at": "2024-01-15T10:45:00Z"
  }
]
```

#### Get Subordinates

```http
GET /agents/{agent_id}/subordinates
```

Returns agents that report to this agent.

**Response**: Array of Agent objects

---

### Tasks

#### List All Tasks

```http
GET /tasks/
```

**Query Parameters**:
- `status` (optional): Filter by status (backlog, in_progress, review, done)
- `agent_id` (optional): Filter by assigned agent
- `goal_id` (optional): Filter by goal

**Example**: `/tasks/?status=in_progress&agent_id=1`

**Response**:
```json
[
  {
    "id": 1,
    "title": "Build landing page",
    "description": "Create HTML/CSS for landing page",
    "status": "in_progress",
    "agent_id": 1,
    "goal_id": 1,
    "priority": 3,
    "move_reason": "Starting work",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

#### Get Single Task

```http
GET /tasks/{task_id}
```

**Response**: Task object

#### Create Task

```http
POST /tasks/
```

**Request Body**:
```json
{
  "title": "Build API endpoint",
  "description": "Create FastAPI endpoint for users",
  "agent_id": 1,
  "goal_id": 1,
  "priority": 2
}
```

**Required Fields**:
- `title`: Task title (max 200 chars)

**Optional Fields**:
- `description`: Task details
- `agent_id`: Assigned agent
- `goal_id`: Associated goal
- `priority`: 1-5 (default: 1)

**Response**: Created task (201)

#### Update Task

```http
PUT /tasks/{task_id}
```

**Request Body**:
```json
{
  "status": "review",
  "move_reason": "Task completed"
}
```

**Fields**:
- `status`: New status (backlog, in_progress, review, done)
- `move_reason`: Why status changed (for audit)
- `agent_id`: Reassign to different agent
- `title`: Update title
- `description`: Update description

**Response**: Updated task

#### Delete Task

```http
DELETE /tasks/{task_id}
```

**Response**: 204 No Content

#### Unassign Task

```http
POST /tasks/{task_id}/unassign
```

Moves task back to backlog and clears agent assignment.

**Response**: Updated task

#### Get Agent Tasks (Agent-Facing)

```http
GET /agent/tasks/my-tasks/{agent_id}
```

Returns tasks grouped by status for agent workspace.

**Response**:
```json
{
  "agent_id": 1,
  "tasks": {
    "BACKLOG": [],
    "IN_PROGRESS": [],
    "REVIEW": [],
    "DONE": []
  },
  "total": 0,
  "markdown": "# Task Board\n\n## BACKLOG\n..."
}
```

#### Get Team Tasks (Agent-Facing)

```http
GET /agent/tasks/team-tasks/{agent_id}
```

Returns team tasks grouped by status.

**Response**: Same structure as my-tasks, but includes `team_id`, `team_agent_ids`, and `assigned_to` field on each task.

---

### Teams

#### List All Teams

```http
GET /teams/
```

**Response**:
```json
[
  {
    "id": 1,
    "name": "Engineering",
    "description": "Backend development team",
    "color": "#4ade80",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### Get Single Team

```http
GET /teams/{team_id}
```

**Response**: Team object

#### Create Team

```http
POST /teams/
```

**Request Body**:
```json
{
  "name": "Design",
  "description": "UI/UX design team",
  "color": "#f59e0b"
}
```

**Required Fields**:
- `name`: Unique team name

**Optional Fields**:
- `description`: Team purpose
- `color`: Hex color code (e.g., #FF5733)

**Response**: Created team (201)

#### Update Team

```http
PUT /teams/{team_id}
```

**Request Body**:
```json
{
  "name": "Engineering Team",
  "color": "#3b82f6"
}
```

**Response**: Updated team

#### Delete Team

```http
DELETE /teams/{team_id}
```

**Response**: 204 No Content

---

### Goals

#### List All Goals

```http
GET /goals/
```

**Response**:
```json
[
  {
    "id": 1,
    "title": "Q1 2024 Launch",
    "description": "Complete product launch by end of Q1",
    "is_main_goal": true,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### Get Single Goal

```http
GET /goals/{goal_id}
```

**Response**: Goal object

#### Create Goal

```http
POST /goals/
```

**Request Body**:
```json
{
  "title": "Improve Performance",
  "description": "Reduce API response time",
  "is_main_goal": false
}
```

**Note**: Setting `is_main_goal: true` automatically unsets previous main goal.

**Response**: Created goal (201)

#### Delete Goal

```http
DELETE /goals/{goal_id}
```

**Response**: 204 No Content

---

### Chat

#### Get Chat Messages

```http
GET /chat/{agent_id}/messages?sync=true
```

**Query Parameters**:
- `sync` (optional): Sync messages from OpenClaw before returning (default: false)

**Response**:
```json
[
  {
    "id": 1,
    "agent_id": 1,
    "sender": "user",
    "content": "Hello!",
    "is_from_user": true,
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "agent_id": 1,
    "sender": "CEO",
    "content": "Hello! How can I help?",
    "is_from_user": false,
    "created_at": "2024-01-15T10:31:00Z"
  }
]
```

#### Send Chat Message

```http
POST /chat/{agent_id}/messages
```

**Request Body**:
```json
{
  "content": "What's the status of task #5?",
  "is_from_user": true
}
```

**Response**: Created message

#### Clear Chat History

```http
DELETE /chat/{agent_id}/messages
```

**Response**: 204 No Content

#### Get Chat Status

```http
GET /chat/{agent_id}/status
```

**Response**:
```json
{
  "agent_id": 1,
  "has_messages": true,
  "last_message": "Hello! How can I help?",
  "last_message_time": "2024-01-15T10:31:00Z"
}
```

---

### Meetings

#### List All Meetings

```http
GET /meetings/
```

**Query Parameters**:
- `meeting_type` (optional): Filter by type (standup, etc.)

**Response**:
```json
[
  {
    "id": 1,
    "title": "Daily Standup - Jan 15",
    "meeting_type": "standup",
    "duration_minutes": 15,
    "created_at": "2024-01-15T09:00:00Z"
  }
]
```

#### Get Single Meeting

```http
GET /meetings/{meeting_id}
```

**Response**: Meeting object

#### Run Standup Meeting

```http
POST /meetings/standup
```

Triggers AI-generated standup meeting with C-suite agents.

**Response**:
```json
{
  "id": 1,
  "title": "Daily Standup - Jan 15, 2024",
  "meeting_type": "standup",
  "transcript": "CEO: Good morning team...\nCTO: We completed the API...",
  "briefing": "API development on track. UI designs approved.",
  "duration_minutes": 12,
  "created_at": "2024-01-15T09:00:00Z"
}
```

#### Get Meeting Transcript

```http
GET /meetings/{meeting_id}/transcript
```

**Response**:
```json
{
  "transcript": "Full conversation text...",
  "briefing": "Executive summary...",
  "duration_minutes": 15
}
```

---

### Logs

#### List All Logs

```http
GET /logs/?agent_id=1&action=CREATED&limit=50
```

**Query Parameters**:
- `agent_id` (optional): Filter by agent
- `action` (optional): Filter by action type
- `limit` (optional): Number of logs (default: 50, max: 500)

**Response**:
```json
[
  {
    "id": 1,
    "agent_id": 1,
    "action": "CREATED",
    "details": "Agent CEO created",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

**Action Types**:
- `CREATED`: Agent created
- `STARTED`: Agent started
- `STOPPED`: Agent stopped
- `RESET`: Agent reset
- `DELETED`: Agent deleted
- `HEARTBEAT_AUTO_ASSIGN`: Tasks auto-assigned
- `TASK_STARTED`: Task execution started
- `TASK_COMPLETED`: Task completed
- `TASK_AUTO_REVIEW`: Task auto-moved to review
- `RATE_LIMITED`: Rate limit hit

---

### Settings

#### Get Settings

```http
GET /settings/
```

**Response**:
```json
{
  "llm_api_url": "https://api.openai.com/v1/chat/completions",
  "llm_model": "gpt-4",
  "debug": true,
  "app_name": "OpenClaw Mission Control",
  "openclaw_gateway_url": "ws://127.0.0.1:18789",
  "openclaw_connected": true
}
```

#### Get LLM Settings

```http
GET /settings/llm
```

**Response**:
```json
{
  "api_url": "https://api.openai.com/v1/chat/completions",
  "api_key": "",  // Masked for security
  "model": "gpt-4",
  "note": "LLM is managed by OpenClaw"
}
```

#### Update LLM Settings

```http
PUT /settings/llm
```

**Request Body**:
```json
{
  "api_url": "http://localhost:1234/v1/chat/completions",
  "api_key": "sk-...",
  "model": "local-model"
}
```

**Response**: Updated settings

#### Get OpenClaw Status

```http
GET /settings/openclaw
```

**Response**:
```json
{
  "connected": true,
  "gateway_url": "ws://127.0.0.1:18789",
  "token_configured": true,
  "error": null
}
```

#### Test OpenClaw Connection

```http
POST /settings/openclaw/test
```

**Response**:
```json
{
  "message": "OpenClaw Gateway is connected",
  "status": {
    "connected": true,
    "agents_count": 5
  }
}
```

---

### Dashboard

#### Get Dashboard Stats

```http
GET /dashboard/stats
```

**Response**:
```json
{
  "total_agents": 10,
  "active_agents": 3,
  "idle_agents": 6,
  "overheated_agents": 1,
  "total_tasks": 25,
  "backlog_tasks": 10,
  "in_progress_tasks": 8,
  "review_tasks": 4,
  "done_tasks": 3,
  "total_teams": 3
}
```

---

### System

#### Root Endpoint

```http
GET /
```

**Response**:
```json
{
  "name": "OpenClaw Mission Control",
  "status": "operational",
  "version": "1.0.0"
}
```

#### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy"
}
```

---

## WebSocket

### Log Streaming

Connect to WebSocket endpoint for real-time logs:

```javascript
const ws = new WebSocket('ws://localhost:8002/ws/logs');

ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(log);
};
```

**Message Format**:
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "level": "INFO",
  "logger": "app.api.agents",
  "message": "Agent created: CEO"
}
```

**Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

## Error Handling

### Rate Limit Error (429)

```json
{
  "detail": {
    "message": "Rate limit exceeded",
    "retry_seconds": 60,
    "agent_id": 1
  }
}
```

**Frontend Handling**:
```typescript
try {
  await api.agents.start(agentId);
} catch (error) {
  if (error instanceof RateLimitError) {
    // Show countdown: "Retry in 60s..."
    startCountdown(error.retrySeconds);
  }
}
```

### Gateway Restart Error (503)

```json
{
  "detail": {
    "message": "OpenClaw Gateway is restarting",
    "retry_seconds": 5
  }
}
```

**Frontend Handling**:
```typescript
try {
  await api.agents.start(agentId);
} catch (error) {
  if (error instanceof GatewayRestartError) {
    // Auto-retry after 5 seconds
    setTimeout(() => api.agents.start(agentId), 5000);
  }
}
```

---

## Pagination

Most list endpoints support pagination:

```http
GET /agents/?skip=0&limit=50
GET /tasks/?skip=100&limit=50
```

**Parameters**:
- `skip`: Number of items to skip (offset)
- `limit`: Number of items to return (max: 500)

**Response includes pagination info**:
```json
{
  "items": [...],
  "total": 150,
  "skip": 0,
  "limit": 50
}
```

---

## Filtering

### Agents
- `status`: active, idle, overheated, offline
- `team_id`: Filter by team

### Tasks
- `status`: backlog, in_progress, review, done
- `agent_id`: Filter by assigned agent
- `goal_id`: Filter by goal

### Logs
- `agent_id`: Filter by agent
- `action`: Filter by action type
- `since`: ISO timestamp
- `until`: ISO timestamp

**Example**:
```http
GET /logs/?agent_id=1&action=HEARTBEAT_AUTO_ASSIGN&since=2024-01-15T00:00:00Z
```

---

## SDKs & Client Libraries

### JavaScript/TypeScript

```typescript
// Using the built-in api client
import { api } from '@/lib/api';

// Get all agents
const agents = await api.agents.list();

// Create an agent
const newAgent = await api.agents.create({
  name: 'Developer',
  role: 'Senior Developer',
  team_id: 1
});

// Update task status
await api.tasks.update(taskId, {
  status: 'review',
  move_reason: 'Completed successfully'
});
```

### Python

```python
import httpx

BASE_URL = "http://localhost:8002"

async def get_agents():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/agents/")
        return response.json()

async def create_agent(name: str, role: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/agents/",
            json={"name": name, "role": role}
        )
        return response.json()
```

### cURL Examples

```bash
# List agents
curl http://localhost:8002/agents/

# Create agent
curl -X POST http://localhost:8002/agents/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "role": "Developer"}'

# Update task
curl -X PUT http://localhost:8002/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "done", "move_reason": "Completed"}'
```

---

## Rate Limits

The API has the following rate limits:

- **OpenClaw Gateway**: ~60 second cooldown between `config.apply` calls
- **Background Jobs**: Minimum 1 minute intervals
- **WebSocket**: No specific limit, but implement reconnection logic

**Best Practices**:
1. Implement retry logic with exponential backoff
2. Cache responses where appropriate
3. Use WebSocket for real-time updates instead of polling
4. Batch operations when possible

---

## Changelog

### v1.0.0
- Initial API release
- Agent CRUD operations
- Task management
- Team management
- Real-time log streaming
- Chat functionality
- Meeting generation

---

For questions or issues, please open an issue on GitHub.
