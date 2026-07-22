"""YU-NA background tasks — Celery workers.

Faza 5: task definitions for BZP sync, document processing, analysis.
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import os
import logging
from datetime import datetime, timezone

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="services.api.services.api.tasks.sync_bzp_task",
    queue="normal",
    bind=True,
    max_retries=3,
)
def sync_bzp_task(self, days_back: int = 7, offline: bool = False):
    """Synchronize BZP tenders — runs every 15 minutes."""
    try:
        from terra_db.session import get_engine
        from services.ingestion.pipeline import run_ingest

        engine = get_engine()
        result = run_ingest(engine, days_back=days_back, offline=offline)
        logger.info(
            "BZP sync complete: fetched=%d created=%d updated=%d",
            result.raw_fetched, result.created, result.updated,
        )

        # S87 — Invalidate cache for all tenants after ingest
        try:
            from . import cache as _api_cache
            _api_cache.invalidate()
            logger.info("Cache invalidated after BZP sync")
        except Exception as _ce:
            logger.warning("Cache invalidation failed: %s", _ce)

        return {
            "status": "ok",
            "fetched": result.raw_fetched,
            "created": result.created,
            "updated": result.updated,
        }
    except Exception as exc:
        logger.error("BZP sync failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    name="services.api.services.api.tasks.process_document_task",
    queue="normal",
    bind=True,
    max_retries=2,
)
def process_document_task(self, document_id: str, org_id: str):
    """Process uploaded document — OCR (marker-pdf) → document_chunk."""
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text
        import uuid
        from pathlib import Path

        engine = get_engine()

        # 1. Pobierz ścieżkę pliku z tender_document
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT local_path, tenant_id, tender_id, mime FROM tender_document WHERE id = :id"),
                {"id": document_id},
            ).fetchone()

        if not row or not row[0]:
            logger.warning("process_document_task: brak local_path dla doc_id=%s", document_id)
            return {"status": "skip", "reason": "no_local_path"}

        local_path = Path(row[0])
        tenant_id  = str(row[1])
        tender_id  = str(row[2])

        if not local_path.exists():
            logger.warning("process_document_task: plik nie istnieje: %s", local_path)
            return {"status": "skip", "reason": "file_not_found"}

        # 2. OCR z marker-pdf
        logger.info("OCR start: doc_id=%s path=%s", document_id, local_path)
        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.config.parser import ConfigParser

            config = ConfigParser({"output_format": "markdown"})
            converter = PdfConverter(
                config=config.generate_config_dict(),
                artifact_dict=create_model_dict(),
                processor_list=config.get_processors(),
                renderer=config.get_renderer(),
            )
            rendered = converter(str(local_path))
            markdown_text = rendered.markdown
            pages_count = getattr(rendered, "page_count", None) or markdown_text.count("\n\n## ")
        except Exception as ocr_exc:
            logger.error("OCR failed doc_id=%s: %s", document_id, ocr_exc)
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE tender_document SET parsed_ok=false WHERE id=:id"),
                    {"id": document_id},
                )
            raise self.retry(exc=ocr_exc, countdown=60)

        # 3. Split na chunki (co ~3000 znaków z zachowaniem akapitów)
        def split_chunks(text: str, max_chars: int = 3000) -> list[str]:
            paragraphs = text.split("\n\n")
            chunks, current = [], ""
            for p in paragraphs:
                if len(current) + len(p) > max_chars and current:
                    chunks.append(current.strip())
                    current = p
                else:
                    current = (current + "\n\n" + p) if current else p
            if current.strip():
                chunks.append(current.strip())
            return chunks

        chunks = split_chunks(markdown_text)
        logger.info("OCR done: doc_id=%s chunks=%d pages≈%s", document_id, len(chunks), pages_count)

        # 4. Zapisz do document_chunk + oznacz tender_document.parsed_ok=true
        with engine.begin() as conn:
            for ordinal, chunk_text in enumerate(chunks):
                conn.execute(
                    text("""
                        INSERT INTO document_chunk (id, tenant_id, document_id, page, ordinal, content, created_at)
                        VALUES (:id, :tid, :doc_id, :page, :ordinal, :content, NOW())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "id":      str(uuid.uuid4()),
                        "tid":     tenant_id,
                        "doc_id":  document_id,
                        "page":    ordinal // 3,
                        "ordinal": ordinal,
                        "content": chunk_text,
                    },
                )
            conn.execute(
                text("UPDATE tender_document SET parsed_ok=true, pages=:pages WHERE id=:id"),
                {"pages": len(chunks), "id": document_id},
            )

        logger.info("process_document_task done: doc_id=%s chunks=%d", document_id, len(chunks))
        return {"status": "ok", "document_id": document_id, "chunks": len(chunks)}

    except Exception as exc:
        if not self.request.retries:
            logger.error("Document processing failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(
    name="services.api.services.api.tasks.run_analysis_task",
    queue="normal",
    bind=True,
    max_retries=2,
)
def run_analysis_task(self, tender_id: str, org_id: str):
    """Run full analysis on a tender — cost estimation + risk extraction."""
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        with engine.connect() as conn:
            tender = conn.execute(
                text("SELECT id, title, tenant_id FROM tender WHERE id = :tid"),
                {"tid": tender_id},
            ).fetchone()

            if not tender:
                return {"status": "error", "message": "Tender not found"}

            # Update status to analyzing
            conn.execute(
                text("UPDATE tender SET status = 'analyzing' WHERE id = :tid"),
                {"tid": tender_id},
            )
            conn.commit()

        logger.info("Analysis task for tender %s started (placeholder)", tender_id)
        return {"status": "ok", "tender_id": tender_id}
    except Exception as exc:
        logger.error("Analysis task failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(
    name="services.api.services.api.tasks.fire_tender_alerts",
    queue="normal",
    bind=True,
    max_retries=2,
)
def fire_tender_alerts(self, tenant_id: str | None = None, frequency: str = "daily"):
    """Faza 19 — Send alert email digests for all due tender_alert rows."""
    try:
        from services.ingestion.alert_runner import run_alert_runner
        stats = run_alert_runner(tenant_id=tenant_id, frequency=frequency)
        logger.info("Alert runner done: %s", stats)
        return {"status": "ok", **stats}
    except Exception as exc:
        logger.error("fire_tender_alerts failed: %s", exc)
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(
    name="services.api.services.api.tasks.notify_task",
    queue="critical",
)
def notify_task(user_id: str, org_id: str, notif_type: str, title: str, body: str = "", link: str = ""):
    """Create in-app notification."""
    try:
        from terra_db.session import get_engine
        from sqlalchemy import text

        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO notifications (user_id, org_id, type, title, body, link)
                    VALUES (:uid, :oid, :type, :title, :body, :link)
                """),
                {"uid": user_id, "oid": org_id, "type": notif_type,
                 "title": title, "body": body, "link": link},
            )
            conn.commit()
        return {"status": "ok"}
    except Exception as exc:
        logger.error("Notify task failed: %s", exc)
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="uzp.sync")
def sync_uzp_task():
    """Synchronizuje zmiany UZP — uruchamiany co 6 godzin przez Beat."""
    import subprocess
    result = subprocess.run(
        ['/home/ubuntu/terra-os/.venv/bin/python3.12', '/home/ubuntu/terra-os/scripts/uzp_tracker.py'],
        capture_output=True, text=True, timeout=300
    )
    return {'stdout': result.stdout[-500:], 'returncode': result.returncode}


@celery_app.task(name="ted.sync")
def sync_ted_task():
    """Synchronizuje ogłoszenia TED (UE) — uruchamiany raz dziennie."""
    import subprocess
    result = subprocess.run(
        ['/home/ubuntu/terra-os/.venv/bin/python3.12', '/home/ubuntu/terra-os/scripts/ted_importer.py', '--days-back', '7'],
        capture_output=True, text=True, timeout=600,
        cwd='/home/ubuntu/terra-os'
    )
    return {'returncode': result.returncode, 'stdout': result.stdout[-300:]}


@celery_app.task(name="pretender.sync")
def sync_pretender_task():
    """Synchronizuje sygnały pre-przetargowe — uruchamiany co 12 godzin."""
    import subprocess
    result = subprocess.run(
        ['/home/ubuntu/terra-os/.venv/bin/python3.12', '/home/ubuntu/terra-os/scripts/pretender_scanner.py'],
        capture_output=True, text=True, timeout=300,
        cwd='/home/ubuntu/terra-os'
    )
    return {'returncode': result.returncode, 'stdout': result.stdout[-300:]}

