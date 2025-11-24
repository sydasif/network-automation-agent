"""Device management utilities for the Network AI Agent.

This module handles device inventory loading and connection management
for network devices using Netmiko.
"""

import logging
import os
from contextlib import contextmanager
from typing import Dict, Generator, List

import yaml
from netmiko import BaseConnection, ConnectHandler

from settings import DEVICE_TIMEOUT, INVENTORY_FILE


def _load_inventory() -> Dict[str, dict]:
    """Loads the YAML inventory from the hosts.yaml file.

    Returns:
        A dictionary mapping device names to their configuration dictionaries.
        Returns an empty dictionary if the inventory file doesn't exist.
    """
    if not INVENTORY_FILE.exists():
        return {}

    with open(INVENTORY_FILE, "r") as f:
        data = yaml.safe_load(f) or {}

    return {d["name"]: d for d in data.get("devices", [])}


def get_all_device_names() -> List[str]:
    """Retrieves a list of all device names from the inventory.

    Returns:
        A list of strings containing all device names in the inventory.
    """
    return list(_load_inventory().keys())


@contextmanager
def get_device_connection(device_name: str) -> Generator[BaseConnection, None, None]:
    """Context manager to establish and manage a connection to a network device.

    Args:
        device_name: The name of the device to connect to, as defined in the inventory.

    Yields:
        A Netmiko BaseConnection object for the connected device.

    Raises:
        ValueError: If the device is not found in the inventory or if the
            password environment variable is not set.
        Exception: If there's an error connecting to the device.
    """
    conn = None
    try:
        inventory = _load_inventory()
        # Get device configuration from inventory
        dev_conf = inventory.get(device_name)

        if not dev_conf:
            raise ValueError(f"Device {device_name} not found.")

        # Retrieve password from environment variable specified in inventory
        password = os.environ.get(dev_conf["password_env_var"])
        if not password:
            raise ValueError(f"Password env var not set for {device_name}")

        # Prepare connection parameters
        params = {
            "device_type": dev_conf["device_type"],
            "host": dev_conf["host"],
            "username": dev_conf["username"],
            "password": password,
            "timeout": DEVICE_TIMEOUT,
        }

        # Establish the connection to the device
        conn = ConnectHandler(**params)
        yield conn

    except Exception as e:
        logging.getLogger(__name__).error(f"Connection error on {device_name}: {e}")
        raise e
    finally:
        # Ensure connection is properly closed even if an exception occurs
        if conn:
            conn.disconnect()

