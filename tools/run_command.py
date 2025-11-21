"""Network command execution tool for the network automation agent.

This module provides a tool for executing commands on network devices
using Netmiko. It supports both single and multiple device execution
with parallel processing capabilities.
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Union

from langchain_core.tools import tool
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

from utils.database import Device, get_db
from utils.devices import get_device_by_name, get_all_device_names


# Set up logging for the run_command tool
logger = logging.getLogger(__name__)


@tool
def run_command(device: Union[str, list[str]], command: str) -> str:
    """Execute a command on one or more network devices.

    This tool connects to the specified network device(s) using SSH and
    executes the given command. It handles both structured (parsed with
    textfsm) and raw command outputs, returning the results in JSON format.

    Args:
        device: A single device name as a string or a list of device names
        command: The command to execute on the specified device(s)

    Returns:
        JSON string containing the command execution results for each device,
        including success status, output type (structured/raw), and the output data.

    Raises:
        Connection errors if unable to connect to specified devices
    """
    # --- SOLUTION: Add immediate validation for the command argument ---
    if not command or not command.strip():
        error_msg = "Input validation error: The 'command' argument cannot be empty."
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
    # --- End of Solution ---

    with get_db() as db:
        all_device_names = get_all_device_names(db)
        device_list = [device] if isinstance(device, str) else device
        invalid_devices = [dev for dev in device_list if dev not in all_device_names]
        if invalid_devices:
            logger.warning(f"Device(s) not found: {', '.join(invalid_devices)}")
            return json.dumps({
                "error": f"Device(s) not found: {', '.join(invalid_devices)}",
                "available_devices": all_device_names,
            })

        # Pre-fetch all device configurations
        devices_to_run = db.query(Device).filter(Device.name.in_(device_list)).all()
        device_configs = {dev.name: dev for dev in devices_to_run}

    results = {}

    def execute_on_device(cfg: Device) -> tuple[str, dict[str, Any]]:
        """Helper function to execute a command on a single device.

        Args:
            cfg: The device configuration object

        Returns:
            Tuple of device name and execution result
        """
        dev_name = cfg.name
        try:
            # --- SOLUTION: Explicitly validate password before attempting connection ---
            password = os.environ.get(cfg.password_env_var)
            if not password:
                # This check handles both None (not set) and empty string.
                error_msg = (
                    f"Configuration error: The password environment variable "
                    f"'{cfg.password_env_var}' for device '{dev_name}' is not set or is empty."
                )
                logger.error(error_msg)
                # Return a structured failure immediately.
                return dev_name, {"success": False, "error": error_msg}
            # --- End of Solution ---

            # Establish SSH connection to the device
            conn = ConnectHandler(
                device_type=cfg.device_type,
                host=cfg.host,
                username=cfg.username,
                password=password,
                timeout=30,
            )

            # Execute command with textfsm parsing - netmiko handles fallback
            # automatically. If no textfsm template is available or parsing
            # fails, netmiko returns raw output
            out = conn.send_command(command, use_textfsm=True)
            if isinstance(out, str):
                parsed_type = "raw"
                parsed_output = out
            else:
                parsed_type = "structured"
                parsed_output = out

            conn.disconnect()

            return dev_name, {
                "success": True,
                "type": parsed_type,
                "data": parsed_output,
            }

        except NetmikoAuthenticationException as e:
            error_msg = f"Authentication failed for device {dev_name}: {str(e)}"
            logger.error(error_msg)
            return dev_name, {"success": False, "error": error_msg}
        except NetmikoTimeoutException as e:
            error_msg = f"Connection timeout for device {dev_name}: {str(e)}"
            logger.error(error_msg)
            return dev_name, {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Connection error for device {dev_name}: {str(e)}"
            logger.error(error_msg)
            return dev_name, {"success": False, "error": error_msg}

    max_workers = min(len(device_list), 10)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_device = {
            executor.submit(execute_on_device, device_configs[dev_name]): dev_name
            for dev_name in device_list
        }

        for future in as_completed(future_to_device):
            dev, out = future.result()
            results[dev] = out

    # --- SOLUTION: Add a summary of execution results ---
    successful_count = 0
    failed_count = 0
    for device_name, result in results.items():
        if result.get("success"):
            successful_count += 1
        else:
            failed_count += 1

    summary = {
        "total_devices": len(results),
        "successful": successful_count,
        "failed": failed_count,
    }
    # --- End of Solution ---

    return json.dumps(
        {
            "command": command,
            "summary": summary, # Add the summary to the output
            "devices": results,
        },
        indent=2,
    )
