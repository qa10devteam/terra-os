"""P1: Generuje embeddingi dla document_chunk i tender.embedding (jeśli brakuje).
Używa sentence-transformers paraphrase-multilingual-MiniLM-L12-v2 (384 dim).
Liczy też match_score dla tenderów bez score (per scoring_config).
"""
from __future__ import annotations
import sys, os, logging, json, math

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("embed_chunks")

sys.path.insert(0, "/home/ubuntu/terra-os")
sys.path.insert(0, "/home/ubuntu/terra-os/services")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/db")

with open("/home/ubuntu/terra-os/.env") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)
os.environ["DB_HOST"] = "127.0.0.1"
os.environ["DB_NAME"] = "terraos"
os.environ["DB_USER"] = "terraos"

import sqlalchemy as sa
from terra_db.session import get_engine

engine = get_engine()

# ── 1. Embed document_chunk ────────────────────────────────────────────────────
def embed_chunks(batch_size: int = 64) -> int:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    log.info("Model loaded")

    with engine.connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT id, content FROM document_chunk WHERE embedding IS NULL ORDER BY id"
        )).fetchall()

    if not rows:
        log.info("document_chunk: already embedded")
        return 0

    log.info("document_chunk: %d to embed", len(rows))
    ids = [str(r[0]) for r in rows]
    texts = [r[1] or "" for r in rows]

    done = 0
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        vecs = model.encode(batch_texts, batch_size=batch_size, normalize_embeddings=True).tolist()
        with engine.begin() as conn:
            for chunk_id, vec in zip(batch_ids, vecs):
                emb_str = "[" + ",".join(str(x) for x in vec) + "]"
                conn.execute(sa.text(
                    "UPDATE document_chunk SET embedding = CAST(:e AS vector) WHERE id = :id"
                ), {"e": emb_str, "id": chunk_id})
        done += len(batch_ids)
        log.info("  chunk embeddings: %d/%d", done, len(rows))

    return done


# ── 2. Compute match_score per scoring_config ──────────────────────────────────
def compute_match_scores() -> int:
    """
    Deterministyczny scoring per tenant:
    score = cpv_weight * cpv_match
          + value_weight * value_match
          + region_weight * region_match
          + deadline_weight * deadline_match
    Każdy składnik 0..1.
    """
    import datetime

    with engine.connect() as conn:
        configs = conn.execute(sa.text("SELECT * FROM scoring_config")).fetchall()
        cfg_cols = [r[0] for r in conn.execute(sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='scoring_config' ORDER BY ordinal_position"
        )).fetchall()]

    if not configs:
        log.info("No scoring_config — skipping match_score")
        return 0

    total_updated = 0
    for row in configs:
        cfg = dict(zip(cfg_cols, row))
        tenant_id = str(cfg["tenant_id"])

        preferred_cpvs: list[str] = cfg.get("preferred_cpvs") or []
        preferred_regions: list[str] = [r.lower().strip() for r in (cfg.get("preferred_regions") or [])]
        min_val = float(cfg.get("min_value_pln") or 0)
        max_val = float(cfg.get("max_value_pln") or 1e12)

        w_cpv = float(cfg.get("cpv_weight") or 0.35)
        w_val = float(cfg.get("value_weight") or 0.2)
        w_reg = float(cfg.get("region_weight") or 0.15)
        w_dead = float(cfg.get("deadline_weight") or 0.1)

        with engine.connect() as conn:
            tenders = conn.execute(sa.text(
                "SELECT id, cpv, value_pln, voivodeship, deadline_at "
                "FROM tender WHERE tenant_id = :tid AND match_score IS NULL"
            ), {"tid": tenant_id}).fetchall()

        if not tenders:
            continue

        log.info("tenant %s: computing score for %d tenders", tenant_id[:8], len(tenders))
        now = datetime.datetime.now(datetime.timezone.utc)

        with engine.begin() as conn:
            for t in tenders:
                tender_id, cpv_list, value_pln, voivodeship, deadline_at = t

                # CPV match — partial prefix match
                cpv_match = 0.0
                if cpv_list and preferred_cpvs:
                    tender_cpvs = cpv_list if isinstance(cpv_list, list) else [str(cpv_list)]
                    best = 0.0
                    for tc in tender_cpvs:
                        for pc in preferred_cpvs:
                            # exact prefix overlap
                            overlap = len(os.path.commonprefix([str(tc), str(pc)]))
                            best = max(best, min(1.0, overlap / max(len(str(pc)), 1)))
                    cpv_match = best

                # Value match — gaussian around range midpoint
                val_match = 0.0
                if value_pln is not None:
                    v = float(value_pln)
                    if min_val <= v <= max_val:
                        val_match = 1.0
                    elif v < min_val and min_val > 0:
                        val_match = max(0.0, 1.0 - (min_val - v) / min_val)
                    elif v > max_val and max_val > 0:
                        val_match = max(0.0, 1.0 - (v - max_val) / max_val)

                # Region match
                reg_match = 0.0
                if voivodeship and preferred_regions:
                    vv = voivodeship.lower().strip()
                    reg_match = 1.0 if any(vv == r or r in vv or vv in r for r in preferred_regions) else 0.0

                # Deadline match — prefer 14..60 days out
                dead_match = 0.5
                if deadline_at is not None:
                    try:
                        if deadline_at.tzinfo is None:
                            deadline_at = deadline_at.replace(tzinfo=datetime.timezone.utc)
                        days = (deadline_at - now).days
                        if 14 <= days <= 60:
                            dead_match = 1.0
                        elif days < 0:
                            dead_match = 0.0
                        elif days < 14:
                            dead_match = days / 14
                        else:
                            dead_match = max(0.2, 1.0 - (days - 60) / 300)
                    except Exception:
                        dead_match = 0.5

                score = round(w_cpv * cpv_match + w_val * val_match + w_reg * reg_match + w_dead * dead_match, 4)

                conn.execute(sa.text(
                    "UPDATE tender SET match_score = :s WHERE id = :id"
                ), {"s": score, "id": str(tender_id)})

        total_updated += len(tenders)
        log.info("  tenant %s: %d scores written", tenant_id[:8], len(tenders))

    return total_updated


# ── 3. Refresh MVs ─────────────────────────────────────────────────────────────
def refresh_mvs():
    mvs_to_refresh = ["mv_dashboard_stats", "mv_pipeline_kpi", "mv_scoring"]
    with engine.begin() as conn:
        for mv in mvs_to_refresh:
            try:
                conn.execute(sa.text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}"))
                log.info("MV %s refreshed", mv)
            except Exception as ex:
                try:
                    conn.execute(sa.text(f"REFRESH MATERIALIZED VIEW {mv}"))
                    log.info("MV %s refreshed (non-concurrent)", mv)
                except Exception as ex2:
                    log.warning("MV %s refresh failed: %s", mv, ex2)


if __name__ == "__main__":
    log.info("=== P1: Embeddingi + match_score ===")

    n_chunks = embed_chunks()
    log.info("document_chunk embeddingi: %d", n_chunks)

    n_scores = compute_match_scores()
    log.info("match_score updates: %d", n_scores)

    refresh_mvs()

    # Weryfikacja
    with engine.connect() as conn:
        dc_total = conn.execute(sa.text("SELECT COUNT(*) FROM document_chunk")).scalar()
        dc_emb = conn.execute(sa.text("SELECT COUNT(*) FROM document_chunk WHERE embedding IS NOT NULL")).scalar()
        t_null = conn.execute(sa.text("SELECT COUNT(*) FROM tender WHERE match_score IS NULL")).scalar()
        t_total = conn.execute(sa.text("SELECT COUNT(*) FROM tender")).scalar()

    log.info("=== DONE ===")
    log.info("document_chunk embeddings: %d/%d", dc_emb, dc_total)
    log.info("tender match_score NULL: %d/%d", t_null, t_total)
