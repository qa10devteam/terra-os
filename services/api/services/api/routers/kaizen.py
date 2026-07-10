"""Kaizen metrics router — S45, S83, S90, S135."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..auth.deps import AuthUser, get_current_user

router = APIRouter(prefix="/api/v2/kaizen", tags=["kaizen"])


def _engine():
    from terra_db.session import get_engine
    return get_engine()


# ── S45 ─────────────────────────────────────────────────────────────────────

@router.get("/metrics")
async def kaizen_metrics(user: AuthUser):
    """S45: Kluczowe metryki operacyjne."""
    tid = str(user.org_id)
    engine = _engine()
    with engine.connect() as conn:
        ingest_p95 = conn.execute(
            text(
                "SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (updated_at - created_at)))"
                " FROM ingest_task WHERE status='done'"
            )
        ).scalar() or 0
        total = conn.execute(text("SELECT count(*) FROM tender WHERE tenant_id=:t"), {"t": tid}).scalar() or 0
        high_score = conn.execute(
            text("SELECT count(*) FROM tender WHERE tenant_id=:t AND match_score >= 0.5"), {"t": tid}
        ).scalar() or 0
    return {
        "ingest_latency_p95_s": round(float(ingest_p95), 2),
        "total_tenders": total,
        "high_score_pct": round(high_score * 100 / max(total, 1), 1),
    }


# ── S83/S90 ──────────────────────────────────────────────────────────────────

@router.get("/faza2")
async def kaizen_faza2(user: AuthUser):
    """S83: Phase gate Fazy 2."""
    tid = str(user.org_id)
    engine = _engine()
    with engine.connect() as conn:
        total_or = conn.execute(text("SELECT count(*) FROM offer_result WHERE tenant_id=:t"), {"t": tid}).scalar() or 0
        won = conn.execute(text("SELECT count(*) FROM offer_result WHERE tenant_id=:t AND status='won'"), {"t": tid}).scalar() or 0
        high_score = conn.execute(
            text("SELECT count(*) FROM tender WHERE tenant_id=:t AND match_score>=0.5"), {"t": tid}
        ).scalar() or 0
    return {
        "total_offer_results": total_or,
        "win_rate_pct": round(won / max(total_or, 1) * 100, 1),
        "high_score_tenders": high_score,
    }


@router.get("/faza2/summary")
async def kaizen_faza2_summary(user: AuthUser):
    """S90: Podsumowanie Fazy 2."""
    tid = str(user.org_id)
    engine = _engine()
    with engine.connect() as conn:
        total_or = conn.execute(text("SELECT count(*) FROM offer_result WHERE tenant_id=:t"), {"t": tid}).scalar() or 0
        won = conn.execute(text("SELECT count(*) FROM offer_result WHERE tenant_id=:t AND status='won'"), {"t": tid}).scalar() or 0
        cw = conn.execute(text("SELECT count(*) FROM competitor_watch WHERE tenant_id=:t"), {"t": tid}).scalar() or 0
        risk = conn.execute(text("SELECT count(*) FROM tender_document WHERE risk_level != 'unknown'")).scalar() or 0
    return {
        "total_offer_results": total_or,
        "win_rate": round(won / max(total_or, 1) * 100, 1),
        "competitor_watches": cw,
        "risk_assessments_done": risk,
        "ml_scorer_active": True,
    }


# ── S135 ─────────────────────────────────────────────────────────────────────

@router.get("/faza3/summary")
async def kaizen_faza3_summary(user: AuthUser):
    """S135: Podsumowanie Fazy 3."""
    tid = str(user.org_id)
    engine = _engine()
    with engine.connect() as conn:
        workflows = conn.execute(
            text("SELECT count(*) FROM workflow_definition WHERE tenant_id=:t AND is_active=true"), {"t": tid}
        ).scalar() or 0
        wh_7d = conn.execute(
            text("SELECT count(*) FROM webhook_deliveries WHERE created_at > now()-interval '7 days'")
        ).scalar() or 0
        api_keys = conn.execute(text("SELECT count(*) FROM api_keys WHERE tenant_id=:t"), {"t": tid}).scalar() or 0
        flags = conn.execute(
            text("SELECT count(*) FROM feature_flags WHERE tenant_id=:t AND enabled=true"), {"t": tid}
        ).scalar() or 0
        ab_exp = conn.execute(text("SELECT count(*) FROM ab_experiments WHERE tenant_id=:t"), {"t": tid}).scalar() or 0
    return {
        "workflows_active": workflows,
        "webhook_deliveries_7d": wh_7d,
        "api_keys_count": api_keys,
        "feature_flags_active": flags,
        "ab_experiments": ab_exp,
    }
