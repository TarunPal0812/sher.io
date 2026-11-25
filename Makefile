.PHONY: install dev test lint fmt lock upgrade up down
install:
	uv sync
dev:
	uv run fastapi dev app/asgi.py
test:
	uv run pytest --cov=app --cov-report=term-missing
lint:
	uv run ruff check .
fmt:
	uv run ruff check . --fix
lock:
	uv lock
upgrade:
	uv lock --upgrade && uv sync
up:
	docker compose up --build -d
down:
	docker compose down
