#!/usr/bin/env python3
"""
bulk_ocr.py — OCR wszystkich PDFów w /var/lib/terra-os/documents
Wpisuje tender_document + document_chunk dla istniejących plików na dysku.

Użycie:
  cd /home/ubuntu/terra-os
  .venv/bin/python3.12 scripts/bulk_ocr.py [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from pathlib import Path

# PYTHONPATH
sys.path.insert(0, "/home/ubuntu/terra-os")
sys.path.insert(0, "/home/ubuntu/terra-os/services")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/db")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/shared")

import psycopg2
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bulk_ocr")

DOCS_DIR = Path(os.environ.get("TERRA_DOCUMENTS_DIR", "/var/lib/terra-os/documents"))
DEFAULT_TENANT = os.environ.get("DEFAULT_TENANT_ID", "ec3d1e16-2139-48c2-93b5-ffe0defd606d")


def get_db_url() -> str:
    env = {}
    env_path = Path("/home/ubuntu/terra-os/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v
    host = env.get("DB_HOST", "127.0.0.1")
    port = env.get("DB_PORT", "5432")
    name = env.get("DB_NAME", "terraos")
    user = env.get("DB_USER", "terraos")
    pw   = env.get("DB_PASSWORD", "")
    return f"postgresql://{user}:{pw}@{host}:{port}/{name}"


def ocr_pdf(pdf_path: Path) -> tuple[str, int]:
    """Wyciąga tekst z PDF (pdftext — szybkie, bez GPU, dla embeddowanych PDF).
    Zwraca (text, char_count)."""
    from pdftext.extraction import plain_text_output
    text = plain_text_output(str(pdf_path), sort=True)
    return text, len(text)


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
    return [c for c in chunks if len(c.strip()) > 30]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10, help="Max liczba PDF do przetworzenia")
    parser.add_argument("--dry-run", action="store_true", help="Tylko pokaż co by zrobiło")
    args = parser.parse_args()

    engine = create_engine(get_db_url())

    # Zbierz wszystkie PDFy
    all_pdfs = sorted(DOCS_DIR.rglob("*.pdf"))
    log.info("PDFy na dysku: %d | limit: %d", len(all_pdfs), args.limit)

    # Sprawdź które tender_document już istnieje (po local_path)
    with engine.connect() as conn:
        already = set(
            r[0] for r in conn.execute(
                text("SELECT local_path FROM tender_document WHERE parsed_ok=true AND local_path IS NOT NULL")
            ).fetchall()
        )
    log.info("Już przetworzone: %d", len(already))

    to_process = [p for p in all_pdfs if str(p) not in already][:args.limit]
    log.info("Do przetworzenia: %d", len(to_process))

    if args.dry_run:
        for p in to_process:
            print(f"  DRY: {p}")
        return

    ok, skip, err = 0, 0, 0

    for pdf_path in to_process:
        log.info("→ OCR: %s", pdf_path.name)

        # Wyciągnij numer BZP z nazwy pliku i matchuj w tender
        # Format: ogloszenie_2026_BZP_00345466.pdf → "2026/BZP 00345466"
        matched_tender = None
        import re
        m = re.search(r"(\d{4})_BZP_(\d+)", pdf_path.stem)
        if m:
            bzp_num = m.group(2)  # np. 00345466
            # Matchuj po samym numerze — ignoruje rok w ścieżce pliku
            # (scraper zapisuje pliki z rokiem pobrania, BZP numer ma rok publikacji)
            with engine.connect() as conn:
                row = conn.execute(
                    text("SELECT id::text, tenant_id::text, external_id FROM tender WHERE external_id LIKE :pat"),
                    {"pat": f"%BZP {bzp_num}%"},
                ).fetchone()
            if row:
                matched_tender = row
                log.info("  matched tender: %s → %s", row[2], row[0][:8])

        tender_id = matched_tender[0] if matched_tender else None
        tenant_id_to_use = matched_tender[1] if matched_tender else DEFAULT_TENANT

        # OCR
        try:
            markdown_text, _ = ocr_pdf(pdf_path)
        except Exception as e:
            log.error("  OCR FAILED: %s — %s", pdf_path.name, e)
            err += 1
            continue

        chunks = split_chunks(markdown_text)
        if not chunks:
            log.warning("  SKIP: brak treści po OCR: %s", pdf_path.name)
            skip += 1
            continue

        log.info("  chunks=%d | len=%d chars", len(chunks), len(markdown_text))

        # Zapisz tender_document + document_chunk
        doc_id = str(uuid.uuid4())
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO tender_document
                        (id, tenant_id, tender_id, kind, filename, local_path, mime, parsed_ok, pages, created_at)
                    VALUES
                        (:id, :tid, :tender_id, 'pdf', :filename, :local_path, 'application/pdf', true, :pages, NOW())
                    ON CONFLICT DO NOTHING
                """), {
                    "id":         doc_id,
                    "tid":        tenant_id_to_use,
                    "tender_id":  tender_id or None,
                    "filename":   pdf_path.name,
                    "local_path": str(pdf_path),
                    "pages":      len(chunks),
                })

                for ordinal, chunk_text in enumerate(chunks):
                    conn.execute(text("""
                        INSERT INTO document_chunk
                            (id, tenant_id, document_id, page, ordinal, content, created_at)
                        VALUES
                            (:id, :tid, :doc_id, :page, :ordinal, :content, NOW())
                        ON CONFLICT DO NOTHING
                    """), {
                        "id":      str(uuid.uuid4()),
                        "tid":     tenant_id_to_use,
                        "doc_id":  doc_id,
                        "page":    ordinal // 3,
                        "ordinal": ordinal,
                        "content": chunk_text,
                    })

            log.info("  ✓ saved: doc_id=%s chunks=%d", doc_id[:8], len(chunks))
            ok += 1

        except Exception as e:
            log.error("  DB ERROR: %s — %s", pdf_path.name, e)
            err += 1

    log.info("=== DONE: ok=%d skip=%d err=%d ===", ok, skip, err)

    # Podsumowanie
    with engine.connect() as conn:
        td = conn.execute(text("SELECT COUNT(*) FROM tender_document WHERE parsed_ok=true")).scalar()
        dc = conn.execute(text("SELECT COUNT(*) FROM document_chunk")).scalar()
    log.info("tender_document(parsed_ok=true)=%d | document_chunk=%d", td, dc)


if __name__ == "__main__":
    main()
