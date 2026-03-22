"""
OpenClaw Gateway Service Unit Tests.

Note: These tests verify the structure and methods of the gateway.
Full integration tests require a running OpenClaw Gateway instance.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from app.services.openclaw_gateway import OpenClawGateway


class TestOpenClawGatewayStructure:
    """Test gateway class structure and methods."""

    def test_gateway_has_required_methods(self):
        """Test that OpenClawGateway has all required methods."""
        gateway = OpenClawGateway()
        assert hasattr(gateway, "create_agent")
        assert hasattr(gateway, "update_agent")
        assert hasattr(gateway, "delete_agent")
        assert hasattr(gateway, "run_agent")
        assert hasattr(gateway, "send_chat_message")
        assert hasattr(gateway, "get_chat_history")
        assert hasattr(gateway, "health_check")
        assert hasattr(gateway, "get_status")
        assert hasattr(gateway, "set_agent_heartbeat")
        assert hasattr(gateway, "get_agent_heartbeat")
        assert hasattr(gateway, "add_agent_to_config")

    def test_gateway_initialization(self):
        """Test gateway initializes with config."""
        gateway = OpenClawGateway()
        assert hasattr(gateway, "ws_url")
        assert hasattr(gateway, "token")

    @pytest.mark.asyncio
    async def test_set_agent_heartbeat_returns_correct_structure(self):
        """Test set_agent_heartbeat returns HeartbeatResult."""
        gateway = OpenClawGateway()

        with patch(
            "app.services.openclaw_gateway.openclaw_call", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = None  # Simulates failure to get config

            result = await gateway.set_agent_heartbeat("test_agent", 10, "/workspace")

            assert isinstance(result, dict)
            assert "success" in result
            assert "rate_limited" in result
            assert "retry_seconds" in result
            assert "error_message" in result

    @pytest.mark.asyncio
    async def test_get_agent_heartbeat_returns_int(self):
        """Test get_agent_heartbeat returns integer minutes."""
        gateway = OpenClawGateway()

        with patch(
            "app.services.openclaw_gateway.openclaw_call", new_callable=AsyncMock
        ) as mock_call:
            mock_call.return_value = None  # Simulates failure

            result = await gateway.get_agent_heartbeat("test_agent")

            assert isinstance(result, int)
            assert result == 0  # Should return 0 on error

    @pytest.mark.asyncio
    async def test_health_check_returns_dict(self):
        """Test health_check returns a dictionary."""
        gateway = OpenClawGateway()

        with patch(
            "app.services.openclaw_gateway.openclaw_call", new_callable=AsyncMock
        ) as mock_call:
            mock_call.side_effect = Exception("Connection failed")

            result = await gateway.health_check()

            assert isinstance(result, dict)
            assert "connected" in result
            assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_run_agent_returns_none_on_error(self):
        """Test run_agent returns None on exception."""
        gateway = OpenClawGateway()

        with patch(
            "app.services.openclaw_gateway.ensure_session", new_callable=AsyncMock
        ) as mock_session:
            mock_session.side_effect = Exception("WebSocket error")

            result = await gateway.run_agent("test_agent")

            assert result is None
