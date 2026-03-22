"""
Workspace Manager Service Unit Tests.
"""

import pytest
from app.services.workspace_manager import workspace_manager


class TestWorkspaceManager:
    """Test workspace manager functions via the global instance."""

    def test_get_agent_workspace_returns_path(self):
        """Test get workspace path for agent returns a string."""
        result = workspace_manager.get_agent_workspace("test_agent")
        assert isinstance(result, str)
        assert "test_agent" in result

    def test_list_agents_returns_list(self):
        """Test listing agents returns a list."""
        result = workspace_manager.list_agents()
        assert isinstance(result, list)
