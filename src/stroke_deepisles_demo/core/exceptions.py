"""Custom exceptions for stroke-deepisles-demo."""

from __future__ import annotations


class StrokeDemoError(Exception):
    """Base exception for stroke-deepisles-demo."""


class DataLoadError(StrokeDemoError):
    """Failed to load data from HuggingFace Hub."""


class DockerNotAvailableError(StrokeDemoError):
    """Docker is not installed or not running."""


class DeepISLESError(StrokeDemoError):
    """DeepISLES inference failed."""


class MissingInputError(StrokeDemoError):
    """Required input files are missing."""


class DockerGPUNotAvailableError(StrokeDemoError):
    """GPU requested but NVIDIA Container Runtime not available."""
