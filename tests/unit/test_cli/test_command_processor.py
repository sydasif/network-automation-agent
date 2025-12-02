"""Unit tests for CommandProcessor."""

from unittest.mock import MagicMock

import pytest

from cli.command_processor import CommandProcessor
from core.device_inventory import DeviceInventory


@pytest.fixture
def mock_device_inventory():
    inventory = MagicMock(spec=DeviceInventory)
    inventory.get_all_device_names.return_value = ["R1", "R2", "Switch1"]
    inventory.device_exists.side_effect = lambda x: x in ["R1", "R2", "Switch1"]
    inventory.validate_devices.return_value = ({"R1"}, set())  # Default for validate_devices
    return inventory


def test_parse_command_simple(mock_device_inventory):
    """Test parsing a simple command."""
    processor = CommandProcessor(mock_device_inventory)

    parsed = processor.parse_command("show version")
    assert parsed["command"] == "show version"
    assert parsed["devices"] == []
    assert parsed["has_device_context"] is False


def test_parse_command_with_device(mock_device_inventory):
    """Test parsing a command with default device."""
    processor = CommandProcessor(mock_device_inventory)

    parsed = processor.parse_command("show version", default_device="R1")
    assert parsed["command"] == "show version"
    assert parsed["devices"] == ["R1"]
    assert parsed["has_device_context"] is True


def test_extract_device_from_command_at_end(mock_device_inventory):
    """Test extracting device from command string (at end)."""
    processor = CommandProcessor(mock_device_inventory)

    parsed = processor.parse_command("show version on R1")
    assert parsed["command"] == "show version"
    assert parsed["devices"] == ["R1"]
    assert parsed["has_device_context"] is True


def test_extract_device_from_command_case_insensitive(mock_device_inventory):
    """Test extracting device case-insensitively."""
    processor = CommandProcessor(mock_device_inventory)

    parsed = processor.parse_command("show version on r1")
    assert parsed["command"] == "show version"
    assert parsed["devices"] == ["r1"]  # It keeps original case from command


def test_validate_device_valid(mock_device_inventory):
    """Test validating a valid device."""
    processor = CommandProcessor(mock_device_inventory)
    parsed = {"command": "cmd", "devices": ["R1"]}

    is_valid, error = processor.validate_command(parsed)
    assert is_valid is True
    assert error == ""


def test_validate_device_invalid(mock_device_inventory):
    """Test validating an invalid device."""
    processor = CommandProcessor(mock_device_inventory)
    # Mock validate_devices to return invalid
    mock_device_inventory.validate_devices.return_value = (set(), {"Unknown"})

    parsed = {"command": "cmd", "devices": ["Unknown"]}

    is_valid, error = processor.validate_command(parsed)
    assert is_valid is False
    assert "Unknown devices" in error
