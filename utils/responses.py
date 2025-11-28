"""JSON response helpers for tools."""

import json


def error(msg: str) -> str:
    """Return JSON error."""
    return json.dumps({"error": msg})


def success(devices: dict, **extra) -> str:
    """Return JSON success with devices + optional metadata."""
    return json.dumps({"devices": devices, **extra}, indent=2)


def passthrough(data: dict) -> str:
    """Return raw dict as JSON (for Nornir global errors)."""
    return json.dumps(data)
