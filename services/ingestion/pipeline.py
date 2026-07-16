"""M1 — Ingestion pipeline: orchestrates fetch → normalize → filter → score → upsert."""
from __future__ import annotations
import logging
import os
import sqlalchemy as sa
from datetime import date, timedelta
from typing import Callable

from sqlalchemy.engine import Engine

from .bzp_connector import BZPConnector
from .filters import apply_filters
from .fixtures import load_bzp_fixtures
from .normalize import normalize_bzp_notice, normalize_ted_notice
from .repository import get_or_create_default_tenant, upsert_tender
from .scorer import OwnerProfileSnap, ScoringWeights, load_scoring_config, score_tender
from .ted_connector import TEDConnector
from .bk_connector import fetch_bk_notices, normalize_bk_notice

try:
    from terra_shared.audit import AuditWriter
    _AUDIT_AVAILABLE = True
except ImportError:
    _AUDIT_AVAILABLE = False

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
        self.bip_stored: int = 0
        self.dedup_pairs: int = 0

    def __repr__(self) -> str:
        return (
            f"IngestResult(fetched={self.raw_fetched}, norm={self.normalized}, "
            f"passed={self.passed_filter}, dropped={self.dropped_filter}, "
            f"created={self.created}, updated={self.updated}, errors={self.errors}, "
            f"bip={self.bip_stored}, dedup={self.dedup_pairs})"
        )


def run_ingest(
    engine: Engine,
    *,
    days_back: int = 7,
    offline: bool | None = None,
    owner_profile: OwnerProfileSnap | None = None,
    include_ted: bool = True,
    include_bip: bool = False,
    bip_region: str | None = None,
    bip_max_sites: int = 50,
    include_bk: bool = True,
    run_dedup: bool = True,
    tenant_id: str | None = None,  # explicit tenant override (multitenant SaaS)
    progress_cb: "Callable[[str, int], None] | None" = None,  # S23: (step, pct)
) -> IngestResult:
    """Full M1 ingestion pipeline — BZP + TED EU.

    Steps:
      1. Fetch raw notices from BZP + TED (or fixtures if offline)
      2. Normalize each notice to TenderIn
      3. Apply CPV + geo filters
      4. Score each tender vs owner profile
      5. Upsert to DB (idempotent)
    """
    result = IngestResult()
    use_fixtures = offline if offline is not None else TERRA_OFFLINE

    # S23: helper to safely call progress callback
    def _progress(step: str, pct: int) -> None:
        if progress_cb is not None:
            try:
                progress_cb(step, pct)
            except Exception:
                pass

    _progress("init", 5)

    date_from = date.today() - timedelta(days=days_back)
    date_to = date.today()

    # S19: BZP + TED both receive the same days_back (default 7) for consistency

    # Step 1a: BZP fetch
    _progress("fetching_bzp", 15)
    if use_fixtures:
        logger.info("OFFLINE mode — loading BZP fixtures")
        bzp_raw = load_bzp_fixtures()
    else:
        connector = BZPConnector()
        bzp_raw = connector.fetch_notices(date_from=date_from, date_to=date_to)

    logger.info("BZP fetched %d raw notices", len(bzp_raw))

    # Step 1b: TED fetch
    _progress("fetching_ted", 30)
    ted_raw: list = []
    if include_ted and not use_fixtures:
        try:
            ted = TEDConnector()
            ted_raw = ted.fetch_notices(date_from=date_from, date_to=date_to)
            ted.close()
            logger.info("TED fetched %d raw notices", len(ted_raw))
        except Exception as exc:
            logger.error("TED fetch failed: %s", exc)

    result.raw_fetched = len(bzp_raw) + len(ted_raw)

    # Step 1c: BK fetch (Baza Konkurencyjności)
    _progress("fetching_bk", 35)
    bk_raw: list = []
    if include_bk and not use_fixtures:
        try:
            bk_raw = fetch_bk_notices(date_from=date_from, date_to=date_to)
            logger.info("BK fetched %d raw notices", len(bk_raw))
        except Exception as exc:
            logger.error("BK fetch failed: %s", exc)

    result.raw_fetched += len(bk_raw)

    # Step 2a: Normalize BZP
    _progress("normalizing", 60)
    tenders_in = []
    for notice in bzp_raw:
        try:
            tin = normalize_bzp_notice(notice)
            if tin is not None:
                tenders_in.append(tin)
        except Exception as exc:
            logger.warning("BZP normalize error: %s", exc)
            result.errors += 1

    # Step 2b: Normalize TED
    for notice in ted_raw:
        try:
            tin = normalize_ted_notice(notice)
            if tin is not None:
                tenders_in.append(tin)
        except Exception as exc:
            logger.warning("TED normalize error: %s", exc)
            result.errors += 1

    # Step 2c: Normalize BK
    for notice in bk_raw:
        try:
            tin = normalize_bk_notice(notice)
            if tin is not None:
                tenders_in.append(tin)
        except Exception as exc:
            logger.warning("BK normalize error: %s", exc)
            result.errors += 1

    result.normalized = len(tenders_in)

    # Step 3: Resolve tenant + load per-tenant scoring config
    if not tenant_id:
        tenant_id = get_or_create_default_tenant(engine)
    logger.info("Ingest for tenant_id=%s", tenant_id)

    # Load per-tenant scoring weights (falls back to defaults if not configured)
    if owner_profile is not None:
        profile: ScoringWeights = owner_profile
    else:
        profile = load_scoring_config(str(tenant_id))

    # For geo pre-filtering: use preferred_regions from profile if it's OwnerProfileSnap
    # (has .voivodeships), otherwise fall back to preferred_regions
    _voivodeships = set(getattr(profile, "voivodeships", None) or list(profile.preferred_regions))

    # Step 3 (filter): Filter
    passed, dropped = apply_filters(
        tenders_in,
        voivodeships=_voivodeships,
    )
    result.passed_filter = len(passed)
    result.dropped_filter = len(dropped)
    logger.info("Filter: %d passed, %d dropped", result.passed_filter, result.dropped_filter)

    # Step 4+5: Score + Upsert
    _progress("scoring", 75)
    # tenant_id and profile already loaded above (Step 3)
    # Lazy import of ML scorer (optional, non-fatal)
    try:
        from services.ingestion.scorer_ml import get_ml_scorer as _get_ml_scorer
        _ml_scorer_inst = _get_ml_scorer()
    except Exception:
        _ml_scorer_inst = None

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
                # Notify ML scorer about each new tender inserted
                if _ml_scorer_inst is not None:
                    try:
                        _ml_scorer_inst.on_new_result()
                    except Exception:
                        pass
            else:
                result.updated += 1
        except Exception as exc:
            logger.warning("Upsert error for %s: %s", tender.external_id, exc)
            result.errors += 1

    # Trigger ML retrain in background if enough new tenders were created this run
    if result.created >= 7 and _ml_scorer_inst is not None:
        def _ml_retrain_bg(eng: object) -> None:
            try:
                logger.info("source=pipeline ml_retrain triggered (created=%d)", result.created)
                retrain_result = _ml_scorer_inst.retrain_from_db(eng)
                logger.info("source=pipeline ml_retrain done: %s", retrain_result)
            except Exception as exc:
                logger.warning("source=pipeline ml_retrain error: %s", exc)

        import threading as _threading
        _threading.Thread(target=_ml_retrain_bg, args=(engine,), daemon=True).start()

    logger.info("Ingest done: %r", result)

    # Step 5b: Auto-embed newly created tenders (background, non-blocking)
    if result.created > 0:
        try:
            import threading
            from services.ai.embedder import embed_tenders_batch as _embed_tenders_batch

            def _run_embed(eng, tid: str) -> None:
                try:
                    n = _embed_tenders_batch(eng, tid)
                    logger.info("Step 5b: embedded %d tenders for tenant=%s", n, tid)
                except Exception as _e:
                    logger.info("Step 5b: embed_tenders_batch skipped: %s", _e)

            threading.Thread(
                target=_run_embed,
                args=(engine, str(tenant_id)),
                daemon=True,
            ).start()
        except Exception as _exc5b:
            logger.info("Step 5b: auto-embed init skipped: %s", _exc5b)

    # S58: KRS auto-enrich for new tenders with buyer_nip not yet in buyer_crm
    try:
        with engine.connect() as conn:
            rows_nip = conn.execute(sa.text("""
                SELECT DISTINCT t.buyer_nip
                FROM tender t
                WHERE t.tenant_id = :tid
                  AND t.buyer_nip IS NOT NULL
                  AND t.buyer_nip <> ''
                  AND NOT EXISTS (
                      SELECT 1 FROM buyer_crm bc
                      WHERE bc.nip = t.buyer_nip AND bc.tenant_id = :tid
                  )
                LIMIT 20
            """), {"tid": str(tenant_id)}).fetchall()
        if rows_nip:
            def _krs_enrich_batch(nips: list[str], tid: str) -> None:
                try:
                    from terra_db.session import get_engine as _get_engine
                    eng2 = _get_engine()
                    for nip_val in nips:
                        try:
                            info: dict = {"name": ""}
                            try:
                                import httpx
                                with httpx.Client(
                                    timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=3.0),
                                    follow_redirects=True,
                                    headers={"Accept": "application/json", "User-Agent": "TerraOS/1.0"},
                                ) as krs_client:
                                    r = krs_client.get(
                                        f"https://api-krs.ms.gov.pl/api/krs/OdpisAktualny/podmiot/nip/{nip_val}",
                                    )
                                if r.status_code == 200:
                                    d = r.json()
                                    info = {"name": d.get("odpis", {}).get("dane", {}).get("dzialy", {}).get("dzial1", {}).get("danePodmiotu", {}).get("nazwa", "")}
                            except Exception as e:
                                logger.debug("source=pipeline krs_enrich nip=%s: %s", nip_val, e)
                            with eng2.connect() as c2:
                                c2.execute(sa.text("""
                                    INSERT INTO buyer_crm (id, tenant_id, buyer_nip, crm_stage, notes, last_verified_at)
                                    VALUES (gen_random_uuid(), :tid, :nip, 'prospect',
                                            :note, now())
                                    ON CONFLICT (tenant_id, buyer_nip) DO UPDATE
                                    SET last_verified_at = now()
                                """), {"tid": tid, "nip": nip_val,
                                       "note": info.get("name", "")})
                                c2.commit()
                        except Exception as e:
                            logger.debug("source=pipeline krs_enrich nip=%s: %s", nip_val, e)
                except Exception as e:
                    logger.warning("source=pipeline krs_enrich_batch failed: %s", e)
            import threading
            nip_list = [r[0] for r in rows_nip]
            threading.Thread(target=_krs_enrich_batch, args=(nip_list, str(tenant_id)), daemon=True).start()
            logger.info("S58: KRS enrich started for %d NIPs", len(nip_list))
    except Exception as exc_s58:
        logger.debug("S58 KRS enrich skip: %s", exc_s58)

    # Step 6 (optional): BIP scraping
    if include_bip and not use_fixtures:
        _progress("fetching_bip", 45)
        try:
            from services.ingestion.bip_connector import run_bip_scraper
            bip_stats = run_bip_scraper(
                engine=engine,
                tenant_id=str(tenant_id),
                region=bip_region,
                max_sites=bip_max_sites,
                days_back=days_back,
            )
            result.bip_stored = bip_stats.get("tenders_stored", 0)
            logger.info("BIP ingest: %d tenders stored", result.bip_stored)
        except Exception as exc:
            logger.error("BIP ingest failed: %s", exc)

    # Step 7 (optional): Same-source deduplication
    if run_dedup and not use_fixtures:
        try:
            from services.ingestion.deduplicator import run_deduplicator
            dedup_stats = run_deduplicator(engine=engine, tenant_id=str(tenant_id))
            result.dedup_pairs = dedup_stats.get("new_pairs", 0)
            logger.info("Dedup: %d new duplicate pairs", result.dedup_pairs)
        except Exception as exc:
            logger.error("Dedup failed: %s", exc)

    # Step 7b (optional): Cross-source BZP↔TED deduplication
    if run_dedup and not use_fixtures:
        try:
            from services.ingestion.deduplicator import find_cross_source_duplicates
            cross_stats = find_cross_source_duplicates(engine)
            cross_pairs = cross_stats.get("pairs_marked", 0)
            result.dedup_pairs += cross_pairs
            logger.info(
                "Cross-source dedup (BZP↔TED): %d pairs marked, %d skipped",
                cross_pairs,
                cross_stats.get("skipped", 0),
            )
        except Exception as exc:
            logger.error("Cross-source dedup failed: %s", exc)

    # Step 8 (optional): Auto-fetch SWZ documents for high-score new tenders
    if not use_fixtures and result.created > 0:
        try:
            from services.ingestion.bzp_document_scraper import BZPDocumentScraper
            import sqlalchemy as sa

            # Fetch top matched new tenders (BZP only, score >= 0.5)
            with engine.connect() as conn:
                rows = conn.execute(sa.text("""
                    SELECT t.id, t.external_id
                    FROM tender t
                    LEFT JOIN bzp_documents bd ON bd.tender_id = t.id
                    WHERE t.source = 'bzp'
                      AND t.match_score >= 0.5
                      AND t.tenant_id = :tid
                      AND bd.id IS NULL
                    ORDER BY t.match_score DESC, t.created_at DESC
                    LIMIT 10
                """), {"tid": str(tenant_id)}).fetchall()

            if rows:
                logger.info("Auto-fetch SWZ: %d high-score tenders", len(rows))
                with BZPDocumentScraper(db_engine=engine) as scraper:
                    fetched_ok = 0
                    for row in rows:
                        try:
                            fr = scraper.fetch_all(
                                tender_id=str(row[0]),
                                bzp_number=row[1],
                                download_files=False,  # nie pobieraj plików, tylko metadane
                            )
                            if fr.documents:
                                fetched_ok += 1
                                # Step 8b: embed document chunks for RAG
                                try:
                                    from services.ai.rag import embed_document_chunks as _embed_doc_chunks
                                    for doc in fr.documents:
                                        try:
                                            _doc_text = ""
                                            if doc.local_path:
                                                try:
                                                    with open(doc.local_path, "r", errors="ignore") as _fh:
                                                        _doc_text = _fh.read(100_000)
                                                except Exception:
                                                    pass
                                            if _doc_text:
                                                _embed_doc_chunks(
                                                    engine,
                                                    str(row[0]),
                                                    _doc_text,
                                                    source_id=doc.object_id,
                                                    source_type="bzp_document",
                                                )
                                        except Exception as _e_doc:
                                            logger.debug("Step 8b: embed doc chunk skip %s: %s", doc.filename, _e_doc)
                                except Exception as _e_rag:
                                    logger.debug("Step 8b: rag embed skipped for tender %s: %s", row[0], _e_rag)
                        except Exception as e:
                            logger.debug("Auto-fetch SWZ skip %s: %s", row[0], e)
                logger.info("Auto-fetch SWZ done: %d/%d OK", fetched_ok, len(rows))
        except Exception as exc:
            logger.warning("Auto-fetch SWZ failed (non-fatal): %s", exc)

    # S69: Risk extraction for newly fetched SWZ documents
    try:
        from services.documents.risk_extractor import extract_risk_flags, risk_level as _risk_level
        with engine.connect() as conn:
            docs = conn.execute(sa.text("""
                SELECT td.id, td.tender_id, td.local_path, td.parsed_ok
                FROM tender_document td
                JOIN tender t ON t.id = td.tender_id
                WHERE t.tenant_id = :tid
                  AND td.risk_level = 'unknown'
                  AND td.parsed_ok = true
                ORDER BY td.created_at DESC
                LIMIT 20
            """), {"tid": str(tenant_id)}).fetchall()

        for doc in docs:
            try:
                text_content = ""
                if doc.local_path:
                    try:
                        with open(doc.local_path, "r", errors="ignore") as fh:
                            text_content = fh.read(50_000)
                    except Exception:
                        pass
                flags = extract_risk_flags(text_content)
                lvl, rscore = _risk_level(flags)
                with engine.connect() as conn2:
                    conn2.execute(sa.text("""
                        UPDATE tender_document
                        SET risk_level = :lvl, risk_score = :score
                        WHERE id = :doc_id
                    """), {"lvl": lvl, "score": rscore, "doc_id": str(doc.id)})
                    # S69: notification for high-risk documents
                    if lvl == "high":
                        conn2.execute(sa.text("""
                            INSERT INTO notifications (id, org_id, type, title, body)
                            SELECT gen_random_uuid(), o.id,
                                   'high_risk_document',
                                   'Wysokie ryzyko w dokumencie SWZ',
                                   :body
                            FROM organizations o
                            JOIN tenant ten ON ten.id = :tid
                            WHERE o.id = ten.id
                            LIMIT 1
                        """), {
                            "tid": str(tenant_id),
                            "body": f"Dokument {doc.id}: flagi {flags}",
                        })
                    conn2.commit()
            except Exception as exc2:
                logger.debug("S69 risk extraction skip doc %s: %s", doc.id, exc2)
    except Exception as exc_s69:
        logger.debug("S69 risk extraction skip: %s", exc_s69)

    # Sprint 9: Audit log — ingest.complete
    if _AUDIT_AVAILABLE:
        try:
            from terra_shared.audit import AuditWriter as _AW
            _audit = _AW()
            _audit.log(
                tenant_id=str(tenant_id),
                actor="pipeline",
                action="ingest.complete",
                entity_kind="ingest_result",
                payload={
                    "raw_fetched": result.raw_fetched,
                    "normalized": result.normalized,
                    "created": result.created,
                    "updated": result.updated,
                    "errors": result.errors,
                },
                ok=result.errors == 0,
            )
            _audit.write_to_db(engine)
        except Exception as exc:
            logger.debug("Audit log failed (non-critical): %s", exc)

    # S15: Auto-refresh mv_dashboard_stats after ingest complete
    try:
        from sqlalchemy import text as _t
        with engine.connect() as _c:
            _c.execute(_t('REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_stats'))
            _c.commit()
    except Exception as e:
        logger.warning('MV refresh failed: %s', e)

    # S91: n8n trigger_webhook on ingest complete
    try:
        from services.api.services.api.integrations.n8n_client import trigger_webhook
        trigger_webhook(
            "TenderCreated",
            {"count": result.created, "normalized": result.normalized},
            str(tenant_id),
        )
    except Exception as exc:
        logger.debug("n8n trigger_webhook non-critical: %s", exc)

    # AI Enrichment: embed vectors + RAG chunks + ML retrain + auto-summaries
    # Runs in background daemon thread — non-blocking, best-effort
    try:
        from services.ai.enricher import run_enrichment
        run_enrichment(engine, str(tenant_id), background=True)
        logger.info("source=pipeline ai_enrichment scheduled for tenant=%s", tenant_id)
    except Exception as exc:
        logger.debug("source=pipeline ai_enrichment skip: %s", exc)

    # S23: final done step
    _progress("done", 100)

    return result
