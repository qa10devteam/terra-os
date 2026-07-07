"""Faza 37 — Bid Recommendation Engine.

Łączy AHP + Friedman + risk flags → rekomendacja GO/NO-GO.
"""
from __future__ import annotations

from .ahp import compute_ahp_score, DEFAULT_CRITERIA
from .bidding import optimal_markup
from .risk_extractor import extract_risks_from_text


def generate_recommendation(
    tender_data: dict,
    scores: dict[str, float] | None = None,
    cost_estimate: float | None = None,
    n_competitors: int = 4,
    historical_win_rates: list[dict] | None = None,
    swz_text: str = "",
) -> dict:
    """Generuje rekomendację ofertową.

    Args:
        tender_data: Dane przetargu z bazy
        scores: Oceny AHP {criterion_id: 0-10}
        cost_estimate: Szacowany koszt (PLN); jeśli None używa value_pln * 0.85
        n_competitors: Liczba oczekiwanych konkurentów
        historical_win_rates: Historia wygranych ofert
        swz_text: Tekst SWZ do analizy ryzyk

    Returns:
        Dict z pełną rekomendacją
    """
    # 1. AHP Score
    if scores is None:
        # Domyślne oceny na podstawie danych przetargu
        value_pln = float(tender_data.get("value_pln") or 0)
        scores = {
            "technical_fit": 6.0,
            "expected_margin": 5.0 if value_pln > 500_000 else 4.0,
            "team_load": 5.0,
            "penalty_risk": 5.0,
            "strategic_value": 5.0,
            "cashflow_impact": 5.0,
            "buyer_history": 5.0,
        }

    ahp_result = compute_ahp_score(scores)

    # 2. Cost & bidding model
    if cost_estimate is None:
        value_pln = float(tender_data.get("value_pln") or 0)
        cost_estimate = value_pln * 0.85 if value_pln > 0 else 100_000.0

    bidding = optimal_markup(cost_estimate, n_competitors, historical_win_rates)

    # 3. Risk extraction
    risks = extract_risks_from_text(swz_text) if swz_text else {"red_flags": []}

    # 4. Agregacja rekomendacji
    ahp_score = ahp_result["total"]
    win_prob = bidding["win_probability"]
    high_risks = [r for r in risks.get("red_flags", []) if r.get("severity") == "high"]

    # Override recommendation przy wysokim ryzyku
    recommendation = ahp_result["recommendation"]
    confidence = 0.7

    if len(high_risks) >= 3 and recommendation == "GO":
        recommendation = "CONSIDER"
        confidence = 0.5
    elif len(high_risks) >= 5:
        recommendation = "NO-GO"
        confidence = 0.8

    # Key opportunities
    key_opportunities = []
    if win_prob > 0.6:
        key_opportunities.append("Wysokie prawdopodobieństwo wygrania")
    if bidding["optimal_markup"] > 0.20:
        key_opportunities.append(f"Możliwy narzut {bidding['optimal_markup']*100:.1f}%")
    if ahp_score >= 65:
        key_opportunities.append("Dobry fit techniczny i strategiczny")

    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "ahp_score": ahp_score,
        "ahp_breakdown": ahp_result["breakdown"],
        "win_probability": win_prob,
        "optimal_markup": bidding["optimal_markup"],
        "expected_profit": bidding["expected_profit"],
        "cost_estimate": cost_estimate,
        "key_risks": [r["message"] for r in risks.get("red_flags", [])],
        "key_opportunities": key_opportunities,
        "bidding_chart": bidding["chart_data"],
        "n_competitors": n_competitors,
    }
