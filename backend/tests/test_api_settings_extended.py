"""
Extended Settings API Tests - OpenClaw settings.

Note: OpenClaw connection tests require external service.
"""

import pytest
import pytest_asyncio


class TestSettingsBasic:
    """Basic settings tests."""

    async def test_update_llm_settings_accepts_request(self, client):
        """Test LLM settings endpoint accepts requests."""
        response = await client.put(
            "/settings/llm",
            json={
                "llm_api_url": "https://api.example.com",
            },
        )
        # Should accept the request (may return 200 or error depending on config)
        assert response.status_code in [200, 422]


class TestOpenClawSettings:
    """OpenClaw settings tests."""

    async def test_test_openclaw_connection_returns_status(self, client):
        """Test OpenClaw connection test endpoint."""
        response = await client.post("/settings/openclaw/test")
        # Should return a response (success or failure)
        assert response.status_code in [200, 503]
