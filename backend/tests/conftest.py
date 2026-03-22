import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.models import (
    Agent,
    Team,
    Task,
    Goal,
    Message,
    Meeting,
    Settings,
    AgentLog,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_mission_control.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create fresh database for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield TestingSessionLocal()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """HTTP client for API testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def sample_team(db_session):
    """Sample team for testing."""
    team = Team(name="Engineering", description="Backend team")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest_asyncio.fixture
async def sample_agent(db_session, sample_team):
    """Sample agent for testing."""
    agent = Agent(name="TestAgent", role="Developer", team_id=sample_team.id)
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest_asyncio.fixture
async def sample_task(db_session, sample_agent):
    """Sample task for testing."""
    task = Task(
        title="Test Task",
        description="A test task",
        agent_id=sample_agent.id,
        status="backlog",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def sample_goal(db_session):
    """Sample goal for testing."""
    goal = Goal(title="Q1 Objective", description="Complete Q1 goals")
    db_session.add(goal)
    await db_session.commit()
    await db_session.refresh(goal)
    return goal


@pytest_asyncio.fixture
async def sample_message(db_session, sample_agent):
    """Sample message for testing."""
    message = Message(
        agent_id=sample_agent.id, sender="test", content="Test message content"
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)
    return message


@pytest_asyncio.fixture
async def c_suite_team(db_session):
    """Team with C-suite level agents for standup testing."""
    team = Team(name="Executive", description="C-Suite team")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)

    # Add CEO agent
    ceo = Agent(name="CEO", role="Chief Executive Officer", team_id=team.id)
    db_session.add(ceo)
    await db_session.commit()
    await db_session.refresh(ceo)

    return {"team": team, "ceo": ceo}


# ============================================================================
# MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_openclaw_gateway(mocker):
    """Mock OpenClaw Gateway for agent operations."""
    mock = mocker.patch("app.api.agents.openclaw", new_callable=AsyncMock)
    mock.health_check.return_value = {"connected": True}
    mock.set_agent_heartbeat.return_value = {
        "success": True,
        "rate_limited": False,
        "retry_seconds": 0,
        "error_message": "",
    }
    mock.add_agent_to_config.return_value = True
    mock.get_agent_heartbeat.return_value = 10
    mock.run_agent.return_value = {"success": True, "message": "Agent started"}
    mock.stop_agent.return_value = {"success": True}
    return mock


@pytest.fixture
def mock_openclaw_health_check_fail(mocker):
    """Mock OpenClaw Gateway with failed health check."""
    mock = mocker.patch("app.api.agents.openclaw", new_callable=AsyncMock)
    mock.health_check.return_value = {"connected": False, "error": "Gateway offline"}
    return mock


@pytest.fixture
def mock_openclaw_rate_limited(mocker):
    """Mock OpenClaw Gateway with rate limiting."""
    mock = mocker.patch("app.api.agents.openclaw", new_callable=AsyncMock)
    mock.health_check.return_value = {"connected": True}
    mock.set_agent_heartbeat.return_value = {
        "success": False,
        "rate_limited": True,
        "retry_seconds": 60,
        "error_message": "Rate limited",
    }
    return mock


@pytest.fixture
def mock_llm_service(mocker):
    """Mock LLM Service."""
    mock = mocker.patch("app.api.chat.llm_service", new_callable=AsyncMock)
    mock.generate.return_value = "LLM generated response"
    mock.generate_agent_files.return_value = {
        "memory": "Agent memory content",
        "identity": "Agent identity content",
        "instructions": "Agent instructions content",
    }
    return mock


@pytest.fixture
def mock_workspace_manager(mocker):
    """Mock Workspace Manager."""
    mock = mocker.patch("app.api.agents.workspace_manager", new_callable=AsyncMock)
    mock.get_agent_workspace.return_value = "/test/workspace/agent_1"
    mock.create_default_files.return_value = MagicMock()
    mock.save_file.return_value = True
    mock.read_file.return_value = "file content"
    mock.list_agents.return_value = ["agent_1", "agent_2"]

    mock_files = MagicMock()
    mock_files.model_dump.return_value = {
        "memory": "test memory content",
        "identity": "test identity",
        "instructions": "test instructions",
    }
    mock.read_all.return_value = mock_files

    return mock


@pytest_asyncio.fixture
async def mock_settings(db_session):
    """Mock settings for testing."""
    settings = Settings(
        llm_api_url="https://api.openai.com",
        llm_api_key="test-key",
        openclaw_gateway_url="http://localhost:8080",
    )
    db_session.add(settings)
    await db_session.commit()
    await db_session.refresh(settings)
    return settings
