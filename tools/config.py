"""Configuration network tools using Nornir."""

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_send_config
from pydantic import BaseModel, Field

from utils.devices import execute_nornir_task
from utils.responses import error, passthrough, success


class ConfigInput(BaseModel):
    """Input schema for configuration commands."""

    devices: list[str] = Field(description="List of device hostnames (e.g., ['sw1', 'sw2']).")
    configs: list[str] = Field(
        description="List of configuration commands.",
    )


@tool(args_schema=ConfigInput)
def config_command(devices: list[str], configs: list[str]) -> str:
    """Apply configuration changes to network devices.

    Note: Changes are applied to running-config only.
    Use a separate save command if you want to persist changes to startup-config.
    """

    # 1. Validation & Sanitization
    if not devices:
        return error("No devices specified.")

    clean_configs = [c.strip() for cmd in configs for c in cmd.split("\n") if c.strip()]
    if not clean_configs:
        return error("No configuration commands provided.")

    # 2. Apply Configuration
    results = execute_nornir_task(
        target_devices=devices,
        task_function=netmiko_send_config,
        config_commands=clean_configs,
    )

    # 4. Global error check
    if "error" in results and len(results) == 1:
        return passthrough(results)

    # 5. Return structured JSON with applied configs
    return success(results, configs=clean_configs)
