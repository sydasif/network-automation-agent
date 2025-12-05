"""CLI application package.

This package manages the command-line interface:
- Application lifecycle
- Command processing
- Session management
- Argument parsing
"""

from cli.application import NetworkAgentCLI

__all__ = [
    "NetworkAgentCLI",
]
