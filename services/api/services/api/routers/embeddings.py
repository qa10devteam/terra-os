"""Embeddings stats router."""
from __future__ import annotations
import sqlalchemy as sa
from fastapi import APIRouter
from ..auth.deps import AuthUser
from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2/embeddings", tags=["embeddings"])


@router.get("/stats", summary="Statystyki embeddingów — liczba wektorów w DB")
def embeddings_stats(user: AuthUser):
    engine = get_engine()
    with engine.connect() as conn:
        try:
            count = conn.execute(sa.text(
                "SELECT count(*) FROM document_chunk WHERE embedding IS NOT NULL"
            )).scalar() or 0
            total = conn.execute(sa.text("SELECT count(*) FROM document_chunk")).scalar() or 0
        except Exception:
            count, total = 0, 0
    return {"embedded": count, "total_chunks": total, "coverage_pct": round(count / max(total, 1) * 100, 1)}
