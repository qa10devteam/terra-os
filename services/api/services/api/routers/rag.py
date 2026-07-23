"""RAG stats router."""
from __future__ import annotations
import sqlalchemy as sa
from fastapi import APIRouter
from ..auth.deps import AuthUser
from terra_db.session import get_engine

router = APIRouter(prefix="/api/v2/rag", tags=["rag"])


@router.get("/stats", summary="Statystyki RAG — chunks, pytania, wyniki")
def rag_stats(user: AuthUser):
    engine = get_engine()
    with engine.connect() as conn:
        try:
            chunks = conn.execute(sa.text("SELECT count(*) FROM document_chunk")).scalar() or 0
            docs = conn.execute(sa.text("SELECT count(DISTINCT tender_id) FROM document_chunk")).scalar() or 0
        except Exception:
            chunks, docs = 0, 0
    return {"chunks": chunks, "indexed_documents": docs, "vector_store": "pgvector", "status": "ok"}
