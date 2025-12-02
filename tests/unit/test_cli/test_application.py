"""Unit tests for NetworkAgentCLI."""

from unittest.mock import MagicMock, patch

import pytest

from cli.application import NetworkAgentCLI
from core.config import NetworkAgentConfig


@pytest.fixture
def mock_components():
    with (
        patch("cli.application.NetworkAgentConfig") as mock_config_cls,
        patch("cli.application.NornirManager") as mock_nornir_cls,
        patch("cli.application.DeviceInventory") as mock_inventory_cls,
        patch("cli.application.TaskExecutor") as mock_executor_cls,
        patch("cli.application.LLMProvider") as mock_llm_cls,
        patch("cli.application.NetworkAgentWorkflow") as mock_workflow_cls,
        patch("cli.application.NetworkAgentUI") as mock_ui_cls,
    ):
        # Setup config mock
        mock_config = MagicMock(spec=NetworkAgentConfig)
        mock_config_cls.return_value = mock_config

        # Setup workflow mock to avoid infinite loop in _handle_approvals
        mock_workflow_instance = mock_workflow_cls.return_value
        mock_workflow_instance.get_approval_request.return_value = None

        yield {
            "config": mock_config,
            "workflow": mock_workflow_instance,
            "ui": mock_ui_cls.return_value,
        }


def test_cli_initialization(mock_components):
    """Test CLI initialization."""
    cli = NetworkAgentCLI(mock_components["config"])
    assert cli is not None


def test_run_single_command(mock_components):
    """Test running a single command."""
    cli = NetworkAgentCLI(mock_components["config"])

    # Mock workflow execution
    mock_components["workflow"].run.return_value = {"messages": []}
    # Mock graph invoke
    cli._graph = MagicMock()
    cli._graph.invoke.return_value = {"messages": []}

    cli.run_single_command("show version", "R1")

    # Verify workflow was run (via graph invoke)
    cli._graph.invoke.assert_called_once()


def test_run_interactive_chat_exit(mock_components):
    """Test interactive chat loop exit."""
    cli = NetworkAgentCLI(mock_components["config"])

    # Mock user input to exit immediately
    mock_components["ui"].print_command_input_prompt.return_value = "exit"

    cli.run_interactive_chat()

    # Verify we tried to get input
    mock_components["ui"].print_command_input_prompt.assert_called()

    # Verify workflow was NOT run (graph not invoked)
    if hasattr(cli, "_graph"):
        cli._graph.invoke.assert_not_called()


def test_cleanup(mock_components):
    """Test resource cleanup."""
    cli = NetworkAgentCLI(mock_components["config"])

    # Access private nornir manager to verify close is called
    # We need to mock the instance created inside __init__
    with patch.object(cli, "_nornir_manager") as mock_manager:
        cli.cleanup()
        mock_manager.close.assert_called_once()
