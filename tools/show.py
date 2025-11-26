"""Read-only network tools using Nornir."""

import json

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_command
from pydantic import BaseModel, Field

from utils.devices import execute_nornir_task
from utils.validators import FlexibleList


class ShowInput(BaseModel):
    """Input schema for show commands."""

    # Using FlexibleList ensures that if the LLM lazily sends "sw1" (string),
    # it is automatically converted to ["sw1"] (list) before the function runs.
    devices: FlexibleList = Field(
        description="List of device hostnames (e.g., ['sw1', 'sw2']).",
    )
    command: str = Field(description="The show command to execute (e.g., 'show ip int brief').")


@tool(args_schema=ShowInput)
def show_command(devices: list[str], command: str) -> str:
    """Execute a read-only 'show' command on one or more devices."""
    # 1. Validation
    if not command.strip():
        return json.dumps({"error": "Command cannot be empty."})

    # 2. Execution (KISS: No manual looping, let Nornir handle it)
    results = execute_nornir_task(
        target_devices=devices,
        task_function=netmiko_send_command,
        command_string=command,
        use_textfsm=True,  # Automatically parses output if template exists
    )

    # 3. Error Handling for global failures (e.g., device not found)
    if "error" in results and len(results) == 1:
        return json.dumps(results)

    # 4. Return structured JSON
    return json.dumps({"command": command, "devices": results}, indent=2)
