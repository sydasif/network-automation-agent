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
