"""Show command tool for read-only network operations.

This module provides a function-based show command tool for executing
read-only show commands on network devices.
"""

from nornir_netmiko.tasks import netmiko_send_command
from pydantic import BaseModel, Field

from core.task_executor import TaskExecutor
from tools.registry import network_tool
from tools.validators import ToolValidator
from utils.responses import process_nornir_result


class ShowCommandInput(BaseModel):
    """Input schema for show commands."""

    devices: list[str] = Field(description="List of device hostnames (e.g., ['sw1', 'sw2']).")
    command: str = Field(description="The show command to execute (e.g., 'show ip int brief').")


@network_tool(
    name="show_command",
    description=(
        "Run 'show' commands on network devices. "
        "Use for: viewing config, status, routing, ARP/MAC. "
        "REQUIREMENT: Use valid device names from inventory. "
        "read-only operation. "
    ),
    schema=ShowCommandInput,
)
def show_command(
    devices: list[str],
    command: str,
    task_executor: TaskExecutor,
) -> str:
    """Execute show command on specified devices.

    Args:
        devices: List of device hostnames to target
        command: Show command to execute
        task_executor: TaskExecutor instance for running tasks

    Returns:
        JSON string with device results
    """
    # Validate inputs using ToolValidator (raises OutputParserException when invalid)
    ToolValidator.validate_devices(devices)
    ToolValidator.validate_command(command)

    # Execute via task executor
    results = task_executor.execute_task(
        target_devices=devices,
        task_function=netmiko_send_command,
        command_string=command,
    )

    # Process and return results
    return process_nornir_result(results, command=command)
