import argparse
import logging
import sys
import uuid

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent.nodes import RESUME_APPROVED, RESUME_DENIED
from agent.workflow import create_graph, get_approval_request


def run_single_command(app, command: str, device: str = None) -> None:
    """Execute a command, relying on the Agent's router to handle permissions."""
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": f"session-{session_id}"}}

    # KISS: Keep the prompt simple. Let the LLM interpret the intent.
    user_input = f"Run command '{command}'"
    if device:
        user_input += f" on device {device}"

    result = app.invoke({"messages": [HumanMessage(content=user_input)]}, config)
    snapshot = app.get_state(config)

    # LOOP: The graph ONLY stops here if the Agent hits the 'approval' node.
    # We don't need to manually check for "show" commands; the graph won't pause for them.
    while tool_call := get_approval_request(snapshot):
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

    if not args.command:
        parser.print_help()
        sys.exit(1)

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
