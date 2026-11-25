# Operations

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `SHER_BASE_URL` | `http://localhost:8000` | Public URL used in share links |
| `SHER_REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `SHER_STORAGE_DIR` | `storage` | File storage root (`.tmp/` is created inside) |
| `SHER_ID_LENGTH` | `5` | Hex ID length, 4-8 |
| `SHER_ALLOWED_TTLS` | `[5,10]` | Allowed lifetimes in minutes (JSON list) |
| `SHER_DEFAULT_TTL_MINUTES` | `5` | Must be in the allowed list |
| `SHER_MAX_TEXT_BYTES` | `102400` | Text cap |
| `SHER_MAX_FILE_BYTES` | `10485760` | File cap |
| `SHER_RATE_LIMIT_UPLOAD_PER_MIN` | `20` | Per IP |
| `SHER_RATE_LIMIT_VIEW_PER_MIN` | `60` | Per IP |
| `SHER_TRUST_PROXY` | `false` | Trust `X-Real-IP` for client IP |
| `SHER_CLEANUP_INTERVAL_SECONDS` | `30` | Sweeper period |
| `SHER_ENABLE_DOCS` | `false` | Expose `/api/docs` |
| `SHER_LOG_LEVEL` | `INFO` | |

## Logging

One line per request: `rid=<id> METHOD /path -> status latency`. The `rid` also appears in the
`X-Request-ID` response header, so a user-reported failure can be traced. The sweeper logs
`cleanup removed=N` when it deletes something. Content is never logged.

## What to monitor

| Signal | Alert when |
|---|---|
| `/readyz` | non-200 for 2 min |
| Disk usage of storage volume | above 70% |
| Redis memory | above 80% of `maxmemory` (with `noeviction`, writes fail at the cap) |
| 5xx rate | above 1% for 5 min |
| 429 rate | sudden spike (abuse or a misconfigured proxy making everyone look like one IP) |
| `cleanup failed` log lines | any repeated |

## Runbook

**Uploads return 500 `storage_error`**: check free space and permissions on the storage volume
(`df -h`, container user UID 10001 must own it).

**Everyone gets 429**: `SHER_TRUST_PROXY` is off behind a proxy, so all traffic appears to come
from the proxy's IP. Enable it and make sure nginx sets `X-Real-IP`.

**Files accumulate on disk**: confirm the sweeper logs run; check that Redis is reachable from
the API. Manual cleanup is safe for files with no matching `share:<id>` key.

**Redis restarted and shares vanished**: expected. There is no persistence.

**Links 404 immediately**: system clock skew between app and Redis hosts, or `expires_at` in the
past. Check NTP.
