"""Audit log middleware — records mutating API calls to audit_log table."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import jwt

logger = logging.getLogger(__name__)

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
SKIP_PATHS = frozenset({"/health", "/metrics"})

class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log all mutating API requests to audit_log table."""

    async def dispatch(self, request: Request, call_next):
        if request.method not in MUTATING_METHODS:
            return await call_next(request)
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)

        # Extract user_id from JWT (best-effort, don't fail request)
        user_id = None
        org_id = None
        try:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                from ..auth.utils import SECRET_KEY, ALGORITHM
                payload = jwt.decode(auth[7:], SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("sub")
                org_id = payload.get("org_id")
        except Exception:
            pass  # anonymous request or invalid token — still log

        # Write to DB async (fire and forget — don't block response)
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
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ip": request.client.host if request.client else None,
                    "dur": duration_ms,
                    "ts": datetime.now(timezone.utc),
                })
        except Exception as e:
            logger.warning("audit_log write failed: %s", e)  # never break the request

        return response
