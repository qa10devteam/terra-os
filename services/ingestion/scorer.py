"""Scorer v3 — konfigurowalny per-tenant, z deadline bonus + CPV win rate.

Zmiany względem v2:
- load_scoring_config() → ScoringWeights z DB (scoring_config table)
- _deadline_score(): <14d→1.0, <30d→0.7, <60d→0.4, else→0.1
- _cpv_win_rate_score(): bazuje na bzp_results (kto wygrywał w CPV)
- score_tender() uwzględnia historical_win_weight z konfigu
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

# ─── ScoringWeights ────────────────────────────────────────────────────────────

@dataclass
class ScoringWeights:
    cpv_weight:            float = 0.35
    value_weight:          float = 0.20
    region_weight:         float = 0.15
    deadline_weight:       float = 0.10
    historical_win_weight: float = 0.20
    min_value_pln:         float | None = None
    max_value_pln:         float | None = None
    preferred_cpvs:        list[str] = field(default_factory=list)
    preferred_regions:     list[str] = field(default_factory=list)

    def normalize(self) -> "ScoringWeights":
        """Normalizuje wagi do sumy 1.0."""
        total = self.cpv_weight + self.value_weight + self.region_weight + \
                self.deadline_weight + self.historical_win_weight
        if total <= 0:
            return ScoringWeights()
        factor = 1.0 / total
        return ScoringWeights(
            cpv_weight=self.cpv_weight * factor,
            value_weight=self.value_weight * factor,
            region_weight=self.region_weight * factor,
            deadline_weight=self.deadline_weight * factor,
            historical_win_weight=self.historical_win_weight * factor,
            min_value_pln=self.min_value_pln,
            max_value_pln=self.max_value_pln,
            preferred_cpvs=self.preferred_cpvs,
            preferred_regions=self.preferred_regions,
        )


_DEFAULT_WEIGHTS = ScoringWeights()

# ─── DB helpers ────────────────────────────────────────────────────────────────

def load_scoring_config(tenant_id: str) -> ScoringWeights:
    """Ładuje konfigurację scoringu z DB dla tenanta. Fallback → defaults."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(text("""
                SELECT cpv_weight, value_weight, region_weight,
                       deadline_weight, historical_win_weight,
                       min_value_pln, max_value_pln,
                       preferred_cpvs, preferred_regions
                FROM scoring_config
                WHERE tenant_id = :tid
                LIMIT 1
            """), {"tid": tenant_id}).fetchone()
        if row:
            return ScoringWeights(
                cpv_weight=float(row[0] or 0.35),
                value_weight=float(row[1] or 0.20),
                region_weight=float(row[2] or 0.15),
                deadline_weight=float(row[3] or 0.10),
                historical_win_weight=float(row[4] or 0.20),
                min_value_pln=float(row[5]) if row[5] else None,
                max_value_pln=float(row[6]) if row[6] else None,
                preferred_cpvs=list(row[7] or []),
                preferred_regions=list(row[8] or []),
            ).normalize()
    except Exception as e:
        logger.warning(f"load_scoring_config failed: {e}")
    return _DEFAULT_WEIGHTS


def load_cpv_win_rates(tenant_id: str | None = None) -> dict[str, float]:
    """
    Ładuje win-rates per CPV prefix (5 cyfr) z bzp_results.
    Zwraca {cpv_prefix: 0.0–1.0}.
    """
    engine = get_engine()
    win_rates: dict[str, float] = {}
    try:
        with engine.connect() as conn:
            # Global win rates z bzp_results (kto często wygrywał)
            rows = conn.execute(text("""
                SELECT LEFT(cpv_main, 5) as prefix, COUNT(*) as wins
                FROM bzp_results
                WHERE cpv_main IS NOT NULL AND length(cpv_main) >= 5
                GROUP BY prefix
                ORDER BY wins DESC
                LIMIT 500
            """)).fetchall()

        if rows:
            max_wins = max(r[1] for r in rows) or 1
            for prefix, wins in rows:
                win_rates[prefix] = min(1.0, wins / max_wins)
    except Exception as e:
        logger.warning(f"load_cpv_win_rates failed: {e}")

    return win_rates


# ─── Scoring components ────────────────────────────────────────────────────────

def _cpv_score(tender_cpv: str | None, preferred_cpvs: list[str]) -> float:
    """CPV match: exact prefix match → 1.0, partial → 0.5, brak konfiguracji → 0.5 (neutral)."""
    if not preferred_cpvs:
        return 0.5  # neutral — tenant nie skonfigurował preferencji
    if not tender_cpv:
        return 0.0
    cpv = str(tender_cpv).strip()
    for pref in preferred_cpvs:
        p = str(pref).strip()
        if cpv.startswith(p) or p.startswith(cpv[:len(p)]):
            if len(p) >= 5:
                return 1.0
            return 0.5
    return 0.0


def _value_score(value_pln: float | None, weights: ScoringWeights) -> float:
    """Wartość w preferowanym przedziale → 1.0, brak konfiguracji → 0.5 (neutral)."""
    if weights.min_value_pln is None and weights.max_value_pln is None:
        return 0.5  # neutral
    if value_pln is None or value_pln <= 0:
        return 0.0
    lo = weights.min_value_pln or 0
    hi = weights.max_value_pln or float("inf")
    if lo <= value_pln <= hi:
        return 1.0
    if value_pln < lo:
        return max(0.0, 1.0 - (lo - value_pln) / max(lo, 1))
    return max(0.0, 1.0 - (value_pln - hi) / max(hi, 1))


def _region_score(voivodeship: str | None, preferred_regions: list[str]) -> float:
    if not preferred_regions:
        return 0.5  # neutral
    if not voivodeship:
        return 0.0
    v = voivodeship.lower().strip()
    for r in preferred_regions:
        if r.lower().strip() in v or v in r.lower().strip():
            return 1.0
    return 0.0


def _deadline_score(deadline: date | datetime | str | None) -> float:
    """
    Deadline proximity bonus:
    <14 dni → 1.0 (pilne, działaj teraz)
    <30 dni → 0.7
    <60 dni → 0.4
    ≥60 dni → 0.1
    brak    → 0.0
    """
    if deadline is None:
        return 0.0
    if isinstance(deadline, str):
        try:
            deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
    if isinstance(deadline, datetime):
        deadline = deadline.date()
    today = date.today()
    delta = (deadline - today).days
    if delta < 0:
        return 0.0  # Minął
    if delta < 14:
        return 1.0
    if delta < 30:
        return 0.7
    if delta < 60:
        return 0.4
    return 0.1


def _cpv_win_rate_score(tender_cpv: str | None, win_rates: dict[str, float]) -> float:
    """CPV win rate z historycznych wygranych."""
    if not tender_cpv or not win_rates:
        return 0.0
    prefix5 = str(tender_cpv)[:5]
    return win_rates.get(prefix5, 0.0)


# ─── Main scoring function ──────────────────────────────────────────────────────

def score_tender(
    tender: dict[str, Any],
    weights: ScoringWeights,
    win_rates: dict[str, float] | None = None,
) -> float:
    """
    Oblicza match_score (0.0–1.0) dla jednego przetargu.
    tender dict musi mieć: cpv_main, value_pln, voivodeship, deadline
    """
    w = weights.normalize()
    cpv   = tender.get("cpv_main") or tender.get("cpv")
    value = tender.get("value_pln") or tender.get("estimated_value_pln")
    region = tender.get("voivodeship") or tender.get("region")
    deadline = tender.get("deadline") or tender.get("submission_deadline")

    if value is not None:
        try:
            value = float(value)
        except (ValueError, TypeError):
            value = None

    components = {
        "cpv":    (w.cpv_weight,            _cpv_score(cpv, w.preferred_cpvs)),
        "value":  (w.value_weight,           _value_score(value, w)),
        "region": (w.region_weight,          _region_score(region, w.preferred_regions)),
        "deadline": (w.deadline_weight,      _deadline_score(deadline)),
        "win_rate": (w.historical_win_weight, _cpv_win_rate_score(cpv, win_rates or {})),
    }

    score = sum(wt * sc for wt, sc in components.values())
    return round(min(1.0, max(0.0, score)), 4)


# ─── Batch rescore ─────────────────────────────────────────────────────────────

def rescore_tenant(tenant_id: str, batch_size: int = 500) -> dict:
    """Rescoruje wszystkie przetargi tenanta. Zwraca statystyki."""
    weights = load_scoring_config(tenant_id)
    win_rates = load_cpv_win_rates(tenant_id)

    engine = get_engine()
    total = 0
    avg_before = 0.0
    avg_after = 0.0

    with engine.connect() as conn:
        count_row = conn.execute(text(
            "SELECT COUNT(*), AVG(match_score) FROM tender WHERE tenant_id = :tid"
        ), {"tid": tenant_id}).fetchone()
        if count_row:
            total = count_row[0]
            avg_before = float(count_row[1] or 0)

    offset = 0
    processed = 0
    with engine.begin() as conn:
        while True:
            rows = conn.execute(text("""
                SELECT id, cpv, value_pln, voivodeship, deadline_at, match_score
                FROM tender
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
                LIMIT :lim OFFSET :off
            """), {"tid": tenant_id, "lim": batch_size, "off": offset}).fetchall()

            if not rows:
                break

            for row in rows:
                tender_dict = {
                    "id": str(row[0]),
                    "cpv_main": row[1],
                    "value_pln": row[2],
                    "voivodeship": row[3],
                    "deadline": row[4],
                }
                new_score = score_tender(tender_dict, weights, win_rates)
                conn.execute(text(
                    "UPDATE tender SET match_score = :score WHERE id = :id"
                ), {"score": new_score, "id": str(row[0])})
                avg_after += new_score
                processed += 1

            offset += batch_size
            if len(rows) < batch_size:
                break

    if processed > 0:
        avg_after /= processed

    logger.info(
        f"Rescore tenant={tenant_id}: {processed} tenders, "
        f"avg {avg_before:.3f} → {avg_after:.3f}"
    )
    return {
        "total": total,
        "processed": processed,
        "avg_score_before": round(avg_before, 4),
        "avg_score_after": round(avg_after, 4),
    }


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant-id", required=True)
    ap.add_argument("--batch-size", type=int, default=500)
    args = ap.parse_args()
    result = rescore_tenant(args.tenant_id, batch_size=args.batch_size)
    print(f"Done: {result}")
