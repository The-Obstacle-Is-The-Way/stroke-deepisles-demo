# phase 5: polish, observability, and docs

## purpose

Add production-quality polish: structured logging, environment-driven configuration, comprehensive documentation, and CI readiness. At the end of this phase, the codebase is maintainable, debuggable, and ready for others to contribute.

## deliverables

- [ ] Structured logging throughout all modules
- [ ] Environment-driven configuration via pydantic-settings
- [ ] Developer documentation (CONTRIBUTING.md, architecture)
- [ ] API documentation (docstrings, optional Sphinx/mkdocs)
- [ ] CI configuration (GitHub Actions)
- [ ] Final cleanup and code review checklist

## logging strategy

### centralized logging setup

```python
# src/stroke_deepisles_demo/core/logging.py

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
    return logging.getLogger(f"stroke_demo.{name}")
```

### logging usage pattern

```python
# In each module
from stroke_deepisles_demo.core.logging import get_logger

logger = get_logger(__name__)


def run_deepisles_on_folder(input_dir: Path, *, fast: bool = True) -> DeepISLESResult:
    logger.info("Starting DeepISLES inference", extra={"input_dir": str(input_dir), "fast": fast})

    try:
        result = _run_docker(...)
        logger.info("Inference complete", extra={"elapsed": result.elapsed_seconds})
        return result
    except Exception as e:
        logger.error("Inference failed", extra={"error": str(e)}, exc_info=True)
        raise
```

## enhanced configuration

### `src/stroke_deepisles_demo/core/config.py`

```python
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
    deepisles_fast_mode: bool = True
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
```

## documentation structure

```
docs/
├── specs/                  # Design specs (these documents)
│   ├── 00-context.md
│   ├── 01-phase-0-repo-bootstrap.md
│   ├── ...
│   └── 06-phase-5-polish.md
│
├── guides/                 # User guides
│   ├── quickstart.md       # Getting started
│   ├── configuration.md    # Environment variables
│   └── deployment.md       # HF Spaces deployment
│
└── reference/              # API reference (auto-generated)
    └── api.md

# Root level
README.md                   # Project overview
CONTRIBUTING.md             # Contribution guidelines
CHANGELOG.md                # Version history
```

### `CONTRIBUTING.md`

```markdown
# Contributing to stroke-deepisles-demo

Thank you for your interest in contributing!

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/The-Obstacle-Is-The-Way/stroke-deepisles-demo.git
   cd stroke-deepisles-demo
   ```

2. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **Install pre-commit hooks**
   ```bash
   uv run pre-commit install
   ```

## Running Tests

```bash
# All tests (excluding integration)
uv run pytest

# With coverage
uv run pytest --cov

# Integration tests (requires Docker)
uv run pytest -m integration

# Slow tests (requires Docker + DeepISLES image)
uv run pytest -m "integration and slow"
```

## Code Quality

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy src/
```

## Project Structure

```
src/stroke_deepisles_demo/
├── core/           # Shared utilities (config, types, exceptions)
├── data/           # HF dataset loading and case management
├── inference/      # DeepISLES Docker integration
├── ui/             # Gradio application
├── pipeline.py     # End-to-end orchestration
└── metrics.py      # Evaluation metrics
```

## Pull Request Process

1. Create a feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass and code quality checks pass
4. Update documentation if needed
5. Submit PR with clear description

## Code Style

- Type hints on all functions
- Docstrings in Google style
- Keep functions focused and small
- Prefer explicit over implicit
```

### `docs/guides/quickstart.md`

```markdown
# Quickstart

Get started with stroke-deepisles-demo in 5 minutes.

## Prerequisites

- Python 3.11+
- Docker (for DeepISLES inference)
- ~10GB disk space (for Docker image and datasets)

## Installation

```bash
# Clone
git clone https://github.com/The-Obstacle-Is-The-Way/stroke-deepisles-demo.git
cd stroke-deepisles-demo

# Install
uv sync
```

## Pull DeepISLES Docker Image

```bash
docker pull isleschallenge/deepisles
```

## Run Locally

### Option 1: Gradio UI

```bash
uv run python -m stroke_deepisles_demo.ui.app
# Open http://localhost:7860
```

### Option 2: CLI

```bash
# List available cases
uv run stroke-demo list

# Run on a specific case
uv run stroke-demo run --case sub-001 --fast
```

### Option 3: Python API

```python
from stroke_deepisles_demo.pipeline import run_pipeline_on_case

result = run_pipeline_on_case("sub-001", fast=True)
print(f"Dice score: {result.dice_score:.3f}")
print(f"Prediction: {result.prediction_mask}")
```

## Configuration

Set environment variables or create a `.env` file:

```bash
# .env
STROKE_DEMO_LOG_LEVEL=DEBUG
STROKE_DEMO_DEEPISLES_USE_GPU=false  # If no GPU available
```

See [Configuration Guide](configuration.md) for all options.
```

### `docs/guides/configuration.md`

```markdown
# Configuration

All settings can be configured via environment variables.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STROKE_DEMO_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `STROKE_DEMO_LOG_FORMAT` | `simple` | Log format (simple, detailed, json) |
| `STROKE_DEMO_HF_DATASET_ID` | `YongchengYAO/ISLES24-MR-Lite` | HuggingFace dataset ID |
| `STROKE_DEMO_HF_CACHE_DIR` | `None` | Custom HF cache directory |
| `STROKE_DEMO_HF_TOKEN` | `None` | HuggingFace API token (for private datasets) |
| `STROKE_DEMO_DEEPISLES_DOCKER_IMAGE` | `isleschallenge/deepisles` | DeepISLES Docker image |
| `STROKE_DEMO_DEEPISLES_FAST_MODE` | `true` | Use single-model mode |
| `STROKE_DEMO_DEEPISLES_TIMEOUT_SECONDS` | `1800` | Inference timeout |
| `STROKE_DEMO_DEEPISLES_USE_GPU` | `true` | Use GPU acceleration |
| `STROKE_DEMO_RESULTS_DIR` | `./results` | Directory for output files |

## Using .env File

Create a `.env` file in the project root:

```bash
STROKE_DEMO_LOG_LEVEL=DEBUG
STROKE_DEMO_DEEPISLES_USE_GPU=false
STROKE_DEMO_RESULTS_DIR=/data/results
```

## Programmatic Configuration

```python
from stroke_deepisles_demo.core.config import settings, reload_settings
import os

# Check current settings
print(settings.log_level)

# Override via environment
os.environ["STROKE_DEMO_LOG_LEVEL"] = "DEBUG"
reload_settings()
print(settings.log_level)  # DEBUG
```
```

## ci configuration

### `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync

      - name: Lint with ruff
        run: uv run ruff check .

      - name: Check formatting
        run: uv run ruff format --check .

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync

      - name: Type check with mypy
        run: uv run mypy src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync

      - name: Run tests
        run: uv run pytest --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml

  integration:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: uv sync

      - name: Run integration tests
        run: uv run pytest -m integration --timeout=600
```

## final code review checklist

### code quality
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] No unused imports or variables
- [ ] No hardcoded paths or secrets
- [ ] Error messages are helpful

### testing
- [ ] Unit test coverage > 80%
- [ ] Edge cases covered
- [ ] Integration tests for critical paths
- [ ] Tests are deterministic (no flakiness)

### documentation
- [ ] README is clear and accurate
- [ ] CONTRIBUTING.md is complete
- [ ] All configuration options documented
- [ ] Example usage in docstrings

### security
- [ ] No secrets in code
- [ ] HF_TOKEN is optional and hidden from logs
- [ ] Docker commands are properly escaped
- [ ] No arbitrary code execution vulnerabilities

### production readiness
- [ ] Logging is consistent and useful
- [ ] Errors are handled gracefully
- [ ] Configuration is environment-driven
- [ ] CI passes on all checks

## tdd plan

### tests for logging

```python
"""Tests for logging configuration."""

from __future__ import annotations

import logging

from stroke_deepisles_demo.core.logging import get_logger, setup_logging


class TestSetupLogging:
    """Tests for setup_logging."""

    def test_sets_log_level(self) -> None:
        """Sets the root logger level."""
        setup_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_format_styles(self) -> None:
        """Different format styles work."""
        for style in ["simple", "detailed", "json"]:
            setup_logging("INFO", format_style=style)
            # Should not raise


class TestGetLogger:
    """Tests for get_logger."""

    def test_returns_namespaced_logger(self) -> None:
        """Returns logger with stroke_demo prefix."""
        logger = get_logger("my_module")
        assert logger.name == "stroke_demo.my_module"
```

### tests for configuration

```python
"""Tests for configuration."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from stroke_deepisles_demo.core.config import Settings, reload_settings


class TestSettings:
    """Tests for Settings."""

    def test_default_values(self) -> None:
        """Has sensible defaults."""
        settings = Settings()
        assert settings.log_level == "INFO"
        assert settings.hf_dataset_id == "YongchengYAO/ISLES24-MR-Lite"

    def test_env_override(self, monkeypatch) -> None:
        """Environment variables override defaults."""
        monkeypatch.setenv("STROKE_DEMO_LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_hf_token_hidden_from_repr(self) -> None:
        """HF token is not visible in repr."""
        settings = Settings(hf_token="secret123")
        assert "secret123" not in repr(settings)

    def test_results_dir_created(self, tmp_path: Path) -> None:
        """Results directory is created if it doesn't exist."""
        new_dir = tmp_path / "new_results"
        settings = Settings(results_dir=new_dir)
        assert new_dir.exists()
```

## "done" criteria

Phase 5 is complete when:

1. Structured logging is in place throughout
2. All settings are configurable via environment
3. README.md and CONTRIBUTING.md are complete
4. Developer guides are written
5. CI workflow passes on GitHub Actions
6. Code coverage > 80% overall
7. All code review checklist items pass
8. Repository is ready for others to contribute

## final deliverables

At the end of all phases, the repository contains:

```
stroke-deepisles-demo/
├── .github/
│   └── workflows/
│       └── ci.yml
├── docs/
│   ├── specs/
│   ├── guides/
│   └── reference/
├── src/
│   └── stroke_deepisles_demo/
│       ├── core/
│       ├── data/
│       ├── inference/
│       ├── ui/
│       ├── pipeline.py
│       ├── metrics.py
│       └── cli.py
├── tests/
├── pyproject.toml
├── uv.lock
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .pre-commit-config.yaml
├── .gitignore
├── .env.example
└── app.py                  # HF Spaces entry point
```
