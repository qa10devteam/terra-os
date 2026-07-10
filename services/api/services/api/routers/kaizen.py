"""S83/S90 — Kaizen Faza2: Phase Gate + summary endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/kaizen", tags=["kaizen"])


@router.get("/faza2")
def kaizen_faza2(user: AuthUser) -> dict:
    """S83 — Phase Gate: metryki sukcesu Fazy 2."""
    engine = get_engine()
    tid = str(user.org_id) if user.org_id else ""

    with engine.connect() as conn:
        total_results = conn.execute(
            text("SELECT count(*) FROM offer_result WHERE tenant_id = :t"),
            {"t": tid},
        ).scalar() or 0

        won_results = conn.execute(
            text("SELECT count(*) FROM offer_result WHERE tenant_id = :t AND status = 'won'"),
            {"t": tid},
        ).scalar() or 0

        high_score = conn.execute(
            text("SELECT count(*) FROM tender WHERE tenant_id = :t AND match_score >= 0.5"),
            {"t": tid},
        ).scalar() or 0

    win_rate = round(won_results / max(total_results, 1) * 100, 1)
    return {
        "total_offer_results": total_results,
        "win_rate_pct": win_rate,
        "high_score_tenders": high_score,
    }


@router.get("/faza2/summary")
def kaizen_faza2_summary(user: AuthUser) -> dict:
    """S90 — Kaizen Faza2 summary: pełne metryki sprintów."""
    engine = get_engine()
    tid = str(user.org_id) if user.org_id else ""

    with engine.connect() as conn:
        total_or = conn.execute(
            text("SELECT count(*) FROM offer_result WHERE tenant_id = :t"),
            {"t": tid},
        ).scalar() or 0

        won = conn.execute(
            text("SELECT count(*) FROM offer_result WHERE tenant_id = :t AND status = 'won'"),
            {"t": tid},
        ).scalar() or 0

        cw = conn.execute(
            text("SELECT count(*) FROM competitor_watch WHERE tenant_id = :t"),
            {"t": tid},
        ).scalar() or 0

        risk = conn.execute(
            text("SELECT count(*) FROM tender_document WHERE risk_level != 'unknown'"),
        ).scalar() or 0

    return {
        "total_offer_results": total_or,
        "win_rate": round(won / max(total_or, 1) * 100, 1),
        "competitor_watches": cw,
        "risk_assessments_done": risk,
        "ml_scorer_active": True,
    }
