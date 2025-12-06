"""Configuration command tool for network device configuration.

This module provides the ConfigCommandTool class for applying
configuration changes to network devices.
"""

from langchain_core.tools import ToolException
from nornir_netmiko.tasks import netmiko_send_config
from pydantic import BaseModel, Field

from core.task_executor import TaskExecutor
from tools.base_tool import NetworkTool
from utils.responses import process_nornir_result


class ConfigCommandInput(BaseModel):
    """Input schema for configuration commands."""

    devices: list[str] = Field(description="List of device hostnames (e.g., ['sw1', 'sw2']).")
    configs: list[str] = Field(
        description="List of configuration commands.",
    )


class ConfigCommandTool(NetworkTool):
    """Apply configuration changes to network devices.

    This tool uses Nornir and Netmiko to apply configuration commands
    to network devices. Requires human approval before execution.
    """

    def __init__(self, task_executor: TaskExecutor):
        """Initialize the config command tool.

        Args:
            task_executor: TaskExecutor instance for running tasks
        """
        self._task_executor = task_executor

    @property
    def name(self) -> str:
        """Tool name."""
        return "config_command"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Apply config changes to devices. REQUIRES APPROVAL. "
            "Use for: interfaces, routing, ACLs, VLANs. "
            "REQUIREMENT: Use valid device platform syntax. "
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        """Arguments schema."""
        return ConfigCommandInput

    def _run(self, devices: list[str], configs: list[str]) -> str:
        """Apply configuration commands to specified devices.

        Args:
            devices: List of device hostnames to target
            configs: List of configuration commands

        Returns:
            JSON string with device results
        """
        # Validate inputs
        if not devices:
            raise ToolException("No devices specified. Please select from inventory.")

        # Sanitize: split multi-line commands and filter empty lines
        clean_configs = [c.strip() for cmd in configs for c in cmd.split("\n") if c.strip()]
        if not clean_configs:
            raise ToolException("No configuration commands provided.")

        # Execute via task executor
        results = self._task_executor.execute_task(
            target_devices=devices,
            task_function=netmiko_send_config,
            config_commands=clean_configs,
        )

        # Process and return results
        return process_nornir_result(results, configs=clean_configs)
