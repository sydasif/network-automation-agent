"""Configuration network tools using Nornir."""

import json  # 🆕 ADD THIS

from langchain_core.tools import tool
from nornir_netmiko.tasks import netmiko_save_config, netmiko_send_config  # 🆕 ADD save_config
from pydantic import Field

from tools.base import DeviceInput
from utils.devices import execute_nornir_task
from utils.responses import error, passthrough  # 🆕 REMOVE 'success' for now
from utils.validators import FlexibleList, is_safe_config_command  # 🆕 ADD validation


class ConfigInput(DeviceInput):
    """Input schema for configuration commands."""

    configs: FlexibleList = Field(
        description="List of configuration commands.",
    )


@tool(args_schema=ConfigInput)
def config_command(devices: list[str], configs: list[str]) -> str:
    """Apply configuration changes with automatic save."""

    # 1. Validation
    if not configs:
        return error("No configuration commands provided.")

    # 2. Sanitization
    clean_configs = [c.strip() for cmd in configs for c in cmd.split("\n") if c.strip()]

    # 🆕 ADD SAFETY CHECK
    is_valid, error_msg = is_safe_config_command(clean_configs)
    if not is_valid:
        return error(f"Unsafe config rejected: {error_msg}")

    # 3. Apply Configuration
    results = execute_nornir_task(
        target_devices=devices,
        task_function=netmiko_send_config,
        config_commands=clean_configs,
    )

    # 4. Global error check
    if "error" in results and len(results) == 1:
        return passthrough(results)

    # 🆕 ADD AUTO-SAVE LOGIC
    # 5. Identify successful devices
    successful_devices = [
        hostname for hostname, result in results.items()
        if result["success"]
    ]
    failed_devices = [
        hostname for hostname, result in results.items()
        if not result["success"]
    ]

    # 6. Auto-save on successful devices
    if successful_devices:
        save_results = execute_nornir_task(
            target_devices=successful_devices,
            task_function=netmiko_save_config,
        )

        # Update results with save status
        for hostname, save_result in save_results.items():
            if hostname in results:
                results[hostname]["config_saved"] = save_result["success"]
                if not save_result["success"]:
                    results[hostname]["save_error"] = save_result.get("error")

    # 7. Return with summary
    response = {
        "devices": results,
        "summary": {
            "total": len(devices),
            "succeeded": len(successful_devices),
            "failed": len(failed_devices),
        }
    }

    if failed_devices:
        response["warning"] = f"Failed on {len(failed_devices)} device(s): {', '.join(failed_devices)}"

    return json.dumps(response, indent=2)
