# ADR 002: Short hex IDs, configurable length

**Status:** Accepted

## Context
Product requirement: links like `sher.io/a3f9c` (4-5 hex chars). That is 65,536 (4) or about
1,048,576 (5) possible IDs.

## Decision
Generate IDs with `secrets` (not `random`). Make length configurable (4-8, default 5). Reserve with
`SET NX` and retry on collision. Rate limit reads per IP, and return an identical 404 for missing,
expired and malformed IDs.

## Consequences
- Collisions are handled atomically. Probability stays small because few shares are live at once.
- Brute force is **mitigated, not prevented**. A distributed attacker can scan a 5-char space.
  Recommend 6+ chars for anything sensitive. This is documented in SECURITY.md.
- Raising the length is a config change with no migration.
