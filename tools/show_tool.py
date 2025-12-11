"""Show command tool for read-only network operations.

This module provides a function-based show command tool for executing
read-only show commands on network devices with enhanced validation.
"""

from nornir_netmiko.tasks import netmiko_send_command
from pydantic import BaseModel, Field, field_validator

from core.task_executor import TaskExecutor
from tools.registry import network_tool
from tools.validators import ToolValidator
from utils.responses import process_nornir_result


class ShowCommandInput(BaseModel):
    """Input schema for show commands with enhanced validation."""

    devices: list[str] = Field(
        description="List of device hostnames (e.g., ['sw1', 'sw2']). Must contain valid device names from inventory."
    )
    command: str = Field(
        description="The show command to execute (e.g., 'show ip int brief'). Must be a read-only command."
    )

    @field_validator('devices')
    @classmethod
    def validate_devices(cls, v):
        """Validate device list using ToolValidator."""
        ToolValidator.validate_devices(v)
        return v

    @field_validator('command')
    @classmethod
    def validate_command(cls, v):
        """Validate command using ToolValidator."""
        validated_command = ToolValidator.validate_command(v)
        ToolValidator.validate_show_command_semantics(validated_command)
        return validated_command


@network_tool(
    name="show_command",
    description=(
        "Run 'show' commands on network devices. "
        "Use for: viewing config, status, routing, ARP/MAC. "
        "REQUIREMENT: Use valid device names from inventory. "
        "REQUIREMENT: Command must be read-only (e.g., 'show', 'display'). "
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
    # Additional validation beyond Pydantic field validators
    command = ToolValidator.validate_command(command)
    ToolValidator.validate_show_command_semantics(command)

    # Execute via task executor
    results = task_executor.execute_task(
        target_devices=devices,
        task_function=netmiko_send_command,
        command_string=command,
    )

    # Process and return results
    return process_nornir_result(results, command=command)
