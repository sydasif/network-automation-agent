# utils/devices.py
import logging
import os
from contextlib import contextmanager
from typing import Dict, Generator, List

import yaml
from cachetools import TTLCache, cached
from netmiko import BaseConnection, ConnectHandler

from settings import CACHE_TTL, DEVICE_TIMEOUT, INVENTORY_FILE

_inventory_cache = TTLCache(maxsize=1, ttl=CACHE_TTL)


@cached(_inventory_cache)
def _load_inventory() -> Dict[str, dict]:
    """Loads and caches the YAML inventory."""
    if not INVENTORY_FILE.exists():
        return {}

    with open(INVENTORY_FILE, "r") as f:
        data = yaml.safe_load(f) or {}

    # Convert list to dict for faster lookups: {'sw1': {...}, 'sw2': {...}}
    return {d["name"]: d for d in data.get("devices", [])}


def get_all_device_names() -> List[str]:
    """Returns just the list of names."""
    return list(_load_inventory().keys())


@contextmanager
def get_device_connection(device_name: str) -> Generator[BaseConnection, None, None]:
    conn = None
    try:
        inventory = _load_inventory()
        dev_conf = inventory.get(device_name)

        if not dev_conf:
            raise ValueError(f"Device {device_name} not found in {INVENTORY_FILE}")

        password = os.environ.get(dev_conf["password_env_var"])
        if not password:
            raise ValueError(f"Password env var not set for {device_name}")

        params = {
            "device_type": dev_conf["device_type"],
            "host": dev_conf["host"],
            "username": dev_conf["username"],
            "password": password,
            "timeout": DEVICE_TIMEOUT,
        }

        conn = ConnectHandler(**params)
        yield conn

    except Exception as e:
        logging.getLogger(__name__).error(f"Connection error on {device_name}: {e}")
        raise e
    finally:
        if conn:
            conn.disconnect()
