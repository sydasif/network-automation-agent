"""Nornir instance lifecycle management.

This module provides the NornirManager class that handles Nornir
initialization and lifecycle management.
"""

from nornir import InitNornir
from nornir.core.inventory import Host

from core.config import NetworkAgentConfig


class NornirManager:
    """Manages Nornir instance lifecycle and configuration.

    This class encapsulates Nornir initialization and provides a clean
    interface for accessing the Nornir instance and inventory.
    """

    def __init__(self, config: NetworkAgentConfig):
        """Initialize the Nornir manager.

        Args:
            config: NetworkAgentConfig instance
        """
        self._config = config
        self._nornir = None

    @property
    def nornir(self):
        """Get or create the Nornir instance (lazy-loaded).

        Returns:
            Initialized Nornir instance
        """
        if self._nornir is None:
            self._nornir = self._initialize_nornir()
        return self._nornir

    def _initialize_nornir(self):
        """Initialize Nornir with configuration.

        Returns:
            Initialized Nornir instance
        """
        # Initialize Nornir using the config file from project root
        return InitNornir(config_file="config.yaml")

    def get_hosts(self) -> dict[str, Host]:
        """Get all available hosts from inventory.

        Returns:
            Dictionary mapping hostname to Host object
        """
        return dict(self.nornir.inventory.hosts.items())

    def filter_hosts(self, hostnames: list[str]):
        """Filter Nornir instance to specific hosts.

        Args:
            hostnames: List of hostnames to filter to

        Returns:
            Filtered Nornir instance
        """
        from nornir.core.filter import F

        return self.nornir.filter(F(name__any=hostnames))

    def close(self) -> None:
        """Close Nornir instance and cleanup resources.

        This should be called when shutting down the application.
        """
        if self._nornir is not None:
            self._nornir.close_connections()
            self._nornir = None
