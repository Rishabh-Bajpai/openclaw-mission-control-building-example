"""
Extended Agent API Tests - Covers missing endpoints and edge cases.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock


class TestAgentStartStop:
    """Test agent start/stop endpoints."""

    async def test_agent_start_success(
        self, client, sample_agent, mock_openclaw_gateway
    ):
        """Test successful agent start."""
        response = await client.post(f"/agents/{sample_agent.id}/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"

    async def test_agent_start_gateway_offline(
        self, client, sample_agent, mock_openclaw_health_check_fail
    ):
        """Test agent start when gateway is offline."""
        response = await client.post(f"/agents/{sample_agent.id}/start")
        assert response.status_code == 503

    async def test_agent_start_rate_limited(
        self, client, sample_agent, mock_openclaw_rate_limited
    ):
        """Test agent start when rate limited."""
        response = await client.post(f"/agents/{sample_agent.id}/start")
        assert response.status_code == 429
        data = response.json()
        assert (
            "retry" in str(data.get("detail", "")).lower()
            or "rate" in str(data.get("detail", "")).lower()
        )

    async def test_agent_start_not_found(self, client):
        """Test agent start with non-existent agent."""
        response = await client.post("/agents/99999/start")
        assert response.status_code == 404

    async def test_agent_stop_success(
        self, client, sample_agent, mock_openclaw_gateway
    ):
        """Test successful agent stop."""
        response = await client.post(f"/agents/{sample_agent.id}/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"

    async def test_agent_stop_gateway_offline(
        self, client, sample_agent, mock_openclaw_health_check_fail
    ):
        """Test agent stop when gateway is offline."""
        response = await client.post(f"/agents/{sample_agent.id}/stop")
        assert response.status_code == 503


class TestAgentSubordinates:
    """Test agent subordinates endpoints."""

    async def test_get_subordinates(self, client, db_session, sample_team):
        """Test get agent subordinates."""
        from app.models.models import Agent

        # Create chief agent
        chief = Agent(name="Chief", role="Lead", team_id=sample_team.id)
        db_session.add(chief)
        await db_session.commit()
        await db_session.refresh(chief)

        # Create subordinate
        subordinate = Agent(
            name="Subordinate",
            role="Developer",
            team_id=sample_team.id,
            chief_id=chief.id,
        )
        db_session.add(subordinate)
        await db_session.commit()
        await db_session.refresh(subordinate)

        response = await client.get(f"/agents/{chief.id}/subordinates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Subordinate"

    async def test_get_subordinates_empty(self, client, sample_agent):
        """Test get subordinates when none exist."""
        response = await client.get(f"/agents/{sample_agent.id}/subordinates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestAgentFiles:
    """Test agent files endpoints."""

    async def test_get_agent_files(self, client, sample_agent, mocker):
        """Test get agent files."""
        mock_wm = MagicMock()
        mock_files = MagicMock()
        mock_files.model_dump.return_value = {
            "memory": "test memory content",
            "identity": "test identity content",
        }
        mock_wm.read_all.return_value = mock_files

        mocker.patch("app.api.agents.workspace_manager", mock_wm)

        response = await client.get(f"/agents/{sample_agent.id}/files")
        assert response.status_code == 200

    async def test_get_agent_files_not_found(
        self, client, sample_agent, mock_workspace_manager
    ):
        """Test get agent files when agent doesn't exist."""
        mock_workspace_manager.read_file.side_effect = FileNotFoundError()

        response = await client.get("/agents/99999/files")
        assert response.status_code == 404

    async def test_update_agent_files(
        self, client, sample_agent, mock_workspace_manager
    ):
        """Test update agent files."""
        response = await client.put(
            f"/agents/{sample_agent.id}/files",
            json={"memory": "new memory", "identity": "new identity"},
        )
        assert response.status_code == 200

    async def test_update_agent_files_not_found(self, client, mock_workspace_manager):
        """Test update agent files when agent doesn't exist."""
        mock_workspace_manager.update_memory.side_effect = FileNotFoundError()

        response = await client.put(
            "/agents/99999/files", json={"memory": "new memory"}
        )
        assert response.status_code == 404


class TestAgentSync:
    """Test agent sync from OpenClaw."""

    async def test_sync_from_openclaw_success(self, client, sample_team, mocker):
        """Test successful sync from OpenClaw."""
        mock_openclaw = mocker.patch("app.api.agents.openclaw", new_callable=AsyncMock)
        mock_openclaw.get_config.return_value = {
            "config": {
                "agents": {
                    "list": [{"name": "NewAgent", "identity": {"theme": "Developer"}}]
                }
            }
        }

        response = await client.post("/agents/sync-from-openclaw")
        assert response.status_code == 200
        data = response.json()
        assert "synced" in data or "updated" in data

    async def test_sync_from_openclaw_error(self, client, mocker):
        """Test sync from OpenClaw with error."""
        mock_openclaw = mocker.patch("app.api.agents.openclaw", new_callable=AsyncMock)
        mock_openclaw.get_config.side_effect = Exception("Sync failed")

        response = await client.post("/agents/sync-from-openclaw")
        assert response.status_code == 500


class TestAgentEdgeCases:
    """Test agent edge cases and error handling."""

    async def test_get_agent_not_found(self, client):
        """Test get non-existent agent."""
        response = await client.get("/agents/99999")
        assert response.status_code == 404

    async def test_update_agent_not_found(self, client):
        """Test update non-existent agent."""
        response = await client.put("/agents/99999", json={"name": "New Name"})
        assert response.status_code == 404

    async def test_delete_agent_not_found(self, client):
        """Test delete non-existent agent."""
        response = await client.delete("/agents/99999")
        assert response.status_code == 404

    async def test_agent_heartbeat_not_found(self, client):
        """Test heartbeat on non-existent agent."""
        response = await client.post("/agents/99999/heartbeat")
        assert response.status_code == 404

    async def test_agent_reset_not_found(self, client):
        """Test reset non-existent agent."""
        response = await client.post("/agents/99999/reset")
        assert response.status_code == 404
