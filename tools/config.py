"""Configuration network tools using Nornir."""

import json
from typing import List, Union

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_config

from utils.devices import execute_nornir_task


@tool
def config_command(devices: Union[str, List[str]], configs: List[str]) -> str:
    """Apply configuration changes to one or more network devices.

    Args:
        devices: The target device(s). Can be a single hostname (str) or list of hostnames.
        configs: A list of configuration commands to execute.
    """
    if not configs:
        return json.dumps({"error": "No configuration commands provided."})

    # Normalize 'devices' to a list
    if not devices:
        return json.dumps({"error": "No devices specified."})

    if isinstance(devices, str):
        target_list = [devices]
    else:
        target_list = devices

    # Sanitize input
    clean_configs = []
    for cmd in configs:
        clean_configs.extend([c.strip() for c in cmd.split("\n") if c.strip()])

    # Execute using the Nornir wrapper
    results = execute_nornir_task(
        target_devices=target_list,
        task_function=netmiko_send_config,
        config_commands=clean_configs,
    )

    if "error" in results and len(results) == 1:
        return json.dumps(results)

    return json.dumps({"devices": results}, indent=2)
