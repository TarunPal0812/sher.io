# Architecture

## Overview

```
 Browser ──HTTPS──> nginx ──> FastAPI (fastapi run) ──> Redis   (text, metadata, TTL)
                                   │
                                   └──────────────> Disk    (file bytes, named by ID)
```

One stateless API process type. All shared state is in Redis and the storage directory, so
the API can be restarted freely.

## Components

| Path | Responsibility |
|---|---|
| `app/main.py` | App factory, middleware (security headers, request logging), lifespan |
| `app/config.py` | Typed settings from `SHER_*` environment variables |
| `app/routers/share.py` | Create shares (text, file) |
| `app/routers/view.py` | Read shares, download, serve HTML pages |
| `app/routers/health.py` | `/healthz`, `/readyz` |
| `app/services/store.py` | Redis operations; atomic ID reservation |
| `app/services/files.py` | Streaming upload, commit, delete, filename sanitising |
| `app/services/cleanup.py` | Background sweeper |
| `app/deps.py` | Dependencies, client IP, Redis-backed rate limiter |
| `app/static/` | Frontend (no build step) |

## Data model

Redis key `share:<id>` holds JSON with a TTL equal to the share's lifetime:

```json
{ "type": "text|file", "content": "..."|null, "filename": "..."|null,
  "size": 123, "expires_at": "2026-11-25T10:05:00Z" }
```

Disk: `<storage_dir>/<id>` for file bytes; `<storage_dir>/.tmp/` for in-flight uploads.
Rate limit keys: `rl:<scope>:<ip>:<minute-bucket>` with a short TTL.

## Request flows

### Create text
1. Validate TTL, non-empty, size cap.
2. `SET share:<id> <json> NX EX <ttl>`. On a collision, retry with a new ID (5 attempts, then `503`).
3. Return the link.

### Create file
1. Reject early if `Content-Length` is far over the cap.
2. Stream to `.tmp/<uuid>` in 1 MB chunks, aborting past the cap.
3. **Reserve the Redis key**, then `os.replace` the temp file to `<id>`.
4. On any failure after step 2, remove the temp file and the key.

The order in step 3 matters: a file on disk always has a Redis key, so the sweeper can
treat "file without key" as garbage without racing live uploads.

### Read / download
1. Validate ID format (`^[0-9a-f]{4,8}$`), then `GET share:<id>`.
2. Missing, expired or malformed all return the same `404`.
3. Downloads re-check Redis before streaming, so a file that outlives its key by a few
   seconds (sweeper interval) is still unreachable.

## Failure modes

| Failure | Behaviour |
|---|---|
| Redis down | `readyz` fails (503), create/read return 500; nothing is lost that wasn't ephemeral |
| Disk full or unwritable | File create returns 500 `storage_error`; key is rolled back |
| API crash mid-upload | Orphan temp file; removed by the sweeper after 10 min |
| Redis restart | All shares vanish (no persistence, by design); orphan files swept |
| Sweeper crash | Logged and retried next interval; correctness unaffected |

## Scaling

- Vertical first: the workload is I/O bound and small.
- Multiple API replicas need **shared file storage** (S3/R2 or a shared volume).
  See [DEPLOYMENT.md](DEPLOYMENT.md#scaling-out).
