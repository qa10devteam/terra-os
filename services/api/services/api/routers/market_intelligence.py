"""Faza 3 — Market Intelligence API.

Endpoints:
  GET /api/v2/intelligence/benchmark        — benchmark cen per CPV/region/kwartał
  GET /api/v2/intelligence/trends           — trendy rynkowe kwartalnie (mv_market_trend)
  GET /api/v2/intelligence/competitors/top  — top wykonawcy (mv_contractor_ranking)
  GET /api/v2/intelligence/buyers/top       — top zamawiający (mv_buyer_ranking)
  GET /api/v2/intelligence/prices/icb       — ceny Intercenbud z filtrem
  GET /api/v2/intelligence/prices/inflation — indeks inflacji cen ICB (mv_labor_inflation_index)
  GET /api/v2/intelligence/regional         — mapa cen regionalnych (mv_regional_price_level)
  GET /api/v2/intelligence/seasonality      — sezonowość przetargów per miesiąc
  GET /api/v2/intelligence/fts              — full-text search w historical_tenders (FTS)
  GET /api/v2/intelligence/summary          — agregowane KPI rynkowe dla dashboardu
  GET /api/v2/intelligence/win-rates        — historyczne win-rates wykonawców per CPV
  GET /api/v2/intelligence/top-buyers-cpv   — top zamawiający per CPV (z historical_tenders)

Źródła: mv_tender_benchmark (6.6k), mv_market_trend, mv_contractor_ranking,
        mv_buyer_ranking, icb_ceny_srednie (784k), mv_labor_inflation_index,
        mv_regional_price_level, mv_competitor_recent_wins (91k), historical_tenders (1.4M)
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from ..auth.deps import AuthUser
from ..auth.plan_gate import require_plan, PlanLevel
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/intelligence", tags=["market-intelligence"])


def _redis_get(key: str):
    """Try to get a cached value from Redis. Returns None on any error."""
    try:
        from ..redis_cache import _get_redis
        r = _get_redis()
        if not r:
            return None
        raw = r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _redis_set(key: str, value, ttl: int = 300):
    """Try to set a value in Redis. Silently swallows errors."""
    try:
        from ..redis_cache import _get_redis
        r = _get_redis()
        if r:
            r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


# ─── Benchmark cen ────────────────────────────────────────────────────────────

@router.get("/benchmark", summary="Benchmark cen przetargów per CPV/region/kwartał")
def benchmark(
    user: AuthUser,
    cpv_prefix: str = Query(..., min_length=2, description="CPV prefix np. '4523' lub '45'"),
    province: str | None = Query(None, description="Kod NUTS województwa np. 'PL22'"),
    quarters: int = Query(8, ge=1, le=20, description="Ile ostatnich kwartałów"),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    """Benchmark cen bezpośrednio z historical_tenders — dokładniejszy niż MV dla wąskich filtrów."""
    conditions = ["left(cpv_code, :cpv_len) = :cpv"]
    params: dict = {
        "cpv": cpv_prefix,
        "cpv_len": len(cpv_prefix),
        "quarters": quarters,
    }

    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT left(cpv_code, 5) AS cpv5, province,
                   date_trunc('quarter', date::timestamp)::date AS quarter,
                   count(*) AS n_tenders,
                   round(avg(estimated_value)::numeric) AS avg_value,
                   round(percentile_cont(0.5) WITHIN GROUP (ORDER BY estimated_value)::numeric) AS median_value,
                   round(min(estimated_value)::numeric) AS min_value,
                   round(max(estimated_value)::numeric) AS max_value,
                   round(avg(offers_count)::numeric, 1) AS avg_competition,
                   count(*) FILTER (WHERE procedure_result = 'zawarcieUmowy') AS n_won
            FROM historical_tenders
            WHERE {where}
              AND estimated_value IS NOT NULL AND estimated_value > 0
              AND date IS NOT NULL
              AND date >= (SELECT max(date) FROM historical_tenders) - (:quarters * INTERVAL '3 months')
            GROUP BY 1, 2, 3
            ORDER BY 3 DESC, 1
            LIMIT 200
        """), params).mappings().all()

    if not rows:
        return {"cpv_prefix": cpv_prefix, "province": province, "data": [], "total": 0}

    return {
        "cpv_prefix": cpv_prefix,
        "province": province,
        "data": [dict(r) for r in rows],
        "total": len(rows),
    }


# ─── Trendy rynkowe ───────────────────────────────────────────────────────────

@router.get("/trends", summary="Trendy rynkowe kwartalnie (mv_market_trend)")
def market_trends(
    user: AuthUser,
    cpv_prefix: str | None = Query(None, description="CPV prefix np. '45'"),
    province: str | None = Query(None),
    quarters: int = Query(12, ge=1, le=24),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    """Dane z mv_market_trend — wstępnie zagregowane, sub-10ms."""
    conditions = ["quarter >= (SELECT max(quarter) FROM mv_market_trend) - ((:quarters - 1) * INTERVAL '3 months')"]
    params: dict = {"quarters": quarters}

    if cpv_prefix:
        conditions.append("left(cpv3, :cpv_len) = :cpv")
        params["cpv"] = cpv_prefix[:3]
        params["cpv_len"] = min(len(cpv_prefix), 3)

    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT cpv3, quarter,
                   sum(n_tenders)::int AS n_tenders,
                   round(sum(total_value_mln) * 1000000) AS total_value,
                   round((sum(total_value_mln) * 1000000 / NULLIF(sum(n_tenders), 0))::numeric) AS avg_value,
                   round(avg(avg_offers)::numeric, 1) AS avg_competition,
                   sum(n_completed)::int AS n_completed
            FROM mv_market_trend
            WHERE {where}
            GROUP BY cpv3, quarter
            ORDER BY quarter DESC, cpv3
            LIMIT 300
        """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Top wykonawcy ────────────────────────────────────────────────────────────

@router.get("/competitors/top", summary="Top wykonawcy per CPV/region (mv_contractor_ranking)")
def top_competitors(
    user: AuthUser,
    cpv_prefix: str | None = Query(None),
    province: str | None = Query(None),
    limit: int = Query(20, le=100),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    """Dane z mv_contractor_ranking — wstępnie zagregowane."""
    conditions = ["contractor_nip IS NOT NULL"]
    params: dict = {"limit": limit}

    if cpv_prefix:
        conditions.append("left(cpv2, :cpv_len) = :cpv")
        params["cpv"] = cpv_prefix[:2]
        params["cpv_len"] = len(cpv_prefix[:2])
    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT contractor_nip AS nip, contractor_name,
                   sum(won_tenders)::int AS wins,
                   round(sum(won_value_mln) * 1000000) AS total_value,
                   round((sum(won_value_mln) * 1000000 / NULLIF(sum(won_tenders), 0))::numeric) AS avg_value,
                   round(avg(avg_competition)::numeric, 1) AS avg_competition,
                   round(avg(win_rate_pct)::numeric, 1) AS win_rate_pct
            FROM mv_contractor_ranking
            WHERE {where}
            GROUP BY contractor_nip, contractor_name
            ORDER BY wins DESC
            LIMIT :limit
        """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Top zamawiający ──────────────────────────────────────────────────────────

@router.get("/buyers/top", summary="Top zamawiający per CPV/region (mv_buyer_ranking)")
def top_buyers(
    user: AuthUser,
    cpv_prefix: str | None = Query(None),
    province: str | None = Query(None),
    limit: int = Query(20, le=100),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    conditions = ["buyer_nip IS NOT NULL"]
    params: dict = {"limit": limit}

    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT buyer_nip, buyer AS buyer_name, province,
                   total_tenders AS n_tenders,
                   round(total_value_mln * 1000000) AS total_value,
                   round(avg_value_k * 1000) AS avg_value,
                   cpv_diversity
            FROM mv_buyer_ranking
            WHERE {where}
            ORDER BY total_value_mln DESC NULLS LAST
            LIMIT :limit
        """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Ceny ICB ─────────────────────────────────────────────────────────────────

@router.get("/prices/icb", summary="Ceny Intercenbud per kategoria/kwartał")
def icb_prices(
    user: AuthUser,
    category: str | None = Query(None, description="np. beton_cement, robocizna"),
    typ_rms: str | None = Query(None, description="R=robocizna, M=materiał, S=sprzęt"),
    year: int | None = Query(None, ge=2010, le=2030),
    quarter: int | None = Query(None, ge=1, le=4),
    symbol: str | None = Query(None, description="Symbol ICB np. '1690000'"),
    limit: int = Query(100, le=500),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    conditions = ["1=1"]
    params: dict = {"limit": limit}

    if category:
        conditions.append("category = :category")
        params["category"] = category
    if typ_rms:
        if typ_rms.upper() not in ("R", "M", "S"):
            raise HTTPException(status_code=400, detail="typ_rms musi być R, M lub S")
        conditions.append("typ_rms = :typ_rms")
        params["typ_rms"] = typ_rms.upper()
    if year:
        conditions.append("kwartalrok = :year")
        params["year"] = year
    if quarter:
        conditions.append("kwartalnr = :quarter")
        params["quarter"] = quarter
    if symbol:
        conditions.append("symbol LIKE :symbol")
        params["symbol"] = f"{symbol}%"

    where = " AND ".join(conditions)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT symbol, indeks_eto, nazwa, typ_rms, category,
                   cena_netto, cena_narzut, kwartalrok, kwartalnr
            FROM icb_ceny_srednie
            WHERE {where}
            ORDER BY kwartalrok DESC, kwartalnr DESC, symbol
            LIMIT :limit
        """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Inflacja ICB ─────────────────────────────────────────────────────────────

@router.get("/prices/inflation", summary="Indeks inflacji cen materiałów/robocizny ICB")
def price_inflation(
    user: AuthUser,
    category: str | None = Query(None),
    typ_rms: str | None = Query(None, description="R|M|S"),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    """YoY i QoQ indeks zmian cen z mv_labor_inflation_index."""
    if typ_rms and typ_rms.upper() not in ("R", "M", "S"):
        raise HTTPException(status_code=400, detail="typ_rms musi być R, M lub S")

    conditions = ["1=1"]
    params: dict = {}

    if category:
        conditions.append("category = :category")
        params["category"] = category
    if typ_rms:
        conditions.append("typ_rms = :typ_rms")
        params["typ_rms"] = typ_rms.upper()

    where = " AND ".join(conditions)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT yr, q, typ_rms, category,
                   avg_price, avg_price_markup, n_items,
                   yoy_pct, qoq_pct
            FROM mv_labor_inflation_index
            WHERE {where}
            ORDER BY yr DESC, q DESC, typ_rms, category
            LIMIT 500
        """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Ceny regionalne ──────────────────────────────────────────────────────────

@router.get("/regional", summary="Mapa cen regionalnych per CPV/województwo (ICB koeficjent)")
def regional_prices(
    user: AuthUser,
    cpv_prefix: str | None = Query(None, min_length=2),
    quarter: str | None = Query(None, description="Kwartał ISO np. '2025-01-01'"),
    nuts2_code: str | None = Query(None, description="Kod NUTS2 np. 'PL22'"),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    conditions = ["1=1"]
    params: dict = {}

    if cpv_prefix:
        conditions.append("cpv5 LIKE :cpv_q")
        params["cpv_q"] = f"{cpv_prefix}%"
    if quarter:
        conditions.append("quarter = :quarter")
        params["quarter"] = quarter
    if nuts2_code:
        conditions.append("nuts2_code = :nuts2_code")
        params["nuts2_code"] = nuts2_code

    where = " AND ".join(conditions)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT nuts2_code, voivodeship_pl, cpv5, quarter,
                   n_tenders, avg_value, median_value, avg_competition, icb_labor_coeff
            FROM mv_regional_price_level
            WHERE {where}
            ORDER BY quarter DESC, nuts2_code, cpv5
            LIMIT 500
        """), params).mappings().all()

    return {"data": [dict(r) for r in rows], "total": len(rows)}


# ─── Sezonowość ───────────────────────────────────────────────────────────────

@router.get("/seasonality", summary="Sezonowość przetargów per miesiąc roku")
def seasonality(
    user: AuthUser,
    cpv_prefix: str | None = Query(None),
    province: str | None = Query(None),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    """Sezonowość ogłoszeń + wartości per miesiąc — agregat wieloletni."""
    conditions = ["date IS NOT NULL", "estimated_value IS NOT NULL", "estimated_value > 0"]
    params: dict = {}

    if cpv_prefix:
        conditions.append("left(cpv_code, :cpv_len) = :cpv")
        params["cpv"] = cpv_prefix
        params["cpv_len"] = len(cpv_prefix)
    if province:
        conditions.append("province = :province")
        params["province"] = province

    where = " AND ".join(conditions)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT EXTRACT(MONTH FROM date::date)::int AS month,
                   count(*) AS n_tenders,
                   round(avg(estimated_value)::numeric) AS avg_value,
                   round(sum(estimated_value)::numeric) AS total_value,
                   round(avg(offers_count)::numeric, 1) AS avg_competition
            FROM historical_tenders
            WHERE {where}
            GROUP BY 1 ORDER BY 1
        """), params).mappings().all()

    return {"data": [dict(r) for r in rows]}


# ─── Full-text search ─────────────────────────────────────────────────────────

@router.get("/fts", summary="Full-text search w 1.4M przetargów (GIN index)")
def fts_search(
    user: AuthUser,
    q: str = Query(..., min_length=2, description="Zapytanie FTS np. 'remont drogi'"),
    cpv_prefix: str | None = Query(None),
    province: str | None = Query(None),
    value_min: float | None = Query(None, ge=0),
    value_max: float | None = Query(None, ge=0),
    notice_type: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    conditions = ["title_tsv @@ plainto_tsquery('simple', :q)"]
    params: dict = {"q": q, "limit": limit, "offset": offset}

    if cpv_prefix:
        conditions.append("left(cpv_code, :cpv_len) = :cpv")
        params["cpv"] = cpv_prefix
        params["cpv_len"] = len(cpv_prefix)
    if province:
        conditions.append("province = :province")
        params["province"] = province
    if value_min is not None:
        conditions.append("estimated_value >= :value_min")
        params["value_min"] = value_min
    if value_max is not None:
        conditions.append("estimated_value <= :value_max")
        params["value_max"] = value_max
    if notice_type:
        conditions.append("notice_type = :notice_type")
        params["notice_type"] = notice_type

    where = " AND ".join(conditions)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT id, title, buyer, buyer_nip, province, cpv_code,
                   estimated_value, date, notice_type, procedure_result,
                   offers_count, contractor_name,
                   ts_rank(title_tsv, plainto_tsquery('simple', :q)) AS rank
            FROM historical_tenders
            WHERE {where}
            ORDER BY rank DESC, date DESC
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()

        total = conn.execute(text(
            f"SELECT count(*) FROM historical_tenders WHERE {where}"
        ), params).scalar()

    return {
        "query": q,
        "items": [dict(r) for r in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


# ─── Summary KPI ─────────────────────────────────────────────────────────────

@router.get("/summary", summary="Agregowane KPI rynkowe dla dashboardu")
def market_summary(
    user: AuthUser,
    cpv_prefix: str | None = Query(None, description="CPV prefix np. '45'"),
    province: str | None = Query(None),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    """Szybkie KPI: łączna liczba + wartość przetargów (1 rok), top CPV, top region.

    Optymalizacja: Redis cache (TTL=5min) + jeden CTE zamiast 3 osobnych query.
    """
    cache_key = f"mi:summary:{cpv_prefix or '_'}:{province or '_'}"
    cached = _redis_get(cache_key)
    if cached:
        return cached
    cond_parts = ["date >= :min_date"]
    params: dict = {}

    if cpv_prefix:
        cond_parts.append(f"left(cpv_code, {len(cpv_prefix)}) = :cpv")
        params["cpv"] = cpv_prefix
    if province:
        cond_parts.append("province = :province")
        params["province"] = province

    where = " AND ".join(cond_parts)

    engine = get_engine()
    with engine.connect() as conn:
        # Resolve min_date once (index-only scan)
        max_date_row = conn.execute(text(
            "SELECT max(date) FROM historical_tenders"
        )).scalar()
        from datetime import date, timedelta
        params["min_date"] = (max_date_row - timedelta(days=365)) if max_date_row else date(2024, 1, 1)

        # Single-pass aggregation with FILTER — eliminates 3 sequential scans
        result = conn.execute(text(f"""
            WITH base AS (
                SELECT
                    estimated_value,
                    offers_count,
                    buyer_nip,
                    contractor_national_id,
                    procedure_result,
                    left(cpv_code, 2) AS cpv2,
                    province AS prov
                FROM historical_tenders
                WHERE {where}
            )
            SELECT
                count(*)                                             AS n_tenders,
                count(estimated_value)                               AS n_with_value,
                round(sum(estimated_value)::numeric / 1e6, 1)       AS total_value_mln,
                round(avg(estimated_value)::numeric)                 AS avg_value,
                round(avg(offers_count)::numeric, 1)                 AS avg_competition,
                count(DISTINCT buyer_nip)                            AS n_buyers,
                count(DISTINCT contractor_national_id)
                    FILTER (WHERE procedure_result = 'zawarcieUmowy') AS n_contractors,
                -- top 5 CPV (encoded as JSON-like text for single row)
                array_agg(DISTINCT cpv2)                             AS cpv_arr,
                array_agg(DISTINCT prov)                             AS prov_arr
            FROM base
        """), params).mappings().one()

        # Top CPV + province in second lightweight query (already filtered by CTE logic)
        top_cpv = conn.execute(text(f"""
            SELECT left(cpv_code, 2) AS cpv2, count(*) AS n
            FROM historical_tenders
            WHERE {where} AND cpv_code IS NOT NULL
            GROUP BY 1 ORDER BY 2 DESC LIMIT 5
        """), params).mappings().all()

        top_province = conn.execute(text(f"""
            SELECT province, count(*) AS n
            FROM historical_tenders
            WHERE {where} AND province IS NOT NULL
            GROUP BY 1 ORDER BY 2 DESC LIMIT 5
        """), params).mappings().all()

    kpi = {
        "n_tenders": result["n_tenders"],
        "n_with_value": result["n_with_value"],
        "total_value_mln": result["total_value_mln"],
        "avg_value": result["avg_value"],
        "avg_competition": result["avg_competition"],
        "n_buyers": result["n_buyers"],
        "n_contractors": result["n_contractors"],
    }

    result_dict = {
        "kpi": kpi,
        "top_cpv": [dict(r) for r in top_cpv],
        "top_province": [dict(r) for r in top_province],
        "filters": {"cpv_prefix": cpv_prefix, "province": province},
    }
    _redis_set(cache_key, result_dict, ttl=300)  # cache 5 min
    return result_dict


# ─── Win-rates per CPV ────────────────────────────────────────────────────────

@router.get("/win-rates", summary="Historyczne win-rates wykonawców per CPV (historical_tenders)")
def win_rates(
    user: AuthUser,
    cpv_prefix: str = Query(..., min_length=2, max_length=8, description="CPV prefix np. '45' lub '45233'"),
    limit: int = Query(20, ge=1, le=100),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    """Top wykonawcy wg liczby wygranych przetargów dla danego prefixu CPV.

    Zapytanie wprost do historical_tenders (1.4M) — pomija pre-agregowane widoki,
    dzięki czemu działa dla dowolnie wąskich prefixów (2–8 znaków).
    """
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                contractor_name,
                COUNT(*)                             AS wins,
                ROUND(AVG(estimated_value)::numeric) AS avg_value,
                array_agg(DISTINCT cpv_code)         AS cpvs
            FROM historical_tenders
            WHERE cpv_code LIKE :prefix || '%'
              AND contractor_name IS NOT NULL
            GROUP BY contractor_name
            ORDER BY wins DESC
            LIMIT :limit
        """), {"prefix": cpv_prefix, "limit": limit}).mappings().all()

    return {
        "cpv_prefix": cpv_prefix,
        "data": [
            {
                "contractor_name": r["contractor_name"],
                "wins": r["wins"],
                "avg_value_pln": float(r["avg_value"]) if r["avg_value"] is not None else None,
                "cpvs": sorted(set(r["cpvs"]))[:10],
            }
            for r in rows
        ],
        "total": len(rows),
    }


# ─── Top buyers per CPV ───────────────────────────────────────────────────────

@router.get("/top-buyers-cpv", summary="Top zamawiający per CPV z historical_tenders")
def top_buyers_cpv(
    user: AuthUser,
    cpv_prefix: str = Query(..., min_length=2, max_length=8, description="CPV prefix np. '45' lub '45233'"),
    limit: int = Query(20, ge=1, le=100),
    _gate: None = require_plan(PlanLevel.BUSINESS),
):
    """Top zamawiający wg liczby przetargów dla danego prefixu CPV.

    Grupowanie po nazwie zamawiającego (buyer) — bezpośrednio z historical_tenders.
    """
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                buyer,
                COUNT(*)                             AS tenders,
                ROUND(AVG(estimated_value)::numeric) AS avg_value,
                array_agg(DISTINCT cpv_code)         AS cpvs
            FROM historical_tenders
            WHERE cpv_code LIKE :prefix || '%'
              AND buyer IS NOT NULL
            GROUP BY buyer
            ORDER BY tenders DESC
            LIMIT :limit
        """), {"prefix": cpv_prefix, "limit": limit}).mappings().all()

    return {
        "cpv_prefix": cpv_prefix,
        "data": [
            {
                "buyer": r["buyer"],
                "tenders": r["tenders"],
                "avg_value_pln": float(r["avg_value"]) if r["avg_value"] is not None else None,
                "cpvs": sorted(set(r["cpvs"]))[:10],
            }
            for r in rows
        ],
        "total": len(rows),
    }


# ─── Sekocenbud search ─────────────────────────────────────────────────────────

@router.get("/sekocenbud", summary="Wyszukiwanie w bazie SEKOCENBUD (23 725 pozycji)")
def sekocenbud_search(
    user: AuthUser,
    q: str = Query("", description="Fraza wyszukiwania w opisie lub symbolu"),
    chapter: str | None = Query(None, description="Filtr po chapter_name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _gate: None = require_plan(PlanLevel.BUSINESS),
) -> dict:
    """Full-text search w bazie SEKOCENBUD. Zwraca pozycje z ceną, jednostką i symbolem."""
    params: dict = {"limit": limit, "offset": offset}
    where_parts = []

    if q:
        where_parts.append("(opis ILIKE :q OR symbol ILIKE :q OR katalog_code ILIKE :q)")
        params["q"] = f"%{q}%"
    if chapter:
        where_parts.append("chapter_name ILIKE :chapter")
        params["chapter"] = f"%{chapter}%"

    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT id, symbol, katalog_code, chapter_name, opis, jm, cena, rg, m, s
            FROM sekocenbud_items
            {where}
            ORDER BY symbol
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()

        total = conn.execute(text(f"""
            SELECT COUNT(*) FROM sekocenbud_items {where}
        """), params).scalar()

    return {
        "total": total,
        "items": [dict(r) for r in rows],
    }


# ─── /api/v2/market-intel alias router ────────────────────────────────────────
market_intel_router = APIRouter(prefix="/api/v2/market-intel", tags=["market-intel"])


@market_intel_router.get("/summary", summary="Szybkie KPI rynkowe dla dashboardu")
def market_intel_summary(user: AuthUser):
    engine = get_engine()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT count(*) FROM historical_tenders")).scalar() or 0
        recent = conn.execute(text(
            "SELECT count(*) FROM historical_tenders WHERE date >= current_date - interval '90 days'"
        )).scalar() or 0
    return {"total_tenders": total, "recent_90d": recent, "status": "ok"}


@market_intel_router.get("/cpv-trends", summary="Trendy CPV ostatnie 12 miesięcy")
def market_intel_cpv_trends(user: AuthUser, limit: int = Query(10, le=50)):
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT cpv_code, count(*) AS cnt
            FROM historical_tenders
            WHERE cpv_code IS NOT NULL AND date >= current_date - interval '365 days'
            GROUP BY cpv_code ORDER BY cnt DESC LIMIT :limit
        """), {"limit": limit}).fetchall()
    return {"items": [dict(r._mapping) for r in rows]}


@market_intel_router.get("/regional", summary="Dane regionalne per województwo")
def market_intel_regional(user: AuthUser, limit: int = Query(16, le=50)):
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT province, cnt, total_pln
            FROM mv_province_stats
            ORDER BY cnt DESC LIMIT :limit
        """), {"limit": limit}).fetchall()
    return {"items": [dict(r._mapping) for r in rows]}
