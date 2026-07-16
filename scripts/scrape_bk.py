#!/usr/bin/env python3
"""Standalone scraper Bazy Konkurencyjności (BK) — źródło przetargów z funduszy UE.

Pobiera ogłoszenia z ostatnich 30 dni i upsertuje do tabeli tender.
Resume-safe: ON CONFLICT (tenant_id, source, external_id) DO UPDATE.

Użycie:
    python3 scripts/scrape_bk.py
    python3 scripts/scrape_bk.py --days-back 7
    python3 scripts/scrape_bk.py --days-back 30 --dry-run

Zmienne środowiskowe:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    DEFAULT_TENANT_ID
    BK_DAYS_BACK (domyślnie 30)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta

# === Paths — spójne z terra-api.service ===
sys.path.insert(0, "/home/ubuntu/terra-os")
sys.path.insert(0, "/home/ubuntu/terra-os/services")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/db")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/shared")
sys.path.insert(0, "/home/ubuntu/terra-os/services/ingestion")

os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DEFAULT_TENANT_ID", "ec3d1e16-2139-48c2-93b5-ffe0defd606d")

LOG_FILE = "/home/ubuntu/terra-os/logs/ingest_bk.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE),
    ],
)
logger = logging.getLogger("scrape_bk")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BK scraper dla Terra.OS")
    parser.add_argument(
        "--days-back",
        type=int,
        default=int(os.getenv("BK_DAYS_BACK", "30")),
        help="Ile dni wstecz pobierać (domyślnie 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pobierz i znormalizuj, ale NIE zapisuj do DB",
    )
    parser.add_argument(
        "--no-filter",
        action="store_true",
        help="Wyłącz filtr CPV (zapisz wszystkie branże, nie tylko budownictwo)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    days_back = args.days_back

    date_from = date.today() - timedelta(days=days_back)
    date_to = date.today()

    logger.info(
        "=== BK scraper start: date_from=%s date_to=%s dry_run=%s ===",
        date_from, date_to, args.dry_run,
    )

    # 1. Fetch
    from ingestion.bk_connector import fetch_bk_notices, normalize_bk_notice

    raw_notices = fetch_bk_notices(date_from=date_from, date_to=date_to)
    logger.info("Pobrano %d surowych ogłoszeń z BK", len(raw_notices))

    if not raw_notices:
        logger.warning("Brak ogłoszeń z BK — zakończono bez zmian w DB.")
        return

    # 2. Normalize
    tenders_in = []
    normalize_errors = 0
    for notice in raw_notices:
        try:
            tin = normalize_bk_notice(notice)
            if tin is not None:
                tenders_in.append(tin)
        except Exception as exc:
            logger.warning("Normalize error dla id=%s: %s", notice.get("id"), exc)
            normalize_errors += 1

    logger.info(
        "Znormalizowano: %d / %d (błędy: %d)",
        len(tenders_in), len(raw_notices), normalize_errors,
    )

    if args.dry_run:
        logger.info("DRY RUN — pomijam zapis do DB.")
        for t in tenders_in[:5]:
            logger.info("  [SAMPLE] %s | %s | cpv=%s", t.external_id, t.title[:60], t.cpv)
        return

    # 3. Upsert
    from terra_db.session import get_engine
    from ingestion.repository import get_or_create_default_tenant, upsert_tender

    engine = get_engine()
    tenant_id = get_or_create_default_tenant(engine)
    logger.info("Tenant ID: %s", tenant_id)

    created = 0
    updated = 0
    errors = 0

    for tin in tenders_in:
        try:
            _, was_created = upsert_tender(
                engine,
                tin,
                match_score=0.0,
                match_reason="bk_scraper",
                tenant_id=tenant_id,
            )
            if was_created:
                created += 1
            else:
                updated += 1
        except Exception as exc:
            logger.error(
                "Upsert error dla BK id=%s: %s", tin.external_id, exc
            )
            errors += 1

    logger.info(
        "=== BK scraper zakończony: created=%d updated=%d errors=%d ===",
        created, updated, errors,
    )

    if errors > 0:
        logger.warning("Było %d błędów podczas upsertu!", errors)

    # Podsumowanie
    print(
        f"\n✅ BK scraper zakończony:\n"
        f"   Pobrano z API:   {len(raw_notices)}\n"
        f"   Znormalizowano:  {len(tenders_in)}\n"
        f"   Nowe rekordy:    {created}\n"
        f"   Zaktualizowane:  {updated}\n"
        f"   Błędy:           {errors}\n"
        f"   Log:             {LOG_FILE}\n"
    )


if __name__ == "__main__":
    main()
