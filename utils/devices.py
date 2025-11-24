import logging
import os
from contextlib import contextmanager
from typing import Generator, List

from cachetools import TTLCache, cached
from netmiko import BaseConnection, ConnectHandler

from .database import Device, get_db

# Cache device names for 5 minutes
_device_names_cache = TTLCache(maxsize=1, ttl=300)


@cached(_device_names_cache)
def get_all_device_names() -> List[str]:
    """
    Retrieves all device names.
    Self-contained: Manages its own DB session so caching works correctly.
    """
    with get_db() as db:
        device_names = [device.name for device in db.query(Device.name).all()]
        return device_names


def clear_device_cache():
    _device_names_cache.clear()
    print("Device cache cleared.")


@contextmanager
def get_device_connection(device_name: str) -> Generator[BaseConnection, None, None]:
    conn = None
    try:
        with get_db() as db:
            dev_conf = db.query(Device).filter(Device.name == device_name).first()
            if not dev_conf:
                raise ValueError(f"Device {device_name} not found.")

            password = os.environ.get(dev_conf.password_env_var)
            if not password:
                raise ValueError(f"Password env var not set for {device_name}")

            params = {
                "device_type": dev_conf.device_type,
                "host": dev_conf.host,
                "username": dev_conf.username,
                "password": password,
                "timeout": 30,
            }

        conn = ConnectHandler(**params)
        yield conn

    except Exception as e:
        logging.getLogger(__name__).error(f"Connection error on {device_name}: {e}")
        raise e
    finally:
        if conn:
            conn.disconnect()
