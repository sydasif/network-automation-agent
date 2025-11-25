"""Read-only network tools using Nornir."""

import json
from typing import Union

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_command

from utils.devices import execute_nornir_task


@tool
def show_command(device: Union[str, list[str]], command: str) -> str:
    """Execute a read-only 'show' command on one or more devices."""
    if not command or not command.strip():
        return json.dumps({"error": "Command cannot be empty."})

    # Execute using the Nornir wrapper
    # we pass use_textfsm=True to netmiko via Nornir
    results = execute_nornir_task(
        target_devices=device,
        task_function=netmiko_send_command,
        command_string=command,
        use_textfsm=True,
    )

    # Handle top-level validation errors
    if "error" in results and len(results) == 1:
        return json.dumps(results)

    return json.dumps({"command": command, "devices": results}, indent=2)
