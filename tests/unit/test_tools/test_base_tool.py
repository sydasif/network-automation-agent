"""Unit tests for NetworkTool base class."""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from core.task_executor import TaskExecutor
from tools.base_tool import NetworkTool


class TestInput(BaseModel):
    arg1: str = Field(description="Argument 1")


class ConcreteTool(NetworkTool):
    """Concrete implementation of NetworkTool for testing."""

    def __init__(self, task_executor):
        self.task_executor = task_executor

    @property
    def name(self) -> str:
        return "test_tool"

    @property
    def description(self) -> str:
        return "Test tool description"

    @property
    def args_schema(self) -> type[BaseModel]:
        return TestInput

    def _execute_impl(self, **kwargs) -> str:
        return f"Executed with {kwargs}"


@pytest.fixture
def mock_task_executor():
    return MagicMock(spec=TaskExecutor)


def test_tool_initialization(mock_task_executor):
    """Test tool initialization."""
    tool = ConcreteTool(mock_task_executor)
    assert tool.name == "test_tool"
    assert tool.description == "Test tool description"
    assert tool.args_schema == TestInput


def test_to_langchain_tool(mock_task_executor):
    """Test conversion to LangChain tool."""
    tool = ConcreteTool(mock_task_executor)
    lc_tool = tool.to_langchain_tool()

    assert lc_tool.name == "test_tool"
    assert lc_tool.description == "Test tool description"
    assert lc_tool.args_schema == TestInput

    # Test execution through LangChain wrapper
    result = lc_tool.invoke({"arg1": "value1"})
    assert result == "Executed with {'arg1': 'value1'}"
