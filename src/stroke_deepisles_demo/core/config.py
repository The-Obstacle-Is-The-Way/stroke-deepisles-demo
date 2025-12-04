"""Application configuration using pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # HuggingFace
    hf_dataset_id: str = "YongchengYAO/ISLES24-MR-Lite"
    hf_cache_dir: str | None = None

    # DeepISLES
    deepisles_docker_image: str = "isleschallenge/deepisles"
    deepisles_fast_mode: bool = True

    # Paths
    temp_dir: str | None = None

    class Config:
        env_prefix = "STROKE_DEMO_"
        env_file = ".env"


settings = Settings()
