"""Faza 16 — Audit Log router."""
from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Query

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/audit", tags=["audit"])


@router.get("")
def list_audit(
    user: AuthUser,
    tender_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """Historia operacji z audit_log."""
    engine = get_engine()
    tenant_id = user.org_id

    conditions = ["tenant_id = :tenant_id"]
    params: dict = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

    if tender_id:
        conditions.append("entity_id = :tender_id::uuid")
        params["tender_id"] = tender_id

    where = " AND ".join(conditions)

    with engine.connect() as conn:
        total = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM audit_log WHERE {where}"),
            {k: v for k, v in params.items() if k not in ("limit", "offset")},
        ).scalar() or 0

        rows = conn.execute(
            sa.text(
                f"""SELECT id, at, actor, action, entity, entity_id, detail
                   FROM audit_log
                   WHERE {where}
                   ORDER BY at DESC
                   LIMIT :limit OFFSET :offset"""
            ),
            params,
        ).fetchall()

    return {
        "items": [
            {
                "id": r.id,
                "at": r.at.isoformat() if r.at else None,
                "actor": r.actor,
                "action": r.action,
                "entity": r.entity,
                "entity_id": str(r.entity_id) if r.entity_id else None,
                "detail": r.detail if isinstance(r.detail, dict) else {},
            }
            for r in rows
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }
