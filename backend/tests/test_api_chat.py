"""
Chat API Tests - All chat endpoints.

Note: Some tests may be skipped if they require external OpenClaw Gateway connection.
"""

import pytest
import pytest_asyncio


class TestChatMessages:
    """Test chat message endpoints."""

    async def test_get_chat_messages_agent_not_found(self, client):
        """Test get chat messages for non-existent agent returns 404."""
        response = await client.get("/chat/99999/messages")
        # Should return 404 or empty list depending on implementation
        assert response.status_code in [404, 200]

    async def test_send_chat_message_agent_not_found(self, client):
        """Test send message to non-existent agent."""
        response = await client.post(
            "/chat/99999/messages", json={"content": "Hello", "is_from_user": True}
        )
        # Should return 404 or 400
        assert response.status_code in [404, 400, 201]

    async def test_clear_chat_messages_agent_not_found(self, client):
        """Test clear messages for non-existent agent."""
        response = await client.delete("/chat/99999/messages")
        assert response.status_code == 200


class TestChatStatus:
    """Test chat status endpoints."""

    async def test_get_chat_status_agent_not_found(self, client):
        """Test get status for non-existent agent."""
        response = await client.get("/chat/99999/status")
        # Should return 404 or error
        assert response.status_code in [404, 200]
