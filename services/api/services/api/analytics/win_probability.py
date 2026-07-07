"""Faza 34 — Win Probability Model.

Regresja logistyczna na danych historycznych ofert.
Fallback: model parametryczny Friedmana.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from .bidding import optimal_markup

logger = logging.getLogger(__name__)


class WinProbabilityModel:
    """Model prawdopodobieństwa wygrania przetargu."""

    def __init__(self) -> None:
        self._model: Any = None
        self._is_trained = False

    def train(self, bids: list[dict]) -> dict:
        """Trenuje model na historycznych ofertach.

        bids: lista dicts z kluczami:
            markup (float), n_competitors (int), cpv_group (str), won (0|1)
        """
        if len(bids) < 20:
            return {"status": "insufficient_data", "samples": len(bids)}

        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import StandardScaler

            X = []
            y = []
            for b in bids:
                markup = float(b.get("markup", 0.1))
                n_comp = float(b.get("n_competitors", 3))
                won = int(b.get("won", 0))
                X.append([markup, n_comp, markup * n_comp])
                y.append(won)

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            model = LogisticRegression(random_state=42)
            model.fit(X_scaled, y)

            self._model = (model, scaler)
            self._is_trained = True
            return {"status": "trained", "samples": len(X)}

        except Exception as e:
            logger.warning(f"Win probability training failed: {e}")
            return {"status": "failed", "error": str(e)}

    def predict(self, markup: float, n_competitors: int, cpv: str = "45") -> dict:
        """Zwraca prawdopodobieństwo wygrania dla danego narzutu."""
        if self._is_trained and self._model is not None:
            try:
                model, scaler = self._model
                X = scaler.transform([[markup, n_competitors, markup * n_competitors]])
                prob = float(model.predict_proba(X)[0][1])
                return {
                    "win_probability": round(prob, 4),
                    "method": "logistic_regression",
                    "markup": markup,
                    "n_competitors": n_competitors,
                }
            except Exception as e:
                logger.warning(f"Win probability prediction failed: {e}")

        # Fallback: model parametryczny Friedmana
        k = 2.5
        p_win = float(np.exp(-k * markup * (n_competitors ** 0.7)))
        return {
            "win_probability": round(p_win, 4),
            "method": "friedman_parametric",
            "markup": markup,
            "n_competitors": n_competitors,
        }

    def predict_curve(self, n_competitors: int, cpv: str = "45") -> list[dict]:
        """Zwraca krzywą P(win) w funkcji markup."""
        markups = np.linspace(0.01, 0.35, 50)
        return [
            {
                "markup": float(m),
                **self.predict(float(m), n_competitors, cpv),
            }
            for m in markups
        ]


# Singleton
_win_model = WinProbabilityModel()


def get_win_model() -> WinProbabilityModel:
    return _win_model
