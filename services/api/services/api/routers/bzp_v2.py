"""Faza 13 — BZP v2 sync endpoint."""
from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks

from terra_db.session import get_engine
from ..auth.deps import AuthUser
from .bzp import _do_sync

router = APIRouter(prefix="/api/v2/bzp", tags=["bzp-v2"])


@router.post("/sync")
def bzp_sync_v2(background_tasks: BackgroundTasks, user: AuthUser, days_back: int = 7) -> dict:
    """Ręczny trigger synchronizacji BZP."""
    background_tasks.add_task(_do_sync, days_back)
    return {
        "status": "started",
        "days_back": days_back,
        "message": f"Synchronizacja BZP uruchomiona — ostatnie {days_back} dni",
    }


@router.get("/status")
def bzp_status(user: AuthUser) -> dict:
    """Status ostatniej synchronizacji i liczba przetargów."""
    engine = get_engine()

    with engine.connect() as conn:
        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM tender WHERE source='bzp'")
        ).scalar() or 0

        last_sync = conn.execute(
            sa.text(
                """SELECT MAX(created_at) as last_sync,
                          COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as today_count
                   FROM tender WHERE source='bzp'"""
            )
        ).fetchone()

        by_status = conn.execute(
            sa.text(
                "SELECT status, COUNT(*) as cnt FROM tender WHERE source='bzp' GROUP BY status ORDER BY cnt DESC"
            )
        ).fetchall()

    return {
        "total_tenders": int(total),
        "last_sync": last_sync.last_sync.isoformat() if last_sync and last_sync.last_sync else None,
        "synced_today": int(last_sync.today_count) if last_sync else 0,
        "by_status": [{"status": r.status, "count": int(r.cnt)} for r in by_status],
    }
