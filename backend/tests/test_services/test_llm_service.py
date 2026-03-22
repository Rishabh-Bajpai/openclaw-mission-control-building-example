"""
LLM Service Unit Tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.llm_service import LLMService


@pytest.fixture
def llm_service():
    """Create LLM service instance with test config."""
    return LLMService(
        api_url="https://api.example.com/v1/chat/completions",
        api_key="test-key",
        model="test-model",
    )


class TestGenerate:
    """Test generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(self, llm_service):
        """Test successful generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Generated response"}}]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = await llm_service.generate([{"role": "user", "content": "Hello"}])
            assert result == "Generated response"

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, llm_service):
        """Test generation with system prompt."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = await llm_service.generate(
                [{"role": "user", "content": "Hi"}], system_prompt="You are helpful"
            )
            assert result == "Response"
            # Verify post was called
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_http_error_returns_none(self, llm_service):
        """Test generation returns None on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        import httpx

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=mock_response
            )

            result = await llm_service.generate([{"role": "user", "content": "Test"}])
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_exception_returns_none(self, llm_service):
        """Test generation returns None on exception."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = Exception("Network error")

            result = await llm_service.generate([{"role": "user", "content": "Test"}])
            assert result is None


class TestParseActions:
    """Test parse_actions method."""

    def test_parse_actions_format_1(self, llm_service):
        """Test parsing actions from pipe-delimited format."""
        response = "ACTION:MOVE_TASK|task_id:123|status:review"
        result = llm_service.parse_actions(response)
        assert len(result) == 1
        assert result[0]["type"] == "MOVE_TASK"
        assert result[0]["task_id"] == "123"
        assert result[0]["status"] == "review"

    def test_parse_actions_format_2(self, llm_service):
        """Test parsing actions from bracket format."""
        response = "[ACTION] MOVE_TASK task_id: 456 status: completed"
        result = llm_service.parse_actions(response)
        assert len(result) == 1
        assert result[0]["type"] == "MOVE_TASK"

    def test_parse_actions_no_actions(self, llm_service):
        """Test parsing response with no actions."""
        response = "This is just a regular response without actions."
        result = llm_service.parse_actions(response)
        assert result == []


class TestGenerateAgentFiles:
    """Test generate_agent_files method."""

    @pytest.mark.asyncio
    async def test_generate_agent_files_success(self, llm_service):
        """Test successful agent files generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"soul": "Soul content", "identity": "Identity content", "agents": "Agents content", "memory": "Memory content", "user": "User content"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            result = await llm_service.generate_agent_files(
                "TestAgent", "Developer", "Engineering"
            )
            assert "soul" in result
            assert "identity" in result
            assert "agents" in result

    @pytest.mark.asyncio
    async def test_generate_agent_files_fallback_on_error(self, llm_service):
        """Test agent files fallback on LLM error."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = Exception("Network error")

            result = await llm_service.generate_agent_files(
                "TestAgent", "Developer", "Engineering"
            )
            # Should return defaults
            assert "soul" in result
            assert "identity" in result
            assert "TestAgent" in result["soul"]
