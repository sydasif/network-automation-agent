"""JSON response helpers for tools."""

import json


def error(msg: str) -> str:
    """Return standardized error response.

    Args:
        msg: Error message

    Returns:
        JSON string with error key
    """
    return json.dumps({"error": msg})


def success(devices: dict, **extra) -> str:
    """Return standardized success response.

    Args:
        devices: Dict mapping hostnames to results
        **extra: Additional metadata (command, configs, etc.)

    Returns:
        JSON string with devices and metadata
    """
    return json.dumps({"devices": devices, **extra}, indent=2)


def to_json(data: dict) -> str:
    """Return raw dict as JSON (for Nornir global errors)."""
    return json.dumps(data)


def process_nornir_result(results: dict, **extra) -> str:
    """Process Nornir results and return appropriate JSON response.

    Handles the common pattern of checking for global errors before returning success.
    """
    if "error" in results and len(results) == 1:
        return to_json(results)
    return success(results, **extra)
