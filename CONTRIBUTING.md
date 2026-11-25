# Contributing

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv sync          # creates .venv and installs locked dependencies
```

Dependencies are managed only with uv. Don't use `pip` or `requirements.txt`.

| Task | Command |
|---|---|
| Add dependency | `uv add <pkg>` (dev: `uv add --dev <pkg>`) |
| Upgrade all | `uv lock --upgrade && uv sync` |
| Run dev server | `uv run fastapi dev app/asgi.py` |

Commit `uv.lock` with any dependency change.

## Workflow

1. Branch from `main`.
2. Make the change with tests.
3. `make lint && make test` (or `uv run ruff check . && uv run pytest`) must pass (CI enforces lint and 85% coverage).
4. Open a PR describing *why*, not just *what*. Update docs and `CHANGELOG.md` for user-visible changes.

## Standards

- Python 3.12+, type hints on public functions, `ruff` clean.
- Routers stay thin; logic lives in `app/services/`.
- Never trust client-supplied filenames or IDs. Validate with `is_valid_id` and `sanitize_filename`.
- Never log share content.
- New endpoints need: rate limiting, uniform error shape, tests (happy path, validation, expiry).
- Significant design changes get an ADR in `docs/adr/`.

## Testing notes

Tests use `fakeredis` and an `httpx.AsyncClient` over `ASGITransport`, so no external services are
needed. Expiry is tested by shortening a key's TTL (`pexpire`) rather than waiting minutes.
