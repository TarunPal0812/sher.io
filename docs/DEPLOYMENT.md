# Deployment

## Single host (Docker Compose)

```bash
git clone <repo> && cd sher
cp .env.example .env     # set SHER_BASE_URL to your public https URL, SHER_ID_LENGTH
docker compose up -d --build
```

The stack: `nginx` (port 80) → `api` (8000, internal) → `redis` (internal). Redis runs without
persistence and with a memory cap. Shares are meant to be lost on restart.

### TLS

Put TLS in front of nginx. Easiest options:
- **Caddy** or a cloud load balancer terminating TLS and forwarding to nginx on port 80.
- Or extend `nginx/default.conf` with `listen 443 ssl` and certbot certificates.

Set `SHER_BASE_URL=https://your-domain` so generated links are correct.

### Verify

```bash
curl -s localhost/healthz        # {"status":"ok"}
curl -s localhost/readyz         # {"status":"ready"}
curl -s -X POST localhost/api/v1/text -H 'Content-Type: application/json' -d '{"content":"hi"}'
```

## Sizing

A 1 vCPU / 1 GB host handles hundreds of concurrent shares. Disk need is roughly
`peak uploads per 10 min × average file size`. With the 10 MB cap and 20 uploads/min/IP,
monitor disk usage and alert at 70%.

## Scaling out

Multiple API replicas work with the Redis side unchanged, but **files must be on shared storage**:

1. Implement an `S3FileStorage` with the same methods as `FileStorage` (`save_upload`, `commit`,
   `delete`, `stored_ids`, a download path or presigned URL).
2. Use a bucket lifecycle rule (expire objects after 1 day) as a backstop to the sweeper.
3. For downloads, return a short-lived presigned URL (60 s) after the Redis check.
4. Use a managed Redis (ElastiCache, Upstash) if you need HA; remember a failover can drop
   recent shares.

## Upgrades

Stateless API: `docker compose up -d --build`. The image installs from `uv.lock` (`uv sync --locked`), so builds are reproducible. In-flight shares survive because
state is in Redis and on the volume. Roll back by redeploying the previous image tag.
