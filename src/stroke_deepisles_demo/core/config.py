"""Application configuration using pydantic-settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_running_in_hf_spaces() -> bool:
    """
    Detect if running inside Hugging Face Spaces environment.

    Returns:
        True if running in HF Spaces, False otherwise

    Detection methods (all env-var based for reliability):
        1. HF_SPACES=1 env var (set by our Dockerfile)
        2. SPACE_ID env var (set by HF Spaces runtime)

    Note:
        We intentionally avoid path-based detection (like checking for
        /home/user or /app) because these paths exist on many Linux
        systems and would cause false positives.
    """
    # Check explicit env vars only - no path-based fallbacks
    if os.environ.get("HF_SPACES") == "1":
        return True
    # SPACE_ID is set by HF Spaces runtime
    return bool(os.environ.get("SPACE_ID"))


def is_deepisles_direct_available() -> bool:
    """
    Check if DeepISLES can be invoked directly (without Docker).

    Returns:
        True if DEEPISLES_DIRECT_INVOCATION env var is set

    This check is intentionally simple and side-effect free.
    The env var is set by our Dockerfile when running on HF Spaces.
    Actual module path setup happens in inference/direct.py when invoked.

    Note:
        We don't attempt import-based detection here because it would
        require modifying sys.path, which is a side effect inappropriate
        for a simple availability check.
    """
    return os.environ.get("DEEPISLES_DIRECT_INVOCATION") == "1"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables with
    the STROKE_DEMO_ prefix.

    Example:
        export STROKE_DEMO_LOG_LEVEL=DEBUG
        export STROKE_DEMO_HF_DATASET_ID=my/dataset
    """

    model_config = SettingsConfigDict(
        env_prefix="STROKE_DEMO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["simple", "detailed", "json"] = "simple"

    # HuggingFace
    hf_dataset_id: str = "hugging-science/isles24-stroke"
    hf_cache_dir: Path | None = None
    hf_token: str | None = Field(default=None, repr=False)  # Hidden from logs

    # DeepISLES
    deepisles_docker_image: str = "isleschallenge/deepisles"
    deepisles_fast_mode: bool = True  # SEALS-only (ISLES'22 winner, no FLAIR needed)
    deepisles_timeout_seconds: int = 1800  # 30 minutes
    deepisles_use_gpu: bool = True
    # Path to DeepISLES repo (for direct invocation mode)
    deepisles_repo_path: Path | None = None

    # Paths
    temp_dir: Path | None = None
    # Results directory - MUST be /tmp for HF Spaces (only /tmp is writable)
    results_dir: Path = Path("/tmp/stroke-results")

    # API Settings
    # Concurrency control
    max_concurrent_jobs: int = 10

    # CORS - frontend origins allowed to call this API
    frontend_origins: list[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    # Public URL for constructing absolute file URLs in responses
    # If not set, uses request.base_url (works for local dev)
    backend_public_url: str | None = None

    # UI
    gradio_server_name: str = "0.0.0.0"
    gradio_server_port: int = 7860
    gradio_share: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_hf_spaces(self) -> bool:
        """Check if running in HF Spaces environment."""
        return is_running_in_hf_spaces()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def use_direct_invocation(self) -> bool:
        """
        Check if should use direct DeepISLES invocation (vs Docker).

        Direct invocation is used when:
        1. Running in HF Spaces (cannot run Docker-in-Docker)
        2. DeepISLES modules are available for import
        """
        return self.is_hf_spaces or is_deepisles_direct_available()

    @field_validator("results_dir", mode="before")
    @classmethod
    def ensure_results_dir_exists(cls, v: Path | str) -> Path:
        """Create results directory if it doesn't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the current settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)."""
    global settings
    settings = Settings()
    return settings
