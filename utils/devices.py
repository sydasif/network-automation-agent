"""Nornir driver and utility functions - KISS implementation."""

import logging
import os
from functools import lru_cache
from typing import Any, Union

from nornir import InitNornir
from nornir.core.filter import F

from pathlib import Path

logger = logging.getLogger(__name__)

_nornir_instance = None


def _get_nornir() -> InitNornir:
    """Lazily initialize Nornir instance (Singleton)."""
    global _nornir_instance
    if _nornir_instance is None:
        # Initialize Nornir using the config file
        nr = InitNornir(config_file="config.yaml")

        # Inject passwords
        for host in nr.inventory.hosts.values():
            if env_var := host.data.get("password_env_var"):
                host.password = os.environ.get(env_var)

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
    """Execute Nornir task on specified devices."""
    targets = {target_devices} if isinstance(target_devices, str) else set(target_devices)
    nr = _get_nornir()

    available_hosts = set(nr.inventory.hosts.keys())

    # Fast validation
    if invalid := targets - available_hosts:
        return {"error": f"Devices not found: {list(invalid)}"}

    # Filter and Run
    filtered_nr = nr.filter(F(name__any=list(targets)))
    results = filtered_nr.run(task=task_function, **kwargs)

    # Transform Results
    output = {}
    for hostname, multi_result in results.items():
        res = multi_result[0] if multi_result else None

        # Handle cases where Nornir/Netmiko returns an exception object as the result
        is_success = not multi_result.failed
        result_data = res.result if res else None
        error_msg = str(res.exception) if res and res.exception else None

        output[hostname] = {"success": is_success, "output": result_data, "error": error_msg}

    return output
