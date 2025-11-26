"""Configuration network tools using Nornir."""

import json
from typing import Union

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_config
from pydantic import BaseModel, Field, field_validator

from utils.devices import execute_nornir_task


# --- PYDANTIC MODEL ---
class ConfigInput(BaseModel):
    """Input schema for configuration commands."""

    # Allow Union to pass API validation
    devices: Union[str, list[str]] = Field(
        description="List of device hostnames (e.g., ['sw1', 'sw2']) or a single device name.",
    )
    configs: Union[str, list[str]] = Field(
        description="List of configuration commands. Accepts a single command string too.",
    )

    # Validator 1: Ensure devices is always a list
    @field_validator("devices", mode="before")
    def parse_devices(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str):
            return [v]
        return v

    # Validator 2: Ensure configs is always a list (Handles user saying "vlan 10" as a string)
    @field_validator("configs", mode="before")
    def parse_configs(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str):
            return [v]
        return v


# --- TOOL DEFINITION ---
@tool(args_schema=ConfigInput)
def config_command(devices: list[str], configs: list[str]) -> str:
    """Apply configuration changes to one or more network devices."""
    if not configs:
        return json.dumps({"error": "No configuration commands provided."})

    # Sanitize input (strip newlines/spaces)
    clean_configs = []
    for cmd in configs:
        clean_configs.extend([c.strip() for c in cmd.split("\n") if c.strip()])

    results = execute_nornir_task(
        target_devices=devices,
        task_function=netmiko_send_config,
        config_commands=clean_configs,
    )

    if "error" in results and len(results) == 1:
        return json.dumps(results)

    return json.dumps({"devices": results}, indent=2)
