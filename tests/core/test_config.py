"""Tests for configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from stroke_deepisles_demo.core.config import (
    Settings,
    is_deepisles_direct_available,
    is_running_in_hf_spaces,
    reload_settings,
)


class TestSettings:
    """Tests for Settings."""

    def test_default_values(self) -> None:
        """Has sensible defaults."""
        settings = Settings()
        assert settings.log_level == "INFO"
        assert settings.hf_dataset_id == "hugging-science/isles24-stroke"
        assert settings.deepisles_timeout_seconds == 1800
        # Default is /tmp/stroke-results for HF Spaces compatibility (only /tmp is writable)
        assert settings.results_dir == Path("/tmp/stroke-results")

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


class TestHFSpacesDetection:
    """Tests for HF Spaces environment detection."""

    def test_not_in_hf_spaces_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns False when not in HF Spaces."""
        # Clear any HF Spaces env vars
        monkeypatch.delenv("HF_SPACES", raising=False)
        monkeypatch.delenv("SPACE_ID", raising=False)
        assert is_running_in_hf_spaces() is False

    def test_detects_hf_spaces_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Detects HF Spaces via HF_SPACES env var."""
        monkeypatch.setenv("HF_SPACES", "1")
        assert is_running_in_hf_spaces() is True

    def test_detects_space_id_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Detects HF Spaces via SPACE_ID env var."""
        monkeypatch.delenv("HF_SPACES", raising=False)
        monkeypatch.setenv("SPACE_ID", "username/space-name")
        assert is_running_in_hf_spaces() is True


class TestDirectInvocationDetection:
    """Tests for direct DeepISLES invocation detection."""

    def test_not_available_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns False when DeepISLES modules not available."""
        # Clear env var
        monkeypatch.delenv("DEEPISLES_DIRECT_INVOCATION", raising=False)
        # In test environment, DeepISLES won't be importable
        assert is_deepisles_direct_available() is False

    def test_detects_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Detects direct invocation via env var."""
        monkeypatch.setenv("DEEPISLES_DIRECT_INVOCATION", "1")
        assert is_deepisles_direct_available() is True


class TestSettingsComputedFields:
    """Tests for Settings computed fields."""

    def test_is_hf_spaces_computed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings.is_hf_spaces reflects environment."""
        monkeypatch.delenv("HF_SPACES", raising=False)
        monkeypatch.delenv("SPACE_ID", raising=False)
        settings = Settings()
        assert settings.is_hf_spaces is False

        monkeypatch.setenv("HF_SPACES", "1")
        # Need new instance to pick up env change
        settings2 = Settings()
        assert settings2.is_hf_spaces is True

    def test_use_direct_invocation_computed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings.use_direct_invocation reflects environment."""
        monkeypatch.delenv("HF_SPACES", raising=False)
        monkeypatch.delenv("SPACE_ID", raising=False)
        monkeypatch.delenv("DEEPISLES_DIRECT_INVOCATION", raising=False)

        settings = Settings()
        # Not in HF Spaces and DeepISLES not directly available
        assert settings.use_direct_invocation is False

        # Enable direct invocation
        monkeypatch.setenv("DEEPISLES_DIRECT_INVOCATION", "1")
        settings2 = Settings()
        assert settings2.use_direct_invocation is True
