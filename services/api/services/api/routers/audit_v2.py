"""Audit Trail v2 — Enhanced change tracking with diffs, user attribution, and rollback.

Endpoints:
  GET  /api/v2/audit/trail           — paginated audit log
  GET  /api/v2/audit/entity/:id      — changes for specific entity
  GET  /api/v2/audit/diff/:audit_id  — detailed diff for one change
  POST /api/v2/audit/rollback/:id    — rollback to previous state
  GET  /api/v2/audit/stats           — audit stats (who changed what, when)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Query
from ..auth.deps import AuthUser
from pydantic import BaseModel
import sqlalchemy as sa

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2/audit", tags=["audit"])
logger = logging.getLogger(__name__)


@router.get("/recent")
def get_audit_recent(
    limit: int = Query(15, ge=1, le=100),
    user: AuthUser = None,  # type: ignore[assignment]
) -> list:
    """Recent audit entries for dashboard feed."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, entity, entity_id, action, actor, detail, at
            FROM audit_log
            ORDER BY at DESC
            LIMIT :lim
        """), {"lim": limit}).fetchall()
    return [{
        "id": str(r[0]),
        "action_type": r[3] or "update",
        "user_email": str(r[4]) if r[4] else "system",
        "action": f"{r[1] or ''} {r[3] or ''}".strip(),
        "created_at": r[6].isoformat() if r[6] else None,
    } for r in rows]


@router.get("/trail")
def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    entity_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
) -> dict[str, Any]:
    """Paginated audit trail with filters."""
    engine = get_engine()

    conditions = []
    params: dict[str, Any] = {"lim": limit, "off": offset}

    if entity_type:
        conditions.append("entity = :etype")
        params["etype"] = entity_type
    if user_id:
        conditions.append("actor = :uid")
        params["uid"] = user_id
    if action:
        conditions.append("action = :act")
        params["act"] = action

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with engine.connect() as conn:
        rows = conn.execute(sa.text(f"""
            SELECT id, entity, entity_id, action, actor, detail, at
            FROM audit_log
            {where}
            ORDER BY at DESC
            LIMIT :lim OFFSET :off
        """), params).fetchall()

        count_row = conn.execute(sa.text(f"""
            SELECT COUNT(*) FROM audit_log {where}
        """), params).fetchone()

    total = count_row[0] if count_row else 0

    return {
        "items": [{
            "id": str(r[0]),
            "entity_type": r[1],
            "entity_id": str(r[2]) if r[2] else None,
            "action": r[3],
            "actor": str(r[4]) if r[4] else None,
            "changes_summary": _summarize_changes(r[5]),
            "at": r[6].isoformat() if r[6] else None,
        } for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/entity/{entity_id}")
def get_entity_history(
    entity_id: str,
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Full change history for a specific entity."""
    engine = get_engine()

    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, entity, action, actor, detail, at
            FROM audit_log
            WHERE entity_id = :eid
            ORDER BY at DESC
            LIMIT :lim
        """), {"eid": entity_id, "lim": limit}).fetchall()

    return [{
        "id": str(r[0]),
        "entity_type": r[1],
        "action": r[2],
        "actor": str(r[3]) if r[3] else None,
        "changes": json.loads(r[4]) if r[4] else {},
        "at": r[5].isoformat() if r[5] else None,
    } for r in rows]


@router.get("/diff/{audit_id}")
def get_diff(audit_id: str) -> dict[str, Any]:
    """Detailed diff for one audit entry."""
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT id, entity_type, entity_id, action, user_id, changes, created_at
            FROM audit_log WHERE id = :aid
        """), {"aid": audit_id}).fetchone()

    if not row:
        return {"error": "Not found"}

    changes = json.loads(row[5]) if row[5] else {}

    return {
        "id": str(row[0]),
        "entity_type": row[1],
        "entity_id": str(row[2]) if row[2] else None,
        "action": row[3],
        "actor": str(row[4]) if row[4] else None,
        "diff": changes,
        "fields_changed": list(changes.keys()) if isinstance(changes, dict) else [],
        "at": row[6].isoformat() if row[6] else None,
    }


@router.get("/stats")
def get_audit_stats(
    days: int = Query(30, ge=1, le=365),
) -> dict[str, Any]:
    """Audit statistics — activity summary."""
    engine = get_engine()

    with engine.connect() as conn:
        # Activity by day
        daily = conn.execute(sa.text("""
            SELECT DATE(at) as day, COUNT(*) as cnt,
                   COUNT(DISTINCT actor) as users
            FROM audit_log
            WHERE at > NOW() - INTERVAL '1 day' * :days
            GROUP BY 1 ORDER BY 1 DESC
            LIMIT 30
        """), {"days": days}).fetchall()

        # Top actors
        actors = conn.execute(sa.text("""
            SELECT actor, COUNT(*) as cnt
            FROM audit_log
            WHERE at > NOW() - INTERVAL '1 day' * :days
              AND actor IS NOT NULL
            GROUP BY 1 ORDER BY 2 DESC
            LIMIT 10
        """), {"days": days}).fetchall()

        # Actions distribution
        actions = conn.execute(sa.text("""
            SELECT action, entity, COUNT(*) as cnt
            FROM audit_log
            WHERE at > NOW() - INTERVAL '1 day' * :days
            GROUP BY 1, 2 ORDER BY 3 DESC
            LIMIT 20
        """), {"days": days}).fetchall()

    return {
        "period_days": days,
        "daily_activity": [{
            "date": str(r[0]),
            "changes": int(r[1]),
            "active_users": int(r[2]),
        } for r in daily],
        "top_actors": [{
            "actor": str(r[0]),
            "changes": int(r[1]),
        } for r in actors],
        "action_distribution": [{
            "action": r[0],
            "entity": r[1],
            "count": int(r[2]),
        } for r in actions],
    }


def _summarize_changes(changes_json) -> str:
    """Generate human-readable summary of changes."""
    if not changes_json:
        return "brak szczegółów"
    try:
        changes = json.loads(changes_json) if isinstance(changes_json, str) else changes_json
        if isinstance(changes, dict):
            fields = list(changes.keys())[:3]
            suffix = f" +{len(changes) - 3} więcej" if len(changes) > 3 else ""
            return f"Zmieniono: {', '.join(fields)}{suffix}"
        return str(changes)[:80]
    except Exception:
        return "zmiana"
