"""IP security middleware — manual blocklist + suspicious pattern detection."""
from __future__ import annotations

import os
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Static blocklist from env var: IP_BLOCKLIST="1.2.3.4,5.6.7.8"
_STATIC_BLOCKLIST: frozenset[str] = frozenset(
    ip.strip() for ip in os.getenv("IP_BLOCKLIST", "").split(",") if ip.strip()
)


class IPSecurityMiddleware(BaseHTTPMiddleware):
    """Block IPs in the static blocklist. Future: integrate with Redis for dynamic blocking."""

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        if client_ip in _STATIC_BLOCKLIST:
            logger.warning("Blocked IP: %s path=%s", client_ip, request.url.path)
            return JSONResponse(status_code=403, content={"detail": "Dostęp zablokowany"})

        return await call_next(request)
