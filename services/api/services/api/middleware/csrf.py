"""CSRF double-submit cookie protection middleware — Pure ASGI, Task 119.

Strategy:
  - Safe methods (GET, HEAD, OPTIONS) are always allowed.
  - Requests using Bearer token are exempted — browsers don't auto-attach Authorization headers.
  - Cookie-based sessions must send matching X-CSRF-Token header.
"""
from __future__ import annotations

import json

_SAFE_METHODS = frozenset({b"GET", b"HEAD", b"OPTIONS"})
_EXEMPT_PREFIXES = (
    b"/health",
    b"/api/v2/auth/login",
    b"/api/v2/auth/register",
    b"/api/v2/auth/refresh",
)

_403_BODY = json.dumps({"error": {"code": "CSRF_INVALID", "message": "CSRF token mismatch"}}).encode()
_403_HEADERS = [
    (b"content-type", b"application/json"),
    (b"content-length", str(len(_403_BODY)).encode()),
]


def _header_val(headers: list, name: bytes) -> bytes | None:
    """Extract first header value by name (case-insensitive)."""
    for k, v in headers:
        if k.lower() == name:
            return v
    return None


def _cookie_val(headers: list, name: bytes) -> bytes | None:
    """Extract a cookie value from Cookie header."""
    raw = _header_val(headers, b"cookie")
    if not raw:
        return None
    for part in raw.split(b";"):
        k, _, v = part.strip().partition(b"=")
        if k.strip() == name:
            return v.strip()
    return None


class CSRFMiddleware:
    """Double-submit cookie CSRF protection — pure ASGI."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", b"").upper()
        if isinstance(method, str):
            method = method.encode()

        # Safe methods — no check
        if method in _SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", b"")
        if isinstance(path, str):
            path = path.encode()

        # Exempt prefixes
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers", [])

        # Bearer token — not CSRF-vulnerable
        auth = _header_val(headers, b"authorization") or b""
        if auth.startswith(b"Bearer "):
            await self.app(scope, receive, send)
            return

        # Cookie-based: validate double-submit
        csrf_cookie = _cookie_val(headers, b"csrf_token") or b""
        csrf_header = _header_val(headers, b"x-csrf-token") or b""

        if csrf_cookie and csrf_cookie == csrf_header:
            await self.app(scope, receive, send)
            return

        if not csrf_cookie:
            # No session cookie — allow API clients
            await self.app(scope, receive, send)
            return

        # CSRF violation
        await send({"type": "http.response.start", "status": 403, "headers": _403_HEADERS})
        await send({"type": "http.response.body", "body": _403_BODY, "more_body": False})
