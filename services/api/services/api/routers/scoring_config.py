"""Scoring Config API — konfiguracja scoringu per tenant.

Endpoints:
  GET  /api/v2/scoring/config          → obecna konfiguracja
  PUT  /api/v2/scoring/config          → aktualizacja wag
  POST /api/v2/scoring/rescore         → wyzwala rescore wszystkich przetargów
  GET  /api/v2/scoring/win-rates       → CPV win rates z historycznych wygranych
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/scoring", tags=["scoring"])


# ─── Schemas ───────────────────────────────────────────────────────────────────

class ScoringConfigResponse(BaseModel):
    tenant_id: str
    cpv_weight: float
    value_weight: float
    region_weight: float
    deadline_weight: float
    historical_win_weight: float
    min_value_pln: float | None
    max_value_pln: float | None
    preferred_cpvs: list[str]
    preferred_regions: list[str]
    is_default: bool = False


class ScoringConfigUpdate(BaseModel):
    cpv_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    value_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    region_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    deadline_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    historical_win_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    min_value_pln: float | None = None
    max_value_pln: float | None = None
    preferred_cpvs: list[str] = Field(default_factory=list)
    preferred_regions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_weights_sum(self) -> "ScoringConfigUpdate":
        total = (
            self.cpv_weight + self.value_weight + self.region_weight +
            self.deadline_weight + self.historical_win_weight
        )
        if total <= 0:
            raise ValueError("Sum of weights must be > 0")
        # Auto-normalize
        factor = 1.0 / total
        self.cpv_weight = round(self.cpv_weight * factor, 4)
        self.value_weight = round(self.value_weight * factor, 4)
        self.region_weight = round(self.region_weight * factor, 4)
        self.deadline_weight = round(self.deadline_weight * factor, 4)
        self.historical_win_weight = round(self.historical_win_weight * factor, 4)
        return self


class RescoreResponse(BaseModel):
    total: int
    processed: int
    avg_score_before: float
    avg_score_after: float
    message: str


class WinRateItem(BaseModel):
    cpv_prefix: str
    wins: int
    win_rate: float
    top_contractors: list[str]


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/config", response_model=ScoringConfigResponse)
def get_scoring_config(user: AuthUser) -> ScoringConfigResponse:
    """Pobiera obecną konfigurację scoringu dla tenanta."""
    tenant_id = str(user.org_id or "")
    if not tenant_id:
        raise HTTPException(status_code=400, detail={"error": "no_tenant", "message": "Brak tenant_id"})

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT cpv_weight, value_weight, region_weight,
                   deadline_weight, historical_win_weight,
                   min_value_pln, max_value_pln,
                   preferred_cpvs, preferred_regions
            FROM scoring_config
            WHERE tenant_id = :tid
        """), {"tid": tenant_id}).fetchone()

    if not row:
        return ScoringConfigResponse(
            tenant_id=tenant_id,
            cpv_weight=0.35, value_weight=0.20, region_weight=0.15,
            deadline_weight=0.10, historical_win_weight=0.20,
            min_value_pln=None, max_value_pln=None,
            preferred_cpvs=[], preferred_regions=[],
            is_default=True,
        )

    return ScoringConfigResponse(
        tenant_id=tenant_id,
        cpv_weight=float(row[0]),
        value_weight=float(row[1]),
        region_weight=float(row[2]),
        deadline_weight=float(row[3]),
        historical_win_weight=float(row[4]),
        min_value_pln=float(row[5]) if row[5] else None,
        max_value_pln=float(row[6]) if row[6] else None,
        preferred_cpvs=list(row[7] or []),
        preferred_regions=list(row[8] or []),
        is_default=False,
    )


@router.put("/config", response_model=ScoringConfigResponse)
def update_scoring_config(user: AuthUser, body: ScoringConfigUpdate) -> ScoringConfigResponse:
    """Aktualizuje konfigurację scoringu (upsert)."""
    tenant_id = str(user.org_id or "")
    if not tenant_id:
        raise HTTPException(status_code=400, detail={"error": "no_tenant", "message": "Brak tenant_id"})

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO scoring_config (
                tenant_id, cpv_weight, value_weight, region_weight,
                deadline_weight, historical_win_weight,
                min_value_pln, max_value_pln, preferred_cpvs, preferred_regions,
                updated_at
            ) VALUES (
                :tenant_id, :cpv, :val, :reg, :dead, :hist,
                :min_val, :max_val, :cpvs, :regions, now()
            )
            ON CONFLICT (tenant_id) DO UPDATE SET
                cpv_weight            = EXCLUDED.cpv_weight,
                value_weight          = EXCLUDED.value_weight,
                region_weight         = EXCLUDED.region_weight,
                deadline_weight       = EXCLUDED.deadline_weight,
                historical_win_weight = EXCLUDED.historical_win_weight,
                min_value_pln         = EXCLUDED.min_value_pln,
                max_value_pln         = EXCLUDED.max_value_pln,
                preferred_cpvs        = EXCLUDED.preferred_cpvs,
                preferred_regions     = EXCLUDED.preferred_regions,
                updated_at            = now()
        """), {
            "tenant_id": tenant_id,
            "cpv": body.cpv_weight, "val": body.value_weight,
            "reg": body.region_weight, "dead": body.deadline_weight,
            "hist": body.historical_win_weight,
            "min_val": body.min_value_pln, "max_val": body.max_value_pln,
            "cpvs": body.preferred_cpvs, "regions": body.preferred_regions,
        })

    return ScoringConfigResponse(
        tenant_id=tenant_id,
        cpv_weight=body.cpv_weight, value_weight=body.value_weight,
        region_weight=body.region_weight, deadline_weight=body.deadline_weight,
        historical_win_weight=body.historical_win_weight,
        min_value_pln=body.min_value_pln, max_value_pln=body.max_value_pln,
        preferred_cpvs=body.preferred_cpvs, preferred_regions=body.preferred_regions,
    )


@router.post("/rescore", response_model=RescoreResponse)
def trigger_rescore(user: AuthUser) -> RescoreResponse:
    """Wyzwala rescore wszystkich przetargów tenanta z aktualną konfiguracją."""
    tenant_id = str(user.org_id or "")
    if not tenant_id:
        raise HTTPException(status_code=400, detail={"error": "no_tenant", "message": "Brak tenant_id"})

    try:
        from services.ingestion.scorer import rescore_tenant
        result = rescore_tenant(tenant_id)
    except Exception as e:
        logger.error(f"Rescore failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "rescore_failed", "message": str(e)},
        )

    return RescoreResponse(
        total=result["total"],
        processed=result["processed"],
        avg_score_before=result["avg_score_before"],
        avg_score_after=result["avg_score_after"],
        message=f"Rescored {result['processed']} tenders. Avg score: {result['avg_score_before']:.3f} → {result['avg_score_after']:.3f}",
    )


@router.get("/win-rates", response_model=list[WinRateItem])
def get_win_rates(user: AuthUser, limit: int = 50) -> list[WinRateItem]:
    """Zwraca top CPV prefixes z największą liczbą wygranych przetargów."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                LEFT(cpv_main, 5) as prefix,
                COUNT(*) as wins,
                array_agg(DISTINCT contractor_name ORDER BY contractor_name)
                    FILTER (WHERE contractor_name IS NOT NULL) as contractors
            FROM bzp_results
            WHERE cpv_main IS NOT NULL AND length(cpv_main) >= 5
            GROUP BY prefix
            ORDER BY wins DESC
            LIMIT :lim
        """), {"lim": limit}).fetchall()

    if not rows:
        return []

    max_wins = max(r[1] for r in rows) or 1
    return [
        WinRateItem(
            cpv_prefix=r[0],
            wins=r[1],
            win_rate=round(r[1] / max_wins, 3),
            top_contractors=(r[2] or [])[:5],
        )
        for r in rows
    ]
