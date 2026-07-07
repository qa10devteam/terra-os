"""Analytics router — Fazy 28-37, 40.

Endpoints: /api/v2/analytics/*, /api/v2/ai/analyze-swz
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import text

from terra_db.session import get_session
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/analytics", tags=["analytics"])
ai_router = APIRouter(prefix="/api/v2/ai", tags=["ai"])


def get_db():
    SessionLocal = get_session()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Request/Response schemas ──────────────────────────────────────────────

class OptimalMarkupRequest(BaseModel):
    cost_estimate: float
    n_competitors: int
    cpv: str = ""
    region: str = ""
    historical_win_rates: list[dict] | None = None


class AHPScoreRequest(BaseModel):
    tender_id: str | None = None
    scores: dict[str, float]
    custom_criteria: list[dict] | None = None


class RecommendationRequest(BaseModel):
    tender_id: str | None = None
    cost_estimate: float
    n_competitors: int
    ahp_scores: dict[str, float] | None = None
    cpv: str = ""
    region: str = ""
    area_m2: float | None = None


class CostEstimateRequest(BaseModel):
    tender_id: str | None = None
    cpv: str
    region: str = ""
    area_m2: float | None = None
    value_estimated: float | None = None
    description: str = ""


class AnalyzeSWZRequest(BaseModel):
    tender_id: str | None = None
    text: str
    use_ai: bool = True


class WinProbabilityRequest(BaseModel):
    markup_pct: float
    n_competitors: int
    cpv: str = ""


# ─── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/optimal-markup")
def calc_optimal_markup(body: OptimalMarkupRequest, current_user: AuthUser):
    """Faza 28 — Friedman/Gates optimal bidding model."""
    from ..analytics import optimal_markup
    result = optimal_markup(
        cost_estimate=body.cost_estimate,
        n_competitors=body.n_competitors,
        historical_win_rates=body.historical_win_rates,
    )
    return result


@router.post("/ahp-score")
def calc_ahp_score(body: AHPScoreRequest, current_user: AuthUser):
    """Faza 29 — AHP decision support."""
    from ..analytics import compute_ahp_score
    result = compute_ahp_score(
        scores=body.scores,
        criteria=body.custom_criteria,
    )
    return result


@router.get("/ahp-criteria")
def get_ahp_criteria(current_user: AuthUser):
    """Get default AHP criteria list."""
    from ..analytics import DEFAULT_CRITERIA
    return {"criteria": DEFAULT_CRITERIA}


@router.post("/cost-estimate")
def calc_cost_estimate(body: CostEstimateRequest, current_user: AuthUser):
    """Faza 31 — Hybrid cost estimation with confidence intervals."""
    from ..analytics import estimate_cost, explain_cost_drivers
    result = estimate_cost(
        cpv=body.cpv,
        region=body.region,
        area_m2=body.area_m2,
        value_estimated=body.value_estimated,
        description=body.description,
    )
    if "error" not in result and result.get("expected_estimate"):
        result["cost_drivers"] = explain_cost_drivers(
            estimate=result["expected_estimate"],
            cpv=body.cpv,
            region=body.region,
            area_m2=body.area_m2,
            description=body.description,
        )
    return result


@router.get("/win-probability")
def calc_win_probability(
    current_user: AuthUser,
    markup: float,
    n_competitors: int,
    cpv: str = "",
):
    """Faza 34 — Win probability at a given markup."""
    from ..analytics import estimate_win_probability
    return estimate_win_probability(
        markup_pct=markup,
        n_competitors=n_competitors,
        cpv=cpv,
    )


@router.post("/recommendation")
def get_recommendation(body: RecommendationRequest, current_user: AuthUser):
    """Faza 37 — Full bid recommendation engine (GO/NO-GO)."""
    from ..analytics import generate_recommendation

    # Optionally fetch red flags from DB if tender_id given
    red_flags = []
    if body.tender_id:
        try:
            from terra_db.session import get_engine
            from sqlalchemy import text as sql_text
            engine = get_engine()
            with engine.connect() as conn:
                risks = conn.execute(
                    sql_text("""
                        SELECT kind, severity, message FROM discrepancy
                        WHERE tender_id = :tid ORDER BY severity
                    """),
                    {"tid": body.tender_id},
                ).fetchall()
                red_flags = [{"message": r.message, "severity": r.severity} for r in risks]
        except Exception:
            pass

    return generate_recommendation(
        cost_estimate=body.cost_estimate,
        n_competitors=body.n_competitors,
        ahp_scores=body.ahp_scores,
        red_flags=red_flags,
        cpv=body.cpv,
        region=body.region,
        area_m2=body.area_m2,
    )


@router.get("/dashboard")
def get_analytics_dashboard(
    current_user: AuthUser,
    db=Depends(get_db),
):
    """Faza 40 — Analytics dashboard KPIs."""
    org_id = current_user.org_id

    # Fallback to tenant data if no org_id
    try:
        # Pipeline value (sum of value_pln for active tenders)
        pipeline_stats = db.execute(
            text("""
                SELECT
                    COUNT(*) as active_bids,
                    COALESCE(SUM(CAST(t.value_pln AS NUMERIC)), 0) as pipeline_value
                FROM tender t
                JOIN tenant tn ON tn.id = t.tenant_id
                WHERE t.status NOT IN ('archived', 'decided_nogo')
            """),
        ).fetchone()

        # Win rate (decided_go / (decided_go + decided_nogo))
        decision_stats = db.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'decided_go') as won,
                    COUNT(*) FILTER (WHERE status IN ('decided_go', 'decided_nogo')) as total
                FROM tender
            """),
        ).fetchone()

        # Pipeline funnel
        funnel = db.execute(
            text("""
                SELECT status, COUNT(*) as count
                FROM tender
                GROUP BY status
                ORDER BY count DESC
            """),
        ).fetchall()

        win_rate = 0.0
        if decision_stats and decision_stats.total > 0:
            win_rate = round(decision_stats.won / decision_stats.total * 100, 1)

        return {
            "pipeline_value": float(pipeline_stats.pipeline_value) if pipeline_stats else 0,
            "active_bids": int(pipeline_stats.active_bids) if pipeline_stats else 0,
            "win_rate_pct": win_rate,
            "avg_margin_pct": 12.5,  # placeholder until historical_bids populated
            "funnel": [{"status": r.status, "count": r.count} for r in funnel],
        }
    except Exception as e:
        return {
            "pipeline_value": 0,
            "active_bids": 0,
            "win_rate_pct": 0,
            "avg_margin_pct": 0,
            "funnel": [],
            "error": str(e),
        }


@router.get("/pipeline-funnel")
def get_pipeline_funnel(current_user: AuthUser, db=Depends(get_db)):
    """Pipeline funnel — count per status."""
    rows = db.execute(
        text("SELECT status, COUNT(*) as count FROM tender GROUP BY status")
    ).fetchall()
    return {"funnel": [{"status": r.status, "count": r.count} for r in rows]}


# ─── AI router — SWZ analysis ─────────────────────────────────────────────

@ai_router.post("/analyze-swz")
async def analyze_swz(body: AnalyzeSWZRequest, current_user: AuthUser):
    """Faza 30 — NLP risk extraction from SWZ document text."""
    from ..analytics import extract_risks_with_ai, extract_risks_from_text

    if body.use_ai:
        result = await extract_risks_with_ai(body.text)
    else:
        result = extract_risks_from_text(body.text)

    # If tender_id given, persist red flags to discrepancy table
    if body.tender_id and result.get("red_flags"):
        try:
            from terra_db.session import get_engine
            from sqlalchemy import text as sql_text
            engine = get_engine()
            with engine.connect() as conn:
                for flag in result["red_flags"][:10]:
                    severity_map = {"high": "block", "medium": "warn", "low": "info"}
                    conn.execute(
                        sql_text("""
                            INSERT INTO discrepancy (tenant_id, tender_id, kind, severity, message, provenance)
                            SELECT t.tenant_id, :tid, 'swz_risk', :sev, :msg, :prov::jsonb
                            FROM tender t WHERE t.id = :tid
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "tid": body.tender_id,
                            "sev": severity_map.get(flag.get("severity", "low"), "info"),
                            "msg": flag["message"],
                            "prov": '{"source": "ai_analysis"}',
                        },
                    )
                conn.commit()
        except Exception:
            pass  # Don't fail the request if DB write fails

    return result
