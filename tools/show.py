"""Read-only network tools using Nornir."""

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_command
from pydantic import BaseModel, Field

from utils.devices import execute_nornir_task
from utils.responses import error, process_nornir_result


class ShowInput(BaseModel):
    """Input schema for show commands."""

    devices: list[str] = Field(description="List of device hostnames (e.g., ['sw1', 'sw2']).")
    command: str = Field(description="The show command to execute (e.g., 'show ip int brief').")


@tool(args_schema=ShowInput)
def show_command(devices: list[str], command: str) -> str:
    """Execute a read-only 'show' command on one or more devices.

    Args:
        devices: List of device hostnames to target
        command: Show command to execute

    Returns:
        JSON string with device results
    """
    if not devices:
        return error("No devices specified.")
    if not command.strip():
        return error("Command cannot be empty.")

    results = execute_nornir_task(
        target_devices=devices,
        task_function=netmiko_send_command,
        command_string=command,
    )

    return process_nornir_result(results, command=command)
