# Security

## Model

sher.io is an **anonymous, link-based** service. Possession of the link is the only access
control. Treat everything shared as potentially readable by anyone who obtains or guesses the link.

### Assets
User-shared text and files for up to 10 minutes; service availability; the host's disk.

### Threats and controls

| Threat | Control |
|---|---|
| Guessing IDs | Random IDs from `secrets`; per-IP rate limit on reads; uniform 404; configurable length (see ADR 002) |
| XSS via text | Rendered with `textContent` only; strict CSP (`script-src 'self'`, no inline) |
| XSS / drive-by via uploaded HTML/SVG | Always `application/octet-stream` + `attachment` + `nosniff`; never rendered |
| Path traversal | Files named by validated ID only; user filename is display-only and sanitised |
| Header injection via filename | Sanitised; Starlette encodes `Content-Disposition` per RFC 6266 |
| Storage exhaustion | Size caps (text 100 KB, file 10 MB), TTL ≤ 10 min, upload rate limit, nginx body cap |
| Memory exhaustion | Uploads streamed in 1 MB chunks, never held in RAM |
| Partial uploads | Temp-file-then-rename; stale temp files swept |
| Clickjacking | `X-Frame-Options: DENY`, CSP `frame-ancestors 'none'` |
| Referrer leakage of links | `Referrer-Policy: no-referrer`; share page has `noindex` |
| Caching of private content | `Cache-Control: no-store` on API responses |
| Log leakage | Content and bytes are never logged; request logs contain method, path, status, latency |

## Known limits (be honest with users)

1. **Short IDs are guessable in principle.** 5 hex chars is about 1M values. With a 10-minute
   lifetime and rate limiting the practical risk is low, but it is not zero, and a botnet
   can bypass per-IP limits. Use `SHER_ID_LENGTH=6` or more for sensitive deployments.
2. **No encryption at rest, no end-to-end encryption.** Redis and disk hold plaintext. If
   confidentiality matters, encrypt client-side before upload.
3. **Abuse content.** An anonymous host can be used to distribute malware or illegal content.
   v1 has no scanning or reporting flow; add one before running a public instance
   (abuse contact, ClamAV, takedown endpoint).
4. **Multipart parsing happens before size checks.** Starlette spools the upload before the
   handler runs. The nginx `client_max_body_size` is the real first line of defence;
   keep it in place.
5. **Rate limiting trusts `X-Real-IP` only when `SHER_TRUST_PROXY=true`.** If enabled without a
   proxy that overwrites the header, clients can spoof their IP.

## Hardening checklist for production

- [ ] TLS everywhere; HSTS at the edge
- [ ] `SHER_TRUST_PROXY=true` only behind nginx/LB that overwrites `X-Real-IP`
- [ ] `SHER_ID_LENGTH >= 6`
- [ ] Redis not exposed publicly; `requirepass` or private network
- [ ] Container runs as non-root, read-only root FS (see `docker-compose.yml`)
- [ ] Separate domain for the app if you later add any inline-rendering features
- [ ] Abuse contact and takedown process published
- [ ] Dependency updates automated (Dependabot/Renovate)

## Reporting vulnerabilities

Email the maintainers privately (add your security contact here) rather than opening a public issue.
