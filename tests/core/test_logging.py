"""Tests for logging configuration."""

from __future__ import annotations

import logging

from stroke_deepisles_demo.core.logging import get_logger, setup_logging


class TestSetupLogging:
    """Tests for setup_logging."""

    def test_sets_log_level(self) -> None:
        """Sets the root logger level."""
        # Reset root logger handlers to avoid interference
        logging.getLogger().handlers = []

        setup_logging("DEBUG")
        # Note: basicConfig might not reset if already configured unless force=True is used
        # The implementation should use force=True
        assert logging.getLogger().level == logging.DEBUG

    def test_format_styles(self) -> None:
        """Different format styles work."""
        for style in ["simple", "detailed", "json"]:
            # Reset handlers
            logging.getLogger().handlers = []
            setup_logging("INFO", format_style=style)  # type: ignore
            # Should not raise


class TestGetLogger:
    """Tests for get_logger."""

    def test_returns_namespaced_logger(self) -> None:
        """Returns logger with stroke_demo prefix."""
        logger = get_logger("my_module")
        assert logger.name == "stroke_deepisles_demo.my_module"
