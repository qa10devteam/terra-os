"""
/api/v2/intelligence/* — Historical Intelligence endpoints.

Expose historical_tenders intelligence: similar tenders, benchmarks, buyer profiles.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
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
