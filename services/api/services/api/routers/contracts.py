"""Contracts router — GET/POST /api/v2/contracts.

Returns and creates contracts for the authenticated user's tenant.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import sqlalchemy as sa

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/contracts", tags=["contracts"])


class ContractCreate(BaseModel):
    title: str
    state: str = "draft"
    tender_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location_address: Optional[str] = None


@router.get("")
def list_contracts(user: AuthUser, limit: int = 50, offset: int = 0) -> dict:
    """List contracts for the current tenant."""
    tenant_id = str(user.org_id) if user.org_id else "default"
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, tenant_id, tender_id, title, state,
                       start_date, end_date, location_address, lat, lng, created_at
                FROM contract
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
                LIMIT :lim OFFSET :off
            """),
            {"tid": tenant_id, "lim": limit, "off": offset},
        ).fetchall()

        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM contract WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        ).scalar()

    items = [
        {
            "id": str(r.id),
            "tender_id": str(r.tender_id) if r.tender_id else None,
            "title": r.title,
            "state": r.state,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "location_address": r.location_address,
            "lat": float(r.lat) if r.lat else None,
            "lng": float(r.lng) if r.lng else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_contract(body: ContractCreate, user: AuthUser) -> dict:
    """Create a new contract for the current tenant."""
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="Tytuł kontraktu jest wymagany")

    tenant_id = str(user.org_id) if user.org_id else "default"
    new_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO contract (id, tenant_id, tender_id, title, state,
                                      start_date, end_date, location_address, created_at)
                VALUES (:id, :tid, :tender_id, :title, :state,
                        :start_date, :end_date, :location_address, :created_at)
            """),
            {
                "id": new_id,
                "tid": tenant_id,
                "tender_id": body.tender_id or None,
                "title": body.title.strip(),
                "state": body.state,
                "start_date": body.start_date or None,
                "end_date": body.end_date or None,
                "location_address": body.location_address or None,
                "created_at": now,
            },
        )

    return {
        "id": new_id,
        "tenant_id": tenant_id,
        "title": body.title.strip(),
        "state": body.state,
        "created_at": now.isoformat(),
    }
