"""Security helpers — RLS access control, OWASP basics.

Faza 61: RLS Hardening helpers
Faza 70: OWASP Top 10 checklist
"""
from __future__ import annotations

import re

from fastapi import HTTPException

from .auth.deps import CurrentUser


# ─── Faza 61: RLS Hardening ────────────────────────────────────────────────────

def require_org_access(resource_org_id: str, user: CurrentUser) -> None:
    """Raise 403 if user's org does not match resource's org.

    Use this before returning or modifying any org-scoped resource.
    All DB queries should also include WHERE org_id = :org_id for defence-in-depth.
    """
    if str(resource_org_id) != str(user.org_id):
        raise HTTPException(status_code=403, detail="Brak dostępu")


def require_user_access(resource_user_id: str, user: CurrentUser) -> None:
    """Raise 403 if resource owner != current user (unless admin/owner)."""
    if user.role in ("admin", "owner"):
        return
    if str(resource_user_id) != str(user.user_id):
        raise HTTPException(status_code=403, detail="Brak dostępu")


def require_admin(user: CurrentUser) -> None:
    """Raise 403 unless user has admin or owner role."""
    if user.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Wymagane uprawnienia administratora")


# ─── Faza 70: OWASP Top 10 Checklist ──────────────────────────────────────────
#
# A01 Broken Access Control:
#   ✓ require_org_access() / require_user_access() enforced per-resource
#   ✓ org_id / user_id filters in every DB query (WHERE org_id = :org_id)
#
# A02 Cryptographic Failures:
#   ✓ Passwords hashed with bcrypt (auth/utils.py)
#   ✓ JWT signed with HS256 + secret from env
#   ✓ HTTPS enforced via Caddy reverse proxy + HSTS header
#
# A03 Injection (SQL):
#   ✓ All queries use SQLAlchemy text() with :named parameters — never f-strings
#   ✓ No raw string interpolation in SQL
#
# A04 Insecure Design:
#   ✓ Auth endpoints rate-limited (10 req/min) via slowapi
#   ✓ Refresh token rotation on every use
#
# A05 Security Misconfiguration:
#   ✓ Security headers middleware (X-Frame-Options, CSP, HSTS etc.)
#   ✓ docs_url disabled in production (ENVIRONMENT != dev)
#   ✓ CORS restricted in production
#
# A06 Vulnerable Components:
#   TODO: add pip-audit / dependabot to CI pipeline
#
# A07 Auth Failures:
#   ✓ JWT in Authorization header only (never in URL params)
#   ✓ Token expiry enforced; refresh tokens revoked on use
#   ✓ Brute-force protection via rate limiting on /auth/* endpoints
#
# A08 Software & Data Integrity:
#   ✓ No untrusted deserialization; only Pydantic-validated inputs
#
# A09 Security Logging:
#   ✓ Audit log table; request counter middleware
#   TODO: ship logs to SIEM / alerting
#
# A10 SSRF:
#   ✓ No user-controlled URLs used in server-side HTTP calls (yet)
#   TODO: allowlist when BZP scraper is added


# ─── Input sanitization ────────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_RE = re.compile(r"javascript:", re.IGNORECASE)


def sanitize_string(value: str, max_length: int = 10_000) -> str:
    """Strip HTML tags and dangerous protocols from user-supplied strings."""
    if not isinstance(value, str):
        return value
    value = _HTML_TAG_RE.sub("", value)
    value = _SCRIPT_RE.sub("", value)
    return value[:max_length].strip()


def sanitize_dict(data: dict, fields: list[str] | None = None) -> dict:
    """Sanitize string fields in a dict in-place."""
    keys = fields if fields is not None else list(data.keys())
    for key in keys:
        if isinstance(data.get(key), str):
            data[key] = sanitize_string(data[key])
    return data
