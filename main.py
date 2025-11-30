"""Network AI Agent CLI entry point.

This module provides a command-line interface for the Network AI Agent,
allowing users to execute network commands and configurations via natural language.
Supports both single command execution and interactive chat mode.
"""

import argparse
import logging
import sys
import uuid

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent.nodes import RESUME_APPROVED, RESUME_DENIED
from agent.workflow import create_graph, get_approval_request
from utils.logger import setup_logging
from utils.ui import NetworkAgentUI, setup_colored_logging


def run_single_command(
    app, command: str, config: dict, ui: NetworkAgentUI, print_output: bool = True
) -> dict:
    """Execute a single network command through the agent workflow.

    This function processes a command by sending it to the agent workflow,
    handling any required approvals, and returning the results.

    Args:
        app: The compiled LangGraph workflow instance.
        command: The natural language command to execute.
        config: The configuration dict containing thread_id and other settings.
        print_output: Whether to print the result (True for single command mode, False for interactive mode)
        ui: The UI instance to use for display

    Returns:
        The result of the command execution.
    """
    # KISS: Keep the prompt simple. Let the LLM interpret the intent.
    user_input = f"Run command '{command}'"

    # Invoke the workflow with the user's command
    if ui:
        with ui.thinking_status("Agent is working..."):
            result = app.invoke({"messages": [HumanMessage(content=user_input)]}, config)
    else:
        result = app.invoke({"messages": [HumanMessage(content=user_input)]}, config)
    # Get the current state of the workflow to check for pending approvals
    snapshot = app.get_state(config)

    # LOOP: The graph ONLY stops here if the Agent hits the 'approval' node.
    # We don't need to manually check for "show" commands; the graph won't pause for them.
    # This loop handles multiple approval requests if they occur in sequence
    while tool_call := get_approval_request(snapshot):
        ui.print_approval_request(tool_call["name"], tool_call["args"])
        choice = ui.get_approval_decision()

        resume_value = RESUME_APPROVED if choice in ["yes", "y"] else RESUME_DENIED

        # Resume the workflow with the user's decision
        if ui:
            with ui.thinking_status("Resuming workflow..."):
                result = app.invoke(
                    Command(resume=resume_value),
                    config,
                )
        else:
            result = app.invoke(
                Command(resume=resume_value),
                config,
            )
        # Update the snapshot for the next iteration
        snapshot = app.get_state(config)

    # Print the final result of the command execution (for single command mode)
    if print_output and "messages" in result and len(result["messages"]) > 0:
        ui.print_output(result["messages"][-1].content)

    return result


def run_interactive_chat(app, initial_device: str = None) -> None:
    """Run the agent in interactive chat mode, allowing multiple commands in one session.

    Args:
        app: The compiled LangGraph workflow instance.
        initial_device: Optional target device for all commands in this session.
    """
    # Generate a unique session ID for this chat session
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": f"session-{session_id}"}}

    # Initialize UI
    ui = NetworkAgentUI()
    ui.print_header()

    while True:
        try:
            # Get command from user
            command = ui.print_command_input_prompt()

            # Check for exit commands
            if command.lower() in ["exit", "quit", "q", "/exit", "/quit", "/q"]:
                ui.print_goodbye()
                break

            # Handle slash commands
            if command.lower() == "/clear":
                ui.console.clear()
                continue

            if not command:
                continue

            # Add device context if specified
            if initial_device:
                full_command = f"{command} on device {initial_device}"
            else:
                full_command = command

            # Process the command (do not print output in interactive mode as we handle it below)
            result = run_single_command(app, full_command, config, ui=ui, print_output=False)

            # Print the result of the command execution
            if "messages" in result and result["messages"]:
                ui.print_output(result["messages"][-1].content)
            else:
                # Handle case where no output is returned (might happen with general chat)
                ui.print_output("Response processed successfully.")

        except KeyboardInterrupt:
            ui.print_session_interruption()
            break
        except EOFError:
            ui.print_session_interruption()
            break
        except Exception as e:
            ui.print_error(f"Error processing command: {e}")

    return  # Explicit return for clarity


def main() -> None:
    """Main entry point for the Network AI Agent CLI.

    Parses command line arguments, sets up logging, creates the agent workflow,
    and executes either a single command or enters interactive chat mode.
    """
    parser = argparse.ArgumentParser(description="Network Agent Command Tool")
    parser.add_argument(
        "command",
        nargs="*",
        help="The command to execute on the device (omit for interactive chat mode)",
    )
    parser.add_argument("--device", "-d", help="Target device for the command (recommended)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--chat",
        "-c",
        action="store_true",
        help="Start interactive chat mode (default when no command provided)",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)

    # Set up colored logging that doesn't interfere with UI
    setup_colored_logging()

    # Prevent other loggers from adding their own handlers that would interfere with UI
    logging.getLogger().setLevel(log_level)

    try:
        app = create_graph()

        # Determine mode based on arguments
        if args.chat or not args.command:
            run_interactive_chat(app, args.device)
        else:
            # Generate config for single command mode
            session_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": f"session-{session_id}"}}

            command = " ".join(args.command)
            ui = NetworkAgentUI()  # Use UI for single command mode too
            run_single_command(app, command, config, ui=ui)
    except Exception as e:
        logging.error(f"Failed to execute command: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
