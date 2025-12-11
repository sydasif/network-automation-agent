"""Unit tests for tool registry and decorator."""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from core.task_executor import TaskExecutor
from tools.registry import get_all_tools, get_tool, network_tool, reset_registry


def test_network_tool_decorator():
    """Test the network_tool decorator functionality."""

    class TestSchema(BaseModel):
        arg1: str = Field(description="Argument 1")
        arg2: int = Field(description="Argument 2", default=0)

    # Reset registry to start fresh
    reset_registry()

    @network_tool(name="test_tool", description="A test tool", schema=TestSchema)
    def test_tool_function(arg1: str, arg2: int = 0, task_executor: TaskExecutor = None):
        return f"Executed with {arg1} and {arg2}"

    # Verify the tool was registered
    tools = get_all_tools()
    assert len(tools) == 1

    tool = tools[0]
    assert tool.name == "test_tool"
    assert "A test tool" in tool.description


def test_get_specific_tool():
    """Test getting a specific tool by name."""
    # Reset registry to start fresh
    reset_registry()

    @network_tool(
        name="specific_tool",
        description="A specific tool",
    )
    def specific_tool_function(task_executor: TaskExecutor = None):
        return "Specific tool executed"

    # Get the specific tool
    tool = get_tool("specific_tool")
    assert tool.name == "specific_tool"
    assert "A specific tool" in tool.description

    # Test that getting a non-existent tool raises an error
    with pytest.raises(KeyError):
        get_tool("non_existent_tool")


def test_create_tools_integration():
    """Test that the tools are properly created via create_tools function."""
    from tools import create_tools

    mock_task_executor = MagicMock(spec=TaskExecutor)

    # Create the tools
    tools = create_tools(mock_task_executor)

    # Should have both show_command and config_command tools
    tool_names = [tool.name for tool in tools]
    assert "show_command" in tool_names
    assert "config_command" in tool_names
    assert len(tool_names) == 2
