"""Utility module for managing network device configurations and caching."""

from typing import List

from cachetools import TTLCache, cached
from sqlalchemy.orm import Session

from .database import Device

_device_names_cache = TTLCache(maxsize=1, ttl=300)


def get_device_by_name(db: Session, device_name: str) -> Device | None:
    """Retrieves a specific device from the database by its name."""
    return db.query(Device).filter(Device.name == device_name).first()


@cached(_device_names_cache)
def get_all_device_names(db: Session) -> List[str]:
    """Retrieves a list of all device names from the database with caching."""
    device_names = [device.name for device in db.query(Device.name).all()]
    return device_names


def clear_device_cache():
    """Clears the cached device names."""
    _device_names_cache.clear()
    print("Device cache cleared.")
