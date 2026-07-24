"""
/api/v2/intelligence/* — Historical Intelligence endpoints.

Expose historical_tenders intelligence: similar tenders, benchmarks, buyer profiles.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth.deps import get_current_user

router = APIRouter(prefix="/api/v2/intelligence", tags=["intelligence"])


class SimilarRequest(BaseModel):
    title: str
    cpv_code: str | None = None
    province: str | None = None
    estimated_value: float | None = None
    buyer: str | None = None
    limit: int = 10


@router.post("/similar")
async def find_similar(req: SimilarRequest, _user=Depends(get_current_user)):
    """Find similar historical tenders based on title, CPV, region."""
    from ..intelligence.historical_intelligence import get_historical_context
    ctx = get_historical_context(
        title=req.title,
        cpv_code=req.cpv_code,
        province=req.province,
        estimated_value=req.estimated_value,
        buyer=req.buyer,
        limit=req.limit,
    )
    return ctx


@router.get("/benchmark/{cpv_prefix}")
async def cpv_benchmark(cpv_prefix: str, province: str | None = None, _user=Depends(get_current_user)):
    """Get value benchmark for CPV segment from 1.4M historical tenders."""
    from ..intelligence.historical_intelligence import _segment_benchmark
    from terra_db.session import get_engine
    engine = get_engine()
    result = _segment_benchmark(engine, cpv_prefix, province)
    if not result:
        raise HTTPException(404, "No data for this CPV prefix")
    return result


@router.get("/buyer/{buyer_name}")
async def buyer_profile(buyer_name: str, _user=Depends(get_current_user)):
    """Get buyer profile — past tenders, winners, budget patterns."""
    from ..intelligence.historical_intelligence import _buyer_profile
    from terra_db.session import get_engine
    engine = get_engine()
    result = _buyer_profile(engine, buyer_name)
    if not result:
        raise HTTPException(404, "Buyer not found in historical data")
    return result


@router.get("/contractors/{cpv_prefix}")
async def top_contractors(cpv_prefix: str, province: str | None = None, _user=Depends(get_current_user)):
    """Top contractors (winners) in a CPV segment."""
    from ..intelligence.historical_intelligence import _top_contractors
    from terra_db.session import get_engine
    engine = get_engine()
    result = _top_contractors(engine, cpv_prefix, province)
    return {"cpv_prefix": cpv_prefix, "province": province, "contractors": result}


@router.get("/seasonality/{cpv_prefix}")
async def seasonality(cpv_prefix: str, _user=Depends(get_current_user)):
    """Monthly distribution of tenders for CPV segment."""
    from ..intelligence.historical_intelligence import _seasonality
    from terra_db.session import get_engine
    engine = get_engine()
    result = _seasonality(engine, cpv_prefix)
    return result


# ---------------------------------------------------------------------------
# Historical Search — full-text + filter search across 1.4M historical_tenders
# ---------------------------------------------------------------------------

@router.get("/historical-search")
async def historical_search(
    q: str | None = Query(None, description="Full-text search query (Polish)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    cpv_prefix: str | None = Query(None, description="CPV prefix filter, e.g. '45'"),
    province: str | None = Query(None, description="Province / voivodeship filter"),
    _user=Depends(get_current_user),
) -> dict[str, Any]:
    """
    Search 1.4M historical tenders with optional FTS, CPV prefix and province filters.
    Returns {items: [...], total: int}.
    """
    import os
    import psycopg2
    import psycopg2.extras

    db_host = os.environ.get("DB_HOST", "127.0.0.1")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "terraos")
    db_user = os.environ.get("DB_USER", "terraos")
    db_password = os.environ.get("DB_PASSWORD", "terra_dev_2026")

    where_clauses: list[str] = []
    params: list[Any] = []

    if q:
        where_clauses.append("title_tsv @@ plainto_tsquery('simple', %s)")
        params.append(q)

    if cpv_prefix:
        where_clauses.append("cpv_code LIKE %s")
        params.append(cpv_prefix + "%")

    if province:
        where_clauses.append("province ILIKE %s")
        params.append(province)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_sql = f"SELECT COUNT(*) FROM historical_tenders {where_sql}"
    data_sql = f"""
        SELECT
            id,
            title,
            buyer,
            estimated_value,
            submitting_offers_date,
            province,
            cpv_code
        FROM historical_tenders
        {where_sql}
        ORDER BY date DESC NULLS LAST
        LIMIT %s OFFSET %s
    """

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=int(db_port),
            dbname=db_name,
            user=db_user,
            password=db_password,
        )
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(count_sql, params)
                row = cur.fetchone()
                total: int = row["count"] if row else 0  # type: ignore[index]

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(data_sql, params + [limit, offset])
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc

    items = [
        {
            "id": r["id"],
            "title": r["title"],
            "buyer": r["buyer"],
            "value_pln": float(r["estimated_value"]) if r["estimated_value"] is not None else None,
            "deadline": r["submitting_offers_date"],
            "province": r["province"],
            "cpv_code": r["cpv_code"],
            "source": "bzp",
            "match_score": 0.75,
            "status": "scouting",
        }
        for r in rows
    ]

    return {"items": items, "total": total}

