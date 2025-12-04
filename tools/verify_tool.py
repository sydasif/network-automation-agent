"""Verify changes tool for validating network state.

This module provides the VerifyChangesTool class for user-triggered
verification of network configuration changes.
"""

from nornir_netmiko.tasks import netmiko_send_command
from pydantic import BaseModel, Field

from core.task_executor import TaskExecutor
from tools.base_tool import NetworkTool
from utils.responses import error, process_nornir_result


class VerifyChangesInput(BaseModel):
    """Input schema for verify_changes tool."""

    devices: list[str] = Field(
        description="List of device hostnames to verify (e.g., ['sw1', 'sw2'])."
    )
    check_commands: list[str] = Field(
        description="List of verification commands to run (e.g., ['show run | include hostname', 'show ip int brief'])."
    )


class VerifyChangesTool(NetworkTool):
    """Verify network configuration changes.

    This tool allows users to explicitly verify that configuration changes
    were applied correctly by running verification commands.
    """

    def __init__(self, task_executor: TaskExecutor):
        """Initialize the verify changes tool.

        Args:
            task_executor: TaskExecutor instance for running tasks
        """
        self._task_executor = task_executor

    @property
    def name(self) -> str:
        """Tool name."""
        return "verify_changes"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Verify that configuration changes were applied correctly. "
            "Use this when the user explicitly asks to verify, check, or validate recent changes. "
            "Examples: 'verify the last changes', 'check if OSPF is configured', 'validate the hostname change'. "
            "This tool runs verification commands and compares output to confirm changes were applied. "
            "REQUIREMENT: All device names MUST be from the inventory."
        )

    @property
    def args_schema(self) -> type[BaseModel]:
        """Arguments schema."""
        return VerifyChangesInput

    def _execute_impl(self, devices: list[str], check_commands: list[str]) -> str:
        """Verify changes on specified devices.

        Args:
            devices: List of device hostnames to verify
            check_commands: List of verification commands to run

        Returns:
            JSON string with verification results
        """
        # Validate inputs
        if not devices:
            return error("No devices specified for verification.")
        if not check_commands:
            return error("No verification commands provided.")

        # Run each verification command
        all_results = {}
        for command in check_commands:
            results = self._task_executor.execute_task(
                target_devices=devices,
                task_function=netmiko_send_command,
                command_string=command,
            )
            all_results[command] = process_nornir_result(results, command=command)

        # Combine results
        import json

        return json.dumps(
            {
                "verification_results": all_results,
                "devices_checked": devices,
                "commands_run": check_commands,
            },
            indent=2,
        )
