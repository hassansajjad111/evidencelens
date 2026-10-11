# Convenience commands for repeatable local setup, services, and quality checks.
# Run these targets from the repository root; `uv.lock` pins Python dependencies.
.PHONY: setup sync venv up down serve lint test compose-check check

# `setup` and the compatibility target `venv` converge on the same locked sync.
setup: sync

# Install/synchronize project and development dependencies from uv.lock.
sync:
	uv sync --locked

# Retained so older notes using `make venv` keep working; uv owns the venv.
venv: sync

# Start the three local databases and wait until their health checks pass.
up:
	docker compose up -d --wait

# Stop containers but preserve named Docker volumes and the local Neo4j directory.
down:
	docker compose down

# Run the ASGI app with src-layout imports and hot reload for local development.
serve: venv
	PYTHONPATH=src uv run --locked uvicorn evidencelens.api.main:app --reload --reload-dir src --port 8000

# Static style and type checks.
lint: venv
	uv run --locked ruff check .
	uv run --locked mypy src

# Fast unit tests; integration tests should be marked separately when added.
test: venv
	uv run --locked pytest

# Parse Compose configuration without creating or restarting containers.
compose-check:
	docker compose config --quiet

# One command gate used before committing: lint, type-check, tests, Compose parse.
check: lint test compose-check