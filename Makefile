.PHONY: venv up down sample-data index-sample serve lint test

venv:
	@if [ ! -d .venv ]; then \
		echo "Initializing virtual environment (.venv)..."; \
		python3 -m venv .venv; \
		.venv/bin/python -m ensurepip --upgrade; \
	fi
	@if [ ! -f .venv/bin/uvicorn ]; then \
		echo "Installing project dependencies..."; \
		.venv/bin/python -m pip install -e .; \
	fi

up:
	docker compose up -d --wait

down:
	docker compose down

sample-data: venv
	PYTHONPATH=src .venv/bin/python -c "print('Sample corpus generation placeholder')"

index-sample: venv
	PYTHONPATH=src .venv/bin/python -c "print('Indexing sample corpus...')"

serve: venv
	PYTHONPATH=src .venv/bin/uvicorn evidencelens.api.main:app --reload --reload-dir src --port 8000

lint: venv
	.venv/bin/ruff check .
	.venv/bin/mypy src

test: venv
	PYTHONPATH=src .venv/bin/pytest