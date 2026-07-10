"""S50/S51 — CPV Win Rate + Competitor Win Rate endpoints.

S50: GET /api/v2/intelligence/cpv-win-rates
     — aggregate win rates per CPV 2-digit prefix from offer_result.

S51: GET /api/v2/intelligence/competitor-win-rates?nip=...
     — competitor wins from bzp_results.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from terra_db.session import get_engine
from ..auth.deps import AuthUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/intelligence", tags=["intelligence-cpv"])


@router.get("/cpv-win-rates")
def get_cpv_win_rates(user: AuthUser = Depends(get_current_user)) -> dict:
    """S50: Win rates per CPV 2-digit prefix from offer_result."""
    if not user or not user.org_id:
        raise HTTPException(status_code=403, detail="Brak org_id")
    tenant_id = user.org_id

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    LEFT(COALESCE(cpv_code, '00'), 2)                            AS cpv2,
                    COUNT(*)                                                      AS total,
                    COUNT(*) FILTER (WHERE status = 'won')                        AS won,
                    ROUND(
                        COUNT(*) FILTER (WHERE status = 'won')::numeric
                        / NULLIF(COUNT(*), 0), 4
                    )                                                             AS win_rate,
                    ROUND(AVG(bid_value_pln), 2)                                 AS avg_bid_pln
                FROM offer_result
                WHERE tenant_id = :tenant_id
                  AND status IN ('won', 'lost')
                GROUP BY 1
                ORDER BY win_rate DESC NULLS LAST
            """),
            {"tenant_id": tenant_id},
        ).fetchall()

    return {
        "items": [
            {
                "cpv_prefix": r[0],
                "total": r[1],
                "won": r[2],
                "win_rate": float(r[3]) if r[3] is not None else None,
                "avg_bid_pln": float(r[4]) if r[4] is not None else None,
            }
            for r in rows
        ],
        "tenant_id": tenant_id,
    }


@router.get("/competitor-win-rates")
def get_competitor_win_rates(
    nip: str = Query(..., description="NIP konkurenta"),
    user: AuthUser = Depends(get_current_user),
) -> dict:
    """S51: Competitor wins from bzp_results by contractor NIP."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    contractor_name,
                    contractor_nip,
                    COUNT(*)                       AS total_wins,
                    ROUND(AVG(awarded_value), 2)   AS avg_value_pln,
                    MIN(awarded_date)              AS first_win,
                    MAX(awarded_date)              AS last_win,
                    ARRAY_AGG(DISTINCT cpv_main)   AS cpv_codes
                FROM bzp_results
                WHERE contractor_nip = :nip
                GROUP BY 1, 2
                LIMIT 1
            """),
            {"nip": nip},
        ).fetchone()

    if not rows:
        return {"nip": nip, "found": False, "total_wins": 0}

    return {
        "nip": nip,
        "found": True,
        "contractor_name": rows[0],
        "contractor_nip": rows[1],
        "total_wins": rows[2],
        "avg_value_pln": float(rows[3]) if rows[3] else None,
        "first_win": str(rows[4]) if rows[4] else None,
        "last_win": str(rows[5]) if rows[5] else None,
        "cpv_codes": [c for c in (rows[6] or []) if c],
    }
