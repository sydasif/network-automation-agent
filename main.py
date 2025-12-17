"""
This module provides a command-line interface for the Network AI Agent,
allowing users to execute network commands and configurations via natural language.
Supports both single command execution and interactive chat mode.
"""

import argparse
import logging
import sys

from cli import NetworkAgentCLI
from core import NetworkAgentConfig
from ui import setup_colored_logging
from utils.logger import setup_logging


def main() -> None:
    """Main entry point for the Network AI Agent CLI.

    Parses command line arguments, sets up logging, creates the agent application,
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
    parser.add_argument(
        "--monitor",
        "-m",
        action="store_true",
        help="Show monitoring dashboard and exit",
    )

    args = parser.parse_args()

    # Determine logging levels
    # File logging: Always detailed (INFO or DEBUG)
    file_log_level = logging.DEBUG if args.debug else logging.INFO

    # Console logging: Clean (WARNING) in chat mode, unless debugging.
    # In single command mode, we usually want to see what's happening (INFO), unless explicitly quiet?
    # Actually, for a clean chat UI, we only want warnings/errors.
    if args.debug:
        console_log_level = logging.DEBUG
    elif args.chat or not args.command:
        # Interactive mode: Hide INFO logs to keep UI clean
        console_log_level = logging.WARNING
    else:
        # Single command mode: Show INFO logs (execution progress)
        console_log_level = logging.INFO

    # Setup file logging (Root logger)
    setup_logging(level=file_log_level)

    # Setup console UI logging
    setup_colored_logging(level=console_log_level)

    # Prevent other loggers from adding handlers that might bypass our settings
    logging.getLogger().setLevel(file_log_level)

    try:
        # Initialize configuration and validate
        config = NetworkAgentConfig.load()
        config.validate()

        # Create the CLI application
        app = NetworkAgentCLI(config)

        # Determine mode based on arguments
        if args.monitor:
            # Show monitoring dashboard and exit
            print(app.show_dashboard())
        elif args.chat or not args.command:
            # Interactive chat mode
            app.run_interactive_chat(device=args.device)
        else:
            # Single command mode
            command = " ".join(args.command)
            app.run_single_command(command, device=args.device)

        # Cleanup resources
        app.cleanup()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Failed to execute command: {e}")
        if args.debug:
            logging.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
