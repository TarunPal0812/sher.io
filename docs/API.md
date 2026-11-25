# API Reference

Base path: `/api/v1`. All responses are JSON except downloads. Interactive docs are available
at `/api/docs` when `SHER_ENABLE_DOCS=true`.

## Error format

```json
{ "error": { "code": "too_large", "message": "File is over the 10 MB limit." } }
```

| Status | Code | Meaning |
|---|---|---|
| 404 | `not_found` | Unknown, malformed or expired ID (deliberately indistinguishable) |
| 413 | `too_large` | Text or file over the limit |
| 422 | `validation_error`, `invalid_ttl`, `empty_content` | Bad input |
| 429 | `rate_limited` | Includes a `Retry-After` header |
| 500 | `storage_error` | Couldn't persist the file |
| 503 | `id_space_busy` | Couldn't reserve a free ID; retry |

## POST /api/v1/text

```bash
curl -X POST https://sher.io/api/v1/text \
  -H 'Content-Type: application/json' \
  -d '{"content": "hello", "ttl_minutes": 5}'
```

| Field | Type | Rules |
|---|---|---|
| `content` | string | Required, not blank, at most 100 KB (UTF-8 bytes) |
| `ttl_minutes` | int | `5` or `10`; default `5` |

`201`:
```json
{ "id": "a3f9c", "url": "https://sher.io/a3f9c",
  "expires_at": "2026-11-25T10:05:00Z", "ttl_seconds": 300 }
```

## POST /api/v1/file

```bash
curl -X POST https://sher.io/api/v1/file -F file=@report.pdf -F ttl_minutes=10
```

Multipart fields: `file` (required, non-empty, at most 10 MB), `ttl_minutes` (`5` or `10`).
Response is the same as for text.

## GET /api/v1/{id}

```bash
curl https://sher.io/api/v1/a3f9c
```

`200` (text):
```json
{ "id": "a3f9c", "type": "text", "content": "hello", "filename": null, "size": 5,
  "download_url": null, "expires_at": "2026-11-25T10:05:00Z", "seconds_remaining": 241 }
```

`200` (file): `type` is `"file"`, `content` is `null`, and `filename`, `size` and
`download_url` are set.

## GET /api/v1/{id}/download

Streams the file. Always sent as `Content-Type: application/octet-stream` with
`Content-Disposition: attachment`. Returns `404` for text shares or expired shares.

## GET /{id}

HTML page that renders the share. Returns `404` if the ID is not 4-8 lowercase hex characters.

## Ops

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness |
| `GET /readyz` | Readiness (Redis + storage writable); `503` with the failing parts |
