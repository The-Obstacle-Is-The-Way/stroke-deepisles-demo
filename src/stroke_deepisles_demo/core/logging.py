"""Centralized logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def setup_logging(
    level: LogLevel = "INFO",
    *,
    format_style: Literal["simple", "detailed", "json"] = "simple",
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Minimum log level
        format_style: Output format style

    Example:
        >>> setup_logging("DEBUG", format_style="detailed")
    """
    formats = {
        "simple": "%(levelname)s: %(message)s",
        "detailed": "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        "json": '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
    }

    logging.basicConfig(
        level=getattr(logging, level),
        format=formats[format_style],
        stream=sys.stderr,
        force=True,
    )

    # Reduce noise from libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("datasets").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    # Using the package name as prefix
    return logging.getLogger(f"stroke_deepisles_demo.{name}")
