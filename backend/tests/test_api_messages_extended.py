"""
Extended Message API Tests - Agent-to-agent messaging.
"""

import pytest
import pytest_asyncio
from app.models.models import Agent, Message


class TestAgentMessages:
    """Test agent-to-agent message endpoints."""

    async def test_send_agent_to_agent_message_success(
        self, client, db_session, sample_team
    ):
        """Test successful agent-to-agent message."""
        # Create two agents
        agent1 = Agent(name="Agent1", role="Dev", team_id=sample_team.id)
        agent2 = Agent(name="Agent2", role="Dev", team_id=sample_team.id)
        db_session.add_all([agent1, agent2])
        await db_session.commit()
        await db_session.refresh(agent1)
        await db_session.refresh(agent2)

        response = await client.post(
            f"/messages/agent/{agent1.id}/to/{agent2.id}",
            json={"content": "Hello from Agent1"},
        )
        assert response.status_code in [201, 200]

    async def test_send_agent_message_sender_not_found(self, client, sample_agent):
        """Test send message with non-existent sender."""
        response = await client.post(
            "/messages/agent/99999/to/1", json={"content": "Hello"}
        )
        assert response.status_code == 404

    async def test_send_agent_message_recipient_not_found(self, client, sample_agent):
        """Test send message to non-existent recipient."""
        response = await client.post(
            f"/messages/agent/{sample_agent.id}/to/99999", json={"content": "Hello"}
        )
        assert response.status_code == 404

    async def test_get_agent_messages(self, client, sample_agent, db_session):
        """Test get all messages for an agent."""
        response = await client.get(f"/messages/agent/{sample_agent.id}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
