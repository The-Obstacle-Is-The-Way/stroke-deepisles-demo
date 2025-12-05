"""Tests for configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from stroke_deepisles_demo.core.config import Settings, reload_settings


class TestSettings:
    """Tests for Settings."""

    def test_default_values(self) -> None:
        """Has sensible defaults."""
        settings = Settings()
        assert settings.log_level == "INFO"
        assert settings.hf_dataset_id == "YongchengYAO/ISLES24-MR-Lite"
        assert settings.deepisles_timeout_seconds == 1800
        assert settings.results_dir == Path("./results")

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables override defaults."""
        monkeypatch.setenv("STROKE_DEMO_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("STROKE_DEMO_DEEPISLES_TIMEOUT_SECONDS", "60")

        settings = Settings()
        assert settings.log_level == "DEBUG"
        assert settings.deepisles_timeout_seconds == 60

    def test_hf_token_hidden_from_repr(self) -> None:
        """HF token is not visible in repr."""
        settings = Settings(hf_token="secret123")
        assert "secret123" not in repr(settings)

    def test_results_dir_created(self, tmp_path: Path) -> None:
        """Results directory is created if it doesn't exist."""
        # This test relies on the validator running during instantiation
        new_dir = tmp_path / "new_results"
        assert not new_dir.exists()

        Settings(results_dir=new_dir)
        assert new_dir.exists()

    def test_reload_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that reload_settings updates the global instance."""
        from stroke_deepisles_demo.core import config

        # Set env var
        monkeypatch.setenv("STROKE_DEMO_LOG_LEVEL", "ERROR")

        # Reload
        new_settings = reload_settings()

        assert new_settings.log_level == "ERROR"
        assert config.settings.log_level == "ERROR"
        # Ensure it's the same object instance reference in the module
        assert config.settings is new_settings
