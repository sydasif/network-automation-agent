"""Utility module for managing network device configurations.

This module provides functionality to load and access network device
configurations from a YAML file, making it easy to manage multiple
devices with different connection parameters.
"""

from pathlib import Path
from typing import Dict

import yaml

# Path to the device configuration file
CONFIG_PATH = Path("hosts.yaml")


def load_devices() -> dict[str, dict]:
    """Load network device configurations from hosts.yaml file.

    This function reads the hosts.yaml file and returns a dictionary
    of device configurations, with device names as keys and their
    configuration parameters as values.

    Returns:
        Dictionary mapping device names to their configuration parameters
        (host, username, password, device_type, etc.)

    Raises:
        FileNotFoundError: If the hosts.yaml configuration file is not found
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Device config not found: {CONFIG_PATH}")

    with open(CONFIG_PATH) as fh:
        cfg = yaml.safe_load(fh)

    devices = cfg.get("devices") or []
    return {d["name"]: d for d in devices}
