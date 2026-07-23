"""
historical_intelligence.py — Terra-OS Historical Tender Intelligence.

Wzbogaca analizę przetargu o:
1. Podobne przetargi historyczne (tytuł + CPV + region)
2. Benchmark wartości (estymowana vs rzeczywista)
3. Profil zamawiającego (ile ogłoszeń, średni budżet, typy)
4. Konkurencja — kim są typowi wykonawcy w segmencie
5. Sezonowość — kiedy pojawiają się przetargi w CPV

Integracja: wywoływany z langgraph_pipeline node_analyze_swz jako context.
"""
from __future__ import annotations

import logging
from typing import Any

import sqlalchemy as sa

from terra_db.session import get_engine

logger = logging.getLogger(__name__)


def get_historical_context(
    title: str,
    cpv_code: str | None = None,
    province: str | None = None,
    estimated_value: float | None = None,
    buyer: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Główna funkcja — zwraca pełen kontekst historyczny dla przetargu.
    
    Wywoływana z LangGraph pipeline przed analyze_swz żeby LLM miał benchmark.
    """
    engine = get_engine()
    result: dict[str, Any] = {}
    
    # 1. Podobne przetargi (full-text search po tytule + filtr CPV)
    result["similar_tenders"] = _find_similar(engine, title, cpv_code, province, limit)
    
    # 2. Benchmark wartości dla segmentu
    cpv_prefix = (cpv_code or "")[:8]  # np. "45233140"
    if cpv_prefix:
        result["segment_benchmark"] = _segment_benchmark(engine, cpv_prefix, province)
    
    # 3. Profil zamawiającego
    if buyer:
        result["buyer_profile"] = _buyer_profile(engine, buyer)
    
    # 4. Top wykonawcy w segmencie
    if cpv_prefix:
        result["top_contractors"] = _top_contractors(engine, cpv_prefix, province)
    
    # 5. Sezonowość
    if cpv_prefix:
        result["seasonality"] = _seasonality(engine, cpv_prefix)
    
    return result


def _find_similar(
    engine: sa.Engine, title: str, cpv_code: str | None, province: str | None, limit: int
) -> list[dict]:
    """Full-text search po tytule + opcjonalnie CPV i region."""
    # Buduj tsquery z tytułu — weź 3-5 kluczowych słów
    keywords = _extract_keywords(title)
    if not keywords:
        return []
    
    tsquery = " & ".join(keywords[:5])
    
    params: dict[str, Any] = {"query": tsquery, "limit": limit}
    
    cpv_filter = ""
    if cpv_code:
        cpv_prefix = cpv_code[:5]
        cpv_filter = "AND cpv_code LIKE :cpv_prefix"
        params["cpv_prefix"] = f"{cpv_prefix}%"
    
    province_filter = ""
    if province:
        province_filter = "AND province = :province"
        params["province"] = province
    
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.text(f"""
                SELECT id, title, buyer, cpv_code, estimated_value, province,
                       offers_count, contractor_name, procedure_result, date,
                       ts_rank(title_tsv, to_tsquery('simple', :query)) AS rank
                FROM historical_tenders
                WHERE title_tsv @@ to_tsquery('simple', :query)
                  {cpv_filter}
                  {province_filter}
                  AND estimated_value > 0
                ORDER BY rank DESC, date DESC
                LIMIT :limit
            """), params).fetchall()
        
        return [
            {
                "id": r.id,
                "title": r.title[:120],
                "buyer": r.buyer,
                "cpv": (r.cpv_code or "")[:12],
                "value_pln": float(r.estimated_value) if r.estimated_value else None,
                "province": r.province,
                "offers_count": int(r.offers_count) if r.offers_count else None,
                "winner": r.contractor_name,
                "result": r.procedure_result,
                "date": str(r.date) if r.date else None,
                "relevance": round(float(r.rank), 3),
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("historical_intelligence._find_similar: %s", e)
        return []


def _segment_benchmark(engine: sa.Engine, cpv_prefix: str, province: str | None) -> dict:
    """Statystyki wartości dla segmentu CPV + opcjonalnie region."""
    params: dict[str, Any] = {"cpv": f"{cpv_prefix}%"}
    prov_filter = ""
    if province:
        prov_filter = "AND province = :province"
        params["province"] = province
    
    try:
        with engine.connect() as conn:
            row = conn.execute(sa.text(f"""
                SELECT 
                    COUNT(*) AS n,
                    ROUND(AVG(estimated_value)::numeric, 0) AS avg_val,
                    ROUND(percentile_cont(0.25) WITHIN GROUP (ORDER BY estimated_value)::numeric, 0) AS p25,
                    ROUND(percentile_cont(0.50) WITHIN GROUP (ORDER BY estimated_value)::numeric, 0) AS median,
                    ROUND(percentile_cont(0.75) WITHIN GROUP (ORDER BY estimated_value)::numeric, 0) AS p75,
                    ROUND(MIN(estimated_value)::numeric, 0) AS min_val,
                    ROUND(MAX(estimated_value)::numeric, 0) AS max_val,
                    ROUND(AVG(offers_count)::numeric, 1) AS avg_offers
                FROM historical_tenders
                WHERE cpv_code LIKE :cpv
                  AND estimated_value > 0
                  AND estimated_value < 1e9
                  {prov_filter}
            """), params).fetchone()
        
        if row and row.n and row.n > 0:
            return {
                "n_tenders": int(row.n),
                "avg_value": float(row.avg_val) if row.avg_val else 0,
                "p25": float(row.p25) if row.p25 else 0,
                "median": float(row.median) if row.median else 0,
                "p75": float(row.p75) if row.p75 else 0,
                "min": float(row.min_val) if row.min_val else 0,
                "max": float(row.max_val) if row.max_val else 0,
                "avg_offers_count": float(row.avg_offers) if row.avg_offers else 0,
                "cpv_prefix": cpv_prefix,
                "province": province,
            }
    except Exception as e:
        logger.warning("historical_intelligence._segment_benchmark: %s", e)
    return {}


def _buyer_profile(engine: sa.Engine, buyer: str) -> dict:
    """Profil zamawiającego — ile przetargów, jakie typy, średni budżet."""
    try:
        with engine.connect() as conn:
            row = conn.execute(sa.text("""
                SELECT 
                    COUNT(*) AS n,
                    ROUND(AVG(estimated_value)::numeric, 0) AS avg_val,
                    ROUND(SUM(estimated_value)::numeric, 0) AS total_val,
                    MIN(date) AS first_tender,
                    MAX(date) AS last_tender,
                    ROUND(AVG(offers_count)::numeric, 1) AS avg_offers
                FROM historical_tenders
                WHERE buyer = :buyer AND estimated_value > 0
            """), {"buyer": buyer}).fetchone()
            
            # Top CPV per buyer
            cpvs = conn.execute(sa.text("""
                SELECT LEFT(cpv_code, 5) AS cpv5, COUNT(*) AS cnt
                FROM historical_tenders
                WHERE buyer = :buyer AND cpv_code IS NOT NULL
                GROUP BY cpv5 ORDER BY cnt DESC LIMIT 5
            """), {"buyer": buyer}).fetchall()
            
            # Past winners
            winners = conn.execute(sa.text("""
                SELECT contractor_name, COUNT(*) AS wins
                FROM historical_tenders
                WHERE buyer = :buyer AND contractor_name IS NOT NULL
                GROUP BY contractor_name ORDER BY wins DESC LIMIT 5
            """), {"buyer": buyer}).fetchall()
        
        if row and row.n and row.n > 0:
            return {
                "n_tenders": int(row.n),
                "avg_value": float(row.avg_val) if row.avg_val else 0,
                "total_value": float(row.total_val) if row.total_val else 0,
                "first_tender": str(row.first_tender) if row.first_tender else None,
                "last_tender": str(row.last_tender) if row.last_tender else None,
                "avg_offers_count": float(row.avg_offers) if row.avg_offers else 0,
                "top_cpv": [{"cpv5": r.cpv5, "count": r.cnt} for r in cpvs],
                "frequent_winners": [{"name": r.contractor_name, "wins": r.wins} for r in winners],
            }
    except Exception as e:
        logger.warning("historical_intelligence._buyer_profile: %s", e)
    return {}


def _top_contractors(engine: sa.Engine, cpv_prefix: str, province: str | None) -> list[dict]:
    """Top wykonawcy w segmencie CPV+region."""
    params: dict[str, Any] = {"cpv": f"{cpv_prefix}%"}
    prov_filter = ""
    if province:
        prov_filter = "AND province = :province"
        params["province"] = province
    
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.text(f"""
                SELECT contractor_name, 
                       COUNT(*) AS wins,
                       ROUND(AVG(estimated_value)::numeric, 0) AS avg_val,
                       ROUND(AVG(offers_count)::numeric, 1) AS avg_competition
                FROM historical_tenders
                WHERE cpv_code LIKE :cpv
                  AND contractor_name IS NOT NULL
                  AND contractor_name != ''
                  AND estimated_value > 0
                  {prov_filter}
                GROUP BY contractor_name
                ORDER BY wins DESC
                LIMIT 10
            """), params).fetchall()
        
        return [
            {
                "name": r.contractor_name,
                "wins": int(r.wins),
                "avg_contract_value": float(r.avg_val) if r.avg_val else 0,
                "avg_competition": float(r.avg_competition) if r.avg_competition else 0,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("historical_intelligence._top_contractors: %s", e)
    return []


def _seasonality(engine: sa.Engine, cpv_prefix: str) -> dict:
    """Rozkład przetargów per miesiąc — kiedy pojawiają się w roku."""
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT EXTRACT(MONTH FROM date) AS month, COUNT(*) AS cnt
                FROM historical_tenders
                WHERE cpv_code LIKE :cpv AND date IS NOT NULL
                GROUP BY month ORDER BY month
            """), {"cpv": f"{cpv_prefix}%"}).fetchall()
        
        monthly = {int(r.month): int(r.cnt) for r in rows}
        total = sum(monthly.values()) or 1
        peak_month = max(monthly, key=lambda m: monthly[m], default=1)
        
        return {
            "monthly_distribution": monthly,
            "peak_month": peak_month,
            "peak_share": round(monthly.get(peak_month, 0) / total, 3),
            "total_historical": total,
        }
    except Exception as e:
        logger.warning("historical_intelligence._seasonality: %s", e)
    return {}


def _extract_keywords(title: str) -> list[str]:
    """Wyciągnij kluczowe słowa z tytułu (filtruj stop words PL)."""
    import re
    
    STOP_PL = {
        "w", "i", "z", "na", "do", "od", "dla", "o", "po", "ze", "nr",
        "oraz", "ul", "lub", "przez", "przy", "że", "się", "jest",
        "to", "nie", "tak", "jak", "co", "ale", "już",
        "realizacja", "wykonanie", "przedmiot", "zamówienia", "zakres",
        "zadanie", "część", "etap", "usługa", "dostawa",
    }
    
    # Wyciągnij alfanumeryczne tokeny > 3 znaków
    tokens = re.findall(r"[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]{4,}", title.lower())
    keywords = [t for t in tokens if t not in STOP_PL]
    
    return keywords[:8]


# ─── PUBLIC API: Wersja dla pipeline (single call) ────────────────────────────

def enrich_tender_analysis(
    tender_id: str,
    title: str,
    cpv_code: str | None = None,
    province: str | None = None,
    estimated_value: float | None = None,
    buyer: str | None = None,
) -> str:
    """Zwraca sformatowany kontekst tekstowy dla LLM w pipeline.
    
    Wywoływana z node_analyze_swz → wstrzyknięta do prompta Claude'a.
    """
    ctx = get_historical_context(title, cpv_code, province, estimated_value, buyer)
    
    lines = ["━━ HISTORICAL INTELLIGENCE ━━"]
    
    # Similar tenders
    similar = ctx.get("similar_tenders", [])
    if similar:
        lines.append(f"\n■ PODOBNE PRZETARGI ({len(similar)} najbardziej zbliżonych):")
        for i, s in enumerate(similar[:5], 1):
            val_str = f"{s['value_pln']:,.0f} PLN" if s.get('value_pln') else "?"
            winner = f" → wygr: {s['winner']}" if s.get('winner') else ""
            offers = f", {s['offers_count']} ofert" if s.get('offers_count') else ""
            lines.append(f"  {i}. [{s['date']}] {s['title']}")
            lines.append(f"     Wartość: {val_str}{offers}{winner}")
    
    # Segment benchmark
    bench = ctx.get("segment_benchmark", {})
    if bench and bench.get("n_tenders"):
        lines.append(f"\n■ BENCHMARK SEGMENTU (CPV {bench.get('cpv_prefix', '?')}, n={bench['n_tenders']}):")
        lines.append(f"  Mediana: {bench['median']:,.0f} PLN | Średnia: {bench['avg_value']:,.0f} PLN")
        lines.append(f"  P25–P75: {bench['p25']:,.0f} – {bench['p75']:,.0f} PLN")
        if bench.get("avg_offers_count"):
            lines.append(f"  Śr. liczba ofert: {bench['avg_offers_count']:.1f}")
    
    # Buyer profile
    bp = ctx.get("buyer_profile", {})
    if bp and bp.get("n_tenders"):
        lines.append(f"\n■ PROFIL ZAMAWIAJĄCEGO ({bp['n_tenders']} przetargów historycznie):")
        lines.append(f"  Średni budżet: {bp['avg_value']:,.0f} PLN | Łączna wartość: {bp['total_value']:,.0f} PLN")
        if bp.get("frequent_winners"):
            winners_str = ", ".join(f"{w['name']} ({w['wins']}x)" for w in bp["frequent_winners"][:3])
            lines.append(f"  Najczęstsi wykonawcy: {winners_str}")
    
    # Competition
    contractors = ctx.get("top_contractors", [])
    if contractors:
        lines.append(f"\n■ TOP WYKONAWCY W SEGMENCIE:")
        for c in contractors[:5]:
            lines.append(f"  • {c['name']} — {c['wins']} wygranych, śr. kontrakt {c['avg_contract_value']:,.0f} PLN")
    
    # Seasonality
    season = ctx.get("seasonality", {})
    if season and season.get("peak_month"):
        month_names = {1:"sty",2:"lut",3:"mar",4:"kwi",5:"maj",6:"cze",7:"lip",8:"sie",9:"wrz",10:"paź",11:"lis",12:"gru"}
        peak = month_names.get(season["peak_month"], "?")
        lines.append(f"\n■ SEZONOWOŚĆ: szczyt = {peak} ({season['peak_share']:.0%} przetargów)")
    
    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
