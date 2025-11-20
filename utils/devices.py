"""Utility module for managing network device configurations.

This module provides functionality to load and access network device
configurations from a YAML file, making it easy to manage multiple
devices with different connection parameters.
"""

from pathlib import Path
from typing import Dict, TypedDict

import yaml

# Path to the device configuration file
CONFIG_PATH = Path("hosts.yaml")


# Device configuration structure
class DeviceConfig(TypedDict):
    """Type definition for device configuration."""

    name: str
    host: str
    username: str
    password: str
    device_type: str


# Cache for loaded device configurations to avoid repeated file I/O
_DEVICES_CACHE: dict[str, DeviceConfig] | None = None
_LAST_MOD_TIME: float | None = None


def load_devices() -> dict[str, DeviceConfig]:
    """Load network device configurations from hosts.yaml file.

    This function reads the hosts.yaml file and returns a dictionary
    of device configurations, with device names as keys and their
    configuration parameters as values. Implements caching to avoid
    repeated file reads on subsequent calls.

    Returns:
        Dictionary mapping device names to their configuration parameters
        (host, username, password, device_type, etc.)

    Raises:
        FileNotFoundError: If the hosts.yaml configuration file is not found
    """
    global _DEVICES_CACHE, _LAST_MOD_TIME

    # Check if file has been modified since last read
    if CONFIG_PATH.exists():
        current_mod_time = CONFIG_PATH.stat().st_mtime
        if _DEVICES_CACHE is not None and current_mod_time == _LAST_MOD_TIME:
            # Return cached devices if file hasn't changed
            return _DEVICES_CACHE

    # Load devices from file and cache them
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Device config not found: {CONFIG_PATH}")

    with open(CONFIG_PATH) as fh:
        cfg = yaml.safe_load(fh)

    devices = cfg.get("devices") or []
    device_dict: dict[str, DeviceConfig] = {d["name"]: d for d in devices}  # type: ignore

    # Update cache
    _DEVICES_CACHE = device_dict
    _LAST_MOD_TIME = current_mod_time

    return device_dict
