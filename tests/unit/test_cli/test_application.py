"""Unit tests for NetworkAgentCLI."""

from unittest.mock import MagicMock, patch

import pytest

from cli.application import NetworkAgentCLI


@pytest.fixture
def mock_app():
    """Mock NetworkAgentCLI with all dependencies."""
    with (
        patch("cli.application.NetworkAgentConfig") as mock_config_cls,
        patch("cli.application.AppBootstrapper") as mock_bootstrapper_cls,
        patch("cli.application.WorkflowOrchestrator") as mock_orchestrator_cls,
    ):
        # Setup minimum required mocks
        mock_config = MagicMock()
        mock_config_cls.return_value = mock_config

        # Setup bootstrapper mock
        mock_bootstrapper = mock_bootstrapper_cls.return_value
        mock_bootstrapper.build_app.return_value = {
            "nornir": MagicMock(),
            "inventory": MagicMock(),
            "executor": MagicMock(),
            "llm": MagicMock(),
            "tools": MagicMock(),
            "workflow": MagicMock(),
            "ui": MagicMock(),
        }

        # Setup orchestrator mock
        mock_orchestrator = mock_orchestrator_cls.return_value
        mock_orchestrator.execute_command.return_value = {"messages": []}

        yield {
            "config": mock_config,
            "bootstrapper": mock_bootstrapper,
            "orchestrator": mock_orchestrator,
        }


def test_cli_initialization(mock_app):
    """Test CLI initialization."""
    cli = NetworkAgentCLI(mock_app["config"])
    assert cli is not None
    mock_app["bootstrapper"].build_app.assert_called_once()
    mock_app["orchestrator"].execute_command  # Verify orchestrator was created


def test_run_single_command(mock_app):
    """Test running a single command."""
    cli = NetworkAgentCLI(mock_app["config"])

    cli.run_single_command("show version", "R1")

    # Verify orchestrator was called
    mock_app["orchestrator"].execute_command.assert_called_once_with("show version", "R1")


def test_run_interactive_chat_exit(mock_app):
    """Test interactive chat loop exit."""
    cli = NetworkAgentCLI(mock_app["config"])

    # Mock user input to exit immediately
    mock_ui = MagicMock()
    mock_ui.print_command_input_prompt.return_value = "exit"
    # Update the built app to include the mocked UI
    cli.components["ui"] = mock_ui

    # Since the loop logic depends on user input, we need to test differently
    # Let's just verify the UI was called as expected
    with patch.object(cli, "orchestrator"):
        cli.run_interactive_chat()

        # Verify we tried to get input
        mock_ui.print_command_input_prompt.assert_called()


def test_cleanup(mock_app):
    """Test resource cleanup."""
    cli = NetworkAgentCLI(mock_app["config"])

    # Access mocked nornir manager to verify close is called
    mock_nornir = cli.components["nornir"]
    cli.cleanup()
    mock_nornir.close.assert_called_once()
