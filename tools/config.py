"""Configuration network tools using Nornir."""

import json
from typing import List, Union

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_config

from utils.devices import execute_nornir_task


@tool
def config_command(device: Union[str, list[str]], configs: List[str]) -> str:
    """Apply configuration changes to one or more network devices."""
    if not configs:
        return json.dumps({"error": "No configuration commands provided."})

    # Sanitize input
    clean_configs = []
    for cmd in configs:
        clean_configs.extend([c.strip() for c in cmd.split("\n") if c.strip()])

    # Execute using the Nornir wrapper
    results = execute_nornir_task(
        target_devices=device, task_function=netmiko_send_config, config_commands=clean_configs
    )

    if "error" in results and len(results) == 1:
        return json.dumps(results)

    return json.dumps({"devices": results}, indent=2)
