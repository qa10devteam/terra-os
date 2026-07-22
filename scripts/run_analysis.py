#!/usr/bin/env python3
"""Batch analysis runner — omija plan gate, wywołuje langgraph_pipeline bezpośrednio.

Uruchom:
    cd /home/ubuntu/terra-os
    .venv/bin/python3.12 scripts/run_analysis.py [--limit N] [--tender-id UUID]

Domyślnie: analizuje wszystkie tendersy które mają document_chunk ale nie mają analysis.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

# Paths — identyczne jak terra-api.service
sys.path.insert(0, "/home/ubuntu/terra-os")
sys.path.insert(0, "/home/ubuntu/terra-os/services")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/db")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/shared")

os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "terraos")
os.environ.setdefault("DB_USER", "terraos")
os.environ.setdefault("DEFAULT_TENANT_ID", "ec3d1e16-2139-48c2-93b5-ffe0defd606d")
os.environ.setdefault("BEDROCK_REGION", "eu-west-1")
os.environ.setdefault("BEDROCK_MODEL", "eu.anthropic.claude-sonnet-4-6")

# Wczytaj .env z hasłem DB
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and "=" in _line and not _line.startswith("#"):
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_analysis")


def get_tenders_to_analyze(limit: int) -> list[dict]:
    """Tendersy z document_chunk ale bez analysis."""
    import sqlalchemy as sa
    from terra_db.session import get_engine
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT t.id::text, t.title
            FROM tender t
            WHERE EXISTS (
                SELECT 1 FROM tender_document td
                JOIN document_chunk dc ON dc.document_id = td.id
                WHERE td.tender_id = t.id
            )
            AND NOT EXISTS (
                SELECT 1 FROM analysis a WHERE a.tender_id::text = t.id::text
            )
            ORDER BY t.id
            LIMIT :lim
        """), {"lim": limit}).fetchall()
    return [{"id": r[0], "title": r[1]} for r in rows]


def run_pipeline_for_tender(tender_id: str) -> dict:
    """Odpala app_v1 pipeline bezpośrednio — bez HTTP, bez plan gate."""
    from services.agents.langgraph_pipeline import get_app_v1
    app_v1 = get_app_v1()
    import sqlalchemy as sa
    from terra_db.session import get_engine
    import uuid, json

    engine = get_engine()
    run_id = str(uuid.uuid4())

    # Zapisz agent_run start
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO agent_run (id, tenant_id, agent, status, input, started_at)
            VALUES (:id,
                    (SELECT tenant_id FROM tender WHERE id = CAST(:tid AS uuid)),
                    'v1_batch', 'running',
                    :inp, NOW())
            ON CONFLICT DO NOTHING
        """), {"id": run_id, "tid": tender_id,
               "inp": json.dumps({"tender_id": tender_id})})

    try:
        final_state: dict = {}
        for event in app_v1.stream({"tender_id": tender_id, "steps": []}):
            for node_name, node_output in event.items():
                final_state.update(node_output)
                logger.info("  node=%-25s tender=%s", node_name, tender_id[:8])

        status = "succeeded"
        error = None
    except Exception as exc:
        logger.error("  pipeline FAILED tender=%s: %s", tender_id[:8], exc)
        final_state = {}
        status = "failed"
        error = str(exc)

    # Zaktualizuj agent_run
    with engine.begin() as conn:
        conn.execute(sa.text("""
            UPDATE agent_run
            SET status=:status, output=:out, error=:err, finished_at=NOW()
            WHERE id=:id
        """), {"id": run_id, "status": status,
               "err": error,
               "out": json.dumps(final_state, default=str)})

    return {"run_id": run_id, "status": status, "state": final_state}


def main():
    parser = argparse.ArgumentParser(description="Batch SWZ analysis runner")
    parser.add_argument("--limit", type=int, default=20,
                        help="Maks. liczba przetargów do analizy (domyślnie 20)")
    parser.add_argument("--tender-id", type=str, default=None,
                        help="Analizuj tylko konkretny tender UUID")
    args = parser.parse_args()

    if args.tender_id:
        tenders = [{"id": args.tender_id, "title": "(single)"}]
    else:
        tenders = get_tenders_to_analyze(args.limit)

    if not tenders:
        logger.info("Brak tenderów do analizy — wszystkie mają już wpis w analysis.")
        return

    logger.info("=== START: %d tenderów do analizy ===", len(tenders))
    ok = 0
    fail = 0

    for i, t in enumerate(tenders, 1):
        logger.info("[%d/%d] %s | %s", i, len(tenders), t["id"][:8], (t["title"] or "")[:60])
        result = run_pipeline_for_tender(t["id"])
        if result["status"] == "succeeded":
            ok += 1
            score = result["state"].get("score")
            logger.info("  ✓ ok | score=%s", score)
        else:
            fail += 1

        # Małe opóźnienie między callami Bedrock
        if i < len(tenders):
            time.sleep(1)

    # Podsumowanie
    import sqlalchemy as sa
    from terra_db.session import get_engine
    engine = get_engine()
    with engine.connect() as conn:
        count = conn.execute(sa.text("SELECT COUNT(*) FROM analysis")).scalar()

    logger.info("=== DONE: ok=%d fail=%d | analysis rows=%d ===", ok, fail, count)


if __name__ == "__main__":
    main()
