"""CLI application for the Network AI Agent.

This module provides the NetworkAgentCLI class that manages
the entire application lifecycle and coordinates all components.
"""

import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent import RESUME_APPROVED, RESUME_DENIED, NetworkAgentWorkflow
from core import (
    DeviceInventory,
    LLMProvider,
    NetworkAgentConfig,
    NornirManager,
    TaskExecutor,
)
from tools import get_all_tools
from ui import NetworkAgentUI

logger = logging.getLogger(__name__)


class NetworkAgentCLI:
    """Main CLI application for Network AI Agent.

    This class manages the entire application lifecycle, coordinates
    all components, and provides both single command and interactive
    chat interfaces.
    """

    def __init__(self, config: NetworkAgentConfig):
        """Initialize the CLI application.

        Args:
            config: NetworkAgentConfig instance
        """
        self._config = config
        self._setup_dependencies()

    def _setup_dependencies(self) -> None:
        """Initialize all application dependencies.

        This method creates all required components following the
        dependency injection pattern.
        """
        logger.info("Initializing application dependencies...")

        # Core infrastructure
        self._nornir_manager = NornirManager(self._config)
        self._device_inventory = DeviceInventory(self._nornir_manager)
        self._task_executor = TaskExecutor(self._nornir_manager)
        self._llm_provider = LLMProvider(self._config)

        # Tools
        self._tools = get_all_tools(self._task_executor)
        logger.info(f"Loaded {len(self._tools)} tools")

        # Workflow
        self._workflow = NetworkAgentWorkflow(
            llm_provider=self._llm_provider,
            device_inventory=self._device_inventory,
            task_executor=self._task_executor,
            tools=self._tools,
            max_history_tokens=self._config.max_history_tokens,
        )
        self._graph = self._workflow.build()
        logger.info("Workflow graph built successfully")

        # UI
        self._ui = NetworkAgentUI()

    def run_single_command(
        self, command: str, device: str | None = None, print_output: bool = True
    ) -> dict[str, Any]:
        """Execute a single network command.

        Args:
            command: The command to execute
            device: Optional target device
            print_output: Whether to print output (default: True)

        Returns:
            Result dictionary from workflow execution
        """
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        config = self._workflow.create_session_config(session_id)

        # Add device context if specified
        if device:
            full_command = f"{command} on device {device}"
        else:
            full_command = command

        # Prepare user input
        user_input = f"Run command '{full_command}'"

        # Invoke workflow
        with self._ui.thinking_status("Agent is working..."):
            result = self._graph.invoke({"messages": [HumanMessage(content=user_input)]}, config)

        # Handle approval requests
        result = self._handle_approvals(config, result)

        # Print output if requested
        if print_output:
            self._print_result(result)

        return result

    def run_interactive_chat(self, device: str | None = None) -> None:
        """Run interactive chat mode.

        Args:
            device: Optional target device for all commands
        """
        # Generate session ID
        session_id = str(uuid.uuid4())
        config = self._workflow.create_session_config(session_id)

        # Print header
        self._ui.print_header()

        while True:
            try:
                # Get command from user
                command = self._ui.print_command_input_prompt()

                # Check for exit commands
                if command.lower() in ["exit", "quit", "q", "/exit", "/quit", "/q"]:
                    self._ui.print_goodbye()
                    break

                # Handle slash commands
                if command.lower() == "/clear":
                    self._ui.console.clear()
                    continue

                if not command:
                    continue

                # Add device context if specified
                if device:
                    full_command = f"{command} on device {device}"
                else:
                    full_command = command

                # Process command
                result = self._process_interactive_command(full_command, config)

                # Print result
                self._print_result(result)

            except KeyboardInterrupt:
                self._ui.print_session_interruption()
                break
            except EOFError:
                self._ui.print_session_interruption()
                break
            except Exception as e:
                self._ui.print_error(f"Error processing command: {e}")
                logger.exception("Unexpected error in interactive chat")

    def _process_interactive_command(self, command: str, config: dict) -> dict[str, Any]:
        """Process a single command in interactive mode.

        Args:
            command: The command to process
            config: Session configuration

        Returns:
            Result dictionary from workflow execution
        """
        # Invoke workflow
        with self._ui.thinking_status("Agent is working..."):
            result = self._graph.invoke({"messages": [HumanMessage(content=command)]}, config)

        # Handle approval requests
        result = self._handle_approvals(config, result)

        return result

    def _handle_approvals(self, config: dict, result: dict) -> dict:
        """Handle approval requests in the workflow.

        Args:
            config: Session configuration
            result: Current workflow result

        Returns:
            Updated result after handling approvals
        """
        snapshot = self._graph.get_state(config)

        # Loop to handle multiple approval requests
        while tool_call := self._workflow.get_approval_request(snapshot):
            self._ui.print_approval_request(tool_call["name"], tool_call["args"])
            choice = self._ui.get_approval_decision()

            resume_value = RESUME_APPROVED if choice in ["yes", "y"] else RESUME_DENIED

            # Resume workflow
            with self._ui.thinking_status("Resuming workflow..."):
                result = self._graph.invoke(Command(resume=resume_value), config)

            # Update snapshot
            snapshot = self._graph.get_state(config)

        return result

    def _print_result(self, result: dict) -> None:
        """Print workflow result to user.

        Args:
            result: Workflow result dictionary
        """
        if "messages" not in result or not result["messages"]:
            return

        last_msg = result["messages"][-1]

        # Check for respond tool call
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tool_call in last_msg.tool_calls:
                if tool_call["name"] == "respond":
                    self._ui.print_output(tool_call["args"])
                    return

        # Fallback: print message content
        if last_msg.content:
            self._ui.print_output(last_msg.content)

    def cleanup(self) -> None:
        """Cleanup resources before shutdown."""
        logger.info("Cleaning up application resources...")
        self._nornir_manager.close()
