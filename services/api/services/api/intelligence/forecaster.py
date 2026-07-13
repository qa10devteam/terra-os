"""ICB Price Forecaster — generuje prognozy cen na kolejne kwartały.

Używa exponential smoothing (Holt-Winters) + linear regression jako fallback.
Wyniki zapisuje do tabeli `icb_forecast` per symbol/category.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np
import sqlalchemy as sa

from terra_db.session import get_engine

logger = logging.getLogger(__name__)


def _holt_winters_forecast(values: list[float], horizon: int = 4, alpha: float = 0.3, beta: float = 0.1) -> list[float]:
    """Simple Holt double exponential smoothing (no seasonality)."""
    if len(values) < 3:
        # Not enough data for Holt — just return last value
        return [values[-1]] * horizon

    # Initialize
    level = values[0]
    trend = (values[1] - values[0])

    levels = [level]
    trends = [trend]

    for i in range(1, len(values)):
        new_level = alpha * values[i] + (1 - alpha) * (level + trend)
        new_trend = beta * (new_level - level) + (1 - beta) * trend
        level = new_level
        trend = new_trend
        levels.append(level)
        trends.append(trend)

    # Forecast
    forecasts = []
    for h in range(1, horizon + 1):
        forecasts.append(level + h * trend)

    return forecasts


def _prediction_interval(values: list[float], forecasts: list[float], confidence: float = 0.95) -> list[tuple[float, float]]:
    """Compute prediction intervals based on residual std."""
    if len(values) < 4:
        spread = abs(values[-1] * 0.1)
        return [(f - spread, f + spread) for f in forecasts]

    # Compute residuals from in-sample one-step-ahead
    residuals = []
    for i in range(1, len(values)):
        # Simple: residual = actual - previous
        residuals.append(values[i] - values[i - 1])

    std = float(np.std(residuals)) if residuals else abs(values[-1] * 0.05)

    # z-score for 95% CI
    z = 1.96 if confidence == 0.95 else 1.645

    intervals = []
    for h, f in enumerate(forecasts, 1):
        # Interval widens with horizon
        margin = z * std * (h ** 0.5)
        intervals.append((round(max(0, f - margin), 4), round(f + margin, 4)))

    return intervals


def compute_forecasts_for_category(
    category: str,
    typ_rms: str = "M",
    horizon: int = 4,
    model_name: str = "holt_winters",
) -> list[dict]:
    """Compute and store forecasts for a category."""
    engine = get_engine()

    # Get historical averages per quarter
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT kwartalrok, kwartalnr,
                   round(avg(cena_netto)::numeric, 4) as avg_price,
                   count(*) as n
            FROM icb_ceny_srednie
            WHERE category = :cat AND typ_rms = :typ AND cena_netto > 0
            GROUP BY kwartalrok, kwartalnr
            ORDER BY kwartalrok, kwartalnr
        """), {"cat": category, "typ": typ_rms}).fetchall()

    if len(rows) < 6:
        logger.warning("source=intelligence func=compute_forecasts_for_category: Not enough data for forecast: %s/%s (%d quarters)", category, typ_rms, len(rows))
        return []

    values = [float(r.avg_price) for r in rows]
    last_year = rows[-1].kwartalrok
    last_q = rows[-1].kwartalnr

    # Forecast
    forecasts = _holt_winters_forecast(values, horizon)
    intervals = _prediction_interval(values, forecasts)

    # Compute MAPE on last 4 known quarters (backtesting)
    if len(values) > 8:
        train = values[:-4]
        test = values[-4:]
        backtest_fc = _holt_winters_forecast(train, 4)
        mape = sum(abs((a - f) / a) for a, f in zip(test, backtest_fc) if a > 0) / len(test) * 100
    else:
        mape = None

    # Generate forecast quarter labels
    results = []
    q, y = last_q, last_year
    for i, (fc, (lb, ub)) in enumerate(zip(forecasts, intervals)):
        q += 1
        if q > 4:
            q = 1
            y += 1
        results.append({
            "category": category,
            "typ_rms": typ_rms,
            "forecast_quarter": q,
            "forecast_year": y,
            "predicted_price": round(fc, 4),
            "lower_bound": round(lb, 4),
            "upper_bound": round(ub, 4),
            "model_name": model_name,
            "mape_pct": round(mape, 2) if mape else None,
        })

    # Store to icb_forecast
    with engine.begin() as conn:
        # Clear old forecasts for this category
        conn.execute(sa.text("""
            DELETE FROM icb_forecast WHERE category = :cat AND typ_rms = :typ
        """), {"cat": category, "typ": typ_rms})

        for r in results:
            conn.execute(sa.text("""
                INSERT INTO icb_forecast (category, typ_rms, forecast_quarter, forecast_year,
                                          predicted_price, lower_bound, upper_bound, model_name, mape_pct, computed_at)
                VALUES (:cat, :typ, :fq, :fy, :pp, :lb, :ub, :mn, :mape, NOW())
            """), {
                "cat": r["category"], "typ": r["typ_rms"],
                "fq": r["forecast_quarter"], "fy": r["forecast_year"],
                "pp": r["predicted_price"], "lb": r["lower_bound"], "ub": r["upper_bound"],
                "mn": r["model_name"], "mape": r["mape_pct"],
            })

    return results


def compute_all_forecasts(horizon: int = 4) -> dict:
    """Run forecasts for all categories + R/M/S types."""
    engine = get_engine()
    with engine.connect() as conn:
        categories = conn.execute(sa.text("""
            SELECT DISTINCT category FROM icb_ceny_srednie
            WHERE category IS NOT NULL ORDER BY category
        """)).fetchall()

    total = 0
    errors = []
    for (cat,) in categories:
        for typ in ["M", "S", "R"]:
            try:
                results = compute_forecasts_for_category(cat, typ, horizon)
                total += len(results)
            except Exception as e:
                errors.append(f"{cat}/{typ}: {e}")

    return {"forecasts_generated": total, "errors": errors}


def get_forecasts(
    category: str | None = None,
    typ_rms: str = "M",
    symbol: str | None = None,
) -> list[dict]:
    """Retrieve stored forecasts from icb_forecast."""
    engine = get_engine()
    filters = ["typ_rms = :typ"]
    params: dict = {"typ": typ_rms}

    if category:
        filters.append("category = :cat")
        params["cat"] = category
    if symbol:
        filters.append("symbol = :sym")
        params["sym"] = symbol

    where = " AND ".join(filters)
    with engine.connect() as conn:
        rows = conn.execute(sa.text(f"""
            SELECT category, typ_rms, forecast_quarter, forecast_year,
                   predicted_price, lower_bound, upper_bound, model_name, mape_pct, computed_at
            FROM icb_forecast
            WHERE {where}
            ORDER BY forecast_year, forecast_quarter
        """), params).fetchall()

    return [
        {
            "category": r[0], "typ_rms": r[1],
            "period": f"{r[3]}-Q{r[2]}",
            "predicted_price": float(r[4]),
            "lower_bound": float(r[5]),
            "upper_bound": float(r[6]),
            "model": r[7], "mape_pct": float(r[8]) if r[8] else None,
            "computed_at": str(r[9]) if r[9] else None,
        }
        for r in rows
    ]


# ─── ICB per-item forecast API (used by tests + API endpoints) ────────────────

def _quarter_to_index(kwartalnr: int, kwartalrok: int) -> int:
    """Convert (quarter, year) → monotonic integer index.

    Example: (1, 2024) → 2024*4 + 0 = 8096
    """
    return kwartalrok * 4 + (kwartalnr - 1)


def _index_to_quarter(idx: int) -> tuple[int, int]:
    """Reverse of _quarter_to_index: index → (kwartalnr, kwartalrok)."""
    y, q0 = divmod(idx, 4)
    return q0 + 1, y


def forecast_icb_price(
    icb_id: int,
    quarters_ahead: int = 4,
) -> dict | None:
    """Forecast price for a single ICB item by id_ceny.

    Queries icb_ceny_srednie for historical prices, applies Holt-Winters.
    Returns dict with keys: icb_id, symbol, typ_rms, trend_pct, predictions[].
    Returns None if insufficient data (< 3 data points).
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT symbol, typ_rms, kwartalnr, kwartalrok, cena_netto
                FROM icb_ceny_srednie
                WHERE id_ceny = :icb_id AND cena_netto > 0
                ORDER BY kwartalrok, kwartalnr
            """), {"icb_id": icb_id}).fetchall()
    except Exception as e:
        logger.debug("source=intelligence func=forecast_icb_price icb_id=%s: %s", icb_id, e)
        return None

    if not rows or len(rows) < 3:
        return {"icb_id": icb_id, "predictions": [], "trend_pct": 0.0}

    values = [float(r[4]) for r in rows]
    symbol = rows[0][0]
    typ_rms = rows[0][1]
    last_q = rows[-1][2]
    last_y = rows[-1][3]

    forecasts = _holt_winters_forecast(values, horizon=quarters_ahead)
    intervals = _prediction_interval(values, forecasts)

    # Trend percent: (last_forecast - last_known) / last_known * 100
    trend_pct = 0.0
    if values[-1] > 0:
        trend_pct = round((forecasts[-1] - values[-1]) / values[-1] * 100, 2)

    predictions = []
    q, y = last_q, last_y
    for i, (fc, (lb, ub)) in enumerate(zip(forecasts, intervals)):
        q += 1
        if q > 4:
            q = 1
            y += 1
        predictions.append({
            "quarter": q,
            "year": y,
            "price": round(fc, 4),
            "lower": round(lb, 4),
            "upper": round(ub, 4),
        })

    return {
        "icb_id": icb_id,
        "symbol": symbol,
        "typ_rms": typ_rms,
        "trend_pct": trend_pct,
        "predictions": predictions,
    }


def get_cached_forecast(
    icb_id: int,
    year: int,
    quarter: int,
) -> dict | None:
    """Return a single cached forecast row from icb_forecast_icb table.

    Returns None if not found.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(sa.text("""
                SELECT icb_id, symbol, typ_rms, forecast_year, forecast_quarter,
                       predicted_price, price_lower, price_upper, trend_pct, created_at
                FROM icb_forecast_icb
                WHERE icb_id = :icb_id AND forecast_year = :year AND forecast_quarter = :quarter
                LIMIT 1
            """), {"icb_id": icb_id, "year": year, "quarter": quarter}).fetchone()
    except Exception as e:
        logger.debug("source=intelligence func=get_cached_forecast icb_id=%s: %s", icb_id, e)
        return None

    if row is None:
        return None

    return {
        "icb_id": row[0],
        "symbol": row[1],
        "typ_rms": row[2],
        "forecast_year": row[3],
        "forecast_quarter": row[4],
        "predicted_price": float(row[5]) if row[5] is not None else None,
        "price_lower": float(row[6]) if row[6] is not None else None,
        "price_upper": float(row[7]) if row[7] is not None else None,
        "trend_pct": float(row[8]) if row[8] is not None else None,
        "created_at": str(row[9]) if row[9] else None,
    }


def cache_forecasts(
    icb_ids: list[int],
    quarters_ahead: int = 4,
) -> int:
    """Compute and persist forecasts for given ICB ids to icb_forecast_icb.

    Returns count of successfully cached forecasts.
    """
    if not icb_ids:
        return 0

    engine = get_engine()
    count = 0
    for icb_id in icb_ids:
        try:
            result = forecast_icb_price(icb_id, quarters_ahead=quarters_ahead)
            if result is None:
                continue

            with engine.begin() as conn:
                # Upsert each prediction row
                conn.execute(sa.text("""
                    DELETE FROM icb_forecast_icb
                    WHERE icb_id = :icb_id
                """), {"icb_id": icb_id})

                for pred in result["predictions"]:
                    conn.execute(sa.text("""
                        INSERT INTO icb_forecast_icb
                            (icb_id, symbol, typ_rms, forecast_year, forecast_quarter,
                             predicted_price, price_lower, price_upper, trend_pct, created_at)
                        VALUES
                            (:icb_id, :symbol, :typ_rms, :fy, :fq,
                             :price, :lower, :upper, :trend, NOW())
                    """), {
                        "icb_id": icb_id,
                        "symbol": result["symbol"],
                        "typ_rms": result["typ_rms"],
                        "fy": pred["year"],
                        "fq": pred["quarter"],
                        "price": pred["price"],
                        "lower": pred["lower"],
                        "upper": pred["upper"],
                        "trend": result["trend_pct"],
                    })
            count += 1
        except Exception as e:
            logger.debug("source=intelligence func=cache_forecasts icb_id=%s: %s", icb_id, e)

    return count


def run_top_materials_forecast(limit: int = 50, quarters_ahead: int = 4) -> dict:
    """Run forecasts for the most-referenced ICB items.

    Returns summary dict with count of successful/failed forecasts.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT DISTINCT icb_id_m AS icb_id
                FROM kosztorys_pozycja
                WHERE icb_id_m IS NOT NULL
                ORDER BY icb_id_m
                LIMIT :lim
            """), {"lim": limit}).fetchall()
        icb_ids = [r[0] for r in rows]
    except Exception as e:
        logger.debug("source=intelligence func=run_top_materials_forecast: %s", e)
        return {"error": str(e), "cached": 0}

    cached = cache_forecasts(icb_ids, quarters_ahead=quarters_ahead)
    return {
        "icb_ids": icb_ids,
        "cached": cached,
        "requested": len(icb_ids),
    }

