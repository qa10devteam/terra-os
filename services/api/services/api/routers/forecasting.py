"""Time-series forecasting endpoints — Prophet-like predictions for tender market.

GET  /api/v2/forecast/timeseries
GET  /api/v2/forecast/seasonality
GET  /api/v2/forecast/predict
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Query
import sqlalchemy as sa

from terra_db.session import get_engine
from ..auth.deps import AuthUser
from ..auth.plan_gate import require_plan, PlanLevel

router = APIRouter(prefix="/api/v2/forecast", tags=["forecasting"])


def _holt_winters_forecast(values: list[float], periods: int = 6, alpha=0.3, beta=0.1, gamma=0.2, season_length=4) -> list[dict]:
    """Simple additive Holt-Winters with confidence intervals."""
    n = len(values)
    if n < season_length * 2:
        # Fallback: linear trend
        return _linear_forecast(values, periods)

    # Initialize
    level = sum(values[:season_length]) / season_length
    trend = (sum(values[season_length:2*season_length]) - sum(values[:season_length])) / (season_length ** 2)
    seasonal = [values[i] - level for i in range(season_length)]

    # Fit
    fitted = []
    for i in range(n):
        s_idx = i % season_length
        if i == 0:
            fitted.append(level + trend + seasonal[s_idx])
            continue
        val = values[i]
        prev_level = level
        level = alpha * (val - seasonal[s_idx]) + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
        seasonal[s_idx] = gamma * (val - level) + (1 - gamma) * seasonal[s_idx]
        fitted.append(level + trend + seasonal[s_idx])

    # Residuals for CI
    residuals = [values[i] - fitted[i] for i in range(n)]
    rmse = math.sqrt(sum(r**2 for r in residuals) / max(n - 1, 1))

    # Forecast
    forecasts = []
    for h in range(1, periods + 1):
        s_idx = (n + h - 1) % season_length
        point = level + trend * h + seasonal[s_idx]
        ci_width = 1.96 * rmse * math.sqrt(h)
        forecasts.append({
            "period": h,
            "forecast": round(point, 2),
            "lower_ci": round(point - ci_width, 2),
            "upper_ci": round(point + ci_width, 2),
            "confidence": 0.95,
        })
    return forecasts


def _linear_forecast(values: list[float], periods: int) -> list[dict]:
    """Linear regression fallback."""
    n = len(values)
    if n < 2:
        return [{"period": h, "forecast": values[-1] if values else 0, "lower_ci": 0, "upper_ci": 0, "confidence": 0.5} for h in range(1, periods + 1)]

    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0
    intercept = y_mean - slope * x_mean

    residuals = [values[i] - (intercept + slope * i) for i in range(n)]
    rmse = math.sqrt(sum(r**2 for r in residuals) / max(n - 1, 1))

    forecasts = []
    for h in range(1, periods + 1):
        point = intercept + slope * (n - 1 + h)
        ci_width = 1.96 * rmse * math.sqrt(1 + 1/n + ((n - 1 + h) - x_mean)**2 / max(den, 1))
        forecasts.append({
            "period": h,
            "forecast": round(max(point, 0), 2),
            "lower_ci": round(max(point - ci_width, 0), 2),
            "upper_ci": round(point + ci_width, 2),
            "confidence": 0.95,
        })
    return forecasts


@router.get("/timeseries")
def timeseries(
    user: AuthUser,
    _gate: None = require_plan(PlanLevel.PRO),
    cpv_division: Optional[str] = None,
    granularity: str = Query("quarter", pattern="^(month|quarter)$"),
) -> dict[str, Any]:
    """Historical time-series of tender count and value by CPV."""
    engine = get_engine()
    trunc = "quarter" if granularity == "quarter" else "month"
    
    conditions = ["created_at IS NOT NULL"]
    params: dict = {}
    if cpv_division:
        conditions.append("SUBSTRING(cpv[1] FROM 1 FOR 2) = :cpv")
        params["cpv"] = cpv_division

    sql = sa.text(f"""
        SELECT DATE_TRUNC('{trunc}', created_at) AS period,
               COUNT(*) AS count,
               COALESCE(SUM(value_pln), 0) AS total_value,
               COALESCE(AVG(value_pln), 0) AS avg_value
        FROM tender
        WHERE {" AND ".join(conditions)}
        GROUP BY 1
        ORDER BY 1
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    series = [
        {
            "period": r[0].isoformat() if r[0] else None,
            "count": r[1],
            "total_value": float(r[2]),
            "avg_value": float(r[3]),
        }
        for r in rows
    ]
    return {"granularity": granularity, "cpv_division": cpv_division, "series": series}


@router.get("/seasonality")
def seasonality_analysis(user: AuthUser, _gate: None = require_plan(PlanLevel.PRO), cpv_division: Optional[str] = None) -> dict[str, Any]:
    """Detect seasonal patterns — monthly index for given CPV."""
    engine = get_engine()
    conditions = ["cpv IS NOT NULL AND array_length(cpv, 1) > 0"]
    params: dict = {}
    if cpv_division:
        conditions.append("SUBSTRING(cpv[1] FROM 1 FOR 2) = :cpv")
        params["cpv"] = cpv_division

    sql = sa.text(f"""
        SELECT EXTRACT(MONTH FROM created_at)::int AS month,
               COUNT(*) AS count,
               AVG(value_pln) AS avg_value
        FROM tender
        WHERE {" AND ".join(conditions)}
        GROUP BY 1
        ORDER BY 1
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    total = sum(r[1] for r in rows) if rows else 1
    monthly_avg = total / 12.0

    months = []
    for r in rows:
        index = r[1] / monthly_avg if monthly_avg > 0 else 1.0
        months.append({
            "month": r[0],
            "count": r[1],
            "avg_value": float(r[2]) if r[2] else 0,
            "seasonal_index": round(index, 3),
            "peak": index > 1.3,
            "trough": index < 0.7,
        })

    peak_months = [m["month"] for m in months if m.get("peak")]
    trough_months = [m["month"] for m in months if m.get("trough")]

    return {
        "cpv_division": cpv_division,
        "months": months,
        "peak_months": peak_months,
        "trough_months": trough_months,
        "insight": f"Peak: miesiące {peak_months}. Spadek: miesiące {trough_months}." if peak_months else "Brak wyraźnej sezonowości.",
    }


@router.get("/predict")
def predict(
    user: AuthUser,
    _gate: None = require_plan(PlanLevel.PRO),
    cpv_division: Optional[str] = None,
    periods: int = Query(6, ge=1, le=12),
    method: str = Query("holt_winters", pattern="^(holt_winters|linear)$"),
) -> dict[str, Any]:
    """Forecast future tender count using Holt-Winters or linear regression."""
    engine = get_engine()
    conditions = ["created_at IS NOT NULL"]
    params: dict = {}
    if cpv_division:
        conditions.append("SUBSTRING(cpv[1] FROM 1 FOR 2) = :cpv")
        params["cpv"] = cpv_division

    sql = sa.text(f"""
        SELECT DATE_TRUNC('quarter', created_at) AS period,
               COUNT(*) AS count
        FROM tender
        WHERE {" AND ".join(conditions)}
        GROUP BY 1
        ORDER BY 1
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        return {"error": "Brak danych do prognozowania", "forecasts": []}

    values = [float(r[1]) for r in rows]
    last_period = rows[-1][0]

    if method == "holt_winters":
        forecasts = _holt_winters_forecast(values, periods)
    else:
        forecasts = _linear_forecast(values, periods)

    # Add period dates
    for f in forecasts:
        future_date = last_period + timedelta(days=90 * f["period"])
        f["date"] = future_date.isoformat()

    return {
        "method": method,
        "cpv_division": cpv_division,
        "historical_points": len(values),
        "last_period": last_period.isoformat() if last_period else None,
        "forecasts": forecasts,
    }


# ─── Missing stub: GET /api/v2/forecast/pipeline ─────────────────────────────

@router.get("/pipeline")
def forecast_pipeline(
    user: AuthUser,
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Forecast pipeline — list tenders with win probability. Frontend /app/forecast."""
    import sqlalchemy as sa
    from terra_db.session import get_engine

    engine = get_engine()
    tenant_id = str(user.org_id)

    with engine.connect() as conn:
        try:
            rows = conn.execute(
                sa.text(
                    """SELECT id, title, value_pln, match_score, status, deadline_at
                       FROM tender
                       WHERE tenant_id=:t
                       ORDER BY match_score DESC NULLS LAST
                       LIMIT :lim"""
                ),
                {"t": tenant_id, "lim": limit}
            ).mappings().fetchall()
        except Exception:
            rows = []

    items = [
        {
            "id": str(r["id"]),
            "name": r["title"],
            "value_pln": float(r["value_pln"] or 0),
            "win_probability": round(float(r["match_score"] or 0) * 100, 1),
            "status": r["status"],
            "deadline": str(r["deadline_at"]) if r["deadline_at"] else None,
        }
        for r in rows
    ]

    return {
        "items": items,
        "total": len(items),
        "limit": limit,
        "forecast_model": "match_score_v1",
    }
