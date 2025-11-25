"""Read-only network tools."""

import json
from typing import Union

from langchain_core.tools import tool
from netmiko import BaseConnection

from utils.devices import run_action_on_devices


@tool
def show_command(device: Union[str, list[str]], command: str) -> str:
    """Execute a read-only 'show' command on one or more devices."""
    if not command or not command.strip():
        return json.dumps({"error": "Command cannot be empty."})

    # Define the specific logic for this tool
    def _action(conn: BaseConnection):
        # use_textfsm=True allows structured output if templates exist
        return conn.send_command(command, use_textfsm=True)

    # Offload the execution to the utility
    results = run_action_on_devices(device, _action)

    # Handle top-level validation errors from the utility
    if "error" in results and len(results) == 1:
        return json.dumps(results)

    return json.dumps({"command": command, "devices": results}, indent=2)
