"""Nornir driver and utility functions - KISS implementation."""

import logging
import os
from typing import Any, Union

from nornir import InitNornir
from nornir.core.filter import F

from settings import INVENTORY_GROUP_FILE, INVENTORY_HOST_FILE

logger = logging.getLogger(__name__)

# Lazy initialization - only create Nornir instance when needed
_nornir_instance = None


def _get_nornir() -> InitNornir:
    """Lazily initialize Nornir instance."""
    global _nornir_instance
    if _nornir_instance is None:
        _nornir_instance = InitNornir(
            inventory={
                "plugin": "SimpleInventory",
                "options": {
                    "host_file": str(INVENTORY_HOST_FILE),
                    "group_file": str(INVENTORY_GROUP_FILE),
                },
            },
            runner={
                "plugin": "threaded",
                "options": {
                    "num_workers": 10,
                },
            },
            logging={"enabled": False},  # Disable Nornir's internal logging
        )
        _inject_passwords(_nornir_instance)
    return _nornir_instance


def _inject_passwords(nr) -> None:
    """Set passwords from environment variables."""
    for name, host in nr.inventory.hosts.items():
        env_var = host.data.get("password_env_var")
        if env_var:
            password = os.environ.get(env_var)
            if password:
                host.password = password
            else:
                logger.warning("Password env var %s not found for %s", env_var, name)


def get_all_device_names() -> list[str]:
    """Return list of device names for the LLM prompt."""
    nr = _get_nornir()
    return list(nr.inventory.hosts.keys())


def get_device_info() -> str:
    """Return a formatted string of devices and their platforms."""
    nr = _get_nornir()
    info_list = []

    for name, host in nr.inventory.hosts.items():
        # Get platform, default to "unknown" if missing
        platform = host.platform or "unknown"
        info_list.append(f"- {name} (Platform: {platform})")

    return "\n".join(info_list)


def execute_nornir_task(
    target_devices: Union[str, list[str]],
    task_function: callable,
    **kwargs,
) -> dict[str, Any]:
    """Execute Nornir task on specified devices with simplified result processing."""
    # Normalize input
    targets = [target_devices] if isinstance(target_devices, str) else target_devices
    nr = _get_nornir()
    all_hosts = list(nr.inventory.hosts.keys())

    # Validate devices exist
    invalid = [t for t in targets if t not in all_hosts]
    if invalid:
        return {"error": f"Devices not found: {invalid}. Available: {all_hosts}"}

    # Filter and execute
    filtered_nr = nr.filter(F(name__any=targets))
    if not filtered_nr.inventory.hosts:
        return {
            "error": f"No matching devices found. Requested: {targets}, Available: {all_hosts}",
        }

    results = filtered_nr.run(task=task_function, **kwargs)

    # Simplified result processing
    output = {}
    for hostname, multi_result in results.items():
        # Get the first result in the chain
        task_result = multi_result[0] if multi_result else None

        if task_result and task_result.exception:
            output[hostname] = {"success": False, "error": str(task_result.exception)}
        else:
            success = not multi_result.failed
            output[hostname] = {
                "success": success,
                "output": task_result.result if task_result else None,
                "error": str(task_result.exception)
                if task_result and task_result.exception
                else None,
            }

    return output
