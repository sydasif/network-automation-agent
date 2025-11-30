"""Nornir driver with network-grade error handling."""

import logging
from functools import lru_cache
from typing import Any, Union

from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoBaseException,
    NetmikoTimeoutException,
)
from nornir import InitNornir
from nornir.core.filter import F

logger = logging.getLogger(__name__)

_nornir_instance = None


def _get_nornir() -> InitNornir:
    """Lazily initialize Nornir instance (Singleton)."""
    global _nornir_instance
    if _nornir_instance is None:
        # Initialize Nornir using the config file
        nr = InitNornir(config_file="config.yaml")
        _nornir_instance = nr
    return _nornir_instance


@lru_cache(maxsize=1)
def get_device_info() -> str:
    """Return formatted string of devices and platforms.

    Cached to avoid redundant lookups and ensure deterministic LLM prompts.
    """
    nr = _get_nornir()
    sorted_hosts = sorted(nr.inventory.hosts.items())
    return "\n".join(
        f"- {name} (Platform: {host.platform or 'unknown'})" for name, host in sorted_hosts
    )


def execute_nornir_task(
    target_devices: Union[str, list[str]],
    task_function: callable,
    **kwargs,
) -> dict[str, Any]:
    """Execute Nornir task with network-aware error handling.

    Args:
        target_devices: Single device or list of devices to target
        task_function: Nornir task function to execute
        **kwargs: Additional arguments to pass to task function

    Returns:
        Dict mapping hostname to execution result with success/error info
    """
    targets = {target_devices} if isinstance(target_devices, str) else set(target_devices)
    nr = _get_nornir()

    available_hosts = set(nr.inventory.hosts.keys())

    if invalid := targets - available_hosts:
        return {"error": f"Devices not found: {list(invalid)}"}

    filtered_nr = nr.filter(F(name__any=list(targets)))
    results = filtered_nr.run(task=task_function, **kwargs)

    # Transform Nornir results into standardized format
    output = {}
    for hostname, multi_result in results.items():
        res = multi_result[0] if multi_result else None

        if not multi_result.failed and res:
            output[hostname] = {
                "success": True,
                "output": res.result,
                "error": None,
            }
        else:
            # Map Netmiko exceptions to user-friendly error messages
            error_msg = "Unknown error"
            if res and res.exception:
                if isinstance(res.exception, NetmikoTimeoutException):
                    error_msg = "Connection timed out. Check connectivity and firewall rules."
                elif isinstance(res.exception, NetmikoAuthenticationException):
                    error_msg = "Authentication failed. Check device credentials."
                elif isinstance(res.exception, NetmikoBaseException):
                    error_msg = f"Netmiko Error: {res.exception}"
                else:
                    error_msg = str(res.exception)

            output[hostname] = {
                "success": False,
                "output": None,
                "error": error_msg,
            }

    return output
