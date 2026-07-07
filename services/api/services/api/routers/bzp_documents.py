"""Faza 41 — BZP Full Document Fetch: pobieranie pełnych dokumentów SWZ z BZP API."""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import uuid
from datetime import datetime
from typing import Any

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v1/bzp/documents", tags=["bzp-documents"])

BZP_API_BASE = "https://ezamowienia.gov.pl/mo-board/api/v1"


def _fetch_and_store(tender_id: str, notice_id: str) -> dict:
    """Fetch SWZ documents from BZP API and store in DB."""
    engine = get_engine()
    fetched: list[dict] = []
    try:
        with httpx.Client(timeout=30) as client:
            # Try to get notice detail which contains document links
            resp = client.get(
                f"{BZP_API_BASE}/Notice/NoticePublicationByPagePublished",
                params={"NoticePublicationIdentifier": notice_id},
            )
            resp.raise_for_status()
            data = resp.json()
            docs = data if isinstance(data, list) else [data]
            for doc in docs:
                doc_url = doc.get("fileUrl") or doc.get("url") or ""
                filename = doc.get("fileName") or doc.get("filename") or "SWZ.pdf"
                content_text = doc.get("content") or doc.get("body") or ""
                with engine.connect() as conn:
                    conn.execute(
                        sa.text("""
                            INSERT INTO bzp_documents
                                (id, tender_id, bzp_notice_id, doc_type, filename, content, url, fetched_at)
                            VALUES (:id, :tender_id, :notice_id, 'SWZ', :filename, :content, :url, now())
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "tender_id": tender_id,
                            "notice_id": notice_id,
                            "filename": filename,
                            "content": content_text,
                            "url": doc_url,
                        },
                    )
                    conn.commit()
                fetched.append({"filename": filename, "url": doc_url})
    except Exception as exc:
        # Store stub on API failure
        with engine.connect() as conn:
            conn.execute(
                sa.text("""
                    INSERT INTO bzp_documents
                        (id, tender_id, bzp_notice_id, doc_type, filename, content, url, fetched_at)
                    VALUES (:id, :tender_id, :notice_id, 'SWZ', :filename, :content, :url, now())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "tender_id": tender_id,
                    "notice_id": notice_id,
                    "filename": f"{notice_id}_SWZ.pdf",
                    "content": f"[Fetch failed: {exc}]",
                    "url": f"{BZP_API_BASE}/Notice/{notice_id}",
                },
            )
            conn.commit()
        fetched.append({"error": str(exc)})
    return {"fetched": fetched, "notice_id": notice_id}


@router.post("/{tender_id}/fetch")
def fetch_tender_documents(
    tender_id: str,
    background_tasks: BackgroundTasks,
    user: AuthUser,
    notice_id: str | None = Query(None, description="BZP notice identifier"),
) -> dict:
    """Pobierz pełne dokumenty SWZ z BZP API dla danego przetargu."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, url, source FROM tender WHERE id = :id"),
            {"id": tender_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Przetarg nie istnieje")

    # Try to extract notice_id from url if not provided
    if not notice_id and row.url:
        # BZP URL pattern: .../og-pub/...NOTICE_ID...
        parts = row.url.rstrip("/").split("/")
        notice_id = parts[-1] if parts else tender_id

    background_tasks.add_task(_fetch_and_store, tender_id, notice_id or tender_id)
    return {
        "status": "queued",
        "tender_id": tender_id,
        "notice_id": notice_id,
        "message": "Pobieranie dokumentów SWZ w tle",
    }


@router.get("/{tender_id}")
def list_tender_documents(tender_id: str, user: AuthUser) -> dict:
    """Lista pobranych dokumentów dla przetargu."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, bzp_notice_id, doc_type, filename, url, fetched_at, created_at
                FROM bzp_documents
                WHERE tender_id = :tid
                ORDER BY created_at DESC
            """),
            {"tid": tender_id},
        ).fetchall()
    return {
        "tender_id": tender_id,
        "documents": [
            {
                "id": str(r.id),
                "notice_id": r.bzp_notice_id,
                "doc_type": r.doc_type,
                "filename": r.filename,
                "url": r.url,
                "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
            }
            for r in rows
        ],
    }


@router.get("/{tender_id}/doc/{doc_id}")
def get_document_content(tender_id: str, doc_id: str, user: AuthUser) -> dict:
    """Pobierz treść dokumentu SWZ."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("""
                SELECT id, bzp_notice_id, doc_type, filename, content, url, fetched_at
                FROM bzp_documents WHERE id = :id AND tender_id = :tid
            """),
            {"id": doc_id, "tid": tender_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Dokument nie istnieje")
    return {
        "id": str(row.id),
        "notice_id": row.bzp_notice_id,
        "doc_type": row.doc_type,
        "filename": row.filename,
        "content": row.content,
        "url": row.url,
        "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
    }
