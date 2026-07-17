"""Faza 70 — OWASP Top 10 security audit file.

This file serves two purposes:
1. Documents the security posture of YU-NA against OWASP Top 10 2021
2. Provides runtime validators for string inputs

See also: security.py for RLS helpers and sanitization utilities.
"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════════════
# OWASP TOP 10 — 2021 SECURITY AUDIT CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════
#
# A01:2021 – Broken Access Control                                    STATUS: ✓
#   ✓ require_org_access() in security.py enforced per-resource
#   ✓ require_user_access() for user-owned resources
#   ✓ All DB queries filtered by org_id or user_id (parameterized)
#   ✓ Admin-only endpoints check role (require_admin)
#   ✓ DONE: Auth on all endpoints — JWT required, fail-closed (Faza 0)
#   ✓ DONE: IDOR cross-tenant fix — org_id scoped to JWT claim (Faza 1)
#   ✗ TODO: unit tests covering 403 on cross-org access
#
# A02:2021 – Cryptographic Failures                                   STATUS: ✓
#   ✓ Passwords hashed with bcrypt (work factor ≥ 12) in auth/utils.py
#   ✓ JWTs signed HS256 with SECRET_KEY from env (not hardcoded)
#   ✓ HTTPS enforced by Caddy (HSTS header added by SecurityHeadersMiddleware)
#   ✓ No sensitive data in logs or URLs
#   ✓ DONE: JWT secret fail-closed — app refuses to start without SECRET_KEY (Faza 0)
#   ✓ DONE: Hashed password reset tokens — bcrypt hash stored, not plaintext (Faza 1)
#   ✗ TODO: rotate JWT secret periodically
#
# A03:2021 – Injection (SQLi / command injection)                     STATUS: ✓
#   ✓ All DB queries: SQLAlchemy text() with :named_params — never f-strings
#   ✓ Input validated via Pydantic models before reaching DB layer
#   ✓ No dynamic SQL construction from user inputs
#   ✓ No shell commands executed with user-supplied data (subprocess uses lists)
#   ✓ DONE: XSS DOMPurify — frontend sanitization + CSP unsafe-eval removed (Faza 1)
#
# A04:2021 – Insecure Design                                          STATUS: ✓
#   ✓ Rate limiting on auth endpoints (10 req/min) via slowapi
#   ✓ Refresh token rotation (old token revoked on refresh)
#   ✓ GDPR account deletion available (Faza 69)
#   ✓ DONE: Rate limiting — per-user/IP sliding-window 100 req/min (Faza 1)
#   ✓ DONE: Session invalidation — refresh token revoked on logout/rotation (Faza 1)
#   ✓ DONE: 2FA — TOTP support added (Faza 2, parallel agent)
#
# A05:2021 – Security Misconfiguration                                STATUS: ✓
#   ✓ Security headers middleware: X-Frame-Options DENY, nosniff, HSTS, etc.
#   ✓ X-XSS-Protection: 0 (disabled — CSP is the modern replacement) (Faza 2)
#   ✓ Cache-Control: no-store on /api/v2/auth/* routes (Faza 2)
#   ✓ DONE: Swagger disabled in prod — docs_url=None when ENVIRONMENT=prod (Faza 1)
#   ✓ DONE: Redis password — REDIS_PASSWORD required in production config (Faza 1)
#   ✓ DONE: CORS hardening — restricted to known frontend origins (Faza 2, parallel agent)
#   ✓ DONE: IP blocklist — IPSecurityMiddleware blocks known malicious IPs (Faza 2, parallel agent)
#
# A06:2021 – Vulnerable and Outdated Components                       STATUS: ⚠
#   ✓ Dependencies pinned in pyproject.toml
#   ✗ TODO: add pip-audit / safety to CI pipeline
#   ✗ TODO: Dependabot / Renovate for automated dependency updates
#
# A07:2021 – Identification and Authentication Failures               STATUS: ✓
#   ✓ JWT in Authorization: Bearer *** (never in URL query params)
#   ✓ Token expiry enforced server-side
#   ✓ Brute-force protection: 10 req/min on /auth/* endpoints
#   ✓ is_active check on every login
#   ✓ DONE: 2FA — TOTP support added (Faza 2, parallel agent)
#   ✓ DONE: WebSocket auth — JWT validated on WS handshake (Faza 2, parallel agent)
#
# A08:2021 – Software and Data Integrity Failures                     STATUS: ✓
#   ✓ All input deserialized through Pydantic schemas (no pickle/eval)
#   ✓ API accepts only JSON body (Content-Type validated by validation middleware)
#   ✓ DONE: Error handling — global error boundary, no stack traces to client (Faza 1)
#
# A09:2021 – Security Logging and Monitoring Failures                 STATUS: ✓
#   ✓ DONE: Audit logging — AuditLogMiddleware records all mutating API calls (Faza 2)
#     (user_id, org_id, method, path, status_code, ip, duration_ms, ts)
#   ✓ Request counter in monitoring middleware
#   ✓ Structured JSON logs via JSONFormatter → Loki
#   ✗ TODO: alerting on repeated 401/403 errors
#   ✗ TODO: SIEM integration / log shipping to external sink
#
# A10:2021 – Server-Side Request Forgery (SSRF)                       STATUS: ✓
#   ✓ DONE: SSRF webhook guard — URL allowlist enforced for all outbound HTTP (Faza 1)
#   ✓ External HTTP calls (BZP scraper) use hardcoded base URLs
#
# ═══════════════════════════════════════════════════════════════════════════════
# FAZA 0 / 1 / 2 — COMPLETED SECURITY FIXES SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
#
# Faza 0 (baseline hardening):
#   ✓ DONE: Auth on all endpoints
#   ✓ DONE: JWT secret fail-closed
#
# Faza 1 (OWASP critical fixes):
#   ✓ DONE: IDOR cross-tenant fix
#   ✓ DONE: SSRF webhook guard
#   ✓ DONE: XSS DOMPurify
#   ✓ DONE: Rate limiting
#   ✓ DONE: CSP unsafe-eval removed
#   ✓ DONE: Redis password
#   ✓ DONE: Session invalidation
#   ✓ DONE: Hashed reset tokens
#   ✓ DONE: Swagger disabled in prod
#   ✓ DONE: Error handling
#
# Faza 2 (this release):
#   ✓ DONE: Audit logging (AuditLogMiddleware + migration 0027)
#   ✓ DONE: Security headers updated (X-XSS-Protection: 0, Cache-Control on auth)
#   ✓ DONE: 2FA / TOTP (parallel agent)
#   ✓ DONE: CORS hardening (parallel agent)
#   ✓ DONE: WebSocket auth (parallel agent)
#   ✓ DONE: IP blocklist (parallel agent)
#
# Remaining TODOs:
#   ✗ TODO: penetration testing (scheduled Q3 2026)
#   ✗ TODO: SOC2 Type II audit
#   ✗ TODO: pip-audit in CI
#   ✗ TODO: rotate JWT secret periodically
#   ✗ TODO: unit tests covering 403 on cross-org access
#   ✗ TODO: alerting on repeated 401/403 errors
#
# ═══════════════════════════════════════════════════════════════════════════════
# STRING INPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

import re

_MAX_STRING_LENGTH = 10_000
_HTML_RE = re.compile(r"<[^>]+>")
_JS_PROTO_RE = re.compile(r"javascript:", re.IGNORECASE)
_NULL_BYTE_RE = re.compile(r"\x00")
_PATH_TRAVERSAL_RE = re.compile(r"\.\./|\.\.\\")


def validate_string_input(value: str, field_name: str = "field", max_length: int = _MAX_STRING_LENGTH) -> str:
    """Validate and sanitize a user-supplied string.

    Raises ValueError if input is invalid.
    Returns sanitized string.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name}: expected string")

    if len(value) > max_length:
        raise ValueError(f"{field_name}: przekracza maksymalną długość {max_length} znaków")

    # Remove null bytes (can bypass filters)
    value = _NULL_BYTE_RE.sub("", value)

    # Block path traversal
    if _PATH_TRAVERSAL_RE.search(value):
        raise ValueError(f"{field_name}: niedozwolone sekwencje ścieżki")

    # Strip HTML tags and JS protocol
    value = _HTML_RE.sub("", value)
    value = _JS_PROTO_RE.sub("", value)

    return value.strip()


SECURITY_AUDIT_VERSION = "2.0"
LAST_REVIEWED = "2026-07-18"
