"""Network task execution engine.

This module provides the TaskExecutor class that executes
Nornir tasks with network-aware error handling.
"""

import logging
import time  # <--- Import time
from typing import Any, Union
import random

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

    def _execute_with_retry(self, nornir_instance, task_function, max_retries=3, **kwargs):
        """Execute Nornir task with retry logic for transient failures.

        Args:
            nornir_instance: Filtered Nornir instance to run the task on
            task_function: Nornir task function to execute
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments to pass to task function

        Returns:
            Results from the Nornir task execution
        """
        for attempt in range(max_retries + 1):  # First attempt + retries
            try:
                results = nornir_instance.run(task=task_function, **kwargs)

                # Check if there are any failures that might be transient
                has_transient_failures = False
                for hostname, result in results.items():
                    if result.failed:
                        # Check if the failure is a timeout or connection issue that might be transient
                        if (result.exception and
                            (isinstance(result.exception, (NetmikoTimeoutException, ConnectionError)) or
                             "timeout" in str(result.exception).lower() or
                             "connection" in str(result.exception).lower())):
                            has_transient_failures = True
                            break

                # If there are no failures or no transient failures, return results
                if not has_transient_failures or attempt == max_retries:
                    return results

                # If there are transient failures, log and retry after a delay
                logger.warning(f"Transient failures detected, retrying in {2 ** attempt}s (attempt {attempt + 1}/{max_retries + 1})")
                time.sleep(2 ** attempt + random.uniform(0, 1))  # Exponential backoff with jitter

            except Exception as e:
                if attempt == max_retries:
                    # If we've exhausted retries, re-raise the exception
                    raise e
                logger.warning(f"Attempt {attempt + 1} failed with error: {e}, retrying in {2 ** attempt}s")
                time.sleep(2 ** attempt + random.uniform(0, 1))  # Exponential backoff with jitter

        # This should not be reached, but return results if needed
        return nornir_instance.run(task=task_function, **kwargs)

    def execute_task(
        self,
        target_devices: Union[str, list[str]],
        task_function: callable,
        max_retries: int = 2,  # Default to 2 retries for transient issues
        **kwargs,
    ) -> dict[str, Any]:
        """Execute Nornir task with network-aware error handling.

        Args:
            target_devices: Single device or list of devices to target.
            task_function: Nornir task function to execute.
            max_retries: Maximum number of retry attempts for transient failures (default: 2).
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

        # Calculate optimal number of workers based on target devices
        num_targets = len(targets)
        # Use between 4 and 20 workers, or number of targets if less than 4
        optimal_workers = min(max(4, num_targets), 20)

        # Filter to target devices with optimal worker count
        try:
            filtered_nr = self._nornir_manager.filter_hosts(list(targets), num_workers=optimal_workers)

            # CRITICAL: Check if we actually have hosts after filtering
            if not filtered_nr.inventory.hosts:
                return {"error": f"No valid hosts found in inventory matching: {targets}"}

            # Pre-flight connectivity check
            connectivity_results = self._nornir_manager.test_connectivity(list(targets))
            unreachable = [host for host, is_reachable in connectivity_results.items() if not is_reachable]

            if unreachable:
                logger.warning(f"Unreachable devices detected: {unreachable}")
                # Continue execution but warn - some devices might be temporarily unreachable
                # In a production environment, you might want to fail fast instead
                pass

            # Execute with retry logic for transient failures
            results = self._execute_with_retry(
                nornir_instance=filtered_nr,
                task_function=task_function,
                max_retries=max_retries,
                **kwargs
            )

            # STABILITY FIX: Add a small delay to allow device buffers/sessions to settle
            # This prevents "Prompt not detected" errors when hitting the same device rapidly
            # Reduce the delay since we now have better worker management
            time.sleep(0.5)

            return self._process_results(results)

        except Exception as e:
            logger.error(f"Critical execution failure: {e}")
            # Return a formatted error for ALL targets so the UI can show it
            return {dev: {"success": False, "output": None, "error": str(e)} for dev in targets}

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
