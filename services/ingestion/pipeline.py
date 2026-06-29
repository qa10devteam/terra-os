"""M1 — Ingestion pipeline: orchestrates fetch → normalize → filter → score → upsert."""
from __future__ import annotations

import logging
import os
from datetime import date, timedelta

from sqlalchemy.engine import Engine

from .bzp_connector import BZPConnector
from .filters import apply_filters
from .fixtures import load_bzp_fixtures
from .normalize import normalize_bzp_notice
from .repository import get_or_create_default_tenant, upsert_tender
from .scorer import OwnerProfileSnap, score_tender

logger = logging.getLogger(__name__)

TERRA_OFFLINE = os.getenv("TERRA_OFFLINE", "0") == "1"


class IngestResult:
    def __init__(self) -> None:
        self.raw_fetched: int = 0
        self.normalized: int = 0
        self.passed_filter: int = 0
        self.dropped_filter: int = 0
        self.created: int = 0
        self.updated: int = 0
        self.errors: int = 0

    def __repr__(self) -> str:
        return (
            f"IngestResult(fetched={self.raw_fetched}, norm={self.normalized}, "
            f"passed={self.passed_filter}, dropped={self.dropped_filter}, "
            f"created={self.created}, updated={self.updated}, errors={self.errors})"
        )


def run_ingest(
    engine: Engine,
    *,
    days_back: int = 7,
    offline: bool | None = None,
    owner_profile: OwnerProfileSnap | None = None,
) -> IngestResult:
    """Full M1 ingestion pipeline.

    Steps:
      1. Fetch raw notices from BZP (or fixtures if offline)
      2. Normalize each notice to TenderIn
      3. Apply CPV + geo filters
      4. Score each tender vs owner profile
      5. Upsert to DB (idempotent)
    """
    result = IngestResult()
    use_fixtures = offline if offline is not None else TERRA_OFFLINE
    profile = owner_profile or OwnerProfileSnap()

    # Step 1: Fetch
    if use_fixtures:
        logger.info("OFFLINE mode — loading BZP fixtures")
        raw_notices = load_bzp_fixtures()
    else:
        connector = BZPConnector()
        date_from = date.today() - timedelta(days=days_back)
        raw_notices = connector.fetch_notices(date_from=date_from)

    result.raw_fetched = len(raw_notices)
    logger.info("Fetched %d raw notices", result.raw_fetched)

    # Step 2: Normalize
    tenders_in = []
    for notice in raw_notices:
        try:
            tin = normalize_bzp_notice(notice)
            if tin is not None:
                tenders_in.append(tin)
        except Exception as exc:
            logger.warning("Normalize error: %s", exc)
            result.errors += 1

    result.normalized = len(tenders_in)

    # Step 3: Filter
    passed, dropped = apply_filters(
        tenders_in,
        voivodeships=profile.voivodeships,
    )
    result.passed_filter = len(passed)
    result.dropped_filter = len(dropped)
    logger.info("Filter: %d passed, %d dropped", result.passed_filter, result.dropped_filter)

    # Step 4+5: Score + Upsert
    tenant_id = get_or_create_default_tenant(engine)

    for tender in passed:
        try:
            score_result = score_tender(tender, profile)
            _, created = upsert_tender(
                engine,
                tender,
                match_score=score_result.score,
                match_reason=score_result.reason,
                tenant_id=tenant_id,
            )
            if created:
                result.created += 1
            else:
                result.updated += 1
        except Exception as exc:
            logger.warning("Upsert error for %s: %s", tender.external_id, exc)
            result.errors += 1

    logger.info("Ingest done: %r", result)
    return result
