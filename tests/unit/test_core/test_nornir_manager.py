"""Unit tests for NornirManager."""

from unittest.mock import MagicMock, patch

import pytest

from core.config import NetworkAgentConfig
from core.nornir_manager import NornirManager


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock(spec=NetworkAgentConfig)
    config.nornir_config_file = "config.yaml"
    return config


def test_nornir_lazy_loading(mock_config):
    """Test that Nornir is initialized only when accessed."""
    with patch("core.nornir_manager.InitNornir") as mock_init:
        manager = NornirManager(mock_config)

        # Should not be initialized yet
        mock_init.assert_not_called()

        # Access property
        _ = manager.nornir

        # Should be initialized now
        mock_init.assert_called_once_with(config_file="config.yaml")

        # Access again
        _ = manager.nornir

        # Should still be called only once
        mock_init.assert_called_once()


def test_get_hosts(mock_config):
    """Test retrieving hosts from inventory."""
    with patch("core.nornir_manager.InitNornir") as mock_init:
        # Setup mock inventory
        mock_nornir = MagicMock()
        mock_nornir.inventory.hosts.items.return_value = [
            ("R1", "host_obj_1"),
            ("R2", "host_obj_2"),
        ]
        mock_init.return_value = mock_nornir

        manager = NornirManager(mock_config)
        hosts = manager.get_hosts()

        assert len(hosts) == 2
        assert hosts["R1"] == "host_obj_1"
        assert hosts["R2"] == "host_obj_2"


def test_filter_hosts(mock_config):
    """Test filtering hosts."""
    with patch("core.nornir_manager.InitNornir") as mock_init:
        mock_nornir = MagicMock()
        mock_init.return_value = mock_nornir

        manager = NornirManager(mock_config)

        # Mock the filter method
        manager.filter_hosts(["R1", "R2"])

        # Verify filter was called correctly
        # Note: We can't easily check the F object equality, but we can check the call happened
        mock_nornir.filter.assert_called_once()


def test_filter_hosts_with_workers(mock_config):
    """Test filtering hosts with custom worker count."""
    with patch("core.nornir_manager.InitNornir") as mock_init:
        mock_nornir = MagicMock()
        # Set up the config structure to match actual implementation
        mock_nornir.config.runner.options = {"num_workers": 20}  # Default

        # Mock the filter method to return a filtered instance with proper config structure
        filtered_instance = MagicMock()
        filtered_instance.config.runner.options = {"num_workers": 20}  # Default for filtered instance
        mock_nornir.filter.return_value = filtered_instance

        mock_init.return_value = mock_nornir

        manager = NornirManager(mock_config)

        # Test filtering with custom worker count
        result = manager.filter_hosts(["R1", "R2"], num_workers=10)

        # Verify filter was called and worker count was set in runner options
        mock_nornir.filter.assert_called_once()
        assert result.config.runner.options["num_workers"] == 10


def test_test_connectivity_method(mock_config):
    """Test the connectivity testing method."""
    with patch("core.nornir_manager.InitNornir") as mock_init:
        mock_nornir = MagicMock()
        mock_init.return_value = mock_nornir

        # Setup mock inventory hosts
        mock_hosts = {
            "R1": MagicMock(),
            "R2": MagicMock()
        }
        mock_nornir.inventory.hosts.items.return_value = mock_hosts.items()

        # Setup mock results for connectivity test
        mock_results = MagicMock()
        mock_results.items.return_value = [
            ("R1", MagicMock(failed=False)),  # R1 is reachable
            ("R2", MagicMock(failed=True))   # R2 is not reachable
        ]
        mock_nornir.filter.return_value.run.return_value = mock_results

        manager = NornirManager(mock_config)

        # Test connectivity for all hosts
        results = manager.test_connectivity()

        # Verify results
        assert results["R1"] is True  # R1 should be reachable
        assert results["R2"] is False  # R2 should not be reachable


def test_close(mock_config):
    """Test closing connections."""
    with patch("core.nornir_manager.InitNornir") as mock_init:
        mock_nornir = MagicMock()
        mock_init.return_value = mock_nornir

        manager = NornirManager(mock_config)

        # Initialize
        _ = manager.nornir

        # Close
        manager.close()

        mock_nornir.close_connections.assert_called_once()

        # Verify internal reference is cleared (though implementation detail)
        # We can verify by checking if accessing nornir triggers init again
        mock_init.reset_mock()
        _ = manager.nornir
        mock_init.assert_called_once()
