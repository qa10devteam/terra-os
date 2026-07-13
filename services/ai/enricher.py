"""AI Enricher — post-ingest AI enrichment coordinator.

Orchestrates the full AI enrichment pipeline after tenders are ingested:
  1. embed_tenders()         — compute pgvector embeddings for new tenders
  2. embed_swz_documents()   — chunk + embed SWZ documents for RAG
  3. score_ml()              — apply ML scorer to fresh tenders
  4. auto_summarize()        — generate LLM summaries for high-score tenders
  5. extract_risk()          — run risk flag extraction on SWZ documents

All steps are best-effort (wrapped in try/except) and log with source=enricher.
Designed to run in a background thread after run_ingest() completes.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Individual enrichment steps
# ---------------------------------------------------------------------------

def embed_tenders(engine: Any, tenant_id: str, limit: int = 500) -> int:
    """Embed tenders that lack pgvector embeddings. Returns count embedded."""
    try:
        from services.ai.router import Task  # lazy import — avoids circular deps at module load  # noqa: F401
        from services.ai.embedder import embed_tenders_batch
        count = embed_tenders_batch(engine, tenant_id=tenant_id, limit=limit)
        logger.info("source=enricher step=embed_tenders tenant=%s count=%d", tenant_id, count)
        return count
    except Exception as exc:
        logger.warning("source=enricher step=embed_tenders failed: %s", exc)
        return 0


def embed_swz_documents(engine: Any, tenant_id: str, limit: int = 20) -> int:
    """Embed un-chunked SWZ documents for RAG. Returns total chunks stored."""
    try:
        import sqlalchemy as sa
        from services.ai.rag import embed_document_chunks

        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT td.id, td.tender_id, td.local_path
                FROM tender_document td
                JOIN tender t ON t.id = td.tender_id
                WHERE t.tenant_id = :tid
                  AND td.parsed_ok = true
                  AND td.local_path IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM doc_chunks dc
                      WHERE dc.source_id = td.id
                  )
                ORDER BY td.created_at DESC
                LIMIT :lim
            """), {"tid": tenant_id, "lim": limit}).fetchall()

        if not rows:
            return 0

        total_chunks = 0
        for row in rows:
            try:
                text = ""
                if row[2]:  # local_path
                    try:
                        with open(row[2], "r", errors="ignore") as fh:
                            text = fh.read(100_000)
                    except OSError:
                        continue
                if not text.strip():
                    continue
                n = embed_document_chunks(
                    engine,
                    tender_id=str(row[1]),
                    text=text,
                    source_id=str(row[0]),
                    source_type="bzp_document",
                )
                total_chunks += n
            except Exception as exc:
                logger.debug("source=enricher step=embed_swz doc=%s: %s", row[0], exc)

        logger.info(
            "source=enricher step=embed_swz tenant=%s docs=%d chunks=%d",
            tenant_id, len(rows), total_chunks,
        )
        return total_chunks
    except Exception as exc:
        logger.warning("source=enricher step=embed_swz failed: %s", exc)
        return 0


def extract_risk_after_embed(engine: Any, tenant_id: str, limit: int = 20) -> int:
    """Extract risk flags from newly-chunked SWZ documents and update tender_document.risk_level.

    Runs after embed_swz_documents().  For each recently-embedded document that
    has doc_chunks but no risk_level yet, we load its text, call
    extract_risk_flags() and persist the resulting level back to the DB.

    Returns count of documents whose risk_level was updated.
    """
    try:
        import sqlalchemy as sa
        from services.documents.risk_extractor import extract_risk_flags, risk_level

        with engine.connect() as conn:
            rows = conn.execute(sa.text("""
                SELECT td.id, td.local_path
                FROM tender_document td
                JOIN tender t ON t.id = td.tender_id
                WHERE t.tenant_id = :tid
                  AND td.parsed_ok = true
                  AND td.local_path IS NOT NULL
                  AND (td.risk_level IS NULL OR td.risk_level = '')
                  AND EXISTS (
                      SELECT 1 FROM doc_chunks dc
                      WHERE dc.source_id = td.id
                  )
                ORDER BY td.created_at DESC
                LIMIT :lim
            """), {"tid": tenant_id, "lim": limit}).fetchall()

        if not rows:
            return 0

        updated = 0
        for row in rows:
            doc_id, local_path = row[0], row[1]
            try:
                with open(local_path, "r", errors="ignore") as fh:
                    text = fh.read(100_000)
                if not text.strip():
                    continue
                flags = extract_risk_flags(text)
                level, _score = risk_level(flags)
                with engine.begin() as conn2:
                    conn2.execute(
                        sa.text("UPDATE tender_document SET risk_level = :rl WHERE id = :id"),
                        {"rl": level, "id": str(doc_id)},
                    )
                updated += 1
            except Exception as exc:
                logger.debug("source=enricher step=extract_risk doc=%s: %s", doc_id, exc)

        logger.info(
            "source=enricher step=extract_risk tenant=%s updated=%d", tenant_id, updated
        )
        return updated
    except Exception as exc:
        logger.warning("source=enricher step=extract_risk failed: %s", exc)
        return 0


def trigger_ml_retrain_if_due(engine: Any) -> dict:
    """Trigger ML scorer retrain if enough new results have accumulated."""
    try:
        from services.ingestion.scorer_ml import get_ml_scorer
        ml = get_ml_scorer()
        if ml._records_since_train >= 7:
            result = ml.retrain_from_db(engine)
            logger.info("source=enricher step=ml_retrain result=%s", result)
            return result
        return {"status": "skipped", "reason": "insufficient_new_records",
                "records_since_train": ml._records_since_train}
    except Exception as exc:
        logger.warning("source=enricher step=ml_retrain failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def auto_summarize(engine: Any, tenant_id: str, limit: int = 5) -> int:
    """Generate LLM summaries for high-score tenders that lack summaries.

    Stores result in tender.ai_summary (if column exists).
    Uses AI router to pick correct LLM (LOCAL vLLM or CLOUD).
    Returns count of summaries generated.
    """
    try:
        import sqlalchemy as sa
        from services.ai.router import Task, get_client_for_task, system_prompt_for

        with engine.connect() as conn:
            # Check if ai_summary column exists
            try:
                rows = conn.execute(sa.text("""
                    SELECT t.id, t.title, t.description, t.buyer, t.cpv
                    FROM tender t
                    WHERE t.tenant_id = :tid
                      AND t.match_score >= 0.6
                      AND (t.ai_summary IS NULL OR t.ai_summary = '')
                    ORDER BY t.match_score DESC, t.created_at DESC
                    LIMIT :lim
                """), {"tid": tenant_id, "lim": limit}).fetchall()
            except Exception:
                # ai_summary column may not exist yet — skip silently
                return 0

        if not rows:
            return 0

        llm = get_client_for_task(Task.SUMMARIZE)
        sys_prompt = system_prompt_for(Task.SUMMARIZE)
        count = 0
        for row in rows:
            try:
                prompt = (
                    f"Przetarg: {row[1]}\n"
                    f"Zamawiający: {row[3] or 'nieznany'}\n"
                    f"CPV: {', '.join(row[4] or [])}\n"
                    f"Opis: {(row[2] or '')[:2000]}\n\n"
                    "Napisz krótkie podsumowanie (3-4 zdania) kluczowych wymagań i warunków przetargu."
                )
                summary = llm.generate(
                    prompt,
                    system=sys_prompt,
                    json_mode=True,
                )
                with engine.begin() as conn2:
                    conn2.execute(sa.text(
                        "UPDATE tender SET ai_summary = :s WHERE id = :id"
                    ), {"s": summary[:2000], "id": str(row[0])})
                count += 1
            except Exception as exc:
                logger.debug("source=enricher step=auto_summarize tender=%s: %s", row[0], exc)

        logger.info(
            "source=enricher step=auto_summarize tenant=%s count=%d", tenant_id, count
        )
        return count
    except Exception as exc:
        logger.warning("source=enricher step=auto_summarize failed: %s", exc)
        return 0


# ---------------------------------------------------------------------------
# Orchestrator: run all steps in background
# ---------------------------------------------------------------------------

def run_enrichment(
    engine: Any,
    tenant_id: str,
    *,
    steps: Optional[list[str]] = None,
    background: bool = True,
) -> Optional[threading.Thread]:
    """Run AI enrichment pipeline after ingest.

    Args:
        engine:     SQLAlchemy engine.
        tenant_id:  Tenant UUID string.
        steps:      Which steps to run. Default: all.
                    Options: ["embed_tenders", "embed_swz", "ml_retrain", "summarize"]
        background: If True (default), run in daemon background thread.
                    If False, run synchronously (for testing/manual runs).

    Returns:
        Thread if background=True, else None.
    """
    _all_steps = {"embed_tenders", "embed_swz", "ml_retrain", "summarize", "extract_risk"}
    active_steps = set(steps) if steps else _all_steps

    def _run() -> None:
        logger.info(
            "source=enricher START tenant=%s steps=%s", tenant_id, sorted(active_steps)
        )

        results: dict = {}

        if "embed_tenders" in active_steps:
            results["embed_tenders"] = embed_tenders(engine, tenant_id)

        if "embed_swz" in active_steps:
            results["embed_swz"] = embed_swz_documents(engine, tenant_id)

        if "extract_risk" in active_steps:
            results["extract_risk"] = extract_risk_after_embed(engine, tenant_id)

        if "ml_retrain" in active_steps:
            results["ml_retrain"] = trigger_ml_retrain_if_due(engine)

        if "summarize" in active_steps:
            results["summarize"] = auto_summarize(engine, tenant_id)

        logger.info("source=enricher DONE tenant=%s results=%s", tenant_id, results)

    if background:
        t = threading.Thread(target=_run, daemon=True, name=f"enricher-{tenant_id[:8]}")
        t.start()
        return t
    else:
        _run()
        return None
