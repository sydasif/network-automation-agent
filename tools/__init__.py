"""Network automation tools package.

This package provides all network automation tools using a plugin-like architecture.
Tools can be added/removed by creating new tool classes and registering them here.
"""

from core.task_executor import TaskExecutor
from tools.base_tool import NetworkTool
from tools.config_tool import ConfigCommandTool
from tools.format_tool import FormatOutputTool
from tools.multi_command import MultiCommandTool
from tools.response_tool import ResponseTool
from tools.show_tool import ShowCommandTool
from tools.verify_tool import VerifyChangesTool


def create_tools(task_executor: TaskExecutor) -> list:
    """Create all available network automation tools.

    This is the tool registry. To add a new tool:
    1. Create a new tool class inheriting from NetworkTool
    2. Import it above
    3. Add it to the list below

    Args:
        task_executor: TaskExecutor instance for tools that need it

    Returns:
        List of LangChain-compatible tool instances
    """
    tools = [
        ShowCommandTool(task_executor),
        ConfigCommandTool(task_executor),
        MultiCommandTool(),
        ResponseTool(),
        VerifyChangesTool(task_executor),
    ]

    # Convert to LangChain tool format
    return [tool.to_langchain_tool() for tool in tools]


def create_format_tool() -> FormatOutputTool:
    """Create the format_output tool separately.

    This tool is used by FormatNode and should not be available
    to the main agent routing.

    Returns:
        FormatOutputTool instance
    """
    return FormatOutputTool()


__all__ = [
    "NetworkTool",
    "ShowCommandTool",
    "ConfigCommandTool",
    "MultiCommandTool",
    "ResponseTool",
    "FormatOutputTool",
    "VerifyChangesTool",
    "create_tools",
    "create_format_tool",
]
