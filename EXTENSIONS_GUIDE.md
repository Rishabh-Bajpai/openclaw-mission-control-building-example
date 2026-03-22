# Extension Guide: Building Custom Features

This guide walks you through implementing 3 popular extensions to OpenClaw Mission Control:

1. **Task Dependencies** - Block tasks until prerequisites complete
2. **Agent-to-Agent Messaging** - Enable direct communication between agents
3. **Agent Performance Metrics** - Track and visualize agent productivity

Each extension includes:
- 🎯 What we're building
- 📁 Files to modify
- 💻 Code implementation
- 🧪 Testing steps
- 💡 Extension ideas

---

## Extension 1: Task Dependencies

**Difficulty**: ⭐⭐ Easy  
**Time**: 30 minutes  
**Skills**: Database, API, Frontend

### What We're Building

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

**Example Use Cases**:
- Can't deploy until tests pass
- Can't write tests until API is built
- Can't build UI until design is approved

### Implementation

#### Step 1: Add Database Field

**File**: `backend/app/models/models.py`

```python
class Task(Base):
    __tablename__ = "tasks"
    
    # ... existing fields ...
    
    # NEW: Task dependency
    depends_on = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    """
    Foreign key to another task that must be completed before this task.
    
    If set, this task cannot move from BACKLOG to IN_PROGRESS until
    the dependency task status is DONE.
    """
    
    # NEW: Relationship for dependency
    dependency = relationship("Task", remote_side=[id], back_populates="dependents")
    """The task this task depends on."""
    
    dependents = relationship("Task", back_populates="dependency")
    """Tasks that depend on this task."""
```

**Explanation**:
- `depends_on`: Stores the ID of the prerequisite task
- `dependency`: Relationship to access the prerequisite task object
- `dependents`: Relationship to see which tasks depend on this one

#### Step 2: Update Pydantic Schema

**File**: `backend/app/models/schemas.py` (create if doesn't exist)

```python
from pydantic import BaseModel
from typing import Optional, List

# ... existing schemas ...

class TaskCreate(BaseModel):
    """Schema for creating a new task"""
    title: str
    description: Optional[str] = None
    agent_id: Optional[int] = None
    goal_id: Optional[int] = None
    priority: int = 1
    depends_on: Optional[int] = None  # NEW

class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    agent_id: Optional[int] = None
    priority: Optional[int] = None
    move_reason: Optional[str] = None
    depends_on: Optional[int] = None  # NEW

class TaskResponse(BaseModel):
    """Schema for task responses"""
    id: int
    title: str
    description: Optional[str]
    status: str
    agent_id: Optional[int]
    priority: int
    depends_on: Optional[int]  # NEW
    dependency_title: Optional[str] = None  # NEW: Human-readable
    
    class Config:
        from_attributes = True
```

#### Step 3: Add Dependency Check Logic

**File**: `backend/app/api/tasks.py`

Add this function:

```python
async def check_task_dependencies(db: AsyncSession, task: Task) -> tuple[bool, str]:
    """
    Check if a task can proceed based on dependencies.
    
    Args:
        db: Database session
        task: Task to check
    
    Returns:
        tuple: (can_proceed: bool, message: str)
        
    Example:
        >>> can_proceed, msg = await check_task_dependencies(db, task)
        >>> if not can_proceed:
        ...     raise HTTPException(status_code=400, detail=msg)
    """
    if not task.depends_on:
        return True, "No dependencies"
    
    # Get dependency task
    dependency_result = await db.execute(
        select(Task).where(Task.id == task.depends_on)
    )
    dependency = dependency_result.scalar_one_or_none()
    
    if not dependency:
        return True, "Dependency not found (may have been deleted)"
    
    if dependency.status != TaskStatus.DONE:
        return False, f"Blocked: Depends on task '{dependency.title}' which is {dependency.status}"
    
    return True, "Dependencies satisfied"
```

Update the task update endpoint:

```python
@router.put("/{task_id}")
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a task with dependency checking"""
    
    # Get existing task
    result = await db.execute(select(Task).where(Task.id == task_id))
    db_task = result.scalar_one_or_none()
    
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # NEW: Check if trying to move to IN_PROGRESS
    if task_update.status == "in_progress" and db_task.status == TaskStatus.BACKLOG:
        can_proceed, message = await check_task_dependencies(db, db_task)
        if not can_proceed:
            raise HTTPException(status_code=400, detail=message)
    
    # NEW: Update dependency field
    if task_update.depends_on is not None:
        # Prevent self-dependency
        if task_update.depends_on == task_id:
            raise HTTPException(status_code=400, detail="Task cannot depend on itself")
        
        # Prevent circular dependencies
        if await would_create_cycle(db, task_id, task_update.depends_on):
            raise HTTPException(status_code=400, detail="Would create circular dependency")
        
        db_task.depends_on = task_update.depends_on
    
    # ... rest of update logic ...
    
    await db.commit()
    return db_task

async def would_create_cycle(db: AsyncSession, task_id: int, depends_on: int) -> bool:
    """
    Check if adding a dependency would create a circular dependency.
    
    Example of cycle: A -> B -> C -> A (bad!)
    """
    current = depends_on
    visited = set()
    
    while current:
        if current == task_id:
            return True  # Found a cycle
        if current in visited:
            break  # Already checked this path
        
        visited.add(current)
        
        result = await db.execute(
            select(Task.depends_on).where(Task.id == current)
        )
        current = result.scalar_one_or_none()
    
    return False
```

#### Step 4: Update Scheduler

**File**: `backend/app/core/scheduler.py`

Update `run_agent_heartbeat()`:

```python
def run_agent_heartbeat():
    """Run heartbeat for all agents with dependency checking"""
    db = SessionLocal()
    try:
        agents = db.query(Agent).filter(
            Agent.heartbeat_frequency > 0,
            Agent.status != AgentStatus.OVERHEATED
        ).all()
        
        for agent in agents:
            # Get pending tasks without dependencies
            pending_tasks = db.query(Task).filter(
                Task.agent_id == agent.id,
                Task.status == TaskStatus.BACKLOG,
                # NEW: Only tasks with no dependencies OR satisfied dependencies
                (
                    (Task.depends_on == None) |  # No dependency
                    (Task.dependency.status == TaskStatus.DONE)  # Dependency done
                )
            ).all()
            
            if pending_tasks:
                # Move tasks to IN_PROGRESS
                for task in pending_tasks:
                    task.status = TaskStatus.IN_PROGRESS
                
                db.commit()
                
                # Log the action
                log = AgentLog(
                    agent_id=agent.id,
                    action="HEARTBEAT_AUTO_ASSIGN",
                    details=f"Auto-assigned {len(pending_tasks)} tasks (dependencies checked)"
                )
                db.add(log)
                db.commit()
                
                # Trigger OpenClaw agent
                # ... existing code ...
                
    except Exception as e:
        logger.error(f"Error in agent heartbeat: {e}")
        db.rollback()
    finally:
        db.close()
```

#### Step 5: Update Frontend

**File**: `frontend/src/app/kanban/page.tsx` (or tasks page)

Add dependency selection to task creation form:

```typescript
// Add to task creation form
const [selectedDependency, setSelectedDependency] = useState<number | null>(null);

// In the form JSX
<div className="form-group">
  <label>Depends On (Optional)</label>
  <select
    value={selectedDependency || ''}
    onChange={(e) => setSelectedDependency(e.target.value ? parseInt(e.target.value) : null)}
  >
    <option value="">No dependency</option>
    {tasks
      .filter(t => t.id !== editingTask?.id) // Can't depend on self
      .map(task => (
        <option key={task.id} value={task.id}>
          {task.title} ({task.status})
        </option>
      ))}
  </select>
</div>

// When creating/updating task
const handleSubmit = async () => {
  const taskData = {
    title,
    description,
    agent_id: selectedAgent,
    priority: parseInt(priority),
    depends_on: selectedDependency, // Include dependency
  };
  
  if (editingTask) {
    await api.tasks.update(editingTask.id, taskData);
  } else {
    await api.tasks.create(taskData);
  }
};
```

Add visual indicator for blocked tasks:

```typescript
// In task card component
const TaskCard = ({ task }: { task: Task }) => {
  const isBlocked = task.depends_on && task.status !== 'done';
  
  return (
    <div className={`task-card ${isBlocked ? 'blocked' : ''}`}>
      <h3>{task.title}</h3>
      {isBlocked && (
        <div className="dependency-warning">
          ⏳ Blocked: Waiting for Task #{task.depends_on}
        </div>
      )}
      {/* ... rest of card ... */}
    </div>
  );
};
```

Add CSS for blocked tasks:

```css
/* In your global CSS or component */
.task-card.blocked {
  border: 2px solid #f59e0b;
  opacity: 0.7;
}

.dependency-warning {
  color: #f59e0b;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
```

### Testing

1. **Create tasks**:
   ```bash
   # Task A
   curl -X POST http://localhost:8002/tasks/ \
     -H "Content-Type: application/json" \
     -d '{"title": "Setup Database", "priority": 1}'
   
   # Task B (depends on A)
   curl -X POST http://localhost:8002/tasks/ \
     -H "Content-Type: application/json" \
     -d '{"title": "Build API", "priority": 2, "depends_on": 1}'
   ```

2. **Try to start Task B** - Should fail with error

3. **Complete Task A** - Move to DONE

4. **Try to start Task B again** - Should succeed

### Extension Ideas

- **Dependency chain visualization** - Show graph of task relationships
- **Auto-complete chains** - When a task completes, automatically start dependent tasks
- **Critical path analysis** - Identify bottlenecks in task chains
- **Parallel task suggestions** - Recommend tasks with no dependencies

---

## Extension 2: Agent-to-Agent Messaging

**Difficulty**: ⭐⭐⭐ Medium  
**Time**: 45 minutes  
**Skills**: Database, API, WebSocket, Frontend

### What We're Building

Direct messaging system between agents:

```
┌─────────┐      Message      ┌─────────┐
│  Agent A  │ ──────────────────▶ │  Agent B  │
│ (CEO)    │  "Need status     │ (Dev)    │
│          │   update"         │          │
└─────────┘                   └─────────┘
```

**Example Use Cases**:
- CEO asks developer for status update
- Developer requests clarification from designer
- Agent escalates complex task to senior agent

### Implementation

#### Step 1: Update Message Model

**File**: `backend/app/models/models.py`

```python
class Message(Base):
    __tablename__ = "messages"
    
    # ... existing fields ...
    
    # NEW: Agent-to-agent messaging
    sender_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    """
    ID of agent sending the message (null for system/user messages).
    """
    
    recipient_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    """
    ID of agent receiving the message (null for broadcast messages).
    """
    
    message_type = Column(String(50), default="direct")
    """
    Type of message: direct, broadcast, request, response.
    """
    
    # Relationships
    sender_agent = relationship("Agent", foreign_keys=[sender_agent_id])
    recipient_agent = relationship("Agent", foreign_keys=[recipient_agent_id])
```

#### Step 2: Create Messaging Service

**File**: `backend/app/services/messaging_service.py` (new file)

```python
"""
Messaging service for agent-to-agent communication.

This service handles:
- Sending direct messages between agents
- Broadcasting messages to teams
- Request/response patterns
- Message persistence
"""

import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.models import Message, Agent
from app.services.openclaw_gateway import openclaw

logger = logging.getLogger(__name__)


class MessagingService:
    """Service for agent-to-agent messaging"""
    
    async def send_direct_message(
        self,
        db: AsyncSession,
        sender_agent_id: int,
        recipient_agent_id: int,
        content: str,
        message_type: str = "direct"
    ) -> Message:
        """
        Send a direct message from one agent to another.
        
        Args:
            db: Database session
            sender_agent_id: ID of sending agent
            recipient_agent_id: ID of receiving agent
            content: Message content
            message_type: Type of message (direct, request, etc.)
        
        Returns:
            Created message record
            
        Example:
            >>> msg = await messaging_service.send_direct_message(
            ...     db, sender_id=1, recipient_id=2,
            ...     content="Need status update on task #5"
            ... )
        """
        # Validate agents exist
        sender_result = await db.execute(
            select(Agent).where(Agent.id == sender_agent_id)
        )
        sender = sender_result.scalar_one_or_none()
        
        recipient_result = await db.execute(
            select(Agent).where(Agent.id == recipient_agent_id)
        )
        recipient = recipient_result.scalar_one_or_none()
        
        if not sender or not recipient:
            raise ValueError("Sender or recipient agent not found")
        
        # Create message record
        message = Message(
            sender_agent_id=sender_agent_id,
            recipient_agent_id=recipient_agent_id,
            sender=sender.name,
            content=content,
            message_type=message_type,
            is_from_user=False
        )
        
        db.add(message)
        await db.commit()
        
        # Notify recipient via OpenClaw (optional)
        await self._notify_agent(recipient.name, content)
        
        logger.info(f"Message sent: {sender.name} -> {recipient.name}")
        return message
    
    async def broadcast_to_team(
        self,
        db: AsyncSession,
        sender_agent_id: int,
        team_id: int,
        content: str
    ) -> List[Message]:
        """
        Broadcast a message to all agents in a team.
        
        Returns list of created messages.
        """
        # Get all agents in team
        result = await db.execute(
            select(Agent).where(Agent.team_id == team_id)
        )
        team_agents = result.scalars().all()
        
        messages = []
        for agent in team_agents:
            if agent.id != sender_agent_id:  # Don't send to self
                msg = await self.send_direct_message(
                    db, sender_agent_id, agent.id, content, "broadcast"
                )
                messages.append(msg)
        
        return messages
    
    async def get_agent_messages(
        self,
        db: AsyncSession,
        agent_id: int,
        include_sent: bool = True,
        limit: int = 50
    ) -> List[Message]:
        """
        Get messages for an agent (sent and received).
        
        Args:
            agent_id: Agent ID
            include_sent: Include messages sent by agent
            limit: Max number of messages
        
        Returns:
            List of messages ordered by timestamp (newest first)
        """
        query = select(Message).where(
            (Message.recipient_agent_id == agent_id)
        )
        
        if include_sent:
            query = query.where(
                (Message.sender_agent_id == agent_id) |
                (Message.recipient_agent_id == agent_id)
            )
        
        query = query.order_by(desc(Message.created_at)).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_conversation(
        self,
        db: AsyncSession,
        agent1_id: int,
        agent2_id: int,
        limit: int = 50
    ) -> List[Message]:
        """
        Get conversation between two agents.
        
        Returns messages ordered by timestamp (oldest first for chat view).
        """
        result = await db.execute(
            select(Message)
            .where(
                (
                    (Message.sender_agent_id == agent1_id) &
                    (Message.recipient_agent_id == agent2_id)
                ) |
                (
                    (Message.sender_agent_id == agent2_id) &
                    (Message.recipient_agent_id == agent1_id)
                )
            )
            .order_by(Message.created_at)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def _notify_agent(self, agent_name: str, content: str):
        """
        Notify agent via OpenClaw gateway.
        
        This sends the message to the actual AI agent through OpenClaw.
        """
        try:
            await openclaw.send_chat_message(
                agent_id=agent_name,
                message=content
            )
        except Exception as e:
            logger.warning(f"Could not notify agent {agent_name}: {e}")
            # Don't raise - message is already saved in DB


# Global instance
messaging_service = MessagingService()
```

#### Step 3: Create API Endpoints

**File**: `backend/app/api/messages.py` (update or create)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.models.models import Message
from app.services.messaging_service import messaging_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/")
async def send_message(
    sender_agent_id: int,
    recipient_agent_id: int,
    content: str,
    message_type: str = "direct",
    db: AsyncSession = Depends(get_db)
):
    """
    Send a direct message from one agent to another.
    
    Args:
        sender_agent_id: ID of sending agent
        recipient_agent_id: ID of receiving agent
        content: Message content
        message_type: Type of message (direct, request, response)
    
    Returns:
        Created message object
    
    Example:
        POST /messages/
        {
            "sender_agent_id": 1,
            "recipient_agent_id": 2,
            "content": "Please update the API documentation",
            "message_type": "request"
        }
    """
    try:
        message = await messaging_service.send_direct_message(
            db, sender_agent_id, recipient_agent_id, content, message_type
        )
        return message
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agent/{agent_id}")
async def get_agent_messages(
    agent_id: int,
    include_sent: bool = True,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all messages for an agent (inbox + sent).
    
    Args:
        agent_id: Agent ID
        include_sent: Include messages sent by agent (default: true)
        limit: Maximum number of messages (default: 50)
    
    Returns:
        List of messages ordered by timestamp
    """
    messages = await messaging_service.get_agent_messages(
        db, agent_id, include_sent, limit
    )
    return messages


@router.get("/conversation/{agent1_id}/{agent2_id}")
async def get_conversation(
    agent1_id: int,
    agent2_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get conversation between two agents.
    
    Returns messages in chronological order (oldest first) suitable for chat UI.
    """
    messages = await messaging_service.get_conversation(
        db, agent1_id, agent2_id, limit
    )
    return messages


@router.post("/broadcast/{team_id}")
async def broadcast_to_team(
    sender_agent_id: int,
    team_id: int,
    content: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Broadcast a message to all agents in a team.
    
    Args:
        sender_agent_id: ID of sending agent
        team_id: Team ID to broadcast to
        content: Message content
    
    Returns:
        List of created messages
    """
    messages = await messaging_service.broadcast_to_team(
        db, sender_agent_id, team_id, content
    )
    return {
        "message": f"Broadcasted to {len(messages)} agents",
        "messages": messages
    }
```

#### Step 4: Update Frontend

**File**: `frontend/src/app/chat/page.tsx` (create or update)

```typescript
'use client';

import { useState, useEffect } from 'react';
import { api, Agent, Message } from '@/lib/api';

export default function AgentMessagingPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [recipientAgent, setRecipientAgent] = useState<Agent | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  
  // Load agents
  useEffect(() => {
    api.agents.list().then(setAgents);
  }, []);
  
  // Load conversation when agents selected
  useEffect(() => {
    if (selectedAgent && recipientAgent) {
      api.messages.getConversation(selectedAgent.id, recipientAgent.id)
        .then(setMessages);
    }
  }, [selectedAgent, recipientAgent]);
  
  const sendMessage = async () => {
    if (!selectedAgent || !recipientAgent || !newMessage.trim()) return;
    
    await api.messages.send({
      sender_agent_id: selectedAgent.id,
      recipient_agent_id: recipientAgent.id,
      content: newMessage,
      message_type: 'direct'
    });
    
    setNewMessage('');
    
    // Refresh conversation
    const updated = await api.messages.getConversation(
      selectedAgent.id, recipientAgent.id
    );
    setMessages(updated);
  };
  
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Agent Messaging</h1>
      
      <div className="grid grid-cols-3 gap-6">
        {/* Agent Selection */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">From Agent</label>
            <select
              className="w-full border rounded p-2"
              value={selectedAgent?.id || ''}
              onChange={(e) => {
                const agent = agents.find(a => a.id === parseInt(e.target.value));
                setSelectedAgent(agent || null);
              }}
            >
              <option value="">Select agent...</option>
              {agents.map(agent => (
                <option key={agent.id} value={agent.id}>{agent.name}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">To Agent</label>
            <select
              className="w-full border rounded p-2"
              value={recipientAgent?.id || ''}
              onChange={(e) => {
                const agent = agents.find(a => a.id === parseInt(e.target.value));
                setRecipientAgent(agent || null);
              }}
            >
              <option value="">Select recipient...</option>
              {agents
                .filter(a => a.id !== selectedAgent?.id)
                .map(agent => (
                  <option key={agent.id} value={agent.id}>{agent.name}</option>
                ))}
            </select>
          </div>
        </div>
        
        {/* Chat Window */}
        <div className="col-span-2 border rounded p-4">
          <div className="h-96 overflow-y-auto mb-4 space-y-2">
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`p-3 rounded ${
                  msg.sender_agent_id === selectedAgent?.id
                    ? 'bg-blue-100 ml-auto'
                    : 'bg-gray-100'
                } max-w-[80%]`}
              >
                <div className="text-sm font-medium">{msg.sender}</div>
                <div>{msg.content}</div>
                <div className="text-xs text-gray-500">
                  {new Date(msg.created_at).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
          
          <div className="flex gap-2">
            <input
              type="text"
              className="flex-1 border rounded p-2"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type a message..."
            />
            <button
              className="bg-blue-500 text-white px-4 py-2 rounded"
              onClick={sendMessage}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Update API client** (`frontend/src/lib/api.ts`):

```typescript
export const api = {
  // ... existing methods ...
  
  messages: {
    send: (data: {
      sender_agent_id: number;
      recipient_agent_id: number;
      content: string;
      message_type?: string;
    }) => fetchJSON<Message>('/messages/', {
      method: 'POST',
      body: JSON.stringify(data)
    }),
    
    getAgentMessages: (agentId: number, includeSent?: boolean) =>
      fetchJSON<Message[]>(`/messages/agent/${agentId}?include_sent=${includeSent ?? true}`),
    
    getConversation: (agent1Id: number, agent2Id: number) =>
      fetchJSON<Message[]>(`/messages/conversation/${agent1Id}/${agent2Id}`),
    
    broadcast: (teamId: number, data: { sender_agent_id: number; content: string }) =>
      fetchJSON(`/messages/broadcast/${teamId}`, {
        method: 'POST',
        body: JSON.stringify(data)
      })
  }
};
```

### Testing

1. **Create two agents** in the UI

2. **Send a message**:
   ```bash
   curl -X POST http://localhost:8002/messages/ \
     -H "Content-Type: application/json" \
     -d '{
       "sender_agent_id": 1,
       "recipient_agent_id": 2,
       "content": "Hello! Need a status update on the API task.",
       "message_type": "direct"
     }'
   ```

3. **Check inbox**:
   ```bash
   curl http://localhost:8002/messages/agent/2
   ```

4. **View conversation**:
   ```bash
   curl http://localhost:8002/messages/conversation/1/2
   ```

### Extension Ideas

- **Message templates** - Pre-defined message types
- **Message threading** - Reply to specific messages
- **Read receipts** - Track when messages are read
- **Attachments** - Share files between agents
- **@mentions** - Notify specific agents in group messages

---

## Extension 3: Agent Performance Metrics

**Difficulty**: ⭐⭐⭐⭐ Advanced  
**Time**: 60 minutes  
**Skills**: Database, Aggregation, Charts, Frontend

### What We're Building

Dashboard showing agent productivity:

```
┌─────────────────────────────────────────┐
│  Agent Performance Dashboard            │
├─────────────────────────────────────────┤
│                                         │
│  📊 Tasks Completed (Last 30 Days)     │
│  ┌─────────────────────────────────┐   │
│  │ ████████████████░░░░  42      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ⏱️ Avg Completion Time: 3.2 hours      │
│                                         │
│  📈 Success Rate: 94%                   │
│                                         │
│  🎯 Top Performers                      │
│  1. Agent A - 15 tasks                  │
│  2. Agent B - 12 tasks                  │
│  3. Agent C - 8 tasks                   │
│                                         │
└─────────────────────────────────────────┘
```

### Implementation

#### Step 1: Add Metrics Fields to Agent Model

**File**: `backend/app/models/models.py`

```python
class Agent(Base):
    __tablename__ = "agents"
    
    # ... existing fields ...
    
    # NEW: Performance metrics
    tasks_completed = Column(Integer, default=0)
    """Total number of tasks completed (status -> DONE)."""
    
    tasks_failed = Column(Integer, default=0)
    """Total number of tasks that failed."""
    
    total_working_time_minutes = Column(Integer, default=0)
    """Total time spent working on tasks (in minutes)."""
    
    average_completion_time_minutes = Column(Integer, nullable=True)
    """Average time to complete a task (in minutes)."""
    
    last_task_completed_at = Column(DateTime(timezone=True), nullable=True)
    """Timestamp of last completed task."""
```

#### Step 2: Create Metrics Tracking

**File**: `backend/app/services/metrics_service.py` (new file)

```python
"""
Performance metrics tracking service.

Tracks agent productivity metrics and provides analytics.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Agent, Task, TaskStatus, AgentLog

logger = logging.getLogger(__name__)


class AgentMetrics:
    """Performance metrics for a single agent"""
    
    def __init__(
        self,
        agent_id: int,
        agent_name: str,
        tasks_completed: int = 0,
        tasks_in_progress: int = 0,
        tasks_failed: int = 0,
        average_completion_time: Optional[float] = None,
        success_rate: float = 0.0,
        total_working_hours: float = 0.0
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.tasks_completed = tasks_completed
        self.tasks_in_progress = tasks_in_progress
        self.tasks_failed = tasks_failed
        self.average_completion_time = average_completion_time
        self.success_rate = success_rate
        self.total_working_hours = total_working_hours


class MetricsService:
    """Service for tracking and calculating agent metrics"""
    
    async def track_task_started(self, db: AsyncSession, agent_id: int, task_id: int):
        """
        Track when an agent starts working on a task.
        
        Stores start time in AgentLog for later calculation.
        """
        log = AgentLog(
            agent_id=agent_id,
            action="TASK_STARTED",
            details=f"Task {task_id} started"
        )
        db.add(log)
        await db.commit()
        logger.debug(f"Tracked task {task_id} started for agent {agent_id}")
    
    async def track_task_completed(
        self,
        db: AsyncSession,
        agent_id: int,
        task_id: int,
        completion_time_minutes: int
    ):
        """
        Track task completion and update agent metrics.
        
        Args:
            agent_id: Agent who completed the task
            task_id: Completed task ID
            completion_time_minutes: Time taken to complete
        """
        # Get agent
        agent_result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return
        
        # Update metrics
        agent.tasks_completed += 1
        agent.last_task_completed_at = datetime.now(timezone.utc)
        
        # Calculate new average completion time
        if agent.average_completion_time_minutes:
            # Weighted average: old_avg * 0.7 + new_time * 0.3
            agent.average_completion_time_minutes = int(
                agent.average_completion_time_minutes * 0.7 + 
                completion_time_minutes * 0.3
            )
        else:
            agent.average_completion_time_minutes = completion_time_minutes
        
        # Add to total working time
        agent.total_working_time_minutes += completion_time_minutes
        
        await db.commit()
        
        # Log completion
        log = AgentLog(
            agent_id=agent_id,
            action="TASK_COMPLETED",
            details=f"Task {task_id} completed in {completion_time_minutes} minutes"
        )
        db.add(log)
        await db.commit()
        
        logger.info(f"Agent {agent.name} completed task {task_id} in {completion_time_minutes}m")
    
    async def get_agent_metrics(
        self,
        db: AsyncSession,
        agent_id: int,
        days: int = 30
    ) -> Optional[AgentMetrics]:
        """
        Calculate metrics for a specific agent.
        
        Args:
            agent_id: Agent ID
            days: Time period for metrics (default: 30 days)
        
        Returns:
            AgentMetrics object or None if agent not found
        """
        agent_result = await db.execute(
            select(Agent).where(Agent.id == agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            return None
        
        # Calculate date range
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get task counts
        tasks_result = await db.execute(
            select(
                func.count(Task.id).filter(Task.status == TaskStatus.DONE),
                func.count(Task.id).filter(Task.status == TaskStatus.IN_PROGRESS),
                func.count(Task.id).filter(Task.status == TaskStatus.REVIEW)
            )
            .where(
                Task.agent_id == agent_id,
                Task.updated_at >= since
            )
        )
        completed, in_progress, review = tasks_result.first()
        
        # Calculate success rate
        total_attempted = agent.tasks_completed + agent.tasks_failed
        success_rate = (
            (agent.tasks_completed / total_attempted * 100)
            if total_attempted > 0
            else 0
        )
        
        # Convert working time to hours
        working_hours = agent.total_working_time_minutes / 60 if agent.total_working_time_minutes else 0
        
        return AgentMetrics(
            agent_id=agent.id,
            agent_name=agent.name,
            tasks_completed=completed or 0,
            tasks_in_progress=(in_progress or 0) + (review or 0),
            tasks_failed=agent.tasks_failed,
            average_completion_time=agent.average_completion_time_minutes,
            success_rate=round(success_rate, 1),
            total_working_hours=round(working_hours, 1)
        )
    
    async def get_team_metrics(
        self,
        db: AsyncSession,
        team_id: int,
        days: int = 30
    ) -> List[AgentMetrics]:
        """
        Get metrics for all agents in a team.
        
        Returns list sorted by tasks completed (highest first).
        """
        # Get all agents in team
        agents_result = await db.execute(
            select(Agent).where(Agent.team_id == team_id)
        )
        agents = agents_result.scalars().all()
        
        # Get metrics for each
        metrics = []
        for agent in agents:
            agent_metrics = await self.get_agent_metrics(db, agent.id, days)
            if agent_metrics:
                metrics.append(agent_metrics)
        
        # Sort by tasks completed (descending)
        metrics.sort(key=lambda m: m.tasks_completed, reverse=True)
        
        return metrics
    
    async def get_leaderboard(
        self,
        db: AsyncSession,
        limit: int = 10,
        days: int = 30
    ) -> List[AgentMetrics]:
        """
        Get top performers across all agents.
        
        Returns:
            List of top agents sorted by tasks completed
        """
        # Get all agents
        agents_result = await db.execute(select(Agent))
        agents = agents_result.scalars().all()
        
        # Get metrics for each
        all_metrics = []
        for agent in agents:
            metrics = await self.get_agent_metrics(db, agent.id, days)
            if metrics:
                all_metrics.append(metrics)
        
        # Sort by tasks completed and take top N
        all_metrics.sort(key=lambda m: m.tasks_completed, reverse=True)
        return all_metrics[:limit]


# Global instance
metrics_service = MetricsService()
```

#### Step 3: Update Task Completion Flow

**File**: `backend/app/core/scheduler.py`

Update `check_task_completion()`:

```python
def check_task_completion():
    """Check if any IN_PROGRESS tasks should be moved to REVIEW based on timeout"""
    db = SessionLocal()
    try:
        from app.services.metrics_service import metrics_service
        
        in_progress_tasks = db.query(Task).filter(
            Task.status == TaskStatus.IN_PROGRESS
        ).all()
        
        for task in in_progress_tasks:
            if not task.agent_id:
                continue
            
            try:
                if task.updated_at:
                    updated = task.updated_at
                    if updated.tzinfo is None:
                        updated = updated.replace(tzinfo=timezone.utc)
                    
                    time_in_progress = datetime.now(timezone.utc) - updated
                    
                    if time_in_progress > timedelta(minutes=10):
                        task.status = TaskStatus.REVIEW
                        db.commit()
                        
                        # NEW: Track completion time
                        completion_time_minutes = int(time_in_progress.total_seconds() / 60)
                        
                        # Run async tracking in sync context
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            metrics_service.track_task_completed(
                                db, task.agent_id, task.id, completion_time_minutes
                            )
                        )
                        loop.close()
                        
                        # Log action
                        log = AgentLog(
                            agent_id=task.agent_id,
                            action="TASK_AUTO_REVIEW",
                            details=f"Task '{task.title}' completed in {completion_time_minutes} minutes"
                        )
                        db.add(log)
                        db.commit()
                        
                        logger.info(f"Task {task.id} auto-moved to REVIEW: {task.title}")
                        
            except Exception as e:
                logger.error(f"Error checking task completion for task {task.id}: {e}")
                db.rollback()
    except Exception as e:
        logger.error(f"Error in task completion check: {e}")
    finally:
        db.close()
```

#### Step 4: Create Metrics API Endpoints

**File**: `backend/app/api/metrics.py` (new file)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.services.metrics_service import metrics_service, AgentMetrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/agent/{agent_id}")
async def get_agent_metrics(
    agent_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance metrics for a specific agent.
    
    Args:
        agent_id: Agent ID
        days: Time period for metrics (default: 30 days)
    
    Returns:
        AgentMetrics object with performance data
    """
    metrics = await metrics_service.get_agent_metrics(db, agent_id, days)
    
    if not metrics:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return metrics


@router.get("/team/{team_id}")
async def get_team_metrics(
    team_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance metrics for all agents in a team.
    
    Returns agents sorted by tasks completed (highest first).
    """
    metrics = await metrics_service.get_team_metrics(db, team_id, days)
    return metrics


@router.get("/leaderboard")
async def get_leaderboard(
    limit: int = 10,
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Get top performing agents across the system.
    
    Args:
        limit: Number of agents to return (default: 10)
        days: Time period for metrics (default: 30 days)
    
    Returns:
        List of top agents with metrics
    """
    leaderboard = await metrics_service.get_leaderboard(db, limit, days)
    return leaderboard


@router.get("/dashboard")
async def get_dashboard_metrics(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary metrics for the dashboard.
    
    Returns aggregate statistics across all agents.
    """
    from sqlalchemy import func
    from app.models.models import Agent, Task, TaskStatus
    
    # Total tasks completed
    tasks_result = await db.execute(
        select(func.count(Task.id))
        .where(Task.status == TaskStatus.DONE)
    )
    total_completed = tasks_result.scalar()
    
    # Active agents
    active_result = await db.execute(
        select(func.count(Agent.id))
        .where(Agent.status == "active")
    )
    active_agents = active_result.scalar()
    
    # Get leaderboard
    leaderboard = await metrics_service.get_leaderboard(db, limit=5, days=days)
    
    return {
        "total_tasks_completed": total_completed,
        "active_agents": active_agents,
        "leaderboard": leaderboard,
        "time_period_days": days
    }
```

#### Step 5: Create Frontend Dashboard

**File**: `frontend/src/app/metrics/page.tsx` (new file)

```typescript
'use client';

import { useState, useEffect } from 'react';
import { api, Agent } from '@/lib/api';

interface AgentMetrics {
  agent_id: number;
  agent_name: string;
  tasks_completed: number;
  tasks_in_progress: number;
  tasks_failed: number;
  average_completion_time: number | null;
  success_rate: number;
  total_working_hours: number;
}

export default function MetricsDashboard() {
  const [leaderboard, setLeaderboard] = useState<AgentMetrics[]>([]);
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  const [timeRange, setTimeRange] = useState(30);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadMetrics();
  }, [timeRange]);
  
  const loadMetrics = async () => {
    setLoading(true);
    try {
      const [leaderboardData, dashboardData] = await Promise.all([
        api.metrics.getLeaderboard(10, timeRange),
        api.metrics.getDashboard(timeRange)
      ]);
      setLeaderboard(leaderboardData);
      setDashboardStats(dashboardData);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    }
    setLoading(false);
  };
  
  if (loading) {
    return <div className="p-6">Loading metrics...</div>;
  }
  
  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Performance Metrics</h1>
        
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(parseInt(e.target.value))}
          className="border rounded p-2"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>
      
      {/* Dashboard Stats */}
      {dashboardStats && (
        <div className="grid grid-cols-4 gap-4 mb-8">
          <StatCard
            title="Tasks Completed"
            value={dashboardStats.total_tasks_completed}
            icon="✅"
          />
          <StatCard
            title="Active Agents"
            value={dashboardStats.active_agents}
            icon="👥"
          />
          <StatCard
            title="Time Period"
            value={`${timeRange} days`}
            icon="📅"
          />
          <StatCard
            title="Avg Success Rate"
            value={`${calculateAvgSuccessRate(leaderboard)}%`}
            icon="📈"
          />
        </div>
      )}
      
      {/* Leaderboard */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h2 className="text-xl font-semibold">🏆 Top Performers</h2>
        </div>
        
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left">Rank</th>
              <th className="px-6 py-3 text-left">Agent</th>
              <th className="px-6 py-3 text-right">Completed</th>
              <th className="px-6 py-3 text-right">Success Rate</th>
              <th className="px-6 py-3 text-right">Avg Time</th>
              <th className="px-6 py-3 text-right">Working Hours</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.map((metric, index) => (
              <tr key={metric.agent_id} className="border-t">
                <td className="px-6 py-4">
                  {index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : index + 1}
                </td>
                <td className="px-6 py-4 font-medium">{metric.agent_name}</td>
                <td className="px-6 py-4 text-right">{metric.tasks_completed}</td>
                <td className="px-6 py-4 text-right">
                  <span className={`font-semibold ${
                    metric.success_rate >= 90 ? 'text-green-600' :
                    metric.success_rate >= 70 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {metric.success_rate}%
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  {metric.average_completion_time 
                    ? `${Math.round(metric.average_completion_time / 60)}h`
                    : 'N/A'}
                </td>
                <td className="px-6 py-4 text-right">
                  {metric.total_working_hours}h
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon }: { title: string; value: string | number; icon: string }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-500 text-sm">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  );
}

function calculateAvgSuccessRate(leaderboard: AgentMetrics[]): number {
  if (leaderboard.length === 0) return 0;
  const total = leaderboard.reduce((sum, m) => sum + m.success_rate, 0);
  return Math.round(total / leaderboard.length);
}
```

**Update API client** (`frontend/src/lib/api.ts`):

```typescript
export const api = {
  // ... existing methods ...
  
  metrics: {
    getAgent: (agentId: number, days?: number) =>
      fetchJSON<AgentMetrics>(`/metrics/agent/${agentId}?days=${days ?? 30}`),
    
    getTeam: (teamId: number, days?: number) =>
      fetchJSON<AgentMetrics[]>(`/metrics/team/${teamId}?days=${days ?? 30}`),
    
    getLeaderboard: (limit?: number, days?: number) =>
      fetchJSON<AgentMetrics[]>(`/metrics/leaderboard?limit=${limit ?? 10}&days=${days ?? 30}`),
    
    getDashboard: (days?: number) =>
      fetchJSON<any>(`/metrics/dashboard?days=${days ?? 30}`)
  }
};

interface AgentMetrics {
  agent_id: number;
  agent_name: string;
  tasks_completed: number;
  tasks_in_progress: number;
  tasks_failed: number;
  average_completion_time: number | null;
  success_rate: number;
  total_working_hours: number;
}
```

### Testing

1. **Complete some tasks** - Move tasks through the workflow

2. **Check metrics**:
   ```bash
   curl http://localhost:8002/metrics/leaderboard
   ```

3. **View agent-specific metrics**:
   ```bash
   curl http://localhost:8002/metrics/agent/1
   ```

4. **Check dashboard**:
   ```bash
   curl http://localhost:8002/metrics/dashboard
   ```

### Extension Ideas

- **Performance charts** - Line/bar charts using Chart.js or D3
- **Trends over time** - Compare performance week-over-week
- **Goal setting** - Set targets for agents and track progress
- **Efficiency metrics** - Tasks per hour, cost per task
- **Team comparisons** - Compare team performance
- **Export reports** - Generate PDF/CSV reports

---

## Summary

You've now implemented three powerful extensions:

1. **Task Dependencies** - Complex workflow management
2. **Agent Messaging** - Direct communication channel
3. **Performance Metrics** - Data-driven insights

Each extension follows the same pattern:
- ✅ Database model updates
- ✅ Service layer implementation
- ✅ API endpoints
- ✅ Frontend integration
- ✅ Testing

**Next Steps**:
- Combine extensions (e.g., metrics for messaging)
- Add real-time updates via WebSocket
- Implement charts and visualizations
- Deploy to production

Happy building! 🚀
