"""
Terra-OS Validation Router — /api/v2/validation/{bid_id}

Endpoints:
  GET  /api/v2/validation/{bid_id}          — run 47-point validation from DB
  GET  /api/v2/validation/{bid_id}/summary  — compact summary (status + counts)
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/validation", tags=["validation"])


def _result_to_dict(result) -> dict[str, Any]:
    """Convert ValidationResult dataclass to JSON-serialisable dict."""
    points_list = []
    for p in result.points:
        points_list.append({
            "id": p.id,
            "category": p.category.value if hasattr(p.category, "value") else str(p.category),
            "description": p.description,
            "pzp_reference": p.pzp_reference,
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "details": p.details,
            "auto_fixable": p.auto_fixable,
        })
    return {
        "bid_id": str(result.bid_id),
        "status": result.status,
        "passed": result.passed,
        "failed": result.failed,
        "warnings": result.warnings,
        "not_applicable": result.not_applicable,
        "total_checks": len(result.points),
        "critical_issues": result.critical_issues,
        "recommendations": result.recommendations,
        "validated_at": result.validated_at.isoformat() if result.validated_at else None,
        "points": points_list,
    }


@router.get(
    "/{bid_id}",
    summary="Run 47-point PZP validation for a bid (DB-backed)",
    response_class=JSONResponse,
)
async def validate_bid_endpoint(
    bid_id: UUID,
    strict_mode: bool = Query(False, description="Treat warnings as failures"),
    categories: str | None = Query(
        None,
        description="Comma-separated categories to check: completeness,formal,financial,legal,technical",
    ),
):
    """
    Run the 47-point PZP checklist for the given bid_id.

    Fetches real data from PostgreSQL (offers, kosztorys, tender_document,
    tender_documents, bid_intelligence) and evaluates each checkpoint.

    Returns full ValidationResult with per-point status and recommendations.
    """
    try:
        from ..intelligence.validation_engine import validate_bid

        # Run the DB-backed validation (sync, but fast enough for a request)
        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: validate_bid(bid_id, strict_mode=strict_mode)
        )

        return JSONResponse(content=_result_to_dict(result))

    except Exception as exc:
        logger.exception("Validation failed for bid_id=%s: %s", bid_id, exc)
        raise HTTPException(status_code=500, detail=f"Validation error: {exc}") from exc


@router.get(
    "/{bid_id}/summary",
    summary="Compact validation summary (status + counts only)",
    response_class=JSONResponse,
)
async def validate_bid_summary(
    bid_id: UUID,
    strict_mode: bool = Query(False, description="Treat warnings as failures"),
):
    """
    Returns a compact summary: overall status, pass/fail/warning counts,
    and recommendations — without the full per-point details.
    """
    try:
        from ..intelligence.validation_engine import validate_bid
        import asyncio

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: validate_bid(bid_id, strict_mode=strict_mode)
        )

        d = _result_to_dict(result)
        # Remove the verbose per-point list
        d.pop("points", None)
        return JSONResponse(content=d)

    except Exception as exc:
        logger.exception("Validation summary failed for bid_id=%s: %s", bid_id, exc)
        raise HTTPException(status_code=500, detail=f"Validation error: {exc}") from exc
