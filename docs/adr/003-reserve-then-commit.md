# ADR 003: Reserve the Redis key before committing the file

**Status:** Accepted

## Context
A file upload touches Redis and disk. A crash between the two could leave inconsistent state.

## Decision
1. Stream upload to `.tmp/<uuid>`.
2. Reserve `share:<id>` in Redis.
3. Atomically `os.replace` the temp file to `<id>`.
4. Roll back the key and temp file if step 3 fails.

## Consequences
- Every committed file has a key, so "file without key" is always garbage and the sweeper can
  delete it without racing uploads.
- A reader can fetch metadata in the instant between steps 2 and 3; the download then returns 404.
  This window is milliseconds and acceptable because the link isn't returned to the uploader yet.
- A crash leaves only temp files or a key without a file; both self-heal (sweeper / TTL).
