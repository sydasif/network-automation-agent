"""Structured logging configuration for the Network AI Agent.

This module provides a custom formatter to produce logs similar to Containerlab,
supporting structured key-value pairs for better observability.
"""

import logging

from rich.logging import RichHandler


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with the custom formatter.

    Args:
        level: The logging level to set (default: logging.INFO)
    """
    handler = RichHandler(rich_tracebacks=True, show_path=False, omit_repeated_times=False)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()

    root_logger.addHandler(handler)
