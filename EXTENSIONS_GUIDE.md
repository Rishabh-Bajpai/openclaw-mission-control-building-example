# Extension Guide: Building Custom Features

This guide documents the 3 extensions that have been implemented in OpenClaw Mission Control:

1. **Task Dependencies** - Block tasks until prerequisites complete
2. **Agent-to-Agent Messaging** - Enable direct communication between agents
3. **Agent Performance Metrics** - Track and visualize agent productivity

---

## Extension 1: Task Dependencies

Tasks that can't start until other tasks are completed.

```
Task A (Setup Database)
    │
    ▼
Task B (Build API) ──▶ Task C (Write Tests)
    │
    ▼
Task D (Deploy)
```

### Implementation

**Files modified:**
- `backend/app/models/models.py` - Added `depends_on` field to Task model
- `backend/app/models/schemas.py` - Updated Pydantic schemas
- `backend/app/api/tasks.py` - Added dependency checking logic
- `backend/app/core/scheduler.py` - Updated heartbeat to respect dependencies

### Usage

Create a task with a dependency:
```bash
curl -X POST http://localhost:8002/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Build API", "depends_on": 1}'
```

Try to move a blocked task to IN_PROGRESS:
```bash
curl -X PUT http://localhost:8002/tasks/2 \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'
# Returns: 400 "Blocked: Depends on task 'Setup Database' which is backlog"
```

### API

The `depends_on` field is available on:
- `POST /tasks/` - Create task with `depends_on` field
- `PUT /tasks/{id}` - Update task to add/remove dependency
- `GET /tasks/` - Response includes `depends_on` and `dependency_title`

---

## Extension 2: Agent-to-Agent Messaging

Direct messaging system between agents.

```
┌─────────┐      Message      ┌─────────┐
│  Agent A  │ ──────────────────▶ │  Agent B  │
│ (CEO)    │  "Need status     │ (Dev)    │
│          │   update"         │          │
└─────────┘                   └─────────┘
```

### Implementation

**Files modified:**
- `backend/app/models/models.py` - Added `sender_agent_id`, `recipient_agent_id`, `message_type` fields to Message model
- `backend/app/models/schemas.py` - Updated Message schemas
- `backend/app/api/messages.py` - Added agent messaging endpoints

### Usage

Send a message from one agent to another:
```bash
curl -X POST http://localhost:8002/messages/agent/1/to/2 \
  -H "Content-Type: application/json" \
  -d '{"content": "Need status update on the API task"}'
```

Get messages for an agent:
```bash
curl http://localhost:8002/messages/agent/2?include_sent=true
```

Get conversation between two agents:
```bash
curl http://localhost:8002/messages/conversation/1/2
```

### API

New endpoints:
- `POST /messages/agent/{sender_id}/to/{recipient_id}` - Send agent-to-agent message
- `GET /messages/agent/{agent_id}` - Get agent's messages
- `GET /messages/conversation/{agent1_id}/{agent2_id}` - Get conversation between two agents

---

## Extension 3: Agent Performance Metrics

Track agent productivity with completion counts and success rates.

### Implementation

**Files modified:**
- `backend/app/models/models.py` - Added `tasks_completed`, `tasks_failed`, `total_working_time_minutes` fields to Agent model
- `backend/app/models/schemas.py` - Updated Agent schemas
- `backend/app/api/metrics.py` - New API endpoints
- `backend/app/main.py` - Registered metrics router
- `backend/app/core/scheduler.py` - Metrics are tracked automatically

### Usage

Get metrics for an agent:
```bash
curl http://localhost:8002/metrics/agent/1
```

Get leaderboard of top performers:
```bash
curl http://localhost:8002/metrics/leaderboard?limit=10
```

### Response Example

```json
{
  "agent_id": 1,
  "agent_name": "CEO",
  "tasks_completed": 15,
  "tasks_in_progress": 2,
  "tasks_failed": 1,
  "total_working_time_minutes": 450,
  "success_rate": 93.8
}
```

### API

- `GET /metrics/agent/{agent_id}` - Get metrics for specific agent
- `GET /metrics/leaderboard?limit=10` - Get top performing agents

---

## Metrics Tracking

Metrics are tracked automatically when:
- A task times out and moves to REVIEW (auto-completion)
- Task is marked as DONE manually

The system tracks:
- `tasks_completed` - Total tasks moved to DONE
- `tasks_failed` - Tasks that failed (can be incremented manually)
- `total_working_time_minutes` - Sum of time spent on completed tasks

---

## Future Extensions Ideas

- **Task Attachments** - Upload files to tasks
- **Agent Skills** - Assign specific competencies to agents
- **Recurring Tasks** - Daily/weekly repeating tasks
- **Task Comments** - Discussion threads on tasks
- **Workflow Automation Rules** - "When X happens, do Y"
