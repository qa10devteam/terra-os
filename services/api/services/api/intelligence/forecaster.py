"""
ICB Price Forecaster — predicts price trends for ICB categories.
Uses linear regression (numpy) as default, Prophet if installed.
Output cached in icb_forecast table.
"""
import logging
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from terra_db.session import get_engine

logger = logging.getLogger(__name__)


def _quarter_to_index(kwartalnr: int, kwartalrok: int) -> int:
    """Convert quarter/year to a monotonic integer index for regression."""
    return kwartalrok * 4 + (kwartalnr - 1)


def _index_to_quarter(index: int) -> tuple[int, int]:
    """Convert monotonic index back to (quarter, year)."""
    year = index // 4
    quarter = (index % 4) + 1
    return quarter, year


def forecast_icb_price(icb_id: int, quarters_ahead: int = 4) -> dict:
    """
    Predict price trend for a given ICB item.

    Fetches last 12 quarters of price data from icb_ceny_srednie,
    fits a linear regression (numpy polyfit degree=1), and returns
    forecasted prices with ±1.5 * std(residuals) confidence intervals.

    Returns:
        dict with keys: icb_id, symbol, typ_rms, predictions, trend_pct
        or empty dict on error/no data.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT symbol, typ_rms, kwartalnr, kwartalrok, cena_netto
                    FROM icb_ceny_srednie
                    WHERE id_ceny = :icb_id
                      AND cena_netto IS NOT NULL
                    ORDER BY kwartalrok DESC, kwartalnr DESC
                    LIMIT 12
                    """
                ),
                {"icb_id": icb_id},
            ).fetchall()
    except SQLAlchemyError:
        logger.exception("DB error fetching ICB price data for icb_id=%s", icb_id)
        return {}

    if not rows:
        logger.warning("No price data found for icb_id=%s", icb_id)
        return {}

    symbol = rows[0][0]
    typ_rms = rows[0][1]

    # Build time-series arrays (oldest first)
    data = sorted(rows, key=lambda r: (r[3], r[2]))  # sort by year, quarter
    indices = np.array([_quarter_to_index(r[2], r[3]) for r in data], dtype=float)
    prices = np.array([float(r[4]) for r in data], dtype=float)

    if len(prices) < 2:
        logger.warning("Insufficient data points for regression: icb_id=%s", icb_id)
        return {
            "icb_id": icb_id,
            "symbol": symbol,
            "typ_rms": typ_rms,
            "predictions": [],
            "trend_pct": 0.0,
        }

    # Linear regression
    coeffs = np.polyfit(indices, prices, deg=1)
    poly = np.poly1d(coeffs)

    # Residual std for confidence interval
    residuals = prices - poly(indices)
    residual_std = float(np.std(residuals))
    ci = 1.5 * residual_std

    # Trend percentage: slope over first price
    last_index = indices[-1]
    first_price = float(poly(indices[0]))
    slope = float(coeffs[0])  # price change per quarter
    trend_pct = (slope * len(indices) / first_price * 100.0) if first_price != 0 else 0.0

    # Generate future predictions
    predictions = []
    for i in range(1, quarters_ahead + 1):
        future_index = last_index + i
        pred_price = float(poly(future_index))
        q, y = _index_to_quarter(int(future_index))
        predictions.append(
            {
                "quarter": q,
                "year": y,
                "price": round(pred_price, 4),
                "lower": round(pred_price - ci, 4),
                "upper": round(pred_price + ci, 4),
            }
        )

    return {
        "icb_id": icb_id,
        "symbol": symbol,
        "typ_rms": typ_rms,
        "predictions": predictions,
        "trend_pct": round(trend_pct, 4),
    }


def cache_forecasts(icb_ids: list[int], quarters_ahead: int = 4) -> int:
    """
    Compute and cache forecasts for a list of ICB IDs.

    For each icb_id, calls forecast_icb_price and upserts each
    predicted quarter into the icb_forecast table.

    Returns:
        Total count of cached forecast entries inserted/updated.
    """
    engine = get_engine()
    cached_count = 0

    for icb_id in icb_ids:
        forecast = forecast_icb_price(icb_id, quarters_ahead=quarters_ahead)
        if not forecast or not forecast.get("predictions"):
            continue

        for pred in forecast["predictions"]:
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            INSERT INTO icb_forecast
                                (icb_id, symbol, typ_rms, forecast_year, forecast_quarter,
                                 predicted_price, price_lower, price_upper, trend_pct, created_at)
                            VALUES
                                (:icb_id, :symbol, :typ_rms, :year, :quarter,
                                 :price, :lower, :upper, :trend_pct, NOW())
                            ON CONFLICT (icb_id, forecast_year, forecast_quarter)
                            DO UPDATE SET
                                predicted_price = EXCLUDED.predicted_price,
                                price_lower     = EXCLUDED.price_lower,
                                price_upper     = EXCLUDED.price_upper,
                                trend_pct       = EXCLUDED.trend_pct,
                                created_at      = NOW()
                            """
                        ),
                        {
                            "icb_id": icb_id,
                            "symbol": forecast["symbol"],
                            "typ_rms": forecast["typ_rms"],
                            "year": pred["year"],
                            "quarter": pred["quarter"],
                            "price": pred["price"],
                            "lower": pred["lower"],
                            "upper": pred["upper"],
                            "trend_pct": forecast["trend_pct"],
                        },
                    )
                cached_count += 1
            except SQLAlchemyError:
                logger.exception(
                    "DB error caching forecast for icb_id=%s quarter=%s/%s",
                    icb_id,
                    pred["quarter"],
                    pred["year"],
                )

    logger.info("cache_forecasts: cached %d entries for %d ICB IDs", cached_count, len(icb_ids))
    return cached_count


def get_cached_forecast(icb_id: int, year: int, quarter: int) -> Optional[dict]:
    """
    Retrieve a previously cached forecast for a given ICB item and quarter.

    Returns:
        dict with forecast data or None if not found.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT icb_id, symbol, typ_rms, forecast_year, forecast_quarter,
                           predicted_price, price_lower, price_upper, trend_pct, created_at
                    FROM icb_forecast
                    WHERE icb_id = :icb_id
                      AND forecast_year = :year
                      AND forecast_quarter = :quarter
                    LIMIT 1
                    """
                ),
                {"icb_id": icb_id, "year": year, "quarter": quarter},
            ).fetchone()
    except SQLAlchemyError:
        logger.exception(
            "DB error fetching cached forecast for icb_id=%s %s/Q%s", icb_id, year, quarter
        )
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
        "created_at": row[9].isoformat() if isinstance(row[9], datetime) else str(row[9]),
    }


def run_top_materials_forecast(limit: int = 100) -> dict:
    """
    Find the top `limit` most-used ICB items and cache their forecasts.

    Selects items by entry count in icb_ceny_srednie (proxy for usage frequency).

    Returns:
        dict with 'cached' (int) and 'icb_ids' (list[int]).
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id_ceny, COUNT(*) AS cnt
                    FROM icb_ceny_srednie
                    GROUP BY id_ceny
                    ORDER BY cnt DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).fetchall()
    except SQLAlchemyError:
        logger.exception("DB error fetching top ICB items")
        return {"cached": 0, "icb_ids": []}

    icb_ids = [int(row[0]) for row in rows]
    if not icb_ids:
        logger.warning("run_top_materials_forecast: no ICB items found")
        return {"cached": 0, "icb_ids": []}

    cached = cache_forecasts(icb_ids)
    logger.info("run_top_materials_forecast: cached %d entries for %d items", cached, len(icb_ids))
    return {"cached": cached, "icb_ids": icb_ids}
