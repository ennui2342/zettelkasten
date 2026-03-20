.PHONY: install test test-fast lint shell

## Install all dependencies (including dev, anthropic, voyage extras) into a uv-managed venv
install:
	uv sync --extra dev --extra anthropic --extra voyage

## Run the full test suite
test:
	uv run pytest

## Run tests — stop on first failure
test-fast:
	uv run pytest -x -q

## Open a Python REPL in the project environment
shell:
	uv run python

serve:
	uv run --env-file .env zettelkasten serve
