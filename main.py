import argparse
import logging
import sys
import uuid

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent import RESUME_APPROVED, RESUME_DENIED, create_graph, get_approval_request


def run_single_command(app, command: str, device: str = None) -> None:
    """Execute a single command on the device with appropriate handling for show vs config commands."""
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": f"session-{session_id}"}}

    # Detect if this is a show command (read-only) or config command (changes device state)
    is_show_command = any(
        keyword in command.lower()
        for keyword in [
            "show",
            "display",
            "get",
            "list",
            "view",
            "check",
            "verify",
            "status",
            "monitor",
        ]
    )

    # Construct user input with device context if provided
    if device:
        user_input = f"Run command '{command}' on device {device}. This is {'a show' if is_show_command else 'a configuration'} command."
    else:
        user_input = f"Run command '{command}'. This is {'a show' if is_show_command else 'a configuration'} command."

    result = app.invoke({"messages": [HumanMessage(content=user_input)]}, config)
    snapshot = app.get_state(config)

    # Handle any approval requests
    while tool_call := get_approval_request(snapshot):
        # For show commands, auto-approve since they don't change device state
        if is_show_command:
            result = app.invoke(Command(resume=RESUME_APPROVED), config)
        else:
            # For config commands, ask for user confirmation
            print("\n⚠️  CONFIGURATION CHANGE DETECTED ⚠️")
            print(f"Action:  {tool_call['name']}")
            print(f"Args:    {tool_call['args']}")

            choice = input("Proceed with configuration change? (yes/no): ").strip().lower()
            resume_value = RESUME_APPROVED if choice in ["yes", "y"] else RESUME_DENIED

            result = app.invoke(
                Command(resume=resume_value),
                config,
            )

        snapshot = app.get_state(config)

    # Print the result
    if "messages" in result and result["messages"]:
        print(result["messages"][-1].content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Network Agent Command Tool")
    parser.add_argument("command", nargs="*", help="The command to execute on the device")
    parser.add_argument("--device", "-d", help="Target device for the command (recommended)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # If no command is provided, show help and exit
    if not args.command:
        parser.print_help()
        print("\nExample usage:")
        print(
            "  python main.py --device router1 'show version'           # Run a show command on specific device"
        )
        print(
            "  python main.py --device switch1 'show interfaces status' # Run on specific device"
        )
        print(
            "  python main.py --device router1 'interface eth0 shutdown'# Run a config command (requires approval)"
        )
        print(
            "\nNote: It is recommended to always specify the --device parameter to target the correct device."
        )
        sys.exit(1)

    # Combine command parts into a single string
    command = " ".join(args.command)

    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.ERROR
    logging.basicConfig(level=log_level)

    try:
        app = create_graph()
        run_single_command(app, command, args.device)
    except Exception as e:
        logging.error(f"Failed to execute command: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
