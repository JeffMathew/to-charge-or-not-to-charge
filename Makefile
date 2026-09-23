.PHONY: install lint test build clean

install:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

build:
	uv build

clean:
	rm -rf dist .pytest_cache .ruff_cache
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '*.egg-info' -exec rm -rf {} +
