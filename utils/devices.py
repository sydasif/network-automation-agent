"""Utility module for managing network device configurations and caching.

This module provides utility functions for retrieving device information
from the database with caching capabilities. It includes functions for
getting specific devices by name, retrieving all device names, and
managing the in-memory cache.

The caching mechanism improves performance by reducing database queries
when frequently accessing device names.
"""

from sqlalchemy.orm import Session
from typing import List
from .database import Device
from cachetools import cached, TTLCache

# In-memory cache for device names with TTL (Time To Live)
# Cache stores device names list for 5 minutes (300 seconds) to balance
# performance with data freshness when device inventory changes
_device_names_cache = TTLCache(maxsize=1, ttl=300)  # Cache for 5 minutes


def get_device_by_name(db: Session, device_name: str) -> Device | None:
    """Retrieves a specific device from the database by its name.

    Queries the database for a device with the given name. Since device names
    are unique in the database, this will return at most one device.

    Args:
        db: The database session to use for the query.
        device_name: The unique name identifier of the device to retrieve.

    Returns:
        The Device object if found in the database, otherwise None.
    """
    return db.query(Device).filter(Device.name == device_name).first()


@cached(_device_names_cache)
def get_all_device_names(db: Session) -> List[str]:
    """Retrieves a list of all device names from the database with caching.

    Fetches all device names from the database and caches the result to
    improve performance on subsequent calls. The cache expires after 5 minutes
    to ensure data freshness when devices are added or removed.

    Args:
        db: The database session to use for the query.

    Returns:
        A list containing the names of all devices in the inventory.
    """
    device_names = [device.name for device in db.query(Device.name).all()]
    return device_names


def clear_device_cache():
    """Clears the cached device names.

    This function clears the in-memory cache of device names and should be
    called whenever the device inventory in the database is modified (added,
    updated, or removed) to ensure the cache reflects the current database state.
    """
    # Clear the TTL cache to force fresh data retrieval on next call
    _device_names_cache.clear()
    print("Device cache cleared.")
