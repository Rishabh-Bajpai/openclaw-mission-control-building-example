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
)
from app.api.tasks import goals_router, agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging("DEBUG")
    root_logger = logging.getLogger()
    root_logger.addHandler(BufferedHandler())
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="OpenClaw Mission Control",
    description="Centralized command-and-control dashboard for managing autonomous AI agents",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/")
async def root():
    return {
        "name": "OpenClaw Mission Control",
        "status": "operational",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await log_ws_endpoint(websocket)
