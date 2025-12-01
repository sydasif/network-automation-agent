"""CLI application package.

This package manages the command-line interface:
- Application lifecycle
- Command processing
- Session management
- Argument parsing
"""

from cli.application import NetworkAgentCLI
from cli.command_processor import CommandProcessor

__all__ = [
    "NetworkAgentCLI",
    "CommandProcessor",
]
