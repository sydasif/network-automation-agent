"""Nornir driver with network-grade error handling."""

import logging
from functools import lru_cache
from typing import Any, Union

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
    """Return a formatted string of devices and platforms (Cached)."""
    nr = _get_nornir()
    # Sorting ensures the string is deterministic, helping LLM caching
    sorted_hosts = sorted(nr.inventory.hosts.items())
    return "\n".join(
        f"- {name} (Platform: {host.platform or 'unknown'})" for name, host in sorted_hosts
    )


def execute_nornir_task(
    target_devices: Union[str, list[str]],
    task_function: callable,
    **kwargs,
) -> dict[str, Any]:
    """Execute Nornir task with network-aware error handling."""
    targets = {target_devices} if isinstance(target_devices, str) else set(target_devices)
    nr = _get_nornir()

    available_hosts = set(nr.inventory.hosts.keys())

    # Fast validation
    if invalid := targets - available_hosts:
        return {"error": f"Devices not found: {list(invalid)}"}

    # Filter and Run
    filtered_nr = nr.filter(F(name__any=list(targets)))
    results = filtered_nr.run(task=task_function, **kwargs)

    # Transform Results with error categorization
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
            # 🆕 ADD ERROR CATEGORIZATION
            error_str = str(res.exception) if res and res.exception else "Unknown error"
            error_type = _categorize_network_error(error_str)

            output[hostname] = {
                "success": False,
                "output": None,
                "error": error_str,
                "error_type": error_type,  # 🆕 NEW FIELD
            }

    return output


# 🆕 ADD THIS FUNCTION
def _categorize_network_error(error_str: str) -> str:
    """Categorize network errors for better LLM understanding."""
    error_lower = error_str.lower()

    if "authentication" in error_lower or "permission denied" in error_lower:
        return "AUTH_FAILED"
    elif "timed out" in error_lower or "timeout" in error_lower:
        return "TIMEOUT"
    elif "connection refused" in error_lower or "no route" in error_lower:
        return "UNREACHABLE"
    elif "invalid" in error_lower or "syntax error" in error_lower:
        return "INVALID_COMMAND"
    elif "configuration mode" in error_lower:
        return "CONFIG_MODE_ERROR"
    else:
        return "UNKNOWN"
