import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.models.models import Agent, Team, Task
import os

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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield TestingSessionLocal()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def sample_team(db_session):
    team = Team(name="Engineering", description="Backend team")
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest_asyncio.fixture(scope="function")
async def sample_agent(db_session, sample_team):
    agent = Agent(name="TestAgent", role="Developer", team_id=sample_team.id)
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


class TestHealthEndpoints:
    async def test_root(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "OpenClaw Mission Control"
        assert data["status"] == "operational"

    async def test_health(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestDashboard:
    async def test_get_stats_empty(self, client):
        response = await client.get("/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_agents"] == 0
        assert data["total_tasks"] == 0
        assert data["total_teams"] == 0


class TestTeams:
    async def test_create_team(self, client):
        response = await client.post(
            "/teams/", json={"name": "Marketing", "description": "Marketing team"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Marketing"
        assert data["description"] == "Marketing team"
        assert "id" in data

    async def test_list_teams(self, client, sample_team):
        response = await client.get("/teams/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Engineering"

    async def test_get_team(self, client, sample_team):
        response = await client.get(f"/teams/{sample_team.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Engineering"

    async def test_update_team(self, client, sample_team):
        response = await client.put(
            f"/teams/{sample_team.id}", json={"name": "Updated Team"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Team"

    async def test_delete_team(self, client, sample_team):
        response = await client.delete(f"/teams/{sample_team.id}")
        assert response.status_code == 204

        response = await client.get(f"/teams/{sample_team.id}")
        assert response.status_code == 404


class TestAgents:
    async def test_create_agent(self, client, sample_team):
        response = await client.post(
            "/agents/",
            json={"name": "Alice", "role": "Developer", "team_id": sample_team.id},
        )
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        assert data["name"] == "Alice"
        assert data["role"] == "Developer"
        assert data["team_id"] == sample_team.id
        assert "id" in data

    async def test_create_agent_without_team(self, client):
        response = await client.post(
            "/agents/", json={"name": "Bob", "role": "Designer"}
        )
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        assert data["name"] == "Bob"
        assert data["role"] == "Designer"
        assert data["team_id"] is None

    async def test_create_agent_with_chief(self, client, sample_agent):
        response = await client.post(
            "/agents/",
            json={"name": "Charlie", "role": "Junior Dev", "chief_id": sample_agent.id},
        )
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        assert data["chief_id"] == sample_agent.id

    async def test_create_duplicate_agent_fails(self, client, sample_agent):
        response = await client.post(
            "/agents/", json={"name": "TestAgent", "role": "Another Role"}
        )
        assert response.status_code == 400

    async def test_list_agents(self, client, sample_agent):
        response = await client.get("/agents/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "TestAgent"

    async def test_get_agent(self, client, sample_agent):
        response = await client.get(f"/agents/{sample_agent.id}")
        assert response.status_code == 200
        assert response.json()["name"] == "TestAgent"

    async def test_get_agents_hierarchy(self, client, sample_agent, sample_team):
        response = await client.get("/agents/hierarchy")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "TestAgent"
        assert data[0]["team_name"] == "Engineering"

    async def test_update_agent(self, client, sample_agent):
        response = await client.put(
            f"/agents/{sample_agent.id}", json={"name": "Updated Agent"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TestAgent"

    async def test_reset_agent(self, client, sample_agent):
        response = await client.post(f"/agents/{sample_agent.id}/reset")
        assert response.status_code == 200
        assert response.json()["status"] == "idle"

    async def test_run_agent(self, client, sample_agent):
        response = await client.post(f"/agents/{sample_agent.id}/run")
        assert response.status_code == 404, (
            f"Expected 404 for non-existent endpoint: {response.text}"
        )

    async def test_delete_agent(self, client, sample_agent):
        response = await client.delete(f"/agents/{sample_agent.id}")
        assert response.status_code == 204

        response = await client.get(f"/agents/{sample_agent.id}")
        assert response.status_code == 404

    async def test_agent_logs(self, client, sample_agent):
        response = await client.get(f"/agents/{sample_agent.id}/logs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestTasks:
    async def test_create_task(self, client, sample_agent):
        response = await client.post(
            "/tasks/",
            json={
                "title": "Build feature",
                "description": "Build a new feature",
                "agent_id": sample_agent.id,
            },
        )
        assert response.status_code == 201, f"Failed: {response.text}"
        data = response.json()
        assert data["title"] == "Build feature"
        assert data["status"] == "backlog"

    async def test_list_tasks(self, client, sample_agent):
        await client.post(
            "/tasks/", json={"title": "Task 1", "agent_id": sample_agent.id}
        )
        await client.post(
            "/tasks/", json={"title": "Task 2", "agent_id": sample_agent.id}
        )

        response = await client.get("/tasks/")
        assert response.status_code == 200
        assert len(response.json()) == 2

    async def test_update_task_status(self, client, sample_agent):
        create_resp = await client.post(
            "/tasks/", json={"title": "Move me", "agent_id": sample_agent.id}
        )
        task_id = create_resp.json()["id"]

        response = await client.put(
            f"/tasks/{task_id}",
            json={"status": "in_progress", "move_reason": "Starting work"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    async def test_delete_task(self, client, sample_agent):
        create_resp = await client.post(
            "/tasks/", json={"title": "Delete me", "agent_id": sample_agent.id}
        )
        task_id = create_resp.json()["id"]

        response = await client.delete(f"/tasks/{task_id}")
        assert response.status_code == 204

        response = await client.get(f"/tasks/{task_id}")
        assert response.status_code == 404


class TestGoals:
    async def test_create_goal(self, client):
        response = await client.post(
            "/goals/",
            json={"title": "Q1 Objective", "description": "Complete Q1 goals"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Q1 Objective"

    async def test_list_goals(self, client):
        await client.post("/goals/", json={"title": "Goal 1"})
        await client.post("/goals/", json={"title": "Goal 2"})

        response = await client.get("/goals/")
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestMessages:
    async def test_send_message(self, client, sample_agent):
        response = await client.post(
            "/messages/",
            json={
                "agent_id": sample_agent.id,
                "sender": "test",
                "content": "Hello from agent",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Hello from agent"

    async def test_list_messages(self, client, sample_agent):
        await client.post(
            "/messages/",
            json={
                "agent_id": sample_agent.id,
                "sender": "test",
                "content": "Test message",
            },
        )

        response = await client.get("/messages/")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestLogs:
    async def test_list_logs(self, client, sample_agent):
        response = await client.get("/logs/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestSettings:
    async def test_get_settings(self, client):
        response = await client.get("/settings/")
        assert response.status_code == 200
        data = response.json()
        assert "llm_api_url" in data

    async def test_get_llm_settings(self, client):
        response = await client.get("/settings/llm")
        assert response.status_code == 200
        data = response.json()
        assert "note" in data
        assert "LLM is managed by OpenClaw" in data["note"]
