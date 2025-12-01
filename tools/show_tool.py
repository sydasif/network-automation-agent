"""Show command tool for read-only network operations.

This module provides the ShowCommandTool class for executing
read-only show commands on network devices.
"""

from nornir_netmiko.tasks import netmiko_send_command
from pydantic import BaseModel, Field

from core.task_executor import TaskExecutor
from tools.base_tool import NetworkTool
from utils.responses import error, process_nornir_result


class ShowCommandInput(BaseModel):
    """Input schema for show commands."""

    devices: list[str] = Field(description="List of device hostnames (e.g., ['sw1', 'sw2']).")
    command: str = Field(description="The show command to execute (e.g., 'show ip int brief').")


class ShowCommandTool(NetworkTool):
    """Execute read-only show commands on network devices.

    This tool uses Nornir and Netmiko to execute show commands
    across multiple devices in parallel.
    """

    def __init__(self, task_executor: TaskExecutor):
        """Initialize the show command tool.

        Args:
            task_executor: TaskExecutor instance for running tasks
        """
        self._task_executor = task_executor

    @property
    def name(self) -> str:
        """Tool name."""
        return "show_command"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Execute a read-only 'show' command on one or more network devices. "
            "Use this for gathering information without making changes."
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        """Arguments schema."""
        return ShowCommandInput

    def _execute_impl(self, devices: list[str], command: str) -> str:
        """Execute show command on specified devices.

        Args:
            devices: List of device hostnames to target
            command: Show command to execute

        Returns:
            JSON string with device results
        """
        # Validate inputs
        if not devices:
            return error("No devices specified.")
        if not command.strip():
            return error("Command cannot be empty.")

        # Execute via task executor
        results = self._task_executor.execute_task(
            target_devices=devices,
            task_function=netmiko_send_command,
            command_string=command,
        )

        # Process and return results
        return process_nornir_result(results, command=command)
