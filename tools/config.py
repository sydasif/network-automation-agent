"""Configuration network tools."""

import json
from typing import List, Union

from langchain_core.tools import tool
from netmiko import BaseConnection

from utils.devices import run_action_on_devices


@tool
def config_command(device: Union[str, list[str]], configs: List[str]) -> str:
    """Apply configuration changes to one or more network devices."""
    if not configs:
        return json.dumps({"error": "No configuration commands provided."})

    # Sanitize input: Logic specific to CONFIGURATION, not general connection
    clean_configs = []
    for cmd in configs:
        clean_configs.extend([c.strip() for c in cmd.split("\n") if c.strip()])

    # Define the specific logic for this tool
    def _action(conn: BaseConnection):
        output = conn.send_config_set(clean_configs)
        conn.save_config()
        return output

    # Offload the execution to the utility
    results = run_action_on_devices(device, _action)

    # Handle top-level validation errors
    if "error" in results and len(results) == 1:
        return json.dumps(results)

    return json.dumps({"devices": results}, indent=2)
