"""Read-only network tools using Nornir."""

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_command
from pydantic import Field

from tools.base import DeviceInput
from utils.devices import execute_nornir_task
from utils.responses import error, success, passthrough
from utils.validators import is_safe_show_command  # 🆕 ADD THIS


class ShowInput(DeviceInput):
    """Input schema for show commands."""

    command: str = Field(description="The show command to execute (e.g., 'show ip int brief').")


@tool(args_schema=ShowInput)
def show_command(devices: list[str], command: str) -> str:
    """Execute a read-only 'show' command on one or more devices."""

    # 1. Validation
    if not command.strip():
        return error("Command cannot be empty.")

    # 🆕 ADD SAFETY CHECK
    is_valid, error_msg = is_safe_show_command(command)
    if not is_valid:
        return error(f"Unsafe command rejected: {error_msg}")

    # 2. Execution (KISS: No manual looping, let Nornir handle it)
    results = execute_nornir_task(
        target_devices=devices,
        task_function=netmiko_send_command,
        command_string=command,
        use_textfsm=True,  # Automatically parses output if template exists
    )

    # 3. Error Handling for global failures (e.g., device not found)
    if "error" in results and len(results) == 1:
        return passthrough(results)

    # 4. Return structured JSON
    return success(results, command=command)
