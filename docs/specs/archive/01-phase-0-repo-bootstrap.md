# phase 0: repo bootstrap

## purpose

Set up the foundational project structure with 2025 Python best practices. At the end of this phase, we have a working skeleton that can be installed, linted, type-checked, and tested (even if tests are empty).

## deliverables

- [ ] `pyproject.toml` with uv + hatchling backend
- [ ] `src/stroke_deepisles_demo/` package structure
- [ ] `tests/` directory with pytest configuration
- [ ] Development tooling: ruff, mypy, pre-commit
- [ ] Basic `README.md` with clinical disclaimer
- [ ] `.gitignore` updates if needed

## repo structure

```
stroke-deepisles-demo/
├── pyproject.toml              # Project metadata, deps, tool config
├── uv.lock                     # Locked dependencies (auto-generated)
├── .python-version             # Python version (3.12)
├── README.md                   # Project overview + disclaimer
├── .gitignore                  # Standard Python ignores
├── .pre-commit-config.yaml     # Pre-commit hooks
│
├── src/
│   └── stroke_deepisles_demo/
│       ├── __init__.py         # Package version, exports
│       ├── py.typed            # PEP 561 marker
│       │
│       ├── core/               # Shared utilities
│       │   ├── __init__.py
│       │   ├── config.py       # Pydantic settings (stub)
│       │   ├── types.py        # Shared type definitions (stub)
│       │   └── exceptions.py   # Custom exceptions (stub)
│       │
│       ├── data/               # Data loading (stub)
│       │   └── __init__.py
│       │
│       ├── inference/          # DeepISLES integration (stub)
│       │   └── __init__.py
│       │
│       └── ui/                 # Gradio app (stub)
│           └── __init__.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures
│   └── test_package.py         # Smoke test: package imports
│
└── docs/
    └── specs/                  # These spec documents
        ├── 00-context.md
        ├── 01-phase-0-repo-bootstrap.md
        └── ...
```

## pyproject.toml specification

```toml
[project]
name = "stroke-deepisles-demo"
version = "0.1.0"
description = "Demo: HF datasets + DeepISLES stroke segmentation + Gradio visualization"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Medical Science Apps.",
]
keywords = ["stroke", "neuroimaging", "segmentation", "BIDS", "NIfTI", "deep-learning"]

dependencies = [
    # Core - pinned to Tobias's fork for BIDS + NIfTI lazy loading
    "datasets @ git+https://github.com/CloseChoice/datasets.git@feat/bids-loader-streaming-upload-fix",
    "huggingface-hub>=0.25.0",

    # NIfTI handling
    "nibabel>=5.2.0",
    "numpy>=1.26.0",

    # Configuration
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",

    # UI (Gradio 5.x)
    "gradio>=5.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "mypy>=1.8.0",
    "ruff>=0.8.0",
    "pre-commit>=3.6.0",
    # Type stubs
    "types-requests",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/stroke_deepisles_demo"]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "mypy>=1.8.0",
    "ruff>=0.8.0",
    "pre-commit>=3.6.0",
]

# ─────────────────────────────────────────────────────────────────
# Tool configurations
# ─────────────────────────────────────────────────────────────────

[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "PTH",    # flake8-use-pathlib
    "RUF",    # ruff-specific
]
ignore = [
    "E501",   # line too long (handled by formatter)
]

[tool.ruff.lint.isort]
known-first-party = ["stroke_deepisles_demo"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = [
    "nibabel.*",
    "gradio.*",
    "datasets.*",
    "niivue.*",
]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
]
markers = [
    "integration: marks tests requiring external resources (Docker, network)",
    "slow: marks tests that take >10s to run",
]
filterwarnings = [
    "ignore::DeprecationWarning",
]

[tool.coverage.run]
source = ["src/stroke_deepisles_demo"]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

## module stubs

### `src/stroke_deepisles_demo/__init__.py`

```python
"""stroke-deepisles-demo: HF datasets + DeepISLES + Gradio visualization."""

__version__ = "0.1.0"

__all__ = ["__version__"]
```

### `src/stroke_deepisles_demo/core/config.py`

```python
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
    deepisles_fast_mode: bool = True  # SEALS-only (ISLES'22 winner, no FLAIR needed)

    # Paths
    temp_dir: str | None = None

    class Config:
        env_prefix = "STROKE_DEMO_"
        env_file = ".env"


settings = Settings()
```

### `src/stroke_deepisles_demo/core/types.py`

```python
"""Shared type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


class CaseFiles(TypedDict):
    """Paths to NIfTI files for a single case."""

    dwi: Path
    adc: Path
    flair: Path | None
    ground_truth: Path | None


@dataclass(frozen=True)
class InferenceResult:
    """Result of running DeepISLES on a case."""

    case_id: str
    input_files: CaseFiles
    prediction_mask: Path
    elapsed_seconds: float
```

### `src/stroke_deepisles_demo/core/exceptions.py`

```python
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
```

## pre-commit configuration

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.5.0
          - pydantic-settings>=2.1.0
        args: [--config-file=pyproject.toml]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: [--maxkb=1000]
```

## tdd plan

### tests to write first

1. **`tests/test_package.py`** - Smoke test that package imports work

```python
"""Smoke tests for package structure."""

from __future__ import annotations


def test_package_imports() -> None:
    """Verify the package can be imported."""
    import stroke_deepisles_demo

    assert stroke_deepisles_demo.__version__ == "0.1.0"


def test_core_modules_import() -> None:
    """Verify core modules can be imported without side effects."""
    from stroke_deepisles_demo.core import config, exceptions, types

    assert config.settings is not None
    assert types.CaseFiles is not None
    assert exceptions.StrokeDemoError is not None


def test_subpackages_exist() -> None:
    """Verify subpackage structure exists."""
    from stroke_deepisles_demo import data, inference, ui

    # These are stubs, just verify they exist
    assert data is not None
    assert inference is not None
    assert ui is not None
```

### what to mock

- Nothing needed for Phase 0 - these are pure import tests

### what to test for real

- Package imports
- Module structure
- Type definitions load correctly
- Pydantic settings initialize with defaults

## "done" criteria

Phase 0 is complete when:

1. `uv sync` succeeds and creates virtual environment
2. `uv run pytest` passes all smoke tests
3. `uv run ruff check .` reports no errors
4. `uv run ruff format --check .` reports no changes needed
5. `uv run mypy src/` passes with no errors
6. `uv run pre-commit run --all-files` passes
7. Package can be imported: `uv run python -c "import stroke_deepisles_demo"`

## commands cheatsheet

```bash
# Initialize (if starting fresh)
uv init --package stroke-deepisles-demo

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy src/

# Install pre-commit hooks
uv run pre-commit install

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

## notes

- We use `hatchling` as the build backend (current uv default, stable)
- `uv_build` is newer but `hatchling` is battle-tested
- The `datasets` dependency is pinned to Tobias's fork via git URL
- Gradio 5.x for latest features (SSR, improved components)
- Python 3.11+ for modern typing features (`X | None` syntax)
