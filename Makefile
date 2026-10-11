up:
	docker compose up -d --wait

down:
	docker compose down

sample-data:
	python3 -c "print('Sample corpus generation placeholder')"

index-sample:
	python3 -c "print('Indexing sample corpus...')"

serve:
	uvicorn src.evidencelens.api.main:app --reload --port 8000

lint:
	uv run ruff check .
	uv run mypy src

test:
	uv run pytest
