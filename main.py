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

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)
    setup_colored_logging()

    # Prevent other loggers from adding handlers
    logging.getLogger().setLevel(log_level)

    try:
        # Initialize configuration and validate
        config = NetworkAgentConfig()
        config.validate()

        # Create the CLI application
        app = NetworkAgentCLI(config)

        # Determine mode based on arguments
        if args.chat or not args.command:
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
