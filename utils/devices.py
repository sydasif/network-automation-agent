from pathlib import Path
from typing import Dict

import yaml

CONFIG_PATH = Path("hosts.yaml")


def load_devices() -> dict[str, dict]:
    """Load devices from hosts.yaml and return dict keyed by name."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Device config not found: {CONFIG_PATH}")

    with open(CONFIG_PATH) as fh:
        cfg = yaml.safe_load(fh)

    devices = cfg.get("devices") or []
    return {d["name"]: d for d in devices}
