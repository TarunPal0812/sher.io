# Changelog

Format: [Keep a Changelog](https://keepachangelog.com), versioning: [SemVer](https://semver.org).

## [1.1.0] - 2026-11-25
### Changed
- Migrated to uv (`pyproject.toml` + `uv.lock`), `fastapi[standard]`, `fastapi` CLI entrypoint `app/asgi.py`.
- Dockerfile and CI use `uv sync --locked`.

## [1.0.0] - 2026-11-25
### Added
- Text and file shares with 5 or 10 minute lifetimes and short hex links.
- Redis TTL-based expiry, disk file storage, background orphan sweeper.
- Rate limiting, security headers, CSP-safe frontend, health/readiness probes.
- Docker Compose stack (API, Redis, nginx), CI pipeline, full documentation.
