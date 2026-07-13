"""Price Intelligence — predykcja cen R/M/S, indeks inflacji, material risk.

Warstwy:
1. ICB trend analysis (YoY, QoQ z mv_labor_inflation_index)
2. Quantile regression na historycznych cenach  
3. Material risk score (zmienność ceny w ostatnich 4Q)
4. Price forecast — linear extrapolation + Prophet (jeśli dostępny)
"""
from __future__ import annotations

import logging
import math
from typing import Any

import sqlalchemy as sa
import numpy as np

from terra_db.session import get_engine

logger = logging.getLogger(__name__)


def get_inflation_index(
    category: str | None = None,
    typ_rms: str | None = None,
    quarters: int = 8,
) -> list[dict]:
    """Pobierz indeks inflacji kosztów budowlanych z mv_labor_inflation_index.

    mv_labor_inflation_index zawiera prekalkulowane YoY/QoQ per typ_rms+category.
    """
    engine = get_engine()
    filters = []
    params: dict[str, Any] = {"limit": quarters}

    if category:
        filters.append("category = :cat")
        params["cat"] = category
    if typ_rms:
        filters.append("typ_rms = :typ")
        params["typ"] = typ_rms

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    with engine.connect() as conn:
        # Sprawdź czy mv istnieje i ma dane
        rows = conn.execute(sa.text(f"""
            SELECT * FROM mv_labor_inflation_index
            {where}
            ORDER BY kwartalrok DESC, kwartalnr DESC
            LIMIT :limit
        """), params).fetchall()

    if not rows:
        return []

    return [dict(r._mapping) for r in rows]


def get_material_risk_score(
    category: str,
    quarters: int = 8,
) -> dict:
    """Oblicz Material Risk Score dla kategorii materiałów.

    Oparty na:
    - Coefficient of Variation (CV) cen w ostatnich N kwartałach
    - Trend (wzrostowy/neutralny/spadkowy)
    - YoY zmiana ostatniego kwartału

    Zwraca score 0.0–1.0 (0=stable, 1=high_risk)
    """
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT kwartalrok, kwartalnr,
                   round(avg(cena_netto)::numeric, 2) as avg_price,
                   round(stddev(cena_netto)::numeric, 2) as std_price
            FROM icb_ceny_srednie
            WHERE category = :cat AND typ_rms = 'M' AND cena_netto > 0
            ORDER BY kwartalrok DESC, kwartalnr DESC
            LIMIT :n
        """), {"cat": category, "n": quarters}).fetchall()

    if len(rows) < 2:
        return {"score": 0.5, "level": "unknown", "reason": "insufficient_data"}

    prices = [float(r.avg_price) for r in rows if r.avg_price]
    if not prices:
        return {"score": 0.5, "level": "unknown", "reason": "no_price_data"}

    mean = sum(prices) / len(prices)
    std = (sum((p - mean) ** 2 for p in prices) / len(prices)) ** 0.5
    cv = std / mean if mean > 0 else 0

    # YoY change (porównaj Q[0] vs Q[4] jeśli dostępne)
    yoy_change = 0.0
    if len(prices) >= 4:
        yoy_change = (prices[0] - prices[min(4, len(prices) - 1)]) / prices[min(4, len(prices) - 1)]

    # Trend: regresja liniowa
    n = len(prices)
    x = list(range(n))
    slope = 0.0
    if n >= 3:
        x_mean = sum(x) / n
        y_mean = mean
        num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, prices))
        den = sum((xi - x_mean) ** 2 for xi in x)
        slope = (num / den) if den > 0 else 0.0
        # Znormalizuj slope per mean per quarter
        slope_norm = slope / mean if mean > 0 else 0.0
    else:
        slope_norm = 0.0

    # Composite risk score
    cv_score = min(cv * 3, 1.0)          # CV>0.33 → max
    yoy_score = min(abs(yoy_change) * 2, 1.0)
    trend_score = min(abs(slope_norm) * 4, 1.0) if slope_norm > 0 else 0.0

    score = round(0.4 * cv_score + 0.4 * yoy_score + 0.2 * trend_score, 3)

    if score >= 0.7:
        level = "high"
    elif score >= 0.4:
        level = "medium"
    else:
        level = "low"

    trend_dir = "rising" if slope_norm > 0.01 else ("falling" if slope_norm < -0.01 else "stable")

    return {
        "category": category,
        "score": score,
        "level": level,
        "cv": round(cv, 4),
        "yoy_change_pct": round(yoy_change * 100, 2),
        "trend": trend_dir,
        "slope_per_quarter_pct": round(slope_norm * 100, 3),
        "latest_avg": prices[0] if prices else None,
        "quarters_analyzed": len(prices),
    }


def get_all_material_risks(quarters: int = 8) -> list[dict]:
    """Risk score dla wszystkich kategorii materiałów."""
    engine = get_engine()
    with engine.connect() as conn:
        cats = conn.execute(sa.text("""
            SELECT DISTINCT category FROM icb_ceny_srednie
            WHERE typ_rms = 'M' AND category IS NOT NULL
            ORDER BY category
        """)).fetchall()

    results = []
    for (cat,) in cats:
        risk = get_material_risk_score(cat, quarters)
        results.append(risk)

    return sorted(results, key=lambda x: x["score"], reverse=True)


def forecast_price(
    category: str | None = None,
    symbol: str | None = None,
    typ_rms: str = "M",
    horizon_quarters: int = 4,
) -> dict:
    """Prognoza ceny na kolejne N kwartałów.

    Metoda: linear extrapolation na ostatnich 8Q (minimum viable).
    Jeśli Prophet dostępny — użyj Prophet.
    Zwraca przedziały: p10/p50/p90.
    """
    engine = get_engine()
    params: dict[str, Any] = {"typ": typ_rms}
    filters = ["typ_rms = :typ", "cena_netto > 0"]

    if symbol:
        filters.append("symbol = :sym")
        params["sym"] = symbol
    elif category:
        filters.append("category = :cat")
        params["cat"] = category

    where = " AND ".join(filters)

    with engine.connect() as conn:
        rows = conn.execute(sa.text(f"""
            SELECT kwartalrok, kwartalnr,
                   round(avg(cena_netto)::numeric, 4) as avg_price
            FROM icb_ceny_srednie
            WHERE {where}
            GROUP BY kwartalrok, kwartalnr
            ORDER BY kwartalrok, kwartalnr
        """), params).fetchall()

    if len(rows) < 4:
        return {"error": "Za mało danych do prognozy (min. 4 kwartały)"}

    # Zbuduj szereg czasowy
    prices = [float(r.avg_price) for r in rows if r.avg_price]
    n = len(prices)

    # Spróbuj Prophet
    try:
        import pandas as pd
        from prophet import Prophet

        periods = [f"{r.kwartalrok}-Q{r.kwartalnr}" for r in rows if r.avg_price]
        # Convert quarterly periods to date (środek kwartału)
        dates = []
        for r in rows:
            if r.avg_price:
                month = (r.kwartalnr - 1) * 3 + 2  # Feb/May/Aug/Nov
                dates.append(f"{r.kwartalrok}-{month:02d}-15")

        df = pd.DataFrame({"ds": pd.to_datetime(dates), "y": prices})
        m = Prophet(interval_width=0.8, yearly_seasonality=False, weekly_seasonality=False)
        m.fit(df)

        last_row = rows[-1]
        future_periods = horizon_quarters * 3  # months
        future = m.make_future_dataframe(periods=future_periods, freq="MS")
        forecast = m.predict(future)
        future_fc = forecast.tail(horizon_quarters * 3).iloc[::3]  # co kwartał

        forecasts = [
            {
                "period": str(row.ds)[:7],
                "p50": round(float(row.yhat), 2),
                "p10": round(float(row.yhat_lower), 2),
                "p90": round(float(row.yhat_upper), 2),
                "method": "prophet",
            }
            for _, row in future_fc.iterrows()
        ]
        return {
            "method": "prophet",
            "history_n": n,
            "forecasts": forecasts[:horizon_quarters],
        }

    except ImportError:
        pass
    except Exception as e:
        logger.warning("source=intelligence func=forecast_price: Prophet forecast failed: %s", e)

    # Fallback: linear trend z confidence interval
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(prices) / n

    num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, prices))
    den = sum((xi - x_mean) ** 2 for xi in x)
    slope = num / den if den > 0 else 0.0
    intercept = y_mean - slope * x_mean

    # Residual std
    residuals = [prices[i] - (intercept + slope * i) for i in range(n)]
    rmse = (sum(r ** 2 for r in residuals) / n) ** 0.5

    # Ostatni kwartał w danych
    last = rows[-1]
    last_q = last.kwartalnr
    last_y = last.kwartalrok

    forecasts = []
    for h in range(1, horizon_quarters + 1):
        q = last_q + h
        y = last_y + (q - 1) // 4
        q = ((q - 1) % 4) + 1
        pred = intercept + slope * (n - 1 + h)
        z = 1.28  # ~80% CI
        forecasts.append({
            "period": f"{y}-Q{q}",
            "p50": round(pred, 2),
            "p10": round(pred - z * rmse, 2),
            "p90": round(pred + z * rmse, 2),
            "method": "linear_trend",
        })

    return {
        "method": "linear_trend",
        "slope_per_quarter": round(slope, 4),
        "rmse": round(rmse, 4),
        "history_n": n,
        "forecasts": forecasts,
    }


def get_price_index(quarters: int = 8) -> list[dict]:
    """Zagregowany indeks cen budowlanych (composite R+M+S) per kwartał."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT kwartalrok, kwartalnr, typ_rms,
                   round(avg(cena_netto)::numeric, 2) as avg_price,
                   count(*) as n
            FROM icb_ceny_srednie
            WHERE cena_netto > 0 AND cena_netto < 50000
            GROUP BY kwartalrok, kwartalnr, typ_rms
            ORDER BY kwartalrok DESC, kwartalnr DESC, typ_rms
            LIMIT :n
        """), {"n": quarters * 3}).fetchall()

    # Pivot: per period → {R, M, S}
    from collections import defaultdict
    by_period: dict[str, dict] = defaultdict(dict)
    for r in rows:
        p = f"{r.kwartalrok}-Q{r.kwartalnr}"
        by_period[p][r.typ_rms] = float(r.avg_price)
        by_period[p]["rok"] = r.kwartalrok
        by_period[p]["kwartal"] = r.kwartalnr

    result = []
    for period, d in sorted(by_period.items(), reverse=True)[:quarters]:
        result.append({
            "period": period,
            "rok": d.get("rok"),
            "kwartal": d.get("kwartal"),
            "R_avg": d.get("R"),
            "M_avg": d.get("M"),
            "S_avg": d.get("S"),
        })

    return result
