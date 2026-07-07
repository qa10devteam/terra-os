"""Faza 15 — Full-Text Search router."""
from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/search", tags=["search"])

# Check once at startup which FTS config is available
def _fts_config() -> str:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT to_tsvector('polish', 'test')"))
        return "polish"
    except Exception:
        return "simple"

_FTS = _fts_config()


@router.get("")
def search(
    user: AuthUser,
    q: str = Query(..., min_length=2, description="Fraza wyszukiwania"),
    type: str | None = Query(None, description="tenders|documents"),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Full-text search po przetargach i dokumentach."""
    engine = get_engine()
    tenant_id = user.org_id

    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    items: list[dict] = []
    search_type = type or "tenders"

    if search_type in ("tenders", "all"):
        with engine.connect() as conn:
            try:
                rows = conn.execute(
                    sa.text(
                        f"""SELECT id, title, buyer, status, url, created_at,
                                  ts_headline('{_FTS}',
                                    coalesce(title,'') || ' ' || coalesce(buyer,''),
                                    plainto_tsquery('{_FTS}', :q),
                                    'MaxWords=15, MinWords=5'
                                  ) AS excerpt
                           FROM tender
                           WHERE tenant_id = :tid
                             AND to_tsvector('{_FTS}', coalesce(title,'') || ' ' || coalesce(buyer,''))
                                 @@ plainto_tsquery('{_FTS}', :q)
                           ORDER BY ts_rank(
                               to_tsvector('{_FTS}', coalesce(title,'') || ' ' || coalesce(buyer,'')),
                               plainto_tsquery('{_FTS}', :q)
                           ) DESC
                           LIMIT :limit"""
                    ),
                    {"tid": tenant_id, "q": q, "limit": limit},
                ).fetchall()
            except Exception:
                # Fallback: ILIKE search (new connection to clear aborted tx)
                rows = []

        # ILIKE fallback if FTS returned nothing or failed
        if not rows:
            with engine.connect() as conn2:
                rows = conn2.execute(
                    sa.text(
                        """SELECT id, title, buyer, status, url, created_at,
                                  '' AS excerpt
                           FROM tender
                           WHERE tenant_id = :tid
                             AND (title ILIKE :q_like OR buyer ILIKE :q_like)
                           ORDER BY created_at DESC
                           LIMIT :limit"""
                    ),
                    {"tid": tenant_id, "q": q, "q_like": f"%{q}%", "limit": limit},
                ).fetchall()

        for r in rows:
            items.append({
                "id": str(r.id),
                "type": "tender",
                "title": r.title,
                "excerpt": r.excerpt if r.excerpt else "",
                "url": f"/api/v2/tenders/{r.id}",
                "status": r.status,
            })

    if search_type in ("documents", "all"):
        with engine.connect() as conn:
            docs = conn.execute(
                sa.text(
                    """SELECT td.id, td.filename, td.tender_id, td.mime, td.created_at
                       FROM tender_document td
                       JOIN tender t ON t.id = td.tender_id
                       WHERE t.tenant_id = :tid
                         AND td.filename ILIKE :q_like
                       ORDER BY td.created_at DESC
                       LIMIT :limit"""
                ),
                {"tid": tenant_id, "q_like": f"%{q}%", "limit": limit},
            ).fetchall()

        for r in docs:
            items.append({
                "id": str(r.id),
                "type": "document",
                "title": r.filename,
                "excerpt": f"Dokument przetargu {r.tender_id}",
                "url": f"/api/v2/documents/{r.id}",
                "mime": r.mime,
            })

    return {"items": items, "total": len(items), "query": q}
