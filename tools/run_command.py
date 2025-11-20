"""Network command execution tool for the network automation agent.

This module provides a tool for executing commands on network devices
using Netmiko. It supports both single and multiple device execution
with parallel processing capabilities.
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Union

from langchain_core.tools import tool
from netmiko import ConnectHandler

from utils.devices import load_devices


@tool
def run_command(device: str | list[str], command: str) -> str:
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
    all_devices = load_devices()

    if isinstance(device, str):
        device_list = [device]
    else:
        device_list = device

    for dev in device_list:
        if dev not in all_devices:
            return json.dumps({
                "error": f"Device '{dev}' not found",
                "available_devices": list(all_devices.keys()),
            })

    results = {}

    def execute_on_device(dev_name: str):
        """Helper function to execute a command on a single device.

        Args:
            dev_name: Name of the device to execute the command on

        Returns:
            Tuple of device name and execution result
        """
        cfg = all_devices[dev_name]
        try:
            # Establish SSH connection to the device
            conn = ConnectHandler(
                device_type=cfg["device_type"],
                host=cfg["host"],
                username=cfg["username"],
                password=cfg["password"],
                timeout=30,
            )

            try:
                # Attempt to execute command with textfsm parsing for structured output
                out = conn.send_command(command, use_textfsm=True)
                if isinstance(out, str):
                    # If output is a string, it means textfsm parsing failed or wasn't applicable
                    parsed_type = "raw"
                    parsed_output = out
                else:
                    # If output is not a string (typically a list of dicts), textfsm parsing worked
                    parsed_type = "structured"
                    parsed_output = out
            except Exception:
                # If textfsm parsing fails, execute command without parsing
                out = conn.send_command(command)
                parsed_type = "raw"
                parsed_output = out

            # Close the SSH connection
            conn.disconnect()

            return dev_name, {
                "success": True,
                "type": parsed_type,  # Indicates whether output is structured or raw
                "data": parsed_output,
            }

        except Exception as e:
            # Return error information if connection or command execution fails
            return dev_name, {"success": False, "error": str(e)}

    # Execute commands in parallel across multiple devices using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as ex:
        # Submit tasks for each device to the thread pool
        futures = {ex.submit(execute_on_device, d): d for d in device_list}
        # Process completed tasks as they finish
        for fut in as_completed(futures):
            dev, out = fut.result()
            results[dev] = out

    return json.dumps({"command": command, "devices": results}, indent=2)
