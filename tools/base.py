"""Shared components for network tools."""

from pydantic import BaseModel, Field
from utils.validators import FlexibleList


class DeviceInput(BaseModel):
    """Base input for tools that target devices."""

    devices: FlexibleList = Field(description="List of device hostnames (e.g., ['sw1', 'sw2']).")
