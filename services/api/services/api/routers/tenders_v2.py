"""Faza 4 — API v2: Tenders router with cursor pagination, filtering, auth."""
from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser, get_current_user

router = APIRouter(prefix="/api/v2/tenders", tags=["tenders-v2"])


class TenderPatch(BaseModel):
    status: str | None = None


def _row_to_dict(row: Any) -> dict:
    return {
        "id": str(row.id),
        "title": row.title,
        "buyer": row.buyer,
        "cpv": list(row.cpv) if row.cpv else [],
        "voivodeship": row.voivodeship,
        "value_pln": float(row.value_pln) if row.value_pln else None,
        "deadline_at": row.deadline_at.isoformat() if row.deadline_at else None,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "url": row.url,
        "status": row.status,
        "match_score": float(row.match_score) if row.match_score else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


VALID_STATUSES = {
    "new", "matched", "watching", "analyzing", "estimated",
    "decided_go", "decided_nogo", "archived",
}


def _resolve_tenant_id(engine, org_id: str) -> str:
    """Resolve user org_id to the actual tenant_id via organizations table."""
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT tenant_id FROM organizations WHERE id = :org_id"),
            {"org_id": org_id}
        ).fetchone()
    if row and row.tenant_id:
        return str(row.tenant_id)
    # Fallback: org_id might itself be used as tenant_id (legacy)
    return org_id


@router.get("")
def list_tenders(
    user: AuthUser,
    cursor: str | None = Query(None, description="Cursor for pagination (opaque)"),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    cpv: str | None = Query(None, description="CPV prefix filter"),
    voivodeship: str | None = Query(None),
    value_min: float | None = Query(None),
    value_max: float | None = Query(None),
    deadline_before: str | None = Query(None),
) -> dict:
    """Lista przetargów z cursor pagination."""
    engine = get_engine()
    _org_id = user.org_id
    if not _org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Użytkownik nie należy do organizacji"})
    tenant_id = _resolve_tenant_id(engine, _org_id)

    conditions = ["tenant_id = :tenant_id", "status != 'archived'"]
    params: dict = {"tenant_id": tenant_id, "limit": limit + 1}

    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(
                status_code=422,
                detail={"error": "invalid_status", "message": f"Nieprawidłowy status: {status}"},
            )
        conditions[1] = "1=1"  # remove archived filter when explicit status given
        conditions.append("status = :status")
        params["status"] = status

    if cpv:
        conditions.append("EXISTS (SELECT 1 FROM unnest(cpv) c WHERE c LIKE :cpv_prefix)")
        params["cpv_prefix"] = cpv + "%"

    if voivodeship:
        conditions.append("voivodeship ILIKE :voivodeship")
        params["voivodeship"] = f"%{voivodeship}%"

    if value_min is not None:
        conditions.append("value_pln >= :value_min")
        params["value_min"] = value_min

    if value_max is not None:
        conditions.append("value_pln <= :value_max")
        params["value_max"] = value_max

    if deadline_before:
        conditions.append("deadline_at <= :deadline_before")
        params["deadline_before"] = deadline_before

    # Cursor decode
    cursor_condition = ""
    if cursor:
        try:
            cursor_data = json.loads(base64.b64decode(cursor).decode())
            cursor_created_at = cursor_data["created_at"]
            cursor_id = cursor_data["id"]
            cursor_condition = (
                "AND (created_at < :cursor_created_at OR "
                "(created_at = :cursor_created_at AND id < :cursor_id))"
            )
            params["cursor_created_at"] = cursor_created_at
            params["cursor_id"] = cursor_id
        except Exception:
            raise HTTPException(status_code=400, detail={"error": "invalid_cursor", "message": "Nieprawidłowy cursor"})

    where_clause = " AND ".join(conditions)

    with engine.connect() as conn:
        # Count total (bez cursor)
        count_params = {k: v for k, v in params.items() if k not in ("limit", "cursor_created_at", "cursor_id")}
        total = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM tender WHERE {where_clause}"),
            count_params,
        ).scalar() or 0

        rows = conn.execute(
            sa.text(
                f"""SELECT id, title, buyer, cpv, voivodeship, value_pln, deadline_at,
                          published_at, url, status, match_score, created_at
                   FROM tender
                   WHERE {where_clause} {cursor_condition}
                   ORDER BY created_at DESC, id DESC
                   LIMIT :limit"""
            ),
            params,
        ).fetchall()

    items = [_row_to_dict(r) for r in rows[:limit]]
    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        cursor_data = {"created_at": last.created_at.isoformat(), "id": str(last.id)}
        next_cursor = base64.b64encode(json.dumps(cursor_data).encode()).decode()

    return {"items": items, "total": int(total), "next_cursor": next_cursor}


@router.get("/{tender_id}")
def get_tender(tender_id: str, user: AuthUser) -> dict:
    """Szczegóły przetargu."""
    _org_id = user.org_id
    if not _org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, _org_id)

    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                """SELECT id, title, buyer, cpv, voivodeship, value_pln, deadline_at,
                          published_at, url, status, match_score, match_reason,
                          raw, created_at
                   FROM tender WHERE id = :id AND tenant_id = :tenant_id"""
            ),
            {"id": tender_id, "tenant_id": tenant_id},
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Przetarg nie znaleziony"},
        )

    result = _row_to_dict(row)
    result["match_reason"] = row.match_reason
    result["raw"] = row.raw if isinstance(row.raw, dict) else {}
    return result


@router.patch("/{tender_id}")
def patch_tender(tender_id: str, body: TenderPatch, user: AuthUser) -> dict:
    """Zmień status przetargu."""
    _org_id = user.org_id
    if not _org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, _org_id)

    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_status", "message": f"Nieprawidłowy status: {body.status}"},
        )

    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                """UPDATE tender SET status = :status
                   WHERE id = :id AND tenant_id = :tenant_id
                   RETURNING id, status"""
            ),
            {"status": body.status, "id": tender_id, "tenant_id": tenant_id},
        ).fetchone()

    if not result:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Przetarg nie znaleziony"},
        )

    return {"id": str(result.id), "status": result.status}


@router.delete("/{tender_id}")
def delete_tender(tender_id: str, user: AuthUser) -> dict:
    """Soft delete — ustaw status='archived'."""
    engine = get_engine()
    _org_id = user.org_id
    if not _org_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})
    engine = get_engine()
    tenant_id = _resolve_tenant_id(engine, _org_id)

    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                """UPDATE tender SET status = 'archived'
                   WHERE id = :id AND tenant_id = :tenant_id
                   RETURNING id"""
            ),
            {"id": tender_id, "tenant_id": tenant_id},
        ).fetchone()

    if not result:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Przetarg nie znaleziony"},
        )

    return {"id": str(result.id), "status": "archived", "message": "Przetarg zarchiwizowany"}
