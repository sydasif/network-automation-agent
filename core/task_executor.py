"""Network task execution engine.

This module provides the TaskExecutor class that executes
Nornir tasks with network-aware error handling.
"""

import logging
from typing import Any, Union

from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoBaseException,
    NetmikoTimeoutException,
)

from core.nornir_manager import NornirManager

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executes network tasks with error handling.

    This class wraps Nornir task execution with network-specific
    error handling and result processing.
    """

    def __init__(self, nornir_manager: NornirManager):
        """Initialize the task executor.

        Args:
            nornir_manager: NornirManager instance
        """
        self._nornir_manager = nornir_manager

    def execute_task(
        self,
        target_devices: Union[str, list[str]],
        task_function: callable,
        **kwargs,
    ) -> dict[str, Any]:
        """Execute Nornir task with network-aware error handling.

        Args:
            target_devices: Single device or list of devices to target.
            task_function: Nornir task function to execute.
            **kwargs: Additional arguments to pass to task function.

        Returns:
            Dict mapping hostname to execution result with success/error info.
            Format:
            {
                "hostname": {
                    "success": bool,
                    "output": Any,  # Result from task if successful
                    "error": str | None  # Error message if failed
                }
            }

        Example:
            >>> executor = TaskExecutor(nornir_manager)
            >>> results = executor.execute_task(
            ...     target_devices=["sw1", "sw2"],
            ...     task_function=netmiko_send_command,
            ...     command_string="show version"
            ... )
        """
        # Normalize to set for consistent handling
        targets = {target_devices} if isinstance(target_devices, str) else set(target_devices)

        # Get available hosts
        available_hosts = set(self._nornir_manager.get_hosts().keys())

        # Check for invalid devices
        if invalid := targets - available_hosts:
            return {"error": f"Devices not found: {sorted(invalid)}"}

        # Filter to target devices and run task
        filtered_nr = self._nornir_manager.filter_hosts(list(targets))
        results = filtered_nr.run(task=task_function, **kwargs)

        # Transform Nornir results into standardized format
        return self._process_results(results)

    def _process_results(self, results) -> dict[str, Any]:
        """Process Nornir results into standardized format.

        Args:
            results: Nornir AggregatedResult object

        Returns:
            Dict mapping hostname to processed result
        """
        output = {}

        for hostname, multi_result in results.items():
            res = multi_result[0] if multi_result else None

            if not multi_result.failed and res:
                # Success case
                output[hostname] = {
                    "success": True,
                    "output": res.result,
                    "error": None,
                }
            else:
                # Error case - map exceptions to user-friendly messages
                error_msg = self._get_error_message(res)

                output[hostname] = {
                    "success": False,
                    "output": None,
                    "error": error_msg,
                }

        return output

    def _get_error_message(self, result) -> str:
        """Get user-friendly error message from Nornir result.

        Args:
            result: Nornir MultiResult object

        Returns:
            User-friendly error message
        """
        if not result or not result.exception:
            return "Unknown error"

        exception = result.exception

        # Map Netmiko exceptions to user-friendly messages
        if isinstance(exception, NetmikoTimeoutException):
            return "Connection timed out. Check connectivity and firewall rules."
        elif isinstance(exception, NetmikoAuthenticationException):
            return "Authentication failed. Check device credentials."
        elif isinstance(exception, NetmikoBaseException):
            return f"Netmiko Error: {exception}"
        else:
            return str(exception)
