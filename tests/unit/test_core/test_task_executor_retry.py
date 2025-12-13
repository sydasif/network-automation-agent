"""Unit tests for TaskExecutor retry functionality."""

from unittest.mock import MagicMock, patch
import pytest

from core.config import NetworkAgentConfig
from core.nornir_manager import NornirManager
from core.task_executor import TaskExecutor
from netmiko.exceptions import NetmikoTimeoutException


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = MagicMock(spec=NetworkAgentConfig)
    config.nornir_config_file = "config.yaml"
    return config


@pytest.fixture
def mock_nornir_manager():
    """Create a mock NornirManager."""
    manager = MagicMock(spec=NornirManager)
    manager.get_hosts.return_value = {"R1": MagicMock(), "R2": MagicMock()}
    manager.filter_hosts.return_value = MagicMock()
    manager.test_connectivity.return_value = {"R1": True, "R2": True}
    return manager


def test_execute_task_with_retries_success(mock_config, mock_nornir_manager):
    """Test that execute_task works with retry functionality."""
    executor = TaskExecutor(mock_nornir_manager)

    # Mock the _execute_with_retry method to return successful results
    with patch.object(executor, '_execute_with_retry') as mock_retry:
        mock_results = MagicMock()
        mock_results.items.return_value = [
            ("R1", MagicMock(failed=False, result="success"))
        ]
        mock_retry.return_value = mock_results

        results = executor.execute_task(
            target_devices=["R1"],
            task_function=MagicMock(),
            max_retries=2
        )

        # Verify the retry method was called with the correct parameters
        mock_retry.assert_called_once()
        assert results["R1"]["success"] is True


def test_execute_with_retry_logic(mock_config, mock_nornir_manager):
    """Test the retry logic with transient failures."""
    executor = TaskExecutor(mock_nornir_manager)

    # Create a mock nornir instance
    mock_nornir_instance = MagicMock()

    # Mock the run method to simulate transient failures that eventually succeed
    call_count = 0
    def mock_run_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count == 1:  # First call fails with timeout
            mock_result = MagicMock()
            mock_result.failed = True
            mock_result.exception = NetmikoTimeoutException("Connection timeout")
            mock_aggregated_result = MagicMock()
            mock_aggregated_result.items.return_value = [("R1", mock_result)]
            return mock_aggregated_result
        else:  # Subsequent call succeeds
            mock_result = MagicMock()
            mock_result.failed = False
            mock_result.result = "Success after retry"
            mock_aggregated_result = MagicMock()
            mock_aggregated_result.items.return_value = [("R1", mock_result)]
            return mock_aggregated_result

    mock_nornir_instance.run.side_effect = mock_run_side_effect

    # Test the retry functionality
    results = executor._execute_with_retry(
        nornir_instance=mock_nornir_instance,
        task_function=MagicMock(),
        max_retries=2
    )

    # Verify that run was called multiple times due to retries
    assert mock_nornir_instance.run.call_count == 2  # First attempt + 1 retry

    # Check that the final result was successful
    for hostname, result in results.items():
        assert not result.failed


def test_execute_with_retry_exhausted(mock_config, mock_nornir_manager):
    """Test that retry logic gives up after max retries."""
    executor = TaskExecutor(mock_nornir_manager)

    # Mock the run method to always fail
    def mock_run_side_effect(*args, **kwargs):
        mock_result = MagicMock()
        mock_result.failed = True
        mock_result.exception = NetmikoTimeoutException("Connection timeout")
        mock_aggregated_result = MagicMock()
        mock_aggregated_result.items.return_value = [("R1", mock_result)]
        return mock_aggregated_result

    mock_nornir_instance = MagicMock()
    mock_nornir_instance.run.side_effect = mock_run_side_effect

    # Test the retry functionality with max retries
    results = executor._execute_with_retry(
        nornir_instance=mock_nornir_instance,
        task_function=MagicMock(),
        max_retries=2
    )

    # Verify that run was called max_retries + 1 times
    assert mock_nornir_instance.run.call_count == 3  # Original attempt + 2 retries

    # Check that the final result still shows failure
    for hostname, result in results.items():
        assert result.failed