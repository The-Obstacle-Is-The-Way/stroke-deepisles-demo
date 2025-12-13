.PHONY: install test test-integration test-all lint format check all clean

install:
	uv sync --extra api --extra gradio

test:
	uv run pytest

test-integration:
	@echo "Running integration tests (requires Docker, optional: local data)..."
	uv run pytest -m integration -v --timeout=600

test-all:
	@echo "Running all tests including integration..."
	uv run pytest -v --timeout=600

lint:
	uv run ruff check .

format:
	uv run ruff format .

check:
	uv run mypy src/ tests/

all: lint check test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache __pycache__ .coverage coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
