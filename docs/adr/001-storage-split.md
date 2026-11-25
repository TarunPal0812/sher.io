# ADR 001: Redis for text and metadata, disk for file bytes

**Status:** Accepted

## Context
Shares live 5-10 minutes. We must decide where text and files are stored.

## Options
1. Everything in a relational DB: needs our own expiry job; blobs bloat tables and backups.
2. Everything in Redis: native TTL, but 10 MB files consume RAM and are costly to scale.
3. **Redis for text and metadata, disk (later object storage) for file bytes.**

## Decision
Option 3. Redis TTL is the single source of truth for expiry. Files are named by share ID on
disk, and a sweeper deletes files with no live key.

## Consequences
- No expiry logic to write for text; very low latency.
- Two stores to keep consistent: handled by reserve-then-commit ordering (ADR 003).
- Horizontal scaling needs shared or object storage for files.
