"""Cross-source tender deduplicator.

Finds near-duplicate tenders across bzp / ted / bip using:
1. PostgreSQL pg_trgm similarity on normalized title
2. Buyer name fuzzy match
3. Value similarity (within 20%)
4. Published-date proximity (within 30 days)

Writes results to tender_duplicate table:
    master_id    → the "best" record (prefer bzp > ted > bip)
    duplicate_id → the lower-quality duplicate

Usage:
    python deduplicator.py --tenant-id <UUID> --db-dsn <DSN>
    python deduplicator.py --tenant-id <UUID> --db-dsn <DSN> --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date

import sqlalchemy as sa
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Source priority: lower = preferred master
SOURCE_PRIORITY = {"bzp": 0, "ted": 1, "bip": 2, "bk": 3, "manual": 4, "excel": 5}

# Thresholds
TITLE_SIM_THRESHOLD = 0.55   # pg_trgm similarity
BUYER_SIM_THRESHOLD = 0.50
VALUE_RATIO_MAX = 0.25        # max 25% difference in value_pln
DATE_DAYS_MAX = 30            # max 30 days apart

# Minimum title similarity to even consider a pair
MIN_TITLE_SIM = 0.45


def normalize_text(s: str) -> str:
    """Lowercase, strip diacritics, remove common stopwords."""
    if not s:
        return ""
    # Lowercase + remove diacritics
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Remove punctuation except spaces
    s = re.sub(r"[^\w\s]", " ", s)
    # Remove stopwords
    STOPWORDS = {
        "w", "z", "na", "do", "i", "oraz", "dla", "nr", "ul", "al",
        "gmina", "miasto", "powiat", "urzad", "spolka", "sp", "zoo",
        "budowa", "przebudowa", "remont", "wykonanie", "dostawa", "zakup",
        "realizacja", "opracowanie", "usluga", "roboty",
    }
    words = [w for w in s.split() if w not in STOPWORDS and len(w) > 2]
    return " ".join(words)


@dataclass
class TenderRow:
    id: str
    source: str
    title: str
    buyer: str
    value_pln: float | None
    published_at: date | None
    title_norm: str = ""
    buyer_norm: str = ""

    def __post_init__(self):
        self.title_norm = normalize_text(self.title or "")
        self.buyer_norm = normalize_text(self.buyer or "")


def run_deduplicator(
    engine: sa.Engine,
    tenant_id: str,
    dry_run: bool = False,
    min_title_sim: float = TITLE_SIM_THRESHOLD,
) -> dict:
    """Find and record duplicate tenders for a tenant."""
    stats = {"pairs_found": 0, "new_pairs": 0, "skipped": 0}

    with engine.connect() as conn:
        # Step 1: Load all tenders for tenant
        rows = conn.execute(
            text("""
                SELECT id::text, source::text, title, buyer, value_pln,
                       published_at::date
                FROM tender
                WHERE tenant_id = :tid
                ORDER BY source, created_at
            """),
            {"tid": tenant_id},
        ).fetchall()

    if not rows:
        logger.info("No tenders found for tenant %s", tenant_id)
        return stats

    tenders = [
        TenderRow(
            id=str(r[0]),
            source=str(r[1]),
            title=str(r[2] or ""),
            buyer=str(r[3] or ""),
            value_pln=float(r[4]) if r[4] is not None else None,
            published_at=r[5],
        )
        for r in rows
    ]
    logger.info("Loaded %d tenders for deduplication", len(tenders))

    # Step 2: Use PostgreSQL pg_trgm to find candidate pairs efficiently
    # We'll do this in batches via SQL to avoid O(N^2) Python loop
    with engine.connect() as conn:
        # Create temp table with normalized titles
        conn.execute(text("DROP TABLE IF EXISTS _dedup_work"))
        conn.execute(text("""
            CREATE TEMP TABLE _dedup_work AS
            SELECT
                id,
                source::text as source,
                title,
                buyer,
                value_pln,
                published_at::date as pub_date
            FROM tender
            WHERE tenant_id = :tid
        """), {"tid": tenant_id})

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS _dedup_work_trgm
            ON _dedup_work USING gin (title gin_trgm_ops)
        """))

        # Step 3: Find candidate pairs using pg_trgm similarity
        logger.info("Searching for duplicate pairs (title sim >= %.2f)...", min_title_sim)
        pairs = conn.execute(text("""
            SELECT
                a.id      AS id_a,
                b.id      AS id_b,
                a.source  AS src_a,
                b.source  AS src_b,
                similarity(a.title, b.title) AS title_sim,
                a.value_pln AS val_a,
                b.value_pln AS val_b,
                a.pub_date  AS pub_a,
                b.pub_date  AS pub_b,
                a.buyer     AS buyer_a,
                b.buyer     AS buyer_b
            FROM _dedup_work a
            JOIN _dedup_work b
              ON a.id < b.id
             AND similarity(a.title, b.title) >= :min_sim
             AND a.source <> b.source
        """), {"min_sim": min_title_sim}).fetchall()

        logger.info("Candidate pairs from pg_trgm: %d", len(pairs))

        # Step 4: Score each pair
        duplicate_pairs: list[tuple[str, str, float, list[str]]] = []

        for row in pairs:
            id_a, id_b = str(row[0]), str(row[1])
            src_a, src_b = row[2], row[3]
            title_sim = float(row[4])
            val_a, val_b = row[5], row[6]
            pub_a, pub_b = row[7], row[8]
            buyer_a, buyer_b = str(row[9] or ""), str(row[10] or "")

            match_fields = ["title"]
            score = title_sim

            # Value check
            if val_a and val_b:
                ratio = abs(val_a - val_b) / max(val_a, val_b)
                if ratio <= VALUE_RATIO_MAX:
                    match_fields.append("value")
                    score += 0.15
                elif ratio > 0.5:
                    continue  # Values too different, skip

            # Date check
            if pub_a and pub_b:
                days_diff = abs((pub_a - pub_b).days)
                if days_diff <= DATE_DAYS_MAX:
                    match_fields.append("date")
                    score += 0.10
                elif days_diff > 90:
                    continue  # Too far apart in time

            # Buyer check (simple token overlap)
            buyer_a_norm = normalize_text(buyer_a)
            buyer_b_norm = normalize_text(buyer_b)
            if buyer_a_norm and buyer_b_norm:
                tokens_a = set(buyer_a_norm.split())
                tokens_b = set(buyer_b_norm.split())
                if tokens_a and tokens_b:
                    overlap = len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))
                    if overlap >= 0.5:
                        match_fields.append("buyer")
                        score += 0.10

            # Final threshold — require buyer match if title_sim < 0.70
            if title_sim < 0.70 and "buyer" not in match_fields:
                continue
            if score < min_title_sim:
                continue

            # Determine master: prefer bzp > ted > bip
            pri_a = SOURCE_PRIORITY.get(src_a, 9)
            pri_b = SOURCE_PRIORITY.get(src_b, 9)
            if pri_a <= pri_b:
                master_id, dup_id = id_a, id_b
            else:
                master_id, dup_id = id_b, id_a

            duplicate_pairs.append((master_id, dup_id, round(score, 4), match_fields))
            stats["pairs_found"] += 1

        logger.info("Confirmed duplicate pairs: %d", len(duplicate_pairs))

        if dry_run:
            for master_id, dup_id, score, fields in duplicate_pairs[:20]:
                # Look up titles
                t_m = next((t for t in tenders if t.id == master_id), None)
                t_d = next((t for t in tenders if t.id == dup_id), None)
                if t_m and t_d:
                    logger.info(
                        "DUP [%.2f] %s|%s  ≈  %s|%s  fields=%s",
                        score, t_m.source, t_m.title[:60],
                        t_d.source, t_d.title[:60], fields,
                    )
            return stats

        # Step 5: Write to tender_duplicate
        for master_id, dup_id, score, fields in duplicate_pairs:
            try:
                conn.execute(text("""
                    INSERT INTO tender_duplicate
                        (tenant_id, master_id, duplicate_id, similarity, match_fields)
                    VALUES
                        (:tid, :master, :dup, :sim, :fields)
                    ON CONFLICT (tenant_id, master_id, duplicate_id) DO UPDATE
                        SET similarity = EXCLUDED.similarity,
                            match_fields = EXCLUDED.match_fields
                """), {
                    "tid": tenant_id,
                    "master": master_id,
                    "dup": dup_id,
                    "sim": score,
                    "fields": fields,
                })
                stats["new_pairs"] += 1
            except Exception as e:
                logger.warning("Failed to insert duplicate pair: %s", e)
                stats["skipped"] += 1

        conn.commit()

    logger.info(
        "Deduplication done: %d pairs found, %d new, %d skipped",
        stats["pairs_found"], stats["new_pairs"], stats["skipped"],
    )
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cross-source tender deduplicator")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument("--db-dsn", required=True, help="PostgreSQL DSN")
    parser.add_argument("--dry-run", action="store_true", help="Only print, don't write")
    parser.add_argument("--min-sim", type=float, default=TITLE_SIM_THRESHOLD,
                        help=f"Min title similarity threshold (default {TITLE_SIM_THRESHOLD})")
    args = parser.parse_args()

    engine = sa.create_engine(args.db_dsn, pool_pre_ping=True)
    stats = run_deduplicator(
        engine=engine,
        tenant_id=args.tenant_id,
        dry_run=args.dry_run,
        min_title_sim=args.min_sim,
    )
    print(json.dumps(stats, indent=2))
