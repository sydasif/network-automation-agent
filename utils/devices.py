"""Utility module for managing network device configurations."""
from sqlalchemy.orm import Session
from typing import List
from .database import Device
import time

# Simple in-memory cache for device names with TTL
_device_names_cache = []
_cache_timestamp = 0
_CACHE_TTL_SECONDS = 300  # 5 minutes


def get_device_by_name(db: Session, device_name: str) -> Device | None:
    """
    Retrieves a device from the database by its name.

    Args:
        db: The database session.
        device_name: The name of the device to retrieve.

    Returns:
        The Device object if found, otherwise None.
    """
    return db.query(Device).filter(Device.name == device_name).first()


def get_all_device_names(db: Session) -> List[str]:
    """
    Retrieves a list of all device names from the database with caching.

    Args:
        db: The database session.

    Returns:
        A list of all device names.
    """
    global _device_names_cache, _cache_timestamp

    current_time = time.time()

    # Check if cache is still valid (not expired)
    if _device_names_cache and (current_time - _cache_timestamp) < _CACHE_TTL_SECONDS:
        return _device_names_cache.copy()  # Return a copy to prevent external modification

    # Cache is expired or empty, fetch from database
    device_names = [device.name for device in db.query(Device.name).all()]

    # Update cache
    _device_names_cache = device_names
    _cache_timestamp = current_time

    return device_names


def invalidate_device_cache():
    """Invalidate the device names cache."""
    global _device_names_cache, _cache_timestamp
    _device_names_cache = []
    _cache_timestamp = 0
