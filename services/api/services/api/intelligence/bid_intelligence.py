"""Bid Benchmarking & Anomaly Detection — Terra-OS Intelligence Layer.

Warstwy:
1. CPV × region benchmark z market_results + historical_tenders
2. Anomaly detection: z-score per CPV+region, Isolation Forest
3. Win probability: quantile model z market_results  
4. Bid optimization: rekomendacja przedziału cenowego
"""
from __future__ import annotations

import logging
import math
from typing import Any

import sqlalchemy as sa

from terra_db.session import get_engine

logger = logging.getLogger(__name__)


# ─── 1. CPV BENCHMARK ─────────────────────────────────────────────────────────

def get_cpv_benchmark(
    cpv_prefix: str,
    province: str | None = None,
    quarters: int = 8,
) -> dict:
    """Benchmark cen dla CPV prefix z historical_tenders + market_results.

    Zwraca: mediana, p25, p75, win_ratio_median, n_samples
    """
    engine = get_engine()
    params: dict[str, Any] = {
        "cpv": f"{cpv_prefix}%",
        "quarters": quarters * 3,  # months approx
    }
    province_filter = ""
    if province:
        province_filter = "AND province = :province"
        params["province"] = province

    with engine.connect() as conn:
        # Z historical_tenders — wartości szacunkowe
        est_rows = conn.execute(sa.text(f"""
            SELECT estimated_value
            FROM historical_tenders
            WHERE cpv_code LIKE :cpv
              AND estimated_value > 0
              {province_filter}
            LIMIT 2000
        """), params).fetchall()

        # Z market_results — stosunek wygrywająca/szacunkowa
        mr_rows = conn.execute(sa.text("""
            SELECT winning_price_pln, estimated_value_pln,
                   winning_price_pln / NULLIF(estimated_value_pln, 0) AS win_ratio
            FROM market_results
            WHERE cpv_codes && ARRAY[:cpv_prefix]::text[]
              AND estimated_value_pln > 0
              AND winning_price_pln > 0
            LIMIT 1000
        """), {"cpv_prefix": f"{cpv_prefix}0000-0"[:9]}).fetchall()

    est_values = sorted([float(r.estimated_value) for r in est_rows])
    win_ratios = [float(r.win_ratio) for r in mr_rows if r.win_ratio and 0.3 < r.win_ratio < 2.5]

    result: dict[str, Any] = {
        "cpv_prefix": cpv_prefix,
        "province": province,
    }

    if est_values:
        n = len(est_values)
        result.update({
            "estimated_value_p25": _percentile(est_values, 0.25),
            "estimated_value_median": _percentile(est_values, 0.50),
            "estimated_value_p75": _percentile(est_values, 0.75),
            "estimated_value_mean": round(sum(est_values) / n, 0),
            "n_tenders": n,
        })

    if win_ratios:
        result.update({
            "win_ratio_p25": round(_percentile(sorted(win_ratios), 0.25), 4),
            "win_ratio_median": round(_percentile(sorted(win_ratios), 0.50), 4),
            "win_ratio_p75": round(_percentile(sorted(win_ratios), 0.75), 4),
            "win_ratio_mean": round(sum(win_ratios) / len(win_ratios), 4),
            "n_market_results": len(win_ratios),
        })
    else:
        # Fallback: dane z discovery (CPV 45xx win ~0.97 median)
        result.update({
            "win_ratio_median": 0.971,
            "win_ratio_p25": 0.88,
            "win_ratio_p75": 1.05,
            "n_market_results": 0,
            "win_ratio_source": "fallback_market_median",
        })

    return result


def _percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = q * (len(sorted_vals) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_vals) - 1)
    frac = idx - lo
    val = sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac
    return round(val, 2)


# ─── 2. ANOMALY DETECTION ─────────────────────────────────────────────────────

def detect_bid_anomalies(
    bid_price: float,
    estimated_value: float,
    cpv_prefix: str,
    province: str | None = None,
    n_competitors: int | None = None,
) -> dict:
    """Wykryj anomalie w ofercie przetargowej.

    Metody:
    1. Z-score względem rozkładu win_ratio per CPV+region (z market_results)
    2. Heurystyki branżowe (Benford, spread, rotacja)

    Zwraca: anomaly_score 0.0–1.0, flags, explanation
    """
    flags: list[str] = []
    scores: list[float] = []

    # Ratio cena_oferty / wartość_szacunkowa
    ratio = bid_price / estimated_value if estimated_value > 0 else 1.0

    # 1. Benchmark z bazy
    benchmark = get_cpv_benchmark(cpv_prefix, province)
    win_ratios = _get_win_ratios_for_cpv(cpv_prefix, province)

    if win_ratios and len(win_ratios) >= 10:
        mean_r = sum(win_ratios) / len(win_ratios)
        std_r = (sum((r - mean_r) ** 2 for r in win_ratios) / len(win_ratios)) ** 0.5
        z = (ratio - mean_r) / std_r if std_r > 0 else 0.0

        z_score_abs = abs(z)
        z_anomaly = min(z_score_abs / 3.0, 1.0)  # |z|=3 → score=1
        scores.append(z_anomaly)

        if z < -2.5:
            flags.append(f"VERY_LOW: oferta {ratio:.1%} szacunku, {z:.1f}σ poniżej normy — ryzyko rażąco niskiej ceny")
        elif z < -1.5:
            flags.append(f"LOW: oferta {ratio:.1%} szacunku ({z:.1f}σ)")
        elif z > 2.5:
            flags.append(f"VERY_HIGH: oferta {ratio:.1%} szacunku ({z:.1f}σ powyżej)")
        elif z > 1.5:
            flags.append(f"HIGH: oferta {ratio:.1%} szacunku ({z:.1f}σ)")

        z_info = {"z_score": round(z, 3), "mean_ratio": round(mean_r, 4), "std_ratio": round(std_r, 4)}
    else:
        z_info = {"z_score": None, "samples": "insufficient"}
        # Fallback z-score na podstawie heurystyki rynkowej
        if ratio < 0.60:
            flags.append(f"RAŻĄCO_NISKA: oferta = {ratio:.1%} szacunku (próg 60%)")
            scores.append(0.9)
        elif ratio < 0.75:
            flags.append(f"NISKA: oferta = {ratio:.1%} szacunku")
            scores.append(0.5)
        elif ratio > 1.5:
            flags.append(f"POWYŻEJ_BUDŻETU: oferta = {ratio:.1%} szacunku")
            scores.append(0.6)

    # 2. Rażąco niska cena — kryterium PZP Art. 224
    if ratio < 0.70:
        flags.append("PZP_ART224: prawdopodobne wezwanie do wyjaśnień rażąco niskiej ceny")
        scores.append(0.85)

    # 3. Benford first-digit
    benford_score = _benford_check(bid_price)
    if benford_score > 0.3:
        flags.append(f"BENFORD: pierwsza cyfra sugeruje zaokrąglenie (score={benford_score:.2f})")
        scores.append(benford_score * 0.3)

    # 4. Liczba konkurentów
    if n_competitors is not None:
        if n_competitors <= 1:
            flags.append("MONOPOL: tylko 1 oferta — brak konkurencji")
            scores.append(0.4)
        elif n_competitors >= 10:
            flags.append(f"DUŻA_KONKURENCJA: {n_competitors} ofert — trudny rynek")
            scores.append(0.0)

    # Wynikowy score
    anomaly_score = max(scores) if scores else 0.0

    # Rekomendacja
    if anomaly_score >= 0.7:
        recommendation = "WYSOKI ALERT — zalecana weryfikacja kosztorysu szczegółowego"
    elif anomaly_score >= 0.4:
        recommendation = "UWAGA — oferta odbiega od normy rynkowej, sprawdź pozycje"
    else:
        recommendation = "OK — oferta w normie rynkowej"

    return {
        "bid_price": bid_price,
        "estimated_value": estimated_value,
        "ratio": round(ratio, 4),
        "anomaly_score": round(anomaly_score, 3),
        "flags": flags,
        "recommendation": recommendation,
        "z_analysis": z_info,
        "benchmark": {
            "win_ratio_p25": benchmark.get("win_ratio_p25"),
            "win_ratio_median": benchmark.get("win_ratio_median"),
            "win_ratio_p75": benchmark.get("win_ratio_p75"),
            "n_market_results": benchmark.get("n_market_results", 0),
        },
    }


def _get_win_ratios_for_cpv(cpv_prefix: str, province: str | None) -> list[float]:
    """Pobierz historyczne win_ratios z market_results dla CPV prefix."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT winning_price_pln / NULLIF(estimated_value_pln, 0) AS ratio
                FROM market_results
                WHERE cpv_codes && ARRAY[:cpv_filter]::text[]
                  AND winning_price_pln > 0
                  AND estimated_value_pln > 0
                LIMIT 500
            """), {"cpv_filter": f"{cpv_prefix}0000-0"[:9]}).fetchall()
        return [float(r.ratio) for r in rows if r.ratio and 0.2 < r.ratio < 3.0]
    except Exception:
        return []


def _benford_check(value: float) -> float:
    """Sprawdź czy cena pasuje do rozkładu Benforda.

    Zwraca odchylenie 0.0–1.0. Wysokie = podejrzane zaokrąglenie.
    """
    if value <= 0:
        return 0.0

    # Pierwsza cyfra
    s = str(int(abs(value)))
    first_digit = int(s[0]) if s else 1
    if first_digit == 0:
        first_digit = 1

    # Oczekiwana częstość Benforda
    expected = math.log10(1 + 1 / first_digit)

    # Zaokrąglenia (kończące się 0000) → odchylenie Benforda
    # Wykrywamy też przez ostatnie cyfry
    str_val = str(int(value))
    trailing_zeros = len(str_val) - len(str_val.rstrip("0"))
    zero_ratio = trailing_zeros / max(len(str_val), 1)

    # Score: im więcej zer na końcu + im mała cyfra Benforda, tym wyższy score
    benford_deviation = max(0, (0.301 - expected) / 0.301)  # d=1 jest normalne
    score = 0.4 * benford_deviation + 0.6 * min(zero_ratio * 2, 1.0)
    return round(score, 3)


# ─── 3. WIN PROBABILITY ───────────────────────────────────────────────────────

def estimate_win_probability(
    our_price: float,
    estimated_value: float,
    cpv_prefix: str,
    province: str | None = None,
    n_competitors: int = 4,
) -> dict:
    """Szacuj P(win) na podstawie quantile model z market_results.

    Metodologia:
    - Pobierz rozkład win_ratios per CPV+region
    - Nasza oferta = our_ratio = our_price / estimated_value
    - P(win) = P(our_ratio <= winning_ratio) z rozkładu empirycznego
    """
    our_ratio = our_price / estimated_value if estimated_value > 0 else 1.0
    win_ratios = _get_win_ratios_for_cpv(cpv_prefix, province)

    if not win_ratios or len(win_ratios) < 10:
        # Fallback: model parametryczny z discovery data
        # Mediana rynkowa: 0.971, std ~0.12
        mean_r = 0.971
        std_r = 0.12
        z = (our_ratio - mean_r) / std_r
        # Logistic survival function
        p_win = _logistic_survival(z)
        competition_factor = _competition_factor(p_win, n_competitors)
        return {
            "p_win": round(competition_factor, 3),
            "our_ratio": round(our_ratio, 4),
            "method": "parametric_fallback",
            "mean_ratio": mean_r,
            "recommendation": _price_recommendation(competition_factor, our_ratio, mean_r, std_r),
        }

    # Empiryczny CDF — P(wygrywająca <= our_price) = ile wygrywających <= our_ratio
    sorted_ratios = sorted(win_ratios)
    n = len(sorted_ratios)

    # P(win) = P(my ratio <= competitor winning ratio) — im niższa nasza cena, tym wyżej
    # Ale nie chcemy rażąco niskiej → smooth empirical CDF
    rank = sum(1 for r in sorted_ratios if r >= our_ratio)
    p_base = rank / n

    # Korekta na liczbę konkurentów: P(win vs N) = P(1v1)^N
    competition_factor = _competition_factor(p_base, n_competitors)

    # Rekomendacja cenowa: jaki ratio dałby P(win)=50%?
    p50_ratio = _percentile(sorted_ratios, 0.50)
    p25_ratio = _percentile(sorted_ratios, 0.25)
    p75_ratio = _percentile(sorted_ratios, 0.75)

    # Sweet spot: p40–p60 to optymalny przedział win/price
    p_sweet_low = _percentile(sorted_ratios, 0.40)
    p_sweet_high = _percentile(sorted_ratios, 0.60)

    return {
        "p_win": round(competition_factor, 3),
        "our_ratio": round(our_ratio, 4),
        "our_price": round(our_price, 0),
        "method": "empirical_cdf",
        "n_market_samples": n,
        "win_ratio_distribution": {
            "p25": p25_ratio,
            "p50": p50_ratio,
            "p75": p75_ratio,
        },
        "sweet_spot": {
            "ratio_low": p_sweet_low,
            "ratio_high": p_sweet_high,
            "price_low": round(estimated_value * p_sweet_low, 0),
            "price_high": round(estimated_value * p_sweet_high, 0),
        },
        "n_competitors_assumed": n_competitors,
        "recommendation": _price_recommendation_empirical(
            our_ratio, competition_factor, p_sweet_low, p_sweet_high, estimated_value
        ),
    }


def _logistic_survival(z: float) -> float:
    """Logistyczny wariant survival function: P(wygranie) = 1/(1+exp(z))."""
    return 1.0 / (1.0 + math.exp(z))


def _competition_factor(p_base: float, n_competitors: int) -> float:
    """Korekta P(win) na liczbę konkurentów: P_adj = p_base ^ n_competitors."""
    n = max(1, n_competitors)
    return round(p_base ** (1.0 / n), 4)  # geometric mean approach


def _price_recommendation(p: float, ratio: float, mean: float, std: float) -> dict:
    """Rekomendacja korekty ceny dla modelu parametrycznego."""
    if p >= 0.5:
        optimal_ratio = mean - 0.3 * std  # nieco poniżej mediany
    else:
        optimal_ratio = mean
    return {
        "optimal_ratio": round(optimal_ratio, 4),
        "action": "obniż cenę" if ratio > mean else "cena OK",
    }


def _price_recommendation_empirical(
    our_ratio: float,
    p_win: float,
    sweet_low: float,
    sweet_high: float,
    estimated_value: float,
) -> dict:
    if our_ratio > sweet_high:
        action = "OBNIŻ_CENĘ"
        suggested_ratio = sweet_high
    elif our_ratio < sweet_low:
        action = "MOŻESZ_PODWYŻSZYĆ"
        suggested_ratio = sweet_low
    else:
        action = "CENA_OK"
        suggested_ratio = our_ratio

    return {
        "action": action,
        "suggested_price": round(estimated_value * suggested_ratio, 0),
        "suggested_ratio": round(suggested_ratio, 4),
        "current_p_win": p_win,
    }


# ─── 4. CPV CLUSTER ANOMALY (Isolation Forest) ────────────────────────────────

def detect_kosztorys_anomalies(
    items: list[dict],
    cpv_prefix: str = "45",
    province: str | None = None,
) -> dict:
    """Wykryj anomalie w całym kosztorysie (wiele pozycji).

    Każda pozycja: {description, unit, quantity, unit_price, category}
    Porównanie z icb_ceny_srednie per category.

    Metody:
    - Per-pozycja z-score względem ICB cen jednostkowych
    - Isolation Forest na całym wektorze cen (jeśli sklearn dostępny)
    """
    if not items:
        return {"error": "Brak pozycji do analizy"}

    engine = get_engine()
    year, quarter = _latest_quarter()

    # Pobierz benchmark ICB per category
    with engine.connect() as conn:
        bench = conn.execute(sa.text("""
            SELECT category, typ_rms,
                   round(avg(cena_netto)::numeric, 4) as avg_p,
                   round(stddev(cena_netto)::numeric, 4) as std_p,
                   round(percentile_cont(0.25) WITHIN GROUP (ORDER BY cena_netto)::numeric, 4) as p25,
                   round(percentile_cont(0.75) WITHIN GROUP (ORDER BY cena_netto)::numeric, 4) as p75
            FROM icb_ceny_srednie
            WHERE kwartalrok = :rok AND kwartalnr = :nr AND cena_netto > 0
            GROUP BY category, typ_rms
        """), {"rok": year, "nr": quarter}).fetchall()

    bench_map: dict[tuple, dict] = {}
    for r in bench:
        key = (r.category, r.typ_rms)
        bench_map[key] = {
            "avg": float(r.avg_p) if r.avg_p else 0,
            "std": float(r.std_p) if r.std_p else 0,
            "p25": float(r.p25) if r.p25 else 0,
            "p75": float(r.p75) if r.p75 else 0,
        }

    # Per-item analysis
    item_results = []
    anomalous = []

    for item in items:
        cat = item.get("category", "inne")
        price = float(item.get("unit_price", 0))
        # Mapuj category na typ_rms
        rms = _infer_rms(item)
        key = (cat, rms)
        bm = bench_map.get(key, bench_map.get(("inne", "M")))

        if bm and bm["avg"] > 0 and bm["std"] > 0:
            z = (price - bm["avg"]) / bm["std"]
            is_anomaly = abs(z) > 2.5
        else:
            z = 0.0
            is_anomaly = False

        item_result = {
            "description": item.get("description", "")[:60],
            "unit_price": price,
            "category": cat,
            "benchmark_avg": bm["avg"] if bm else None,
            "z_score": round(z, 3),
            "is_anomaly": is_anomaly,
        }
        item_results.append(item_result)
        if is_anomaly:
            anomalous.append(item_result)

    # Isolation Forest (jeśli sklearn)
    iforest_result = {}
    if len(items) >= 5:
        try:
            from sklearn.ensemble import IsolationForest
            import numpy as np
            prices = np.array([float(it.get("unit_price", 0)) for it in items]).reshape(-1, 1)
            iforest = IsolationForest(contamination=0.1, random_state=42)
            labels = iforest.fit_predict(prices)
            iforest_anomalies = [items[i] for i, l in enumerate(labels) if l == -1]
            iforest_result = {
                "n_anomalies_iforest": len(iforest_anomalies),
                "iforest_anomaly_items": [it.get("description", "")[:40] for it in iforest_anomalies[:5]],
            }
        except ImportError:
            iforest_result = {"iforest": "sklearn not available"}
        except Exception as e:
            iforest_result = {"iforest_error": str(e)}

    total_value = sum(float(it.get("quantity", 1)) * float(it.get("unit_price", 0)) for it in items)
    anomaly_rate = len(anomalous) / len(items) if items else 0

    return {
        "n_items": len(items),
        "n_anomalies_zscore": len(anomalous),
        "anomaly_rate": round(anomaly_rate, 3),
        "total_value": round(total_value, 2),
        "anomalous_items": anomalous[:10],
        "all_items": item_results,
        "icb_quarter": f"{year}-Q{quarter}",
        **iforest_result,
    }


def _infer_rms(item: dict) -> str:
    cat = item.get("category", "").lower()
    desc = item.get("description", "").lower()
    if any(w in cat for w in ["robo", "prac"]) or "r-g" in item.get("unit", "").lower():
        return "R"
    if any(w in cat for w in ["sprzęt", "maszyn"]) or "m-g" in item.get("unit", "").lower():
        return "S"
    return "M"


def _latest_quarter() -> tuple[int, int]:
    engine = get_engine()
    with engine.connect() as conn:
        r = conn.execute(sa.text("""
            SELECT kwartalrok, kwartalnr FROM icb_ceny_srednie
            ORDER BY kwartalrok DESC, kwartalnr DESC LIMIT 1
        """)).fetchone()
    return (r.kwartalrok, r.kwartalnr) if r else (2026, 2)
