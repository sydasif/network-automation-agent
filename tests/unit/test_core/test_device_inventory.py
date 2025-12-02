"""Unit tests for DeviceInventory."""

from unittest.mock import MagicMock, Mock

import pytest

from core.device_inventory import DeviceInventory
from core.nornir_manager import NornirManager


@pytest.fixture
def mock_nornir_manager():
    """Create a mock NornirManager."""
    manager = MagicMock(spec=NornirManager)

    # Mock hosts
    r1 = Mock()
    r1.name = "R1"
    r1.hostname = "192.168.1.1"
    r1.platform = "cisco_ios"
    r1.groups = ["routers"]
    r1.data = {"site": "nyc"}

    s1 = Mock()
    s1.name = "S1"
    s1.hostname = "192.168.1.2"
    s1.platform = "cisco_nxos"
    s1.groups = ["switches"]
    s1.data = {}

    manager.get_hosts.return_value = {"R1": r1, "S1": s1}
    return manager


def test_get_device_info(mock_nornir_manager):
    """Test formatting of device information string."""
    inventory = DeviceInventory(mock_nornir_manager)
    info = inventory.get_device_info()

    assert "R1" in info
    assert "cisco_ios" in info
    assert "routers" not in info  # Groups are not in the output string

    assert "S1" in info
    assert "cisco_nxos" in info


def test_validate_devices_all_valid(mock_nornir_manager):
    """Test validation when all devices exist."""
    inventory = DeviceInventory(mock_nornir_manager)
    valid, invalid = inventory.validate_devices(["R1", "S1"])

    assert len(valid) == 2
    assert "R1" in valid
    assert "S1" in valid
    assert len(invalid) == 0


def test_validate_devices_mixed(mock_nornir_manager):
    """Test validation with mixed valid and invalid devices."""
    inventory = DeviceInventory(mock_nornir_manager)
    valid, invalid = inventory.validate_devices(["R1", "INVALID_DEV"])

    assert len(valid) == 1
    assert "R1" in valid
    assert len(invalid) == 1
    assert "INVALID_DEV" in invalid


def test_get_all_device_names(mock_nornir_manager):
    """Test retrieving all device names."""
    inventory = DeviceInventory(mock_nornir_manager)
    names = inventory.get_all_device_names()

    assert len(names) == 2
    assert "R1" in names
    assert "S1" in names
