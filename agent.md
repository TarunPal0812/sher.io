# agent.md: instructions for AI coding agents

Read this fully before changing anything. Humans: see README.md and CONTRIBUTING.md.

## 1. What this project is

**sher.io**: anonymous, short-lived text and file sharing.

- A user uploads text or a file and gets a link like `https://sher.io/a3f9c`.
- The ID is lowercase hex, 4-8 characters (default 5, configurable).
- Anyone with the link can view it for **5 or 10 minutes**. Then it is permanently deleted.

## 2. Tech stack

| Concern | Choice |
|---|---|
| Language | Python 3.12+ |
| Package/project manager | **uv** (latest; 0.13.x at time of writing, update with `uv self update`) |
| Backend | **FastAPI** via `fastapi[standard]` (latest; includes the `fastapi` CLI, Uvicorn, httpx, python-multipart) |
| Temp store (text, metadata, expiry) | Redis, using key TTL |
| File storage | Local disk, named by share ID (swappable for S3/R2) |
| Settings | `pydantic-settings`, env vars prefixed `SHER_` |
| Tests | pytest, pytest-asyncio, fakeredis, httpx `ASGITransport` |
| Lint/format | ruff |
| Frontend | Static HTML/CSS/JS in `app/static/` (no build step) |

## 3. Tooling rules (uv only)

- Use **uv for everything**. Never use `pip install`, `python -m venv`, `poetry`, or hand-edited
  `requirements.txt`. Dependencies live in `pyproject.toml`; the lockfile `uv.lock` is committed.
- Always install `fastapi[standard]` (with the extra), never plain `fastapi`.
- Do not hard-pin versions by hand. Add with `uv add`, which resolves the latest compatible
  release and records it in `uv.lock`. Upgrade with `uv lock --upgrade`.

### Bootstrap (new checkout)

```bash
uv sync                      # creates .venv, installs everything from uv.lock (incl. dev group)
cp .env.example .env
docker run -d -p 6379:6379 redis:7-alpine
```

### Bootstrap (creating the project from scratch)

```bash
uv init --app --python 3.12 sher && cd sher
uv add "fastapi[standard]" redis pydantic-settings aiofiles
uv add --dev pytest pytest-asyncio pytest-cov fakeredis ruff
```

Note: `httpx` and `python-multipart` come with `fastapi[standard]`; don't add them separately.

### Daily commands

| Task | Command |
|---|---|
| Run dev server (reload) | `uv run fastapi dev app/asgi.py` |
| Run production-style | `uv run fastapi run app/asgi.py --port 8000` |
| Tests + coverage | `uv run pytest --cov=app --cov-report=term-missing` |
| Lint | `uv run ruff check .` |
| Auto-fix lint | `uv run ruff check . --fix` |
| Add dependency | `uv add <pkg>` (dev: `uv add --dev <pkg>`) |
| Upgrade all | `uv lock --upgrade && uv sync` |
| Update uv itself | `uv self update` |

Before finishing any task, `uv run ruff check . && uv run pytest` must pass.

### Required entrypoint file

The `fastapi` CLI discovers a module-level `app`. The codebase uses an app factory
(`create_app` in `app/main.py`), so keep this tiny file next to it:

```python
# app/asgi.py
from .main import create_app

app = create_app()
```

Tests must import `create_app` from `app.main` (never `app.asgi`), so importing during tests does
not create real settings or directories.

## 4. Project layout

```
pyproject.toml  uv.lock  .env.example  Dockerfile  docker-compose.yml
app/
  asgi.py               module-level `app` for the fastapi CLI
  main.py               create_app(): middleware, lifespan, routers
  config.py             Settings (SHER_* env vars)
  deps.py               dependencies, client IP, Redis rate limiter
  errors.py schemas.py
  routers/              share.py (create)  view.py (read/download/pages)  health.py
  services/             ids.py  store.py  files.py  cleanup.py
  static/               index.html view.html app.js view.js common.js app.css
tests/                  conftest.py + test_*.py
docs/                   ARCHITECTURE API SECURITY DEPLOYMENT OPERATIONS + adr/
```

## 5. Storage design (do not change without an ADR)

| Data | Where | Why |
|---|---|---|
| Text | Redis value, `SET key val NX EX ttl` | Auto-expires, no cleanup code |
| Metadata (type, filename, size, expires_at) | Same Redis JSON value | One atomic write |
| File bytes | `<storage_dir>/<id>` on disk | Keeps large blobs out of Redis RAM and SQL |

Never add a SQL database or store file bytes in Redis.

## 6. Architecture rules (hard constraints)

1. **Redis TTL is the source of truth for expiry.** Every read and download checks Redis first.
   Never serve a file just because it exists on disk.
2. **File commit order:** stream to `.tmp/<uuid>` → `store.reserve()` (SET NX) → `os.replace` to
   `<id>`. Roll back the key and temp file on failure. The sweeper relies on "file on disk implies
   a key exists".
3. **Files are named by share ID only.** The client filename is display metadata and must pass
   through `sanitize_filename`. Every ID from a URL must pass `is_valid_id` (`^[0-9a-f]{4,8}$`).
4. **Uploads are always served** as `application/octet-stream` with `Content-Disposition: attachment`
   and `nosniff`. Never render user content inline. Show text with `textContent`, never `innerHTML`.
5. **Uniform 404.** Missing, expired and malformed IDs return the identical body
   (`errors.not_found()`), including routing-level 404s.
6. **No inline scripts or styles** in HTML. CSP is `script-src 'self'; style-src 'self'`.
7. **Never log share content** or file bytes.
8. IDs come from `secrets` (never `random`). Collisions are handled by `SET NX` plus retry
   (5 attempts, then `503 id_space_busy`).
9. Uploads are streamed in 1 MB chunks and size-capped while streaming. Never `await file.read()`
   the whole body.
10. Routers stay thin. Logic goes in `app/services/`.
11. Config only via `app/config.py`. No hard-coded limits, TTLs, or URLs.
12. Error shape is always `{"error": {"code": "...", "message": "..."}}`.

## 7. API summary

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/text` | JSON `{content, ttl_minutes}` → `{id, url, expires_at, ttl_seconds}` |
| POST | `/api/v1/file` | multipart `file`, `ttl_minutes` → same response |
| GET | `/api/v1/{id}` | Share JSON (text content or file metadata + `download_url`) |
| GET | `/api/v1/{id}/download` | Stream the file as an attachment |
| GET | `/{id}` | HTML page for the share |
| GET | `/healthz`, `/readyz` | Liveness, readiness (Redis + storage) |

Limits (defaults): text 100 KB, file 10 MB, TTL 5 or 10 min, 20 uploads/min and 60 reads/min per IP.
Status codes: 404 not_found, 413 too_large, 422 validation, 429 rate_limited (with `Retry-After`),
500 storage_error, 503 id_space_busy.

## 8. Docker with uv

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/srv/.venv/bin:$PATH"
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
RUN useradd --system --uid 10001 sher && mkdir -p /data/storage && chown -R sher /data
COPY app ./app
USER sher
ENV SHER_STORAGE_DIR=/data/storage
EXPOSE 8000
CMD ["fastapi", "run", "app/asgi.py", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

- Always `uv sync --locked` in images and CI so builds fail if `uv.lock` is stale.
- Keep the `uv:0.13` tag current when uv's minor version moves.
- Compose stack: `redis` (no persistence, memory-capped), `api`, `nginx` (body cap 11 MB,
  sets `X-Real-IP`). Set `SHER_TRUST_PROXY=true` only behind a proxy that overwrites `X-Real-IP`.

## 9. CI (GitHub Actions)

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: astral-sh/setup-uv@v8
    with: { enable-cache: true }
  - run: uv sync --locked
  - run: uv run ruff check .
  - run: uv run pytest --cov=app --cov-fail-under=85
```

## 10. Testing conventions

- `client` fixture builds `create_app(settings, fakeredis)` over `httpx.ASGITransport`; storage uses
  `tmp_path`. No real Redis needed.
- Test expiry with `redis.pexpire(key, 100)` plus a short sleep, never minute-long waits.
- Patch `app.services.store.generate_id` to test collisions and exhaustion.
- New endpoint checklist: rate limiter dependency, uniform error shape, tests for success,
  validation failure and expiry, an entry in `docs/API.md`.
- Coverage floor is 85%.

## 11. Security reminders

- Short IDs are guessable in principle (5 hex ≈ 1M values). Mitigated by rate limits and uniform
  404, not eliminated. Production should set `SHER_ID_LENGTH>=6`.
- Starlette spools multipart bodies before handlers run, so nginx `client_max_body_size` is the
  real first-line cap. Do not remove it.
- No malware scanning or takedown flow exists yet. Don't claim otherwise in docs.
- Update `docs/SECURITY.md` whenever behavior changes; never weaken its claims silently.

## 12. Good next tasks

- Abuse handling: ClamAV scanning, report/takedown endpoint.
- `S3FileStorage` (same interface as `FileStorage`) for multi-replica deployments, with presigned
  download URLs and a bucket lifecycle rule as a backstop.
- Optional password-protected shares and one-time-view links.
- Prometheus metrics endpoint.
- Enforce the upload size cap before multipart spooling.

## 13. Don't

- Don't use `pip`, `requirements.txt`, or an unlocked install.
- Don't install plain `fastapi` without `[standard]`.
- Don't commit `.env`, `storage/`, or `.venv/`. Do commit `uv.lock`.
- Don't add inline scripts/styles, `innerHTML` for user content, or inline file rendering.
- Don't bypass `is_valid_id` or `sanitize_filename`.
