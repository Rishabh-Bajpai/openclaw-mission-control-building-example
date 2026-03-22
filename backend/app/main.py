"""
OpenClaw Mission Control - FastAPI Application Entry Point

This is the main application file that bootstraps the entire Mission Control system.
It handles:
- Application lifecycle (startup/shutdown)
- Database initialization
- Scheduler startup
- WebSocket log streaming
- CORS middleware configuration
- API route registration

Architecture Overview:
---------------------
Mission Control follows a modular FastAPI architecture:

1. Core Layer (app/core/)
   - Database connections (database.py)
   - Background job scheduler (scheduler.py)
   - Configuration management (config.py)
   - Logging infrastructure (logging.py, log_stream.py)

2. Models Layer (app/models/)
   - SQLAlchemy ORM models (models.py)
   - Pydantic schemas (schemas.py)

3. Services Layer (app/services/)
   - OpenClaw gateway integration (openclaw_gateway.py)
   - Agent workspace management (workspace_manager.py)
   - Task execution (task_executor.py)
   - LLM integration (llm_service.py)

4. API Layer (app/api/)
   - REST endpoints grouped by domain
   - WebSocket endpoints for real-time features

Extension Points:
-----------------
To add new features:

1. New API Endpoint:
   - Create router in app/api/your_feature.py
   - Import and include in this file
   - Follow existing patterns for CRUD operations

2. New Background Job:
   - Add function to app/core/scheduler.py
   - Register in start_scheduler()
   - Use async_session() for database access

3. New Service:
   - Create file in app/services/
   - Define clear interfaces
   - Import where needed in API routes

4. New Database Model:
   - Add to app/models/models.py
   - Create Pydantic schema in schemas.py
   - Run the application (tables auto-create)

Example - Adding a New Router:
-------------------------------
```python
# app/api/notifications.py
from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/")
async def get_notifications():
    return {"message": "Notifications endpoint"}

# In this file (main.py):
from app.api import notifications
app.include_router(notifications.router)
```

Dependencies:
-------------
- FastAPI: Web framework
- SQLAlchemy: Database ORM
- APScheduler: Background jobs
- websockets: WebSocket support

See Also:
---------
- app/core/config.py - Environment configuration
- app/core/database.py - Database setup
- app/core/scheduler.py - Background jobs
"""

import logging
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.database import init_db
from app.core.scheduler import start_scheduler, stop_scheduler
from app.core.logging import configure_logging
from app.core.log_stream import BufferedHandler, log_ws_endpoint
from app.api import (
    teams,
    agents,
    tasks,
    messages,
    dashboard,
    meetings,
    logs,
    settings as settings_router,
    chat,
    metrics,
)
from app.api.tasks import goals_router, agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager - handles startup and shutdown sequences.

    Startup Sequence:
    1. Configure logging (sets up log levels and handlers)
    2. Initialize database (creates tables if they don't exist)
    3. Start background scheduler (APScheduler for heartbeats, task sync, etc.)

    Shutdown Sequence:
    1. Stop background scheduler gracefully

    The @asynccontextmanager decorator allows us to use 'yield' to separate
    startup from shutdown code. Everything before yield runs on startup,
    everything after runs on shutdown.

    Example:
        The lifespan context ensures database is ready before accepting requests
        and scheduler stops cleanly when app shuts down.
    """
    # Startup
    configure_logging("DEBUG")
    root_logger = logging.getLogger()
    root_logger.addHandler(BufferedHandler())
    await init_db()
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


# FastAPI application instance
# See: https://fastapi.tiangolo.com/tutorial/first-steps/
app = FastAPI(
    title="OpenClaw Mission Control",
    description="Centralized command-and-control dashboard for managing autonomous AI agents",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
# Allows frontend (running on different port) to communicate with backend
# In production, restrict this to your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
# Each router handles a specific domain of functionality
# Order doesn't matter here - FastAPI resolves by path
app.include_router(dashboard.router)
app.include_router(teams.router)
app.include_router(agents.router)
app.include_router(tasks.router)
app.include_router(agent_router)
app.include_router(goals_router)
app.include_router(messages.router)
app.include_router(meetings.router)
app.include_router(logs.router)
app.include_router(settings_router.router)
app.include_router(chat.router)
app.include_router(metrics.router)


@app.get("/")
async def root():
    """
    Root endpoint - provides basic system information.

    Returns:
        dict: System name, status, and version

    Example Response:
        {
            "name": "OpenClaw Mission Control",
            "status": "operational",
            "version": "1.0.0"
        }

    Use this endpoint for:
    - Health checks
    - API discovery
    - Verifying deployment
    """
    return {
        "name": "OpenClaw Mission Control",
        "status": "operational",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    """
    Health check endpoint for monitoring systems.

    Returns:
        dict: Health status

    Example Response:
        {"status": "healthy"}

    Use this endpoint for:
    - Load balancer health checks
    - Monitoring systems (e.g., Datadog, New Relic)
    - Kubernetes liveness probes

    Note: This is a simple check. For deeper health checks (database, OpenClaw
    connection), extend this endpoint to verify all dependencies.
    """
    return {"status": "healthy"}


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    """
    WebSocket endpoint for real-time log streaming.

    This endpoint streams backend logs to connected clients in real-time.
    Used by the LogTerminal component in the frontend.

    Connection:
        ws://localhost:8002/ws/logs

    Message Format:
        {
            "timestamp": "2024-01-15T10:30:00",
            "level": "INFO",
            "logger": "app.api.agents",
            "message": "Agent created: CEO"
        }

    Usage:
        const ws = new WebSocket('ws://localhost:8002/ws/logs');
        ws.onmessage = (event) => {
            const log = JSON.parse(event.data);
            console.log(log.message);
        };

    Implementation:
        Uses BufferedHandler to capture all Python logs and stream them
        via WebSocket. See app/core/log_stream.py for details.

    Extension Idea:
        Add filtering parameters (e.g., ?level=ERROR&agent_id=123) to
        stream only specific logs.
    """
    await log_ws_endpoint(websocket)
