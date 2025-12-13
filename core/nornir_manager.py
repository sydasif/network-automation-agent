"""Nornir instance lifecycle management.

This module provides the NornirManager class that handles Nornir
initialization and lifecycle management.
"""

from nornir import InitNornir
from nornir.core.inventory import Host
from nornir.core.configuration import Config
from nornir.core.task import Result

from core.config import NetworkAgentConfig


class NornirManager:
    """Manages Nornir instance lifecycle and configuration.

    This class encapsulates Nornir initialization and provides a clean
    interface for accessing the Nornir instance and inventory.
    It implements the Singleton pattern via lazy loading to ensuring only
    one Nornir instance is active.
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

    def _initialize_nornir(self, num_workers: int = None):
        """Initialize Nornir with configuration.

        Args:
            num_workers: Optional number of workers to override default

        Returns:
            Initialized Nornir instance
        """
        if num_workers is not None:
            # Initialize Nornir with custom configuration
            config = Config()
            config.inventory.plugin = "SimpleInventory"
            config.inventory.options = {
                "host_file": "hosts.yaml",
                "group_file": "groups.yaml"
            }
            config.runner.plugin = "threaded"
            config.runner.options = {"num_workers": num_workers}
            config.logging.enabled = False
            config.defaults.connection_options = {
                "netmiko": {
                    "extras": {
                        "timeout": 30,
                        "conn_timeout": 10,
                        "session_timeout": 60,
                        "keepalive": 30,
                        "fast_cli": True,
                        "global_cmd_verify": False,
                        "auto_connect": True
                    }
                }
            }
            return InitNornir(config=config)
        else:
            # Initialize Nornir using the config file from project root
            return InitNornir(config_file="config.yaml")

    def get_hosts(self) -> dict[str, Host]:
        """Get all available hosts from inventory.

        Returns:
            Dictionary mapping hostname to Host object
        """
        return dict(self.nornir.inventory.hosts.items())

    def filter_hosts(self, hostnames: list[str], num_workers: int = None):
        """Filter Nornir instance to specific hosts.

        Args:
            hostnames: List of hostnames to filter to
            num_workers: Optional number of workers to override default

        Returns:
            Filtered Nornir instance
        """
        from nornir.core.filter import F

        filtered_nornir = self.nornir.filter(F(name__any=hostnames))

        # If num_workers is specified, we need to create a new instance with that setting
        if num_workers is not None:
            # Update the runner configuration for this specific execution
            # The filtered instance should maintain the same configuration structure
            if hasattr(filtered_nornir.config, 'runner') and hasattr(filtered_nornir.config.runner, 'options'):
                filtered_nornir.config.runner.options["num_workers"] = num_workers

        return filtered_nornir

    def close(self) -> None:
        """Close Nornir instance and cleanup resources.

        This should be called when shutting down the application.
        """
        if self._nornir is not None:
            self._nornir.close_connections()
            self._nornir = None

    def test_connectivity(self, hostnames: list[str] = None) -> dict[str, bool]:
        """Test connectivity to specified hosts or all hosts in inventory.

        Args:
            hostnames: Optional list of hostnames to test. If None, tests all hosts.

        Returns:
            Dictionary mapping hostname to connectivity status (True if reachable)
        """
        from nornir_netmiko.tasks import netmiko_send_command

        if hostnames is None:
            hostnames = list(self.get_hosts().keys())

        # Filter to target hosts
        filtered_nornir = self.filter_hosts(hostnames)

        # Run a simple command to test connectivity
        results = filtered_nornir.run(
            task=netmiko_send_command,
            command_string="show version",
            on_failed=True  # Don't stop on first failure
        )

        # Process results
        connectivity_status = {}
        for hostname, result in results.items():
            connectivity_status[hostname] = not result.failed

        return connectivity_status
