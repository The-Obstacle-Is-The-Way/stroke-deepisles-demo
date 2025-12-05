"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    hf_dataset_id: str = "YongchengYAO/ISLES24-MR-Lite"
    hf_cache_dir: Path | None = None
    hf_token: str | None = Field(default=None, repr=False)  # Hidden from logs

    # DeepISLES
    deepisles_docker_image: str = "isleschallenge/deepisles"
    deepisles_fast_mode: bool = True  # SEALS-only (ISLES'22 winner, no FLAIR needed)
    deepisles_timeout_seconds: int = 1800  # 30 minutes
    deepisles_use_gpu: bool = True

    # Paths
    temp_dir: Path | None = None
    results_dir: Path = Path("./results")

    # UI
    gradio_server_name: str = "0.0.0.0"
    gradio_server_port: int = 7860
    gradio_share: bool = False

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
