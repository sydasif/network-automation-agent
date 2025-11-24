import json
import logging
from typing import List, Union

from langchain_core.tools import tool

from utils.devices import get_all_device_names, get_device_connection

logger = logging.getLogger(__name__)


@tool
def show_command(device: Union[str, list[str]], command: str) -> str:
    """Execute a read-only 'show' command on one or more devices."""
    if not command or not command.strip():
        return json.dumps({"error": "Command cannot be empty."})

    device_list = [device] if isinstance(device, str) else device

    all_devs = get_all_device_names()
    invalid = [d for d in device_list if d not in all_devs]
    if invalid:
        return json.dumps({"error": f"Devices not found: {invalid}"})

    results = {}

    # KISS: Sequential Loop
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
def config_command(device: str, configs: List[str]) -> str:
    """Apply configuration changes to a SINGLE network device."""
    if not configs:
        return json.dumps({"error": "No configuration commands provided."})

    try:
        with get_device_connection(device) as conn:
            output = conn.send_config_set(configs)
            conn.save_config()
            return json.dumps({"device": device, "status": "configured", "output": output})
    except Exception as e:
        logger.error(f"Config error on {device}: {e}")
        return json.dumps({"success": False, "error": str(e)})
