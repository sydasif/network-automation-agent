"""User interface package.

This package provides UI components:
- Console UI for terminal interaction
- Output formatters
- Themes and styling
"""

from ui.console_ui import NetworkAgentUI, setup_colored_logging

__all__ = [
    "NetworkAgentUI",
    "setup_colored_logging",
]
