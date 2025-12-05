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
