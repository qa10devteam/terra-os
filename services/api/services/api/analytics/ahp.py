"""Faza 29 — AHP Decision Support.

Wielokryterialna analiza decyzji GO/NO-GO z wagami AHP.
"""
from __future__ import annotations

DEFAULT_CRITERIA = [
    {"id": "technical_fit",   "label": "Fit techniczny",           "weight": 0.25},
    {"id": "expected_margin", "label": "Marża oczekiwana",         "weight": 0.20},
    {"id": "team_load",       "label": "Obciążenie zespołu",       "weight": 0.15},
    {"id": "penalty_risk",    "label": "Ryzyko kar",               "weight": 0.15},
    {"id": "strategic_value", "label": "Wartość strategiczna",     "weight": 0.10},
    {"id": "cashflow_impact", "label": "Cash flow impact",         "weight": 0.10},
    {"id": "buyer_history",   "label": "Historia z zamawiającym",  "weight": 0.05},
]


def compute_ahp_score(
    scores: dict[str, float],
    criteria: list[dict] | None = None,
) -> dict:
    """Oblicza wynik AHP.

    Args:
        scores: {criterion_id: 0-10}
        criteria: Lista kryteriów z wagami (domyślnie DEFAULT_CRITERIA)

    Returns:
        {total: 0-100, recommendation: GO|CONSIDER|NO-GO, breakdown: [...]}
    """
    criteria = criteria or DEFAULT_CRITERIA
    total = 0.0
    breakdown = []
    for c in criteria:
        raw = float(scores.get(c["id"], 5.0))
        raw = max(0.0, min(10.0, raw))
        weighted = (raw / 10.0) * c["weight"] * 100
        total += weighted
        breakdown.append(
            {
                "criterion": c["label"],
                "score": raw,
                "weight": c["weight"],
                "contribution": round(weighted, 2),
            }
        )

    recommendation = "GO" if total >= 65 else ("CONSIDER" if total >= 45 else "NO-GO")
    return {
        "total": round(total, 1),
        "recommendation": recommendation,
        "breakdown": breakdown,
    }
