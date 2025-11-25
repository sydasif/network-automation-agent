"""Device management utilities for the Network AI Agent.

Handles inventory, connections, and the generic execution loop to keep tools DRY.
"""

import logging
import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Callable, Dict, Generator, List, Union

import yaml
from netmiko import BaseConnection, ConnectHandler

from settings import DEVICE_TIMEOUT, INVENTORY_FILE

logger = logging.getLogger(__name__)

# --- INVENTORY & CONNECTION ---


@lru_cache(maxsize=1)
def _load_inventory() -> Dict[str, dict]:
    """Loads YAML inventory with caching to reduce disk I/O."""
    if not INVENTORY_FILE.exists():
        return {}
    try:
        with open(INVENTORY_FILE, "r") as f:
            data = yaml.safe_load(f) or {}
            return {d["name"]: d for d in data.get("devices", [])}
    except Exception as e:
        logger.error(f"Inventory load error: {e}")
        return {}


def get_all_device_names() -> List[str]:
    """Returns a list of all valid device names."""
    return list(_load_inventory().keys())


@contextmanager
def get_device_connection(device_name: str) -> Generator[BaseConnection, None, None]:
    """Context manager for establishing a Netmiko connection."""
    inventory = _load_inventory()
    dev_conf = inventory.get(device_name)

    if not dev_conf:
        raise ValueError(f"Device '{device_name}' not found.")

    password = os.environ.get(dev_conf.get("password_env_var", ""))
    if not password:
        raise ValueError(f"Password env var missing for {device_name}")

    params = {
        "device_type": dev_conf["device_type"],
        "host": dev_conf["host"],
        "username": dev_conf["username"],
        "password": password,
        "timeout": DEVICE_TIMEOUT,
    }

    conn = None
    try:
        conn = ConnectHandler(**params)
        yield conn
    except Exception as e:
        logger.error(f"Connection error {device_name}: {e}")
        raise e
    finally:
        if conn:
            conn.disconnect()


# --- GENERIC EXECUTION HELPER ---


def run_action_on_devices(
    device_input: Union[str, List[str]], action_callback: Callable[[BaseConnection], Any]
) -> Dict[str, Any]:
    """
    Executes a callback function on a list of devices.

    Args:
        device_input: Single string or list of device names.
        action_callback: A function that takes a Netmiko connection and returns data.

    Returns:
        A dictionary with results or an error message.
    """
    # 1. Normalize Input
    targets = [device_input] if isinstance(device_input, str) else device_input

    # 2. Validate
    valid_devices = set(get_all_device_names())
    invalid = [d for d in targets if d not in valid_devices]
    if invalid:
        return {"error": f"Devices not found: {invalid}"}

    # 3. Execute Loop
    results = {}
    for dev in targets:
        try:
            with get_device_connection(dev) as conn:
                output = action_callback(conn)
                results[dev] = {"success": True, "output": output}
        except Exception as e:
            results[dev] = {"success": False, "error": str(e)}

    return results
