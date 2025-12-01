"""Device inventory management.

This module provides the DeviceInventory class that manages
network device inventory information.
"""

from functools import lru_cache

from core.nornir_manager import NornirManager


class DeviceInventory:
    """Manages network device inventory information.

    This class provides methods to query and validate device information
    from the Nornir inventory.
    """

    def __init__(self, nornir_manager: NornirManager):
        """Initialize the device inventory.

        Args:
            nornir_manager: NornirManager instance
        """
        self._nornir_manager = nornir_manager

    @lru_cache(maxsize=1)
    def get_device_info(self) -> str:
        """Return formatted string of devices and platforms.

        This is cached to avoid redundant lookups and ensure
        deterministic LLM prompts.

        Returns:
            Formatted string listing all devices and their platforms
        """
        hosts = self._nornir_manager.get_hosts()
        sorted_hosts = sorted(hosts.items())

        return "\n".join(
            f"- {name} (Platform: {host.platform or 'unknown'})" for name, host in sorted_hosts
        )

    def validate_devices(self, device_names: list[str]) -> tuple[set[str], set[str]]:
        """Validate that device names exist in inventory.

        Args:
            device_names: List of device names to validate

        Returns:
            Tuple of (valid_devices, invalid_devices)
        """
        targets = set(device_names)
        available_hosts = set(self._nornir_manager.get_hosts().keys())

        valid = targets & available_hosts
        invalid = targets - available_hosts

        return valid, invalid

    def get_all_device_names(self) -> list[str]:
        """Get list of all device names in inventory.

        Returns:
            Sorted list of device names
        """
        return sorted(self._nornir_manager.get_hosts().keys())

    def device_exists(self, device_name: str) -> bool:
        """Check if a device exists in inventory.

        Args:
            device_name: Name of the device to check

        Returns:
            True if device exists, False otherwise
        """
        return device_name in self._nornir_manager.get_hosts()
