"""Rate limiting middleware — sliding window per IP + per API key.

Configurable via app_config 'rate_limit' key:
  {requests_per_minute: 60, burst: 10, whitelist_ips: [...]}
"""
from __future__ import annotations

import time
import logging
from collections import defaultdict
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter — per IP, in-memory."""

    def __init__(self, app, requests_per_minute: int = 120, burst: int = 20):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst = burst
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._whitelist = {"127.0.0.1", "::1", "localhost"}

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, ip: str) -> tuple[bool, int]:
        now = time.time()
        window = self._windows[ip]

        # Cleanup old entries (older than 60s)
        cutoff = now - 60
        window[:] = [t for t in window if t > cutoff]

        # Check limit
        if len(window) >= self.rpm:
            retry_after = int(60 - (now - window[0]))
            return True, max(retry_after, 1)

        # Check burst (last 1s)
        recent = [t for t in window if t > now - 1]
        if len(recent) >= self.burst:
            return True, 1

        window.append(now)
        return False, 0

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip health checks and whitelisted IPs
        if request.url.path in ("/api/v2/health", "/health", "/"):
            return await call_next(request)

        ip = self._get_client_ip(request)
        if ip in self._whitelist:
            return await call_next(request)

        limited, retry_after = self._is_rate_limited(ip)
        if limited:
            logger.warning(f"Rate limit hit: {ip} on {request.url.path}")
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.rpm),
                },
            )

        response = await call_next(request)
        remaining = self.rpm - len(self._windows[ip])
        response.headers["X-RateLimit-Remaining"] = str(max(remaining, 0))
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Add X-Response-Time header to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
        return response
