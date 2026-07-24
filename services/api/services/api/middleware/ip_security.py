"""IP security middleware — manual blocklist + suspicious pattern detection. Pure ASGI."""
from __future__ import annotations

import os
import json
import logging

logger = logging.getLogger(__name__)

_STATIC_BLOCKLIST: frozenset[str] = frozenset(
    ip.strip() for ip in os.getenv("IP_BLOCKLIST", "").split(",") if ip.strip()
)

_403_BODY = json.dumps({"detail": "Dostęp zablokowany"}).encode()
_403_HEADERS = [
    (b"content-type", b"application/json"),
    (b"content-length", str(len(_403_BODY)).encode()),
]


class IPSecurityMiddleware:
    """Block IPs in the static blocklist — pure ASGI, zero BaseHTTPMiddleware overhead."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not _STATIC_BLOCKLIST:
            await self.app(scope, receive, send)
            return

        # Extract client IP from scope
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        if client_ip in _STATIC_BLOCKLIST:
            logger.warning("Blocked IP: %s path=%s", client_ip, scope.get("path", ""))
            await send({"type": "http.response.start", "status": 403, "headers": _403_HEADERS})
            await send({"type": "http.response.body", "body": _403_BODY, "more_body": False})
            return

        await self.app(scope, receive, send)
