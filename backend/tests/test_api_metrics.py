"""
Metrics API Tests - Agent metrics and leaderboard.
"""

import pytest
import pytest_asyncio
from app.models.models import Agent


class TestAgentMetrics:
    """Test agent metrics endpoints."""

    async def test_get_agent_metrics_success(self, client, sample_agent, sample_task):
        """Test get metrics for agent with tasks."""
        response = await client.get(f"/metrics/agent/{sample_agent.id}")
        assert response.status_code == 200
        data = response.json()
        assert "agent_id" in data or "metrics" in data

    async def test_get_agent_metrics_not_found(self, client):
        """Test get metrics for non-existent agent."""
        response = await client.get("/metrics/agent/99999")
        assert response.status_code == 404

    async def test_get_agent_metrics_zero_tasks(self, client, sample_agent):
        """Test get metrics for agent with no tasks."""
        response = await client.get(f"/metrics/agent/{sample_agent.id}")
        assert response.status_code == 200
        data = response.json()
        # Should return metrics with zeros
        assert data is not None


class TestLeaderboard:
    """Test leaderboard endpoints."""

    async def test_leaderboard_success(self, client, sample_agent, sample_task):
        """Test get leaderboard."""
        response = await client.get("/metrics/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_leaderboard_empty(self, client):
        """Test get empty leaderboard."""
        response = await client.get("/metrics/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_leaderboard_respects_limit(self, client, sample_team, db_session):
        """Test leaderboard respects limit parameter."""
        # Create multiple agents
        for i in range(5):
            agent = Agent(name=f"Agent{i}", role="Dev", team_id=sample_team.id)
            db_session.add(agent)
        await db_session.commit()

        response = await client.get("/metrics/leaderboard?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 3
