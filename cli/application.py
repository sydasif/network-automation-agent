"""CLI application for the Network AI Agent.

This module provides the NetworkAgentCLI class that manages
the entire application lifecycle and coordinates all components.
"""

import logging
import uuid
from typing import Any

from cli.bootstrapper import AppBootstrapper
from cli.orchestrator import WorkflowOrchestrator
from core import NetworkAgentConfig

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
        self.config = config
        self.bootstrapper = AppBootstrapper(config)
        self.components = self.bootstrapper.build_app()
        self.orchestrator = WorkflowOrchestrator(
            workflow=self.components["workflow"],
            ui=self.components["ui"],
            config=config,
        )

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
        # For single command, we generate a one-off session ID
        # (Though orchestrator would generate one if we passed None, passing it explicitly is cleaner)
        session_id = str(uuid.uuid4())

        # Use the orchestrator to execute the command
        result = self.orchestrator.execute_command(command, device, session_id=session_id)

        # Print output if requested
        if print_output:
            self._print_result(result)

        return result

    def run_interactive_chat(self, device: str | None = None) -> None:
        """Run interactive chat mode.

        Args:
            device: Optional target device for all commands
        """
        # Generate a persistent session ID for the entire chat session
        # This ensures LangGraph memory (conversation history) is preserved between turns.
        session_id = str(uuid.uuid4())

        # Print header
        self.components["ui"].print_header()

        while True:
            try:
                # Get command from user
                command = self.components["ui"].print_command_input_prompt()

                # Check for exit commands
                if command.lower() in ["exit", "quit", "q", "/exit", "/quit", "/q"]:
                    self.components["ui"].print_goodbye()
                    break

                # Handle slash commands
                if command.lower() == "/clear":
                    self.components["ui"].console.clear()
                    continue

                if not command:
                    continue

                # Process command - orchestrator handles device context and approvals
                # CRITICAL: Pass the persistent session_id here!
                result = self.orchestrator.execute_command(command, device, session_id=session_id)

                # Print result
                self._print_result(result)

            except KeyboardInterrupt:
                self.components["ui"].print_session_interruption()
                break
            except EOFError:
                self.components["ui"].print_session_interruption()
                break
            except Exception as e:
                self.components["ui"].print_error(f"Error processing command: {e}")
                logger.exception("Unexpected error in interactive chat")

    def _print_result(self, result: Any) -> None:
        """Print workflow result to user.

        Args:
            result: Workflow result (could be state snapshot or dict)
        """
        # Extract messages from result - the structure depends on what was returned
        messages = []
        if (
            hasattr(result, "values")
            and isinstance(result.values, dict)
            and "messages" in result.values
        ):
            messages = result.values["messages"]
        elif isinstance(result, dict) and "messages" in result:
            messages = result["messages"]
        elif hasattr(result, "messages"):
            messages = result.messages
        elif hasattr(result, "__getitem__") and "messages" in result:
            # result might be a dictionary-like object
            messages = result["messages"]

        if not messages:
            return

        last_msg = messages[-1]

        # Check for final_response tool call
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tool_call in last_msg.tool_calls:
                if tool_call["name"] == "final_response":
                    self.components["ui"].print_output(tool_call["args"])
                    return

        # Fallback: prefer structured artifact if present, else print message content
        artifact = getattr(last_msg, "artifact", None)
        if artifact:
            self.components["ui"].print_output(artifact, getattr(last_msg, "metadata", None))
            return

        if hasattr(last_msg, "content") and last_msg.content:
            # Pass metadata if it exists
            metadata = getattr(last_msg, "metadata", None)
            self.components["ui"].print_output(last_msg.content, metadata)

    def cleanup(self) -> None:
        """Cleanup resources before shutdown."""
        logger.info("Cleaning up application resources...")
        self.components["nornir"].close()
        # Workflow uses in-memory persistence, no additional cleanup required
