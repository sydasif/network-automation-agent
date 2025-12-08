"""Network automation tools package.

This package provides all network automation tools using a plugin-like architecture.
Tools can be added/removed by creating new tool classes and registering them here.
"""

from core.task_executor import TaskExecutor
from tools.base_tool import NetworkTool
from tools.config_tool import ConfigCommandTool
from tools.show_tool import ShowCommandTool


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
    ]

    # Convert to LangChain tool format
    return [tool.to_langchain_tool() for tool in tools]


__all__ = [
    "NetworkTool",
    "ShowCommandTool",
    "ConfigCommandTool",
    "create_tools",
]
