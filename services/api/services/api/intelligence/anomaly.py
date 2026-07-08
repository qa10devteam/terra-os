"""
Anomaly Detection for Kosztorys Pozycje.

Computes z-scores for R/M/S unit prices relative to ICB market averages.
Optionally applies Isolation Forest (sklearn) for multivariate anomaly detection.
Results are persisted back into kosztorys_pozycja and kosztorys tables.
"""
import logging
from typing import Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from terra_db.session import get_engine

logger = logging.getLogger(__name__)

_ANOMALY_ZSCORE_THRESHOLD = 2.5


def _try_isolation_forest(
    feature_matrix: np.ndarray,
) -> Optional[list[bool]]:
    """
    Try to run Isolation Forest on the given feature matrix.
    Returns list of booleans (True = anomaly) or None if sklearn unavailable.
    """
    try:
        from sklearn.ensemble import IsolationForest  # type: ignore[import]
    except ImportError:
        logger.debug("sklearn not available; skipping Isolation Forest")
        return None

    if feature_matrix.shape[0] < 5 or feature_matrix.shape[1] < 1:
        return None

    try:
        clf = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        preds = clf.fit_predict(feature_matrix)
        return [bool(p == -1) for p in preds]
    except Exception:
        logger.exception("IsolationForest failed; skipping")
        return None


def zscore_pozycja(pozycja_id: str) -> dict:
    """
    Compute z-scores for a single kosztorys_pozycja against ICB market prices.

    Fetches the pozycja's r_jcena, m_jcena, s_jcena and compares each to
    the distribution of prices in icb_ceny_srednie for the same symbol/category
    in the latest available quarter.

    Args:
        pozycja_id: UUID string of the kosztorys_pozycja row.

    Returns:
        dict with pozycja_id, r_zscore, m_zscore, s_zscore, is_anomaly.
        Returns a safe default on error.
    """
    _default = {
        "pozycja_id": pozycja_id,
        "r_zscore": None,
        "m_zscore": None,
        "s_zscore": None,
        "is_anomaly": False,
    }

    engine = get_engine()
    try:
        with engine.connect() as conn:
            pozycja = conn.execute(
                text(
                    """
                    SELECT r_jcena, m_jcena, s_jcena, symbol, kategoria
                    FROM kosztorys_pozycja
                    WHERE id = :pozycja_id
                    LIMIT 1
                    """
                ),
                {"pozycja_id": pozycja_id},
            ).fetchone()
    except SQLAlchemyError:
        logger.exception("DB error fetching pozycja id=%s", pozycja_id)
        return _default

    if pozycja is None:
        logger.warning("pozycja not found: id=%s", pozycja_id)
        return _default

    r_jcena, m_jcena, s_jcena, symbol, kategoria = (
        pozycja[0],
        pozycja[1],
        pozycja[2],
        pozycja[3],
        pozycja[4],
    )

    # Fetch ICB price distribution for the same symbol, latest quarter per typ_rms
    def _get_icb_stats(typ: str) -> tuple[Optional[float], Optional[float]]:
        try:
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        """
                        SELECT cena_netto
                        FROM icb_ceny_srednie
                        WHERE symbol = :symbol
                          AND typ_rms = :typ
                          AND (kwartalrok, kwartalnr) = (
                              SELECT kwartalrok, kwartalnr
                              FROM icb_ceny_srednie
                              WHERE symbol = :symbol AND typ_rms = :typ
                              ORDER BY kwartalrok DESC, kwartalnr DESC
                              LIMIT 1
                          )
                          AND cena_netto IS NOT NULL
                        """
                    ),
                    {"symbol": symbol, "typ": typ},
                ).fetchall()
        except SQLAlchemyError:
            logger.exception("DB error fetching ICB stats symbol=%s typ=%s", symbol, typ)
            return None, None

        prices = [float(r[0]) for r in rows if r[0] is not None]
        if len(prices) < 2:
            return None, None
        return float(np.mean(prices)), float(np.std(prices))

    def _zscore(value: Optional[float], mean: Optional[float], std: Optional[float]) -> Optional[float]:
        if value is None or mean is None or std is None or std == 0:
            return None
        return round((float(value) - mean) / std, 4)

    r_mean, r_std = _get_icb_stats("R")
    m_mean, m_std = _get_icb_stats("M")
    s_mean, s_std = _get_icb_stats("S")

    r_zscore = _zscore(r_jcena, r_mean, r_std)
    m_zscore = _zscore(m_jcena, m_mean, m_std)
    s_zscore = _zscore(s_jcena, s_mean, s_std)

    is_anomaly = any(
        z is not None and abs(z) > _ANOMALY_ZSCORE_THRESHOLD
        for z in (r_zscore, m_zscore, s_zscore)
    )

    return {
        "pozycja_id": pozycja_id,
        "r_zscore": r_zscore,
        "m_zscore": m_zscore,
        "s_zscore": s_zscore,
        "is_anomaly": is_anomaly,
    }


def analyze_kosztorys(kosztorys_id: str, tenant_id: str) -> dict:
    """
    Run full anomaly analysis on all pozycje of a kosztorys.

    Steps:
    1. Fetch all pozycje for the kosztorys (tenant-isolated).
    2. Compute z-scores for each pozycja.
    3. Optionally run Isolation Forest for multivariate detection.
    4. Persist z-scores and is_anomaly flag back to kosztorys_pozycja.
    5. Compute and persist kosztorys-level anomaly_score.

    Args:
        kosztorys_id: UUID of the kosztorys.
        tenant_id:    Tenant identifier for row isolation.

    Returns:
        dict with analysis summary.
    """
    _empty = {
        "kosztorys_id": kosztorys_id,
        "pozycje_analyzed": 0,
        "anomalies_found": 0,
        "anomaly_score": 0.0,
        "anomalous_pozycje": [],
    }

    engine = get_engine()

    # 1. Fetch all pozycje
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT kp.id, kp.r_jcena, kp.m_jcena, kp.s_jcena
                    FROM kosztorys_pozycja kp
                    JOIN kosztorys k ON k.id = kp.kosztorys_id
                    WHERE kp.kosztorys_id = :kosztorys_id
                      AND k.tenant_id = :tenant_id
                    """
                ),
                {"kosztorys_id": kosztorys_id, "tenant_id": tenant_id},
            ).fetchall()
    except SQLAlchemyError:
        logger.exception("DB error fetching pozycje for kosztorys_id=%s", kosztorys_id)
        return _empty

    if not rows:
        logger.warning("No pozycje found for kosztorys_id=%s tenant_id=%s", kosztorys_id, tenant_id)
        return _empty

    pozycja_ids = [str(r[0]) for r in rows]
    pozycje_prices = [(r[1], r[2], r[3]) for r in rows]  # (r, m, s)

    # 2. Z-score analysis
    zscore_results: list[dict] = []
    for pid in pozycja_ids:
        result = zscore_pozycja(pid)
        zscore_results.append(result)

    # 3. Optional Isolation Forest on (r_jcena, m_jcena, s_jcena)
    iso_anomalies: Optional[list[bool]] = None
    feature_rows = []
    for r, m, s in pozycje_prices:
        feature_rows.append([
            float(r) if r is not None else 0.0,
            float(m) if m is not None else 0.0,
            float(s) if s is not None else 0.0,
        ])

    if len(feature_rows) >= 5:
        feature_matrix = np.array(feature_rows)
        iso_anomalies = _try_isolation_forest(feature_matrix)

    # Merge isolation forest results
    if iso_anomalies is not None:
        for i, zr in enumerate(zscore_results):
            if iso_anomalies[i]:
                zr["is_anomaly"] = True

    # 4. Persist z-scores to kosztorys_pozycja
    for zr in zscore_results:
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE kosztorys_pozycja
                        SET r_zscore   = :r_zscore,
                            m_zscore   = :m_zscore,
                            s_zscore   = :s_zscore,
                            is_anomaly = :is_anomaly
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": zr["pozycja_id"],
                        "r_zscore": zr["r_zscore"],
                        "m_zscore": zr["m_zscore"],
                        "s_zscore": zr["s_zscore"],
                        "is_anomaly": zr["is_anomaly"],
                    },
                )
        except SQLAlchemyError:
            logger.exception("DB error updating z-scores for pozycja_id=%s", zr["pozycja_id"])

    # 5. Compute and persist anomaly_score
    anomalous_ids = [zr["pozycja_id"] for zr in zscore_results if zr["is_anomaly"]]
    anomaly_score = len(anomalous_ids) / len(zscore_results) if zscore_results else 0.0

    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE kosztorys
                    SET anomaly_score = :score
                    WHERE id = :id
                      AND tenant_id = :tenant_id
                    """
                ),
                {"score": anomaly_score, "id": kosztorys_id, "tenant_id": tenant_id},
            )
    except SQLAlchemyError:
        logger.exception("DB error updating anomaly_score for kosztorys_id=%s", kosztorys_id)

    return {
        "kosztorys_id": kosztorys_id,
        "pozycje_analyzed": len(zscore_results),
        "anomalies_found": len(anomalous_ids),
        "anomaly_score": round(anomaly_score, 4),
        "anomalous_pozycje": anomalous_ids,
    }


def get_anomalies(kosztorys_id: str, tenant_id: str) -> list[dict]:
    """
    Fetch all anomalous pozycje for a given kosztorys.

    Args:
        kosztorys_id: UUID of the kosztorys.
        tenant_id:    Tenant identifier for row isolation.

    Returns:
        List of dicts with pozycja details and z-scores.
        Returns empty list on error.
    """
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT
                        kp.id, kp.symbol, kp.nazwa, kp.kategoria,
                        kp.r_jcena, kp.m_jcena, kp.s_jcena,
                        kp.r_zscore, kp.m_zscore, kp.s_zscore,
                        kp.is_anomaly
                    FROM kosztorys_pozycja kp
                    JOIN kosztorys k ON k.id = kp.kosztorys_id
                    WHERE kp.kosztorys_id = :kosztorys_id
                      AND k.tenant_id = :tenant_id
                      AND kp.is_anomaly = TRUE
                    ORDER BY
                        GREATEST(
                            ABS(COALESCE(kp.r_zscore, 0)),
                            ABS(COALESCE(kp.m_zscore, 0)),
                            ABS(COALESCE(kp.s_zscore, 0))
                        ) DESC
                    """
                ),
                {"kosztorys_id": kosztorys_id, "tenant_id": tenant_id},
            ).fetchall()
    except SQLAlchemyError:
        logger.exception(
            "DB error fetching anomalies for kosztorys_id=%s tenant_id=%s",
            kosztorys_id,
            tenant_id,
        )
        return []

    return [
        {
            "pozycja_id": str(r[0]),
            "symbol": r[1],
            "nazwa": r[2],
            "kategoria": r[3],
            "r_jcena": float(r[4]) if r[4] is not None else None,
            "m_jcena": float(r[5]) if r[5] is not None else None,
            "s_jcena": float(r[6]) if r[6] is not None else None,
            "r_zscore": float(r[7]) if r[7] is not None else None,
            "m_zscore": float(r[8]) if r[8] is not None else None,
            "s_zscore": float(r[9]) if r[9] is not None else None,
            "is_anomaly": bool(r[10]),
        }
        for r in rows
    ]
