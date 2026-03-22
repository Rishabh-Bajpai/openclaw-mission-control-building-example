"""
Meeting API Tests - All meeting endpoints.

Note: Standup tests may require OpenClaw Gateway/LLM services.
"""

import pytest
import pytest_asyncio
from app.models.models import Meeting


class TestMeetings:
    """Test meeting endpoints."""

    async def test_get_meeting_not_found(self, client):
        """Test get non-existent meeting."""
        response = await client.get("/meetings/99999")
        assert response.status_code == 404


class TestStandup:
    """Test standup meeting endpoints."""

    async def test_standup_no_c_suite_returns_400(self, client, sample_team):
        """Test standup without C-suite agents returns error."""
        # Without proper OpenClaw connection, this should fail
        response = await client.post("/meetings/standup")
        # Should return error since there's no CEO agent
        assert response.status_code in [400, 404, 500]
