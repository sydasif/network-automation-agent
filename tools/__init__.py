"""Network automation tools package.

This package provides all network automation tools using a plugin-like architecture.
Tools can be added/removed by creating new tool functions and decorating them with @network_tool.
"""

from functools import partial

from langchain_core.tools import StructuredTool

from core.task_executor import TaskExecutor
from tools.registry import get_all_tools, reset_registry


def create_tools(task_executor: TaskExecutor | None = None) -> list:
    """Create all available network automation tools.

    If `task_executor` is provided (legacy/test usage), the tools will be
    bound to it using partial for backward compatibility. In normal runtime
    the tools should obtain dependencies via InjectedState.
    """
    if task_executor is None:
        return get_all_tools()

    # Backwards-compatible construction (tests may rely on this)
    tools = []
    from tools.config_tool import ConfigCommandInput, config_command
    from tools.show_tool import ShowCommandInput, show_command

    show_tool = StructuredTool.from_function(
        func=partial(show_command, task_executor=task_executor),
        name="show_command",
        description=(
            "Run 'show' commands on network devices. "
            "Use for: viewing config, status, routing, ARP/MAC. "
            "REQUIREMENT: Use valid device names from inventory. "
            "read-only operation. "
        ),
        args_schema=ShowCommandInput,
        handle_tool_errors=True,
    )

    config_tool = StructuredTool.from_function(
        func=partial(config_command, task_executor=task_executor),
        name="config_command",
        description=(
            "Apply config changes to devices. REQUIRES APPROVAL. "
            "Use for: interfaces, routing, ACLs, VLANs. "
            "REQUIREMENT: Use valid device platform syntax. "
        ),
        args_schema=ConfigCommandInput,
        handle_tool_errors=True,
    )

    tools.extend([show_tool, config_tool])
    return tools


__all__ = [
    "create_tools",
    "reset_registry",
]
