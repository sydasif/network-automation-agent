"""Configuration network tools using Nornir."""

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_config
from pydantic import Field

from tools.base import DeviceInput
from utils.devices import execute_nornir_task
from utils.responses import error, success, passthrough
from utils.validators import FlexibleList


class ConfigInput(DeviceInput):
    """Input schema for configuration commands."""

    configs: FlexibleList = Field(
        description="List of configuration commands.",
    )


@tool(args_schema=ConfigInput)
def config_command(devices: list[str], configs: list[str]) -> str:
    """Apply configuration changes to one or more network devices."""
    if not configs:
        return error("No configuration commands provided.")

    # Flatten and sanitize
    clean_configs = [c.strip() for cmd in configs for c in cmd.split("\n") if c.strip()]

    results = execute_nornir_task(
        target_devices=devices,
        task_function=netmiko_send_config,
        config_commands=clean_configs,
    )

    if "error" in results and len(results) == 1:
        return passthrough(results)

    return success(results)
