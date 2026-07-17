# Terra.OS Security

## OWASP Top 10 Status (2026-07-18 — updated through Faza 3)

| # | Vulnerability | Status | Notes |
|---|---|---|---|
| A01 | Broken Access Control | ✅ Mitigated | RLS + TenantMiddleware + auth deps; cross-tenant IDOR fixed (Faza 1) |
| A02 | Cryptographic Failures | ✅ Mitigated | HTTPS (Caddy), JWT HS256, bcrypt passwords; totp_secret Fernet-encrypted (Faza 3) |
| A03 | Injection | ✅ Mitigated | SQLAlchemy parameterized queries; SQL sort/filter allowlists (Faza 0) |
| A04 | Insecure Design | ✅ Mitigated | RFQ gate implemented, AI content gated; 2FA/TOTP (Faza 2) |
| A05 | Security Misconfiguration | ✅ Mitigated | CSP/HSTS via Caddy, non-root Docker; Docker network segmentation (Faza 3) |
| A06 | Vulnerable Components | ✅ Monitoring | pip-audit + npm audit in CI; dedicated security-audit job (Faza 3) |
| A07 | Auth Failures | ✅ Mitigated | JWT rotation, rate limit on auth endpoints; refresh TTL 30d→7d (Faza 3) |
| A08 | Software Integrity | ✅ Mitigated | Gitleaks + detect-secrets in CI; Docker image pinning (Faza 2) |
| A09 | Logging Failures | ✅ Mitigated | Structured JSON logs, audit_log table; full mutation audit middleware (Faza 2) |
| A10 | SSRF | ✅ Mitigated | External API calls gated; SSRF webhook guard with private IP blocklist (Faza 1) |

## Security Controls

### Authentication & Sessions
- **JWT** access tokens (60 min) + **refresh token rotation** (30 day, one-time-use)
- Tokens stored in DB (`refresh_tokens` table) with revocation support
- Passwords hashed with **bcrypt** (12 rounds)
- Rate limiting on auth endpoints via **slowapi** (10 req/min per IP)

### CSRF Protection (Task 119)
- **Double-submit cookie** pattern implemented in `middleware/csrf.py`
- Login/register set an `httpOnly=True` `session` cookie + a JS-readable `csrf_token` cookie
- State-changing requests (`POST/PUT/PATCH/DELETE`) must include matching `X-CSRF-Token` header
- Bearer-token based API calls are exempted (browsers never auto-send `Authorization`)

### Transport Security
- **HTTPS enforced** via Caddy reverse proxy
- HSTS header (`max-age=31536000; includeSubDomains`) set by `SecurityHeadersMiddleware`
- `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`

### Multi-Tenancy Isolation
- PostgreSQL **Row-Level Security** (RLS) scoped to `org_id`
- `TenantMiddleware` sets `app.current_tenant` on every request

### Dependency Scanning (Task 123)
- **pip-audit** runs on every CI push/PR and weekly (Monday 06:00 UTC)
- **npm audit** (`--audit-level=high`) runs for frontend dependencies
- Results are non-blocking (`|| true`) to avoid false positive blocks on informational advisories

### Secrets Detection (Task 122)
- **detect-secrets** baseline maintained at `.secrets.baseline`
- CI job fails when new secrets are detected compared to baseline

## Reporting

Security issues: **security@terra-os.pl** (placeholder — replace with real contact)

Please include:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact assessment
4. (Optional) Suggested fix

We aim to respond within **72 hours** and issue a fix within **14 days** for critical findings.

## Responsible Disclosure

If you discover a security vulnerability, please report it to: security@qa10.io

Do NOT open a public GitHub issue for security vulnerabilities.
We will respond within 48 hours and aim to release a fix within 7 days for critical issues.

## Security Fix History

| Date | Phase | Fix | CVSS |
|------|-------|-----|------|
| 2026-07-17 | Faza 0 | IDOR: TenantDep on all endpoints | 10.0 |
| 2026-07-17 | Faza 0 | JWT secret fail-closed | 9.8 |
| 2026-07-17 | Faza 0 | SQL injection allowlists (5 routers) | 9.1 |
| 2026-07-17 | Faza 0 | Demo mode disabled by default | 7.5 |
| 2026-07-17 | Faza 0 | Stripe webhook fail-closed | 7.5 |
| 2026-07-17 | Faza 1 | SSRF webhook guard (private IP blocklist) | 9.1 |
| 2026-07-17 | Faza 1 | Stored XSS — DOMPurify on all innerHTML | 8.6 |
| 2026-07-17 | Faza 1 | Cross-tenant IDOR — org_id filter in resources | 8.6 |
| 2026-07-17 | Faza 1 | Rate limiting on all auth endpoints | 7.3 |
| 2026-07-17 | Faza 1 | Session invalidation after password reset | 7.5 |
| 2026-07-17 | Faza 1 | Hashed reset tokens (SHA-256 in DB) | 7.5 |
| 2026-07-17 | Faza 1 | Redis requirepass | 7.0 |
| 2026-07-17 | Faza 1 | CSP: unsafe-eval removed | 7.2 |
| 2026-07-18 | Faza 2 | 2FA/TOTP — optional per user | 6.8 |
| 2026-07-18 | Faza 2 | Audit log middleware (all mutations) | 6.5 |
| 2026-07-18 | Faza 2 | CORS hardened (no wildcard *) | 6.1 |
| 2026-07-18 | Faza 2 | WebSocket JWT authentication | 7.5 |
| 2026-07-18 | Faza 2 | IP blocklist middleware (static) | 5.3 |
| 2026-07-18 | Faza 2 | Docker image pinning (no :latest in prod) | 5.0 |
| 2026-07-18 | Faza 3 | Column encryption (totp_secret via Fernet) | 6.5 |
| 2026-07-18 | Faza 3 | IDS — dynamic IP blocking on 401/403 burst | 7.0 |
| 2026-07-18 | Faza 3 | Docker network segmentation | 5.0 |
| 2026-07-18 | Faza 3 | pip-audit in CI (supply chain) | 5.0 |
| 2026-07-18 | Faza 3 | Refresh token TTL: 30d → 7d | 5.0 |
