"""Audit log middleware — records mutating API calls to audit_log table. Pure ASGI."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MUTATING_METHODS = frozenset({b"POST", b"PUT", b"PATCH", b"DELETE"})
SKIP_PATHS = frozenset({b"/health", b"/metrics"})


def _extract_jwt_user(headers: list) -> tuple[str | None, str | None]:
    """Best-effort: extract user_id, org_id from Bearer JWT."""
    for k, v in headers:
        if k.lower() == b"authorization" and v.startswith(b"Bearer "):
            try:
                import jwt as _jwt
                from ..auth.utils import SECRET_KEY, ALGORITHM
                payload = _jwt.decode(v[7:].decode(), SECRET_KEY, algorithms=[ALGORITHM])
                return payload.get("sub"), payload.get("org_id")
            except Exception:
                return None, None
    return None, None


def _write_audit_async(user_id, org_id, method, path, status, ip, duration_ms):
    """Fire-and-forget DB write — runs in thread pool to not block event loop."""
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO audit_log (user_id, org_id, method, path, status_code, ip, duration_ms, ts)
                VALUES (:uid, :org, :method, :path, :status, :ip, :dur, :ts)
                ON CONFLICT DO NOTHING
            """), {
                "uid": user_id,
                "org": org_id,
                "method": method,
                "path": path,
                "status": status,
                "ip": ip,
                "dur": duration_ms,
                "ts": datetime.now(timezone.utc),
            })
    except Exception as e:
        logger.debug("audit_log write failed: %s", e)


class AuditLogMiddleware:
    """Log all mutating API requests to audit_log table — pure ASGI."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", b"").upper()
        if isinstance(method, str):
            method = method.encode()

        path = scope.get("path", b"")
        if isinstance(path, str):
            path_b = path.encode()
        else:
            path_b = path

        if method not in MUTATING_METHODS or path_b in SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers", [])
        user_id, org_id = _extract_jwt_user(headers)

        # Skip unauthenticated (login, health) — tenant_id NOT NULL
        if user_id is None:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        ip = client[0] if client else None

        # Capture response status
        response_status = [200]

        async def send_capture(message):
            if message["type"] == "http.response.start":
                response_status[0] = message.get("status", 200)
            await send(message)

        t0 = time.perf_counter()
        await self.app(scope, receive, send_capture)
        duration_ms = int((time.perf_counter() - t0) * 1000)

        # Fire-and-forget DB write — offloaded to thread pool
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _write_audit_async,
                             user_id, org_id,
                             method.decode() if isinstance(method, bytes) else method,
                             path if isinstance(path, str) else path.decode(),
                             response_status[0], ip, duration_ms)
