"""Unit tests for show_command tool function."""

from unittest.mock import MagicMock

import pytest

from core.task_executor import TaskExecutor
from tools.show_tool import show_command


@pytest.fixture
def mock_task_executor():
    return MagicMock(spec=TaskExecutor)


def test_show_tool_execution(mock_task_executor):
    """Test execution of show commands."""
    # Mock task executor result
    mock_task_executor.execute_task.return_value = {"R1": "output"}

    result = show_command(devices=["R1"], command="show version", task_executor=mock_task_executor)

    # Verify task executor was called correctly
    mock_task_executor.execute_task.assert_called_once()
    call_args = mock_task_executor.execute_task.call_args
    assert call_args.kwargs["target_devices"] == ["R1"]
    assert call_args.kwargs["command_string"] == "show version"

    # Verify result format (JSON string)
    assert "R1" in result
    assert "output" in result


def test_show_tool_execution_no_devices(mock_task_executor):
    """Test execution without specifying devices (should raise ToolException)."""
    # Should raise ToolException
    with pytest.raises(Exception) as exc_info:
        show_command(devices=[], command="show version", task_executor=mock_task_executor)

    assert "No devices specified" in str(exc_info.value)

    # Task executor should NOT be called
    mock_task_executor.execute_task.assert_not_called()
