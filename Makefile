.PHONY: install test lint format check all

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

check:
	uv run mypy src/ tests/

all: lint check test
