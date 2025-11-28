"""Configuration network tools using Nornir."""

import json

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_config
from pydantic import BaseModel, Field

from utils.devices import execute_nornir_task
from utils.validators import FlexibleList


class ConfigInput(BaseModel):
    """Input schema for configuration commands."""

    devices: FlexibleList = Field(
        description="List of device hostnames (e.g., ['sw1', 'sw2']).",
    )
    configs: FlexibleList = Field(
        description="List of configuration commands.",
    )


@tool(args_schema=ConfigInput)
def config_command(devices: list[str], configs: list[str]) -> str:
    """Apply configuration changes to one or more network devices."""
    if not configs:
        return json.dumps({"error": "No configuration commands provided."})

    # Flatten and sanitize
    clean_configs = [c.strip() for cmd in configs for c in cmd.split("\n") if c.strip()]

    results = execute_nornir_task(
        target_devices=devices,
        task_function=netmiko_send_config,
        config_commands=clean_configs,
    )

    if "error" in results and len(results) == 1:
        return json.dumps(results)

    return json.dumps({"devices": results}, indent=2)
