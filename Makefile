.PHONY: install lint test test-slow build plots results clean

install:
	uv sync

lint:
	uv run ruff check .

test:
	uv run pytest

test-slow:
	uv run pytest -m slow -v

build:
	uv build

plots:
	uv run python -m battery_dispatch.plotting

results:
	uv run python -m battery_dispatch.single_market

clean:
	rm -rf dist .pytest_cache .ruff_cache
	find . -name '__pycache__' -exec rm -rf {} +
	find . -name '*.egg-info' -exec rm -rf {} +
