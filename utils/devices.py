"""Utility module for managing network device configurations."""
from sqlalchemy.orm import Session
from .database import Device

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

def get_all_device_names(db: Session) -> list[str]:
    """
    Retrieves a list of all device names from the database.

    Args:
        db: The database session.

    Returns:
        A list of all device names.
    """
    return [device.name for device in db.query(Device.name).all()]
