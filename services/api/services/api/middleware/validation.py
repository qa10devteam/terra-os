"""Faza 62 — Input validation middleware.

- Rejects requests with Content-Length > 10 MB
- Provides sanitize helper for string payloads
"""
from __future__ import annotations

import re

from fastapi import Request
from fastapi.responses import JSONResponse

_MAX_BODY_BYTES = 10 * 1024 * 1024  # 10 MB
_HTML_TAG_RE = re.compile(r"<[^>]+>")


async def validate_request(request: Request, call_next):
    """FastAPI middleware: enforce max body size for write methods."""
    if request.method in ("POST", "PUT", "PATCH"):
        content_length_header = request.headers.get("content-length", "0")
        try:
            content_length = int(content_length_header)
        except ValueError:
            content_length = 0

        if content_length > _MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"error": "Request too large", "max_bytes": _MAX_BODY_BYTES},
            )

    response = await call_next(request)
    return response


def strip_html(value: str) -> str:
    """Remove HTML tags from a string."""
    return _HTML_TAG_RE.sub("", value).strip()
