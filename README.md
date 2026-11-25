# sher.io

Ephemeral text and file sharing. Upload text or a file, get a short link such as
`https://sher.io/a3f9c`, and anyone with the link can open it for **5 or 10 minutes**.
After that it is deleted.

- **Backend:** FastAPI (`fastapi[standard]`), Python 3.12+, async end to end, managed with [uv](https://docs.astral.sh/uv/)
- **Storage:** Redis (text, metadata, expiry) + local disk (file bytes)
- **Frontend:** dependency-free HTML/CSS/JS served by the API, CSP-safe
- **Ops:** Docker Compose, nginx, health probes, CI

## Quick start

### With Docker

```bash
cp .env.example .env
docker compose up --build
# open http://localhost
```

### Local development

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) (it also installs Python 3.12 if needed).

```bash
uv sync                                         # creates .venv from uv.lock
docker run -d -p 6379:6379 redis:7-alpine       # or any local Redis
export SHER_REDIS_URL=redis://localhost:6379/0 SHER_STORAGE_DIR=./storage
uv run fastapi dev app/asgi.py                  # http://localhost:8000 (auto-reload)
uv run pytest                                   # no Redis needed: tests use fakeredis
```

`make dev`, `make test`, `make lint` wrap the same commands.

Set `SHER_ENABLE_DOCS=true` to expose interactive API docs at `/api/docs`.

## How it works

1. `POST /api/v1/text` or `/api/v1/file` reserves a random hex ID in Redis with
   `SET NX EX <ttl>` and returns the link.
2. Text lives inside the Redis value. Files are streamed to disk, named by ID only.
3. `GET /<id>` serves a small page that fetches `GET /api/v1/<id>` and renders the share.
4. When the Redis key expires the share is gone. A sweeper reclaims the file from disk.

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Documentation

| Doc | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data model, request flows, failure modes |
| [docs/API.md](docs/API.md) | Endpoints, schemas, errors, curl examples |
| [docs/SECURITY.md](docs/SECURITY.md) | Threat model, controls, known limits |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production setup, TLS, scaling, S3 migration |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Config reference, monitoring, runbook |
| [docs/adr/](docs/adr/) | Architecture decision records |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Dev workflow and standards |
| [agent.md](agent.md) | Instructions for AI coding agents working in this repo |

## Configuration (essentials)

| Variable | Default | Notes |
|---|---|---|
| `SHER_BASE_URL` | `http://localhost:8000` | Used to build share links |
| `SHER_REDIS_URL` | `redis://localhost:6379/0` | |
| `SHER_STORAGE_DIR` | `storage` | Must be writable |
| `SHER_ID_LENGTH` | `5` | 4-8; use 6+ in production |
| `SHER_TRUST_PROXY` | `false` | `true` only behind a proxy that sets `X-Real-IP` |

Full list in [docs/OPERATIONS.md](docs/OPERATIONS.md).

## License

MIT
