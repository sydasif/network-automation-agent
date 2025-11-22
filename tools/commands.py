"""Network command execution tool for the network automation agent.

This module provides a LangChain tool for executing commands on network devices
using Netmiko. It supports both single and multiple device execution with
parallel processing capabilities.

The tool uses SSH to connect to network devices, executes commands, and returns
results in JSON format. It leverages textfsm parsing when possible to return
structured data, falling back to raw output when needed.

Features:
- Parallel execution for multiple devices
- Structured/raw output detection
- Comprehensive error handling
- Connection validation
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
from utils.devices import get_all_device_names


# Set up logging for the run_command tool
logger = logging.getLogger(__name__)


@tool
def run_command(device: Union[str, list[str]], command: str) -> str:
    """Execute a command on one or more network devices.

    Connects to specified network device(s) using SSH and executes the given
    command. The tool supports both single device and multiple device execution
    with parallel processing. Results are returned in JSON format with detailed
    success/failure information and output type classification.

    The tool leverages Netmiko's textfsm parsing capabilities to return
    structured data when possible. If textfsm parsing fails or templates are
    not available, the tool falls back to returning raw command output.

    Args:
        device: A single device name as a string or a list of device names
        command: The command to execute on the specified device(s)

    Returns:
        JSON string containing the command execution results for each device,
        including success status, output type (structured/raw), and the output data.
        The return format includes:
        - command: The command executed
        - summary: Statistics about execution success/failure
        - devices: Detailed results for each device

    Raises:
        Connection errors are handled internally and returned as part of the JSON response.
    """

    if not command or not command.strip():
        error_msg = "Input validation error: The 'command' argument cannot be empty."
        logger.error(error_msg)

    with get_db() as db:
        all_device_names = get_all_device_names(db)
        device_list = [device] if isinstance(device, str) else device
        invalid_devices = [dev for dev in device_list if dev not in all_device_names]
        if invalid_devices:
            logger.warning(f"Device(s) not found: {', '.join(invalid_devices)}")
            return json.dumps(
                {
                    "error": f"Device(s) not found: {', '.join(invalid_devices)}",
                    "available_devices": all_device_names,
                }
            )

        # Pre-fetch all device configurations to avoid multiple database queries
        devices_to_run = db.query(Device).filter(Device.name.in_(device_list)).all()
        device_configs = {dev.name: dev for dev in devices_to_run}

    results = {}

    def execute_on_device(cfg: Device) -> tuple[str, dict[str, Any]]:
        """Helper function to execute a command on a single device.

        Establishes an SSH connection to the provided device configuration,
        executes the command, and handles connection errors gracefully.
        The function manages the connection lifecycle and result formatting.

        Args:
            cfg: The device configuration object containing connection parameters

        Returns:
            Tuple of device name and execution result dictionary
        """
        dev_name = cfg.name
        try:
            # Retrieve password from environment variable using the configured variable name
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

            # Establish SSH connection to the device with a 30-second timeout
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

            # Properly close the SSH connection
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

    # Limit concurrent connections to 10 or number of devices, whichever is smaller
    max_workers = min(len(device_list), 10)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all device execution tasks to the thread pool
        future_to_device = {
            executor.submit(execute_on_device, device_configs[dev_name]): dev_name
            for dev_name in device_list
        }

        # Collect results as they complete
        for future in as_completed(future_to_device):
            dev, out = future.result()
            results[dev] = out

    # Calculate execution summary statistics
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

    # Return results in a standardized JSON format
    return json.dumps(
        {
            "command": command,
            "summary": summary,  # Add the summary to the output
            "devices": results,
        },
        indent=2,
    )
