"""Faza 28 — Friedman/Gates Bidding Model.

Oblicza optymalny narzut (markup) maximalizując oczekiwany zysk E[profit] = P(win|m) * m * cost.
"""
from __future__ import annotations

import numpy as np


def optimal_markup(
    cost_estimate: float,
    n_competitors: int,
    historical_win_rates: list[dict] | None = None,
) -> dict:
    """Zwraca optymalny narzut wg modelu Friedmana.

    Args:
        cost_estimate: Szacowany koszt realizacji (PLN)
        n_competitors: Liczba konkurentów
        historical_win_rates: Lista dicts z kluczami {markup, won (0/1)}

    Returns:
        Dict z optimal_markup, win_probability, expected_profit, chart_data
    """
    markups = np.linspace(0.01, 0.35, 100)
    # Default prior: win prob decreases with markup
    # P(win|m) ~ exp(-k * m * n_competitors)
    k = 2.5  # calibration constant
    e_profits = []
    win_probs = []
    for m in markups:
        p_win = float(np.exp(-k * m * (n_competitors ** 0.7)))
        if historical_win_rates:
            # update with historical data
            relevant = [h for h in historical_win_rates if abs(h.get("markup", 0) - m) < 0.02]
            if relevant:
                hist_p = float(np.mean([h.get("won", 0) for h in relevant]))
                p_win = 0.6 * p_win + 0.4 * hist_p
        win_probs.append(float(p_win))
        e_profits.append(float(p_win * m * cost_estimate))

    best_idx = int(np.argmax(e_profits))
    return {
        "optimal_markup": float(markups[best_idx]),
        "win_probability": win_probs[best_idx],
        "expected_profit": e_profits[best_idx],
        "chart_data": [
            {"markup": float(m), "e_profit": float(ep), "win_prob": float(wp)}
            for m, ep, wp in zip(markups[::5], e_profits[::5], win_probs[::5])
        ],
    }
