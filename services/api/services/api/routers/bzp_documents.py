"""BZP Documents API Router — Terra-OS.

Endpoints:
  POST /api/v1/bzp/documents/{tender_id}/fetch              — uruchamia scraping (background)
  GET  /api/v1/bzp/documents/{tender_id}                    — lista pobranych dokumentów
  GET  /api/v1/bzp/documents/{tender_id}/download/{doc_id}  — proxy/redirect do pliku
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from terra_db.session import get_engine
from ..auth.deps import AuthUser, TenantDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bzp/documents", tags=["bzp-documents"])

# Import z namespace services.ingestion (działa dzięki namespace package)
from services.ingestion.bzp_document_scraper import (
    BZPDocumentScraper,
    STORAGE_DIR,
    extract_tender_id_from_url,
    _classify_document,
)


# ─────────────────────────────────────────────────────────────────────
# Background task
# ─────────────────────────────────────────────────────────────────────

def _run_fetch(internal_tender_id: str, bzp_number: str | None, ocds_id: str | None) -> None:
    """Background task: pobiera dokumenty SWZ i zapisuje do DB.

    Nie rzuca wyjątków — błędy loguje, żeby FastAPI BackgroundTasks
    nie crashował cicho.
    """
    try:
        engine  = get_engine()
        storage = STORAGE_DIR
        storage.mkdir(parents=True, exist_ok=True)

        with BZPDocumentScraper(storage_dir=storage, db_engine=engine) as scraper:
            result = scraper.fetch_all(
                tender_id=internal_tender_id,
                bzp_number=bzp_number,
                download_files=True,
            )

        logger.info(
            "BZP fetch: tender=%s bzp=%s docs=%d downloaded=%d errors=%d swz=%s",
            internal_tender_id,
            bzp_number or ocds_id or "—",
            len(result.documents),
            result.downloaded,
            len(result.errors),
            result.swz_platform_url or "—",
        )
        if result.errors:
            for err in result.errors:
                logger.warning("BZP fetch error: %s", err)

    except Exception as exc:
        logger.exception("Nieoczekiwany błąd w _run_fetch dla %s: %s", internal_tender_id, exc)


# ─────────────────────────────────────────────────────────────────────
# Endpointy
# ─────────────────────────────────────────────────────────────────────

@router.post("/{tender_id}/fetch")
def fetch_tender_documents(
    tender_id:        str,
    background_tasks: BackgroundTasks,
    user:             AuthUser,
    tenant_id:        TenantDep,
) -> dict:
    """Wyzwól pobieranie dokumentów SWZ z BZP dla przetargu.

    Scraper używa publicznego API ezamowienia.gov.pl (bez logowania):
    - PDF ogłoszenia z GetNoticePdf (wersje /01–/05)
    - Link do zewnętrznej platformy SWZ z treści ogłoszenia (sekcja 3.1)

    Pobieranie jest asynchroniczne (background task).
    Wynik sprawdź przez GET /{tender_id}.
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

    bzp_number = row.external_id   # np. "2026/BZP 00331648"
    ocds_id    = extract_tender_id_from_url(row.url or "")

    if not bzp_number and not ocds_id:
        raise HTTPException(
            status_code=422,
            detail={
                "error":   "cannot_resolve_documents",
                "message": "Przetarg nie ma numeru BZP ani linku ezamowienia.gov.pl.",
                "source":  row.source,
            },
        )

    background_tasks.add_task(_run_fetch, tender_id, bzp_number, ocds_id)

    return {
        "status":     "queued",
        "tender_id":  tender_id,
        "bzp_number": bzp_number,
        "ocds_id":    ocds_id,
        "message":    "Pobieranie dokumentów SWZ w tle. Sprawdź wynik za kilka sekund.",
    }


@router.get("/{tender_id}")
def list_tender_documents(tender_id: str, user: AuthUser) -> dict:
    """Lista pobranych dokumentów SWZ dla przetargu."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, bzp_notice_id, doc_type, filename, url,
                       content, fetched_at
                FROM bzp_documents
                WHERE tender_id = :tid
                ORDER BY doc_type, fetched_at DESC
            """),
            {"tid": tender_id},
        ).fetchall()

    documents = []
    for r in rows:
        # Rozmiar pliku z dysku (jeśli dostępny)
        size_kb: int | None = None
        content_val = r.content or ""
        if content_val.startswith("[file:"):
            try:
                path = Path(content_val[6:].rstrip("]"))
                if path.exists():
                    size_kb = path.stat().st_size // 1024
            except Exception:
                pass

        documents.append({
            "id":           str(r.id),
            "notice_id":    r.bzp_notice_id,
            "doc_type":     r.doc_type,
            "filename":     r.filename,
            "download_url": r.url,
            "size_kb":      size_kb,
            "fetched_at":   r.fetched_at.isoformat() if r.fetched_at else None,
            "is_local":     content_val.startswith("[file:"),
        })

    return {
        "tender_id": tender_id,
        "total":     len(documents),
        "documents": documents,
    }


@router.get("/{tender_id}/download/{doc_id}")
async def download_document(tender_id: str, doc_id: str, user: AuthUser):
    """Serwuje dokument z lokalnego cache lub proxy ze zdalnego URL.

    Logika:
    - Plik na dysku → stream z dysku (szybko, bez wychodzenia na zewnątrz)
    - Notice PDF bez lokalnego cache → proxy stream z ezamowienia.gov.pl
    - SWZ link (platformazakupowa itp.) → redirect 302 do zewnętrznej platformy
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

    content_val  = row.content or ""
    local_path: Path | None = None

    if content_val.startswith("[file:"):
        p = Path(content_val[6:].rstrip("]"))
        if p.exists():
            local_path = p

    # 1. Serwuj z dysku
    if local_path:
        media_type = "application/pdf" if local_path.suffix == ".pdf" else "application/octet-stream"

        def _iter_local():
            with open(local_path, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk

        return StreamingResponse(
            _iter_local(),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{row.filename}"'},
        )

    url = row.url or ""
    if not url.startswith("http"):
        raise HTTPException(status_code=404, detail="URL dokumentu niedostępny")

    # 2. SWZ link → redirect
    if row.doc_type == "SWZ":
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=url, status_code=302)

    # 3. Proxy PDF z ezamowienia.gov.pl
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
