"""Structured logging configuration for the Network AI Agent.

This module provides a custom formatter to produce logs similar to Containerlab,
supporting structured key-value pairs for better observability.
"""

import logging


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with the custom formatter.

    Args:
        level: The logging level to set (default: logging.INFO)
    """
    # Basic configuration - logs will be handled by the UI's colored logging
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Don't add any console handlers here to avoid conflicts with UI
    # Colored logging will be set up separately in the UI module
