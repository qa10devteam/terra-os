"""Scoring configuration & analytics endpoints.

GET  /api/v2/scoring/config
PUT  /api/v2/scoring/config
GET  /api/v2/tenders/{tender_id}/score-breakdown
GET  /api/v2/market/cpv-heatmap
POST /api/v2/admin/refresh-views
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlalchemy as sa

from terra_db.session import get_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2", tags=["scoring"])

# Default weights — stored in DB config table or file
_DEFAULT_WEIGHTS = {
    "cpv_match": 30,
    "value_range": 25,
    "deadline_pressure": 20,
    "buyer_history": 15,
    "document_quality": 10,
}


class ScoringConfigRequest(BaseModel):
    weights: dict[str, int]


# ─── Scoring Config ───────────────────────────────────────────────────────────

@router.get("/scoring/config")
def get_scoring_config() -> dict[str, Any]:
    """Get current scoring weights."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT value FROM app_config WHERE key = 'scoring_weights' LIMIT 1")
        ).fetchone()
    if row:
        return {"weights": json.loads(row[0])}
    return {"weights": _DEFAULT_WEIGHTS}


@router.put("/scoring/config")
def update_scoring_config(body: ScoringConfigRequest) -> dict[str, Any]:
    """Update scoring weights. Sum must equal 100."""
    total = sum(body.weights.values())
    if total != 100:
        raise HTTPException(400, f"Suma wag musi wynosić 100, aktualna: {total}")

    engine = get_engine()
    value_json = json.dumps(body.weights)
    with engine.begin() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO app_config (key, value) VALUES ('scoring_weights', :val)
                ON CONFLICT (key) DO UPDATE SET value = :val
            """),
            {"val": value_json},
        )
        # Audit log
        conn.execute(
            sa.text("""
                INSERT INTO audit_log (action, entity_type, details)
                VALUES ('scoring_config_update', 'config', :details)
            """),
            {"details": json.dumps({"weights": body.weights})},
        )
    return {"weights": body.weights, "saved": True}


# ─── Score Breakdown ──────────────────────────────────────────────────────────

@router.get("/tenders/{tender_id}/score-breakdown")
def get_score_breakdown(tender_id: str) -> dict[str, Any]:
    """Get detailed scoring breakdown for a tender."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT * FROM score_breakdown(:tid::uuid)"),
            {"tid": tender_id},
        ).fetchall()
    if not rows:
        raise HTTPException(404, "Tender not found or no breakdown available")

    breakdown = [
        {
            "criterion": r[0],
            "raw_score": float(r[1]),
            "weight": float(r[2]),
            "weighted_score": float(r[3]),
        }
        for r in rows
    ]
    total = sum(b["weighted_score"] for b in breakdown)
    return {"tender_id": tender_id, "breakdown": breakdown, "total_score": round(total, 2)}


# ─── CPV Heatmap ──────────────────────────────────────────────────────────────

@router.get("/market/cpv-heatmap")
def get_cpv_heatmap() -> list[dict[str, Any]]:
    """Get CPV division heatmap from materialized view."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT cpv_division, year, quarter, total, won, win_rate, avg_value
                FROM mv_cpv_heatmap
                ORDER BY year DESC, quarter DESC, total DESC
            """)
        ).fetchall()
    return [
        {
            "cpv_division": r[0],
            "year": r[1],
            "quarter": r[2],
            "total": r[3],
            "won": r[4],
            "win_rate": float(r[5]) if r[5] else 0,
            "avg_value": float(r[6]) if r[6] else 0,
        }
        for r in rows
    ]


# ─── Admin: Refresh MVs ──────────────────────────────────────────────────────

@router.post("/admin/refresh-views")
def refresh_views() -> dict[str, str]:
    """Refresh all materialized views."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text("REFRESH MATERIALIZED VIEW mv_pipeline_kpi"))
        conn.execute(sa.text("REFRESH MATERIALIZED VIEW mv_cpv_heatmap"))
        conn.execute(sa.text("REFRESH MATERIALIZED VIEW mv_market_forecast"))
        conn.execute(sa.text("REFRESH MATERIALIZED VIEW mv_competitor_radar"))
    return {"status": "refreshed"}
