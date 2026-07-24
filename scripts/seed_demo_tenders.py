#!/usr/bin/env python3
"""
Seed 150+ realistic construction tenders for the BudOS demo tenant.
Pulls from historical_tenders (1.4M records) filtered to construction CPV 45%
with value 500K–50M PLN.
"""
from __future__ import annotations

import os
import random
import sys
import uuid
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "terraos")
DB_USER = os.getenv("DB_USER", "terraos")
DB_PASSWORD = os.getenv("DB_PASSWORD", "terra_dev_2026")

DEMO_TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
BATCH_SIZE = 50

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_date(val: str | None) -> datetime | None:
    """Try to parse date/datetime string into a timezone-aware datetime."""
    if not val:
        return None
    val = str(val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            dt = datetime.strptime(val, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def main() -> None:
    print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}…")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # ------------------------------------------------------------------
    # Fetch source rows from historical_tenders
    # ------------------------------------------------------------------
    print("Querying historical_tenders for construction CPV-45 records…")
    cur.execute(
        """
        SELECT
            id,
            title,
            buyer,
            province,
            cpv_code,
            estimated_value,
            submitting_offers_date,
            date,
            notice_url
        FROM historical_tenders
        WHERE
            estimated_value > 500000
            AND estimated_value < 50000000
            AND cpv_code LIKE '45%%'
            AND submitting_offers_date IS NOT NULL
        ORDER BY date DESC
        LIMIT 300
        """,
    )
    rows = cur.fetchall()
    print(f"Found {len(rows)} candidate historical tender records.")

    if not rows:
        print("ERROR: no source rows found — check DB or filters.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Insert into tender with ON CONFLICT DO NOTHING
    # ------------------------------------------------------------------
    INSERT_SQL = """
        INSERT INTO tender (
            id,
            tenant_id,
            source,
            external_id,
            title,
            buyer,
            cpv,
            voivodeship,
            value_pln,
            deadline_at,
            published_at,
            url,
            status,
            match_score,
            raw,
            pipeline_status
        ) VALUES (
            %(id)s,
            %(tenant_id)s,
            %(source)s::source_kind,
            %(external_id)s,
            %(title)s,
            %(buyer)s,
            %(cpv)s,
            %(voivodeship)s,
            %(value_pln)s,
            %(deadline_at)s,
            %(published_at)s,
            %(url)s,
            %(status)s::tender_status,
            %(match_score)s,
            %(raw)s::jsonb,
            %(pipeline_status)s
        )
        ON CONFLICT (tenant_id, source, external_id) DO NOTHING
    """

    inserted_total = 0
    skipped_total = 0
    batch: list[dict] = []

    def flush_batch(batch_rows: list[dict]) -> tuple[int, int]:
        nonlocal conn
        ins = 0
        skp = 0
        for row_data in batch_rows:
            cur_inner = conn.cursor()
            cur_inner.execute(INSERT_SQL, row_data)
            if cur_inner.rowcount == 1:
                ins += 1
            else:
                skp += 1
        conn.commit()
        return ins, skp

    for idx, hist in enumerate(rows, start=1):
        deadline_dt = parse_date(hist["submitting_offers_date"])
        published_dt = parse_date(hist["date"]) if hist["date"] else None

        record = {
            "id": str(uuid.uuid4()),
            "tenant_id": DEMO_TENANT_ID,
            "source": "bzp",
            "external_id": str(hist["id"]),
            "title": (hist["title"] or "Brak tytułu")[:2000],
            "buyer": hist["buyer"],
            "cpv": [hist["cpv_code"]] if hist["cpv_code"] else [],
            "voivodeship": hist["province"],
            "value_pln": hist["estimated_value"],
            "deadline_at": deadline_dt,
            "published_at": published_dt,
            "url": hist["notice_url"] or "",
            "status": "new",
            "match_score": round(random.uniform(0.55, 0.95), 4),
            "raw": "{}",
            "pipeline_status": "scouting",
        }

        batch.append(record)

        if len(batch) >= BATCH_SIZE:
            ins, skp = flush_batch(batch)
            inserted_total += ins
            skipped_total += skp
            batch = []
            print(f"  Progress: {idx}/{len(rows)} processed — {inserted_total} inserted, {skipped_total} skipped")

    # flush remainder
    if batch:
        ins, skp = flush_batch(batch)
        inserted_total += ins
        skipped_total += skp

    cur.close()
    conn.close()

    print(f"\nDone! Inserted: {inserted_total}, Skipped (conflicts): {skipped_total}")

    # ------------------------------------------------------------------
    # Quick verification
    # ------------------------------------------------------------------
    conn2 = psycopg2.connect(
        host=DB_HOST, port=int(DB_PORT), dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    cur2 = conn2.cursor()
    cur2.execute(
        "SELECT COUNT(*) FROM tender WHERE tenant_id=%s",
        (DEMO_TENANT_ID,),
    )
    total = cur2.fetchone()[0]
    cur2.close()
    conn2.close()
    print(f"Total tenders for demo tenant after seeding: {total}")


if __name__ == "__main__":
    main()
