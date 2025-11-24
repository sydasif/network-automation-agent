import json
import logging
from typing import List, Union

from langchain_core.tools import tool

from utils.devices import get_all_device_names, get_device_connection

logger = logging.getLogger(__name__)


def _validate_devices(device_input: Union[str, list[str]]) -> tuple[list[str], str | None]:
    """Helper to normalize input to a list and validate device names."""
    device_list = [device_input] if isinstance(device_input, str) else device_input
    all_devs = get_all_device_names()

    invalid = [d for d in device_list if d not in all_devs]
    if invalid:
        return [], json.dumps({"error": f"Devices not found: {invalid}"})

    return device_list, None


@tool
def show_command(device: Union[str, list[str]], command: str) -> str:
    """Execute a read-only 'show' command on one or more devices."""
    if not command or not command.strip():
        return json.dumps({"error": "Command cannot be empty."})

    device_list, error = _validate_devices(device)
    if error:
        return error

    results = {}

    for dev_name in device_list:
        try:
            with get_device_connection(dev_name) as conn:
                output = conn.send_command(command, use_textfsm=True)
                results[dev_name] = {"success": True, "data": output}
        except Exception as e:
            logger.error(f"Error on {dev_name}: {e}")
            results[dev_name] = {"success": False, "error": str(e)}

    return json.dumps({"command": command, "devices": results}, indent=2)


@tool
def config_command(device: Union[str, list[str]], configs: List[str]) -> str:
    """Apply configuration changes to one or more network devices."""
    if not configs:
        return json.dumps({"error": "No configuration commands provided."})

    # FIX: Sanitize input to handle cases where LLM sends newlines in list items
    clean_configs = []
    for cmd in configs:
        # Split by newline if present, strip whitespace, and ignore empty strings
        clean_configs.extend([c.strip() for c in cmd.split("\n") if c.strip()])

    device_list, error = _validate_devices(device)
    if error:
        return error

    results = {}

    for dev_name in device_list:
        try:
            with get_device_connection(dev_name) as conn:
                # Use clean_configs instead of raw configs
                output = conn.send_config_set(clean_configs)
                conn.save_config()
                results[dev_name] = {"success": True, "output": output}
        except Exception as e:
            logger.error(f"Config error on {dev_name}: {e}")
            results[dev_name] = {"success": False, "error": str(e)}

    return json.dumps({"devices": results}, indent=2)
