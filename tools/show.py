"""Read-only network tools using Nornir."""

import json
from typing import List, Union

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_command
from pydantic import BaseModel, Field, field_validator

from utils.devices import execute_nornir_task


# --- PYDANTIC MODEL ---
class ShowInput(BaseModel):
    """Input schema for show commands."""

    # We allow Union[str, List] here so the LLM API doesn't throw a validation error
    # if the model outputs a single string.
    devices: Union[str, List[str]] = Field(
        description="List of device hostnames (e.g., ['sw1', 'sw2']) or a single device name."
    )
    command: str = Field(description="The show command to execute (e.g., 'show ip int brief').")

    # This validator ensures the Python code ALWAYS receives a List,
    # even if the LLM sent a string.
    @field_validator("devices", mode="before")
    def parse_devices(cls, v):
        if isinstance(v, str):
            return [v]  # Wrap single string in a list
        return v


# --- TOOL DEFINITION ---
@tool(args_schema=ShowInput)
def show_command(devices: List[str], command: str) -> str:
    """Execute a read-only 'show' command on one or more devices."""

    if not command or not command.strip():
        return json.dumps({"error": "Command cannot be empty."})

    # 'devices' is guaranteed to be a List[str] here because of the validator above
    results = execute_nornir_task(
        target_devices=devices,
        task_function=netmiko_send_command,
        command_string=command,
        use_textfsm=True,
    )

    if "error" in results and len(results) == 1:
        return json.dumps(results)

    return json.dumps({"command": command, "devices": results}, indent=2)
