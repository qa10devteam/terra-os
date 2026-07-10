"""BZP Documents API Router — Terra-OS.

Endpoints:
  POST /api/v1/bzp/documents/{tender_id}/fetch          — trigger document scraping
  GET  /api/v1/bzp/documents/{tender_id}                — list fetched documents
  GET  /api/v1/bzp/documents/{tender_id}/download/{doc_id} — proxy/redirect download
"""
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from terra_db.session import get_engine
from ..auth.deps import AuthUser, TenantDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bzp/documents", tags=["bzp-documents"])

# Import scraper components
from bzp_document_scraper import (
    BZPDocumentScraper,
    extract_tender_id_from_url,
    BZP_BASE,
    NOTICE_PDF_API,
    _classify_document,
)


# ────────────────────────────────────────────────────────────────────
# Background fetch task
# ────────────────────────────────────────────────────────────────────

def _run_fetch(internal_tender_id: str, bzp_number: str | None, ocds_id: str | None):
    """Background task: pobiera dokumenty SWZ dla przetargu i zapisuje do DB.

    Strategia (bez auth):
    1. Notice PDF z GetNoticePdf (zawsze działa)
    2. URL zewnętrznej platformy SWZ z htmlBody (sekcja 3.1)
    """
    engine = get_engine()
    storage = Path("/var/lib/terra-os/documents")
    storage.mkdir(parents=True, exist_ok=True)

    scraper = BZPDocumentScraper(storage_dir=storage, db_engine=engine)
    with scraper:
        # Determine what to pass as tender_id for list_documents
        # Priority: BZP number > OCDS id > internal UUID
        doc_key = bzp_number or ocds_id or internal_tender_id

        result = scraper.fetch_all(
            tender_id=internal_tender_id,
            bzp_number=bzp_number,
            download_files=True,
        )

    logger.info(
        "BZP fetch done: tender=%s bzp=%s docs=%d downloaded=%d errors=%d swz_url=%s",
        internal_tender_id,
        bzp_number,
        len(result.documents),
        result.downloaded,
        len(result.errors),
        result.swz_platform_url or "—",
    )


# ────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────

@router.post("/{tender_id}/fetch")
def fetch_tender_documents(
    tender_id: str,
    background_tasks: BackgroundTasks,
    user: AuthUser,
    tenant_id: TenantDep,
) -> dict:
    """Wyzwól pobieranie dokumentów SWZ z BZP dla danego przetargu.

    Scraper używa publicznego API ezamowienia.gov.pl (nie wymaga logowania):
    - Pobiera PDF ogłoszenia (GetNoticePdf)
    - Wyciąga link do zewnętrznej platformy SWZ z treści ogłoszenia
    """
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT id, url, source, external_id "
                "FROM tender WHERE id = :id AND tenant_id = :tid"
            ),
            {"id": tender_id, "tid": tenant_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Przetarg nie istnieje")

    # BZP number (external_id) is what drives the scraper
    bzp_number = row.external_id  # e.g. "2026/BZP 00331648"
    ocds_id = extract_tender_id_from_url(row.url)  # e.g. "ocds-148610-xxx"

    # Validate we have something useful
    if not bzp_number and not ocds_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "cannot_resolve_documents",
                "message": "Przetarg nie ma numeru BZP ani linku ezamowienia.gov.pl — brak dokumentów SWZ.",
                "source": row.source,
            },
        )

    background_tasks.add_task(_run_fetch, tender_id, bzp_number, ocds_id)

    return {
        "status": "queued",
        "tender_id": tender_id,
        "bzp_number": bzp_number,
        "ocds_id": ocds_id,
        "message": "Pobieranie dokumentów SWZ z ezamowienia.gov.pl w tle",
    }


@router.get("/{tender_id}")
def list_tender_documents(tender_id: str, user: AuthUser) -> dict:
    """Lista pobranych dokumentów SWZ dla przetargu."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, bzp_notice_id, doc_type, filename, url, fetched_at,
                       LENGTH(content) AS content_length
                FROM bzp_documents
                WHERE tender_id = :tid
                ORDER BY doc_type, fetched_at DESC
            """),
            {"tid": tender_id},
        ).fetchall()

    return {
        "tender_id": tender_id,
        "total": len(rows),
        "documents": [
            {
                "id": str(r.id),
                "notice_id": r.bzp_notice_id,
                "doc_type": r.doc_type,
                "filename": r.filename,
                "download_url": r.url,
                "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
            }
            for r in rows
        ],
    }


@router.get("/{tender_id}/download/{doc_id}")
async def download_document(tender_id: str, doc_id: str, user: AuthUser):
    """Proxy download dokumentu z ezamowienia.gov.pl lub lokalnego cache.

    - Jeśli plik jest już na dysku: stream z dysku
    - Jeśli URL zaczyna się http: proxy stream z ezamowienia.gov.pl
    - Jeśli to link SWZ (platformazakupowa itp.): redirect 302
    """
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT url, filename, content, doc_type "
                "FROM bzp_documents WHERE id = :id AND tender_id = :tid"
            ),
            {"id": doc_id, "tid": tender_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Dokument nie istnieje")

    # Check if downloaded locally
    content_val = row.content or ""
    local_path: Path | None = None
    if content_val.startswith("[file:"):
        path_str = content_val[6:].rstrip("]")
        p = Path(path_str)
        if p.exists():
            local_path = p

    # 1. Serve from local disk
    if local_path:
        def _iter_local():
            with open(local_path, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk

        media_type = (
            "application/pdf" if local_path.suffix == ".pdf"
            else "application/octet-stream"
        )
        return StreamingResponse(
            _iter_local(),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{row.filename}"'},
        )

    # 2. Proxy from remote URL (Notice PDF)
    url = row.url or ""
    if not url.startswith("http"):
        raise HTTPException(status_code=404, detail="URL dokumentu niedostępny")

    # SWZ links (platformazakupowa etc.) → redirect
    if row.doc_type == "SWZ" and "ezamowienia.gov.pl" not in url:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=url)

    # Stream PDF from ezamowienia.gov.pl
    async def _stream_remote():
        async with httpx.AsyncClient(
            timeout=120,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 Chrome/124"},
        ) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(65536):
                    yield chunk

    return StreamingResponse(
        _stream_remote(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{row.filename}"'},
    )
