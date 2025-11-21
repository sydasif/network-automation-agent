"""Utility module for managing network device configurations."""
from sqlalchemy.orm import Session
from typing import List
from .database import Device
from cachetools import cached, TTLCache

# In-memory cache for device names with TTL
_device_names_cache = TTLCache(maxsize=1, ttl=300)  # Cache for 5 minutes


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


@cached(_device_names_cache)
def get_all_device_names(db: Session) -> List[str]:
    """
    Retrieves a list of all device names from the database with caching.

    Args:
        db: The database session.

    Returns:
        A list of all device names.
    """
    device_names = [device.name for device in db.query(Device.name).all()]
    return device_names
