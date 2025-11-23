"""Network command execution tools.

Contains tools for:
1. show_command: Read-only operations (Parallel execution supported).
2. config_command: Configuration changes (Single device, requires approval).
"""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Union, List

from langchain_core.tools import tool
from netmiko import ConnectHandler

from utils.database import Device, get_db
from utils.devices import get_all_device_names

logger = logging.getLogger(__name__)


def _get_connection_params(device_name: str) -> dict:
    """Helper: Retrieves connection parameters from DB (DRY)."""
    with get_db() as db:
        dev_conf = db.query(Device).filter(Device.name == device_name).first()
        if not dev_conf:
            raise ValueError(f"Device {device_name} not found.")

        password = os.environ.get(dev_conf.password_env_var)
        if not password:
            raise ValueError(f"Password env var not set for {device_name}")

        return {
            "device_type": dev_conf.device_type,
            "host": dev_conf.host,
            "username": dev_conf.username,
            "password": password,
            "timeout": 30,
        }


@tool
def show_command(device: Union[str, list[str]], command: str) -> str:
    """Execute a read-only 'show' command on one or more devices.

    Use this for: show version, show interfaces, show run, etc.
    """
    if not command or not command.strip():
        return json.dumps({"error": "Command cannot be empty."})

    # Normalize to list
    device_list = [device] if isinstance(device, str) else device

    # Validate devices
    with get_db() as db:
        all_devs = get_all_device_names(db)
        invalid = [d for d in device_list if d not in all_devs]
        if invalid:
            return json.dumps({"error": f"Devices not found: {invalid}"})

    results = {}

    def _exec(dev_name: str):
        try:
            params = _get_connection_params(dev_name)
            with ConnectHandler(**params) as conn:
                # Netmiko auto-detects textfsm
                output = conn.send_command(command, use_textfsm=True)
                return dev_name, {"success": True, "data": output}
        except Exception as e:
            logger.error(f"Error on {dev_name}: {e}")
            return dev_name, {"success": False, "error": str(e)}

    # Parallel Execution
    max_workers = min(len(device_list), 10)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_exec, dev): dev for dev in device_list}
        for future in as_completed(futures):
            dev, res = future.result()
            results[dev] = res

    return json.dumps({"command": command, "devices": results}, indent=2)


@tool
def config_command(device: str, configs: List[str]) -> str:
    """Apply configuration changes to a SINGLE network device.

    Use this for: interface changes, ip addressing, routing protocol config.
    WARNING: This tool requires human approval before execution.
    """
    if not configs:
        return json.dumps({"error": "No configuration commands provided."})

    try:
        params = _get_connection_params(device)
        with ConnectHandler(**params) as conn:
            # send_config_set handles 'conf t' and 'end'
            output = conn.send_config_set(configs)
            conn.save_config()
            return json.dumps({"device": device, "status": "configured", "output": output})
    except Exception as e:
        logger.error(f"Config error on {device}: {e}")
        return json.dumps({"success": False, "error": str(e)})
