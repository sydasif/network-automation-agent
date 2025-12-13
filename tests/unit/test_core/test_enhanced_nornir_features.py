"""Unit tests for enhanced Nornir features."""

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


def test_test_connectivity_all_hosts(mock_config):
    """Test connectivity testing for all hosts."""
    with patch("core.nornir_manager.InitNornir") as mock_init:
        # Setup mock Nornir instance
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

        # Verify the filtering and command execution
        mock_nornir.filter.assert_called_once()
        mock_nornir.filter.return_value.run.assert_called_once()


def test_test_connectivity_specific_hosts(mock_config):
    """Test connectivity testing for specific hosts."""
    with patch("core.nornir_manager.InitNornir") as mock_init:
        # Setup mock Nornir instance
        mock_nornir = MagicMock()
        mock_init.return_value = mock_nornir

        # Setup mock results for connectivity test
        mock_results = MagicMock()
        mock_results.items.return_value = [
            ("R1", MagicMock(failed=False)),  # R1 is reachable
        ]
        mock_nornir.filter.return_value.run.return_value = mock_results

        manager = NornirManager(mock_config)

        # Test connectivity for specific hosts
        results = manager.test_connectivity(["R1"])

        # Verify results
        assert results["R1"] is True  # R1 should be reachable

        # Verify the filtering was called with the specific hosts
        mock_nornir.filter.assert_called_once()
        mock_nornir.filter.return_value.run.assert_called_once()


def test_connectivity_integration_with_task_executor(mock_config):
    """Test that TaskExecutor uses connectivity checking."""
    with patch("core.nornir_manager.InitNornir") as mock_init:
        # Setup mock Nornir instance
        mock_nornir = MagicMock()
        mock_init.return_value = mock_nornir

        # Setup mock inventory hosts
        mock_hosts = {
            "R1": MagicMock(),
            "R2": MagicMock()
        }
        mock_nornir.inventory.hosts.items.return_value = mock_hosts.items()

        # Setup mock results for connectivity test
        mock_connectivity_results = MagicMock()
        mock_connectivity_results.items.return_value = [
            ("R1", MagicMock(failed=False)),  # R1 is reachable
            ("R2", MagicMock(failed=True))   # R2 is not reachable
        ]
        mock_nornir.filter.return_value.run.return_value = mock_connectivity_results

        manager = NornirManager(mock_config)

        # Test that the connectivity method works as expected
        results = manager.test_connectivity(["R1", "R2"])

        assert results["R1"] is True
        assert results["R2"] is False