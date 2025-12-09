"""Configuration command tool for network device configuration.

This module provides a function-based config command tool for applying
configuration changes to network devices.
"""

from nornir_netmiko.tasks import netmiko_send_config
from pydantic import BaseModel, Field

from core.task_executor import TaskExecutor
from tools.registry import network_tool
from tools.validators import ToolValidator
from utils.responses import process_nornir_result


class ConfigCommandInput(BaseModel):
    """Input schema for configuration commands."""

    devices: list[str] = Field(description="List of device hostnames (e.g., ['sw1', 'sw2']).")
    configs: list[str] = Field(
        description="List of configuration commands.",
    )


@network_tool(
    name="config_command",
    description=(
        "Apply config changes to devices. REQUIRES APPROVAL. "
        "Use for: interfaces, routing, ACLs, VLANs. "
        "REQUIREMENT: Use valid device platform syntax. "
    ),
    schema=ConfigCommandInput,
)
def config_command(
    devices: list[str],
    configs: list[str],
    task_executor: TaskExecutor,
) -> str:
    """Apply configuration commands to specified devices.

    Args:
        devices: List of device hostnames to target
        configs: List of configuration commands
        task_executor: TaskExecutor instance for running tasks

    Returns:
        JSON string with device results
    """
    # Validate inputs using ToolValidator
    ToolValidator.validate_devices(devices)
    clean_configs = ToolValidator.validate_configs(configs)

    # Execute via task executor
    results = task_executor.execute_task(
        target_devices=devices,
        task_function=netmiko_send_config,
        config_commands=clean_configs,
    )

    # Process and return results
    return process_nornir_result(results, configs=clean_configs)
