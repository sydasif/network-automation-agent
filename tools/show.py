"""Read-only network tools using Nornir."""

import json
from typing import List, Union

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_command

from utils.devices import execute_nornir_task


@tool
def show_command(devices: Union[str, List[str]], command: str) -> str:
    """Execute a read-only 'show' command on one or more devices.

    Args:
        devices: The target device(s). Can be a single hostname (str) or list of hostnames.
        command: The show command to execute (e.g., 'show ip int brief').
    """
    if not command or not command.strip():
        return json.dumps({"error": "Command cannot be empty."})

    # Normalize 'devices' to a list
    if not devices:
        return json.dumps({"error": "No devices specified."})

    if isinstance(devices, str):
        target_list = [devices]
    else:
        target_list = devices

    # Execute using the Nornir wrapper
    results = execute_nornir_task(
        target_devices=target_list,
        task_function=netmiko_send_command,
        command_string=command,
        use_textfsm=True,
    )

    # Handle top-level validation errors
    if "error" in results and len(results) == 1:
        return json.dumps(results)

    return json.dumps({"command": command, "devices": results}, indent=2)
