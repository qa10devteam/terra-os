"""Escalation log — GET /api/v2/escalation/log."""
from __future__ import annotations

import logging
from typing import Any, Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/escalation", tags=["escalation"])


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


@router.get("/log")
def get_escalation_log(
    user: AuthUser,
    db: DB,
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
) -> dict:
    """Return escalation log entries for the current tenant."""
    tid = str(user.org_id)
    try:
        filters = ["tenant_id = :tid"]
        params: dict = {"tid": tid, "limit": limit}
        if status:
            filters.append("status = :status")
            params["status"] = status
        where = " AND ".join(filters)
        rows = db.execute(
            text(
                f"SELECT id, type, title, status, created_at "
                f"FROM notifications WHERE {where} "
                f"AND type LIKE 'escalat%' "
                f"ORDER BY created_at DESC LIMIT :limit"
            ),
            params,
        ).fetchall()
        entries = [
            {
                "id": str(r.id),
                "type": r.type,
                "title": r.title,
                "status": r.status,
                "created_at": str(r.created_at),
            }
            for r in rows
        ]
    except Exception:
        # Table may not have escalation rows yet — return empty list gracefully
        entries = []
    return {"total": len(entries), "items": entries}
