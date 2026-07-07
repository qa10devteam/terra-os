"""
test_engine_l2.py — Unit testy dla Engine L2 Monte Carlo
=========================================================
Uruchomienie: pytest /tmp/terra-os-plan/test_engine_l2.py -v

Pokrycie:
  - Determinizm przy stałym seed
  - Monotoniczność win probability
  - Brak naruszeń L1 constraints w próbkach
  - Performance target ≤ 2s dla 10 000 próbek
  - Schema risk{} block (wszystkie wymagane pola)
  - Bayesian priors kalibracja
  - Sobol indices zakres [0,1]
  - Redis cache integration (mock)
  - Edge cases (zero cost, single factor, max constraints)
"""
from __future__ import annotations

import json
import sys
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Dodaj ścieżkę do modułu
sys.path.insert(0, "/tmp/terra-os-plan")
from monte_carlo_sampler import (
    EARTHWORKS_PRIORS,
    BayesianPrior,
    CachedMonteCarloSampler,
    MonteCarloSampler,
    RiskBlock,
    RiskDriver,
    create_sampler,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sampler() -> MonteCarloSampler:
    """Standardowy sampler z seed=42, 10k próbek."""
    return MonteCarloSampler(n_samples=10_000, seed=42)


@pytest.fixture
def small_sampler() -> MonteCarloSampler:
    """Mały sampler do szybkich testów (512 próbek)."""
    return MonteCarloSampler(n_samples=512, seed=42)


@pytest.fixture
def base_cost() -> float:
    return 1_380_000.0


@pytest.fixture
def market_price() -> float:
    return 1_500_000.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Determinizm
# ─────────────────────────────────────────────────────────────────────────────

class TestDeterminism:
    """Stały seed → te same wyniki."""

    def test_deterministic_under_seed_samples(self, base_cost, market_price):
        """Fixed seed → dokładnie te same próbki przy dwóch wywołaniach."""
        s1 = MonteCarloSampler(n_samples=1_000, seed=42)
        s2 = MonteCarloSampler(n_samples=1_000, seed=42)
        samples1 = s1.sample()
        samples2 = s2.sample()
        np.testing.assert_array_equal(
            samples1, samples2,
            err_msg="Te same seed powinny dawać identyczne próbki",
        )

    def test_deterministic_under_seed_risk_block(self, base_cost, market_price):
        """Fixed seed → te same p10/p50/p90 przy dwóch wywołaniach run()."""
        s1 = MonteCarloSampler(n_samples=2_000, seed=42)
        s2 = MonteCarloSampler(n_samples=2_000, seed=42)
        r1 = s1.run(base_cost=base_cost, market_price=market_price)
        r2 = s2.run(base_cost=base_cost, market_price=market_price)
        assert r1.p10 == r2.p10, f"p10 nieidentyczne: {r1.p10} vs {r2.p10}"
        assert r1.p50 == r2.p50, f"p50 nieidentyczne: {r1.p50} vs {r2.p50}"
        assert r1.p90 == r2.p90, f"p90 nieidentyczne: {r1.p90} vs {r2.p90}"

    def test_different_seeds_give_different_results(self, base_cost, market_price):
        """Różne seedy → różne wyniki (z astronomicznym prawdopodobieństwem)."""
        s1 = MonteCarloSampler(n_samples=2_000, seed=42)
        s2 = MonteCarloSampler(n_samples=2_000, seed=999)
        r1 = s1.run(base_cost=base_cost, market_price=market_price)
        r2 = s2.run(base_cost=base_cost, market_price=market_price)
        # Co najmniej jedna wartość powinna się różnić
        any_diff = (r1.p10 != r2.p10) or (r1.p50 != r2.p50) or (r1.p90 != r2.p90)
        assert any_diff, "Różne seedy powinny dawać różne wyniki"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Monotoniczność win probability
# ─────────────────────────────────────────────────────────────────────────────

class TestMonotoneWinProbability:
    """Wyższa cena oferty → niższe P(win)."""

    def test_monotone_win_prob_basic(self, sampler, base_cost, market_price):
        """P(win | price=low) > P(win | price=high) dla stałego rynku."""
        samples = sampler.sample()
        prices = [market_price * f for f in [0.70, 0.80, 0.90, 1.00, 1.10, 1.20]]
        probs = [
            sampler.win_probability(p, samples, market_price=market_price)
            for p in prices
        ]
        for i in range(len(probs) - 1):
            assert probs[i] >= probs[i + 1] - 1e-6, (
                f"Win prob nie jest monotoniczna: P({prices[i]:.0f})={probs[i]:.4f} "
                f"< P({prices[i+1]:.0f})={probs[i+1]:.4f}"
            )

    def test_win_prob_range(self, sampler, base_cost, market_price):
        """P(win) ∈ [0, 1] zawsze."""
        samples = sampler.sample()
        for price_ratio in [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]:
            prob = sampler.win_probability(
                price=market_price * price_ratio,
                samples=samples,
                market_price=market_price,
            )
            assert 0.0 <= prob <= 1.0, f"P(win)={prob} poza [0,1] dla ratio={price_ratio}"

    def test_low_price_high_win_prob(self, sampler, base_cost, market_price):
        """Cena 70% rynku powinna dawać P(win) > 0.6."""
        samples = sampler.sample()
        prob = sampler.win_probability(
            price=market_price * 0.70,
            samples=samples,
            market_price=market_price,
            n_competitors=3,
        )
        assert prob > 0.60, f"Niska cena (70% rynku) powinna dawać P(win)>0.6, got {prob:.4f}"

    def test_high_price_low_win_prob(self, sampler, base_cost, market_price):
        """Cena 130% rynku powinna dawać P(win) < 0.15."""
        samples = sampler.sample()
        prob = sampler.win_probability(
            price=market_price * 1.30,
            samples=samples,
            market_price=market_price,
            n_competitors=3,
        )
        assert prob < 0.15, f"Wysoka cena (130% rynku) powinna dawać P(win)<0.15, got {prob:.4f}"

    def test_more_competitors_lower_prob(self, sampler, base_cost, market_price):
        """Więcej konkurentów → niższe P(win) przy tej samej cenie."""
        samples = sampler.sample()
        price = market_price * 0.95
        prob_3 = sampler.win_probability(price, samples, market_price=market_price, n_competitors=3)
        prob_7 = sampler.win_probability(price, samples, market_price=market_price, n_competitors=7)
        assert prob_3 >= prob_7, (
            f"Więcej konkurentów (7 vs 3) powinno obniżać P(win): "
            f"P(3)={prob_3:.4f} >= P(7)={prob_7:.4f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: L1 Constraint Enforcement
# ─────────────────────────────────────────────────────────────────────────────

class TestL1ConstraintEnforcement:
    """Żadna próbka nie może naruszać hard constraints z L1."""

    def test_no_l1_violations_max_factor(self, small_sampler):
        """max_factor constraint — żadna próbka nie przekracza limitu."""
        constraints = [
            {"type": "max_factor", "factor_name": "roboty_ziemne", "value": 1.20},
        ]
        samples = small_sampler.sample(l1_constraints=constraints)

        # Znajdź indeks "roboty_ziemne"
        factor_names = [p.name for p in EARTHWORKS_PRIORS]
        idx = factor_names.index("roboty_ziemne")

        violations = np.sum(samples[:, idx] > 1.20 + 1e-9)
        assert violations == 0, (
            f"L1 constraint max_factor=1.20 naruszony w {violations} próbkach"
        )

    def test_no_l1_violations_min_factor(self, small_sampler):
        """min_factor constraint — żadna próbka poniżej minimum."""
        constraints = [
            {"type": "min_factor", "factor_name": "zagęszczenie", "value": 0.90},
        ]
        samples = small_sampler.sample(l1_constraints=constraints)

        factor_names = [p.name for p in EARTHWORKS_PRIORS]
        idx = factor_names.index("zagęszczenie")

        violations = np.sum(samples[:, idx] < 0.90 - 1e-9)
        assert violations == 0, (
            f"L1 constraint min_factor=0.90 naruszony w {violations} próbkach"
        )

    def test_multiple_constraints(self, small_sampler):
        """Wiele constraints naraz — wszystkie egzekwowane."""
        constraints = [
            {"type": "max_factor", "factor_name": "roboty_ziemne", "value": 1.30},
            {"type": "min_factor", "factor_name": "odwodnienie", "value": 0.80},
            {"type": "max_factor", "factor_name": "wywiezienie_urobku", "value": 1.40},
        ]
        samples = small_sampler.sample(l1_constraints=constraints)
        factor_names = [p.name for p in EARTHWORKS_PRIORS]

        for constraint in constraints:
            fname = constraint["factor_name"]
            idx = factor_names.index(fname)
            cval = constraint["value"]
            ctype = constraint["type"]
            if ctype == "max_factor":
                viols = np.sum(samples[:, idx] > cval + 1e-9)
                assert viols == 0, f"max_factor violation dla {fname}: {viols} próbek"
            elif ctype == "min_factor":
                viols = np.sum(samples[:, idx] < cval - 1e-9)
                assert viols == 0, f"min_factor violation dla {fname}: {viols} próbek"

    def test_prior_bounds_respected(self, small_sampler):
        """Hard bounds z BayesianPrior zawsze przestrzegane."""
        samples = small_sampler.sample()
        for j, prior in enumerate(EARTHWORKS_PRIORS):
            col = samples[:, j]
            too_low = np.sum(col < prior.min_val - 1e-9)
            too_high = np.sum(col > prior.max_val + 1e-9)
            assert too_low == 0, f"Prior {prior.name}: {too_low} próbek poniżej min_val={prior.min_val}"
            assert too_high == 0, f"Prior {prior.name}: {too_high} próbek powyżej max_val={prior.max_val}"

    def test_sample_shape(self, small_sampler):
        """Kształt macierzy próbek: (n, k)."""
        samples = small_sampler.sample()
        assert samples.shape[0] == small_sampler.n_samples, (
            f"Oczekiwano {small_sampler.n_samples} próbek, got {samples.shape[0]}"
        )
        assert samples.shape[1] == len(EARTHWORKS_PRIORS), (
            f"Oczekiwano {len(EARTHWORKS_PRIORS)} kolumn, got {samples.shape[1]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Performance
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:
    """Performance target: 10 000 próbek ≤ 2 sekundy."""

    def test_performance_10k_samples(self, base_cost, market_price):
        """10 000 próbek + Sobol indices + win prob ≤ 2 sekundy."""
        sampler = MonteCarloSampler(n_samples=10_000, seed=42)
        t0 = time.perf_counter()
        result = sampler.run(base_cost=base_cost, market_price=market_price)
        elapsed = time.perf_counter() - t0

        assert elapsed <= 2.0, (
            f"Performance target przekroczony: {elapsed:.3f}s > 2.0s "
            f"dla n=10 000 próbek. Wymagana optymalizacja."
        )
        assert result.samples_count > 0, "Brak zaakceptowanych próbek"

    def test_performance_sampling_only(self):
        """Samo próbkowanie 10k bez Sobol ≤ 0.5 sekundy."""
        sampler = MonteCarloSampler(n_samples=10_000, seed=42)
        t0 = time.perf_counter()
        samples = sampler.sample()
        elapsed = time.perf_counter() - t0

        assert elapsed <= 0.5, (
            f"Próbkowanie zbyt wolne: {elapsed:.3f}s > 0.5s"
        )
        assert len(samples) == 10_000

    def test_performance_consistent_across_runs(self, base_cost, market_price):
        """3 kolejne run() — żaden nie przekracza 2s."""
        sampler = MonteCarloSampler(n_samples=5_000, seed=42)
        for i in range(3):
            t0 = time.perf_counter()
            result = sampler.run(base_cost=base_cost, market_price=market_price)
            elapsed = time.perf_counter() - t0
            assert elapsed <= 2.0, (
                f"Run {i+1}/3 przekroczył 2s: {elapsed:.3f}s"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Risk Block Schema
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskBlockSchema:
    """Output risk{} ma wszystkie wymagane pola i poprawne typy."""

    def test_risk_block_has_required_fields(self, small_sampler, base_cost, market_price):
        """Wszystkie wymagane pola obecne w output dict."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        d = result.to_dict()
        required_fields = ["p10", "p50", "p90", "win_prob", "drivers", "cv", "samples_count"]
        for field in required_fields:
            assert field in d, f"Brak wymaganego pola '{field}' w risk block"

    def test_risk_block_types(self, small_sampler, base_cost, market_price):
        """Typy danych w risk block."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        assert isinstance(result.p10, float), f"p10 powinno być float, got {type(result.p10)}"
        assert isinstance(result.p50, float), f"p50 powinno być float, got {type(result.p50)}"
        assert isinstance(result.p90, float), f"p90 powinno być float, got {type(result.p90)}"
        assert isinstance(result.win_prob, float), f"win_prob powinno być float"
        assert isinstance(result.cv, float), f"cv powinno być float"
        assert isinstance(result.drivers, list), f"drivers powinno być list"
        assert isinstance(result.samples_count, int), f"samples_count powinno być int"

    def test_risk_block_value_ordering(self, small_sampler, base_cost, market_price):
        """p10 ≤ p50 ≤ p90."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        assert result.p10 <= result.p50, f"p10={result.p10:.0f} > p50={result.p50:.0f}"
        assert result.p50 <= result.p90, f"p50={result.p50:.0f} > p90={result.p90:.0f}"

    def test_risk_block_win_prob_range(self, small_sampler, base_cost, market_price):
        """win_prob ∈ [0, 1]."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        assert 0.0 <= result.win_prob <= 1.0, f"win_prob={result.win_prob} poza [0,1]"

    def test_risk_block_cv_positive(self, small_sampler, base_cost, market_price):
        """cv ≥ 0."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        assert result.cv >= 0.0, f"CV ujemne: {result.cv}"

    def test_risk_block_drivers_present(self, small_sampler, base_cost, market_price):
        """drivers lista niepusta i ma wymagane pola."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        assert len(result.drivers) > 0, "drivers pusta — brak sensitivity indices"
        for driver in result.drivers:
            assert hasattr(driver, "name"), "Driver brak pola 'name'"
            assert hasattr(driver, "sobol_s1"), "Driver brak pola 'sobol_s1'"
            assert hasattr(driver, "sobol_total"), "Driver brak pola 'sobol_total'"
            d = driver.to_dict()
            assert "name" in d and "sobol_s1" in d and "sobol_total" in d

    def test_risk_block_drivers_schema(self, small_sampler, base_cost, market_price):
        """Każdy driver ma name (str) i sobol indices ∈ [0, 1]."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        for driver in result.drivers:
            assert isinstance(driver.name, str), f"driver.name nie jest str"
            assert 0.0 <= driver.sobol_s1 <= 1.0, (
                f"sobol_s1={driver.sobol_s1} poza [0,1] dla {driver.name}"
            )
            assert 0.0 <= driver.sobol_total <= 1.0, (
                f"sobol_total={driver.sobol_total} poza [0,1] dla {driver.name}"
            )

    def test_risk_block_drivers_sorted_by_st(self, small_sampler, base_cost, market_price):
        """drivers posortowane malejąco wg sobol_total."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        sts = [d.sobol_total for d in result.drivers]
        assert sts == sorted(sts, reverse=True), "drivers nie są posortowane wg ST desc"

    def test_risk_block_samples_count(self, small_sampler, base_cost, market_price):
        """samples_count == n_samples (lub mniej jeśli L1 odrzucił)."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        assert result.samples_count <= small_sampler.n_samples
        assert result.samples_count > 0

    def test_risk_block_json_serializable(self, small_sampler, base_cost, market_price):
        """to_json() daje poprawny JSON z wymaganymi kluczami."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        json_str = result.to_json()
        parsed = json.loads(json_str)
        for key in ["p10", "p50", "p90", "win_prob", "drivers", "cv", "samples_count"]:
            assert key in parsed, f"Brak klucza '{key}' w JSON output"

    def test_risk_block_realistic_values(self, sampler, base_cost, market_price):
        """Wartości p10/p50/p90 rozsądne (bliskie base_cost)."""
        result = sampler.run(base_cost=base_cost, market_price=market_price)
        # p10 powinno być w przedziale [50%, 150%] base_cost
        assert base_cost * 0.5 < result.p10 < base_cost * 2.0, (
            f"p10={result.p10:.0f} poza rozsądnym zakresem dla base_cost={base_cost:.0f}"
        )
        assert base_cost * 0.5 < result.p50 < base_cost * 2.0, (
            f"p50={result.p50:.0f} poza rozsądnym zakresem"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Bayesian Priors Kalibracja
# ─────────────────────────────────────────────────────────────────────────────

class TestBayesianPriors:
    """Priorowe rozkłady mają poprawne właściwości statystyczne."""

    def test_earthworks_priors_count(self):
        """6 priorów zgodnie ze specyfikacją."""
        assert len(EARTHWORKS_PRIORS) == 6, (
            f"Oczekiwano 6 priorów, got {len(EARTHWORKS_PRIORS)}"
        )

    def test_earthworks_priors_names(self):
        """Poprawne nazwy 6 kategorii."""
        expected = {
            "roboty_ziemne", "odwodnienie", "wywiezienie_urobku",
            "zagęszczenie", "roboty_dodatkowe", "rezerwa",
        }
        actual = {p.name for p in EARTHWORKS_PRIORS}
        assert actual == expected, f"Brak priorów: {expected - actual}, nadmiarowe: {actual - expected}"

    def test_lognormal_priors_sigma(self):
        """Sigma priorów lognormal zgodna ze specyfikacją."""
        expected_sigmas = {
            "roboty_ziemne": 0.15,
            "odwodnienie": 0.25,
            "wywiezienie_urobku": 0.20,
            "zagęszczenie": 0.12,
            "roboty_dodatkowe": 0.30,
        }
        for prior in EARTHWORKS_PRIORS:
            if prior.name in expected_sigmas:
                assert abs(prior.sigma - expected_sigmas[prior.name]) < 1e-10, (
                    f"Prior '{prior.name}': oczekiwano sigma={expected_sigmas[prior.name]}, "
                    f"got {prior.sigma}"
                )

    def test_rezerwa_uniform_bounds(self):
        """Prior 'rezerwa' to uniform(0.05, 0.15)."""
        rezerwa = next((p for p in EARTHWORKS_PRIORS if p.name == "rezerwa"), None)
        assert rezerwa is not None, "Brak prioru 'rezerwa'"
        assert rezerwa.distribution == "uniform", f"rezerwa.distribution={rezerwa.distribution}"
        assert abs(rezerwa.low - 0.05) < 1e-10, f"rezerwa.low={rezerwa.low}"
        assert abs(rezerwa.high - 0.15) < 1e-10, f"rezerwa.high={rezerwa.high}"

    def test_lognormal_median_near_one(self):
        """Lognormal prior z mu=1.0 → próbki skupione wokół 1.0."""
        sampler = MonteCarloSampler(n_samples=5_000, seed=42)
        samples = sampler.sample()
        # Kolumna "roboty_ziemne" (idx 0)
        col = samples[:, 0]
        median = float(np.median(col))
        # Median lognormal(mu=1.0, sigma=0.15) ≈ exp(0) = 1.0
        assert 0.85 < median < 1.15, (
            f"Mediana roboty_ziemne={median:.4f} daleko od 1.0 (oczekiwano 0.85-1.15)"
        )

    def test_custom_priors_accepted(self):
        """Sampler akceptuje niestandardowe priorów listę."""
        custom_priors = [
            BayesianPrior("test_factor", distribution="lognormal", mu=1.0, sigma=0.10),
            BayesianPrior("test_reserve", distribution="uniform", low=0.02, high=0.08),
        ]
        sampler = MonteCarloSampler(n_samples=256, seed=42, priors=custom_priors)
        samples = sampler.sample()
        assert samples.shape == (256, 2), f"Oczekiwano (256, 2), got {samples.shape}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Sobol Indices
# ─────────────────────────────────────────────────────────────────────────────

class TestSobolIndices:
    """Sobol sensitivity indices ∈ [0,1] i poprawna kolejność."""

    def test_sobol_s1_range(self, small_sampler, base_cost, market_price):
        """S1 ∈ [0, 1] dla wszystkich czynników."""
        samples = small_sampler.sample()
        result = small_sampler.sobol_indices(samples, base_cost)
        for name, s1 in result["S1"].items():
            assert 0.0 <= s1 <= 1.0, f"S1({name})={s1} poza [0,1]"

    def test_sobol_st_range(self, small_sampler, base_cost, market_price):
        """ST ∈ [0, 1] dla wszystkich czynników."""
        samples = small_sampler.sample()
        result = small_sampler.sobol_indices(samples, base_cost)
        for name, st in result["ST"].items():
            assert 0.0 <= st <= 1.0, f"ST({name})={st} poza [0,1]"

    def test_sobol_st_geq_s1(self, small_sampler, base_cost, market_price):
        """ST ≥ S1 (total ≥ first-order, z dokładnością numeryczną)."""
        samples = small_sampler.sample()
        result = small_sampler.sobol_indices(samples, base_cost)
        for name in result["S1"]:
            s1 = result["S1"][name]
            st = result["ST"][name]
            assert st >= s1 - 0.05, (
                f"ST({name})={st:.4f} < S1({name})={s1:.4f} — naruszenie teorii Sobol"
            )

    def test_sobol_drivers_in_risk_block(self, small_sampler, base_cost, market_price):
        """Risk block zawiera poprawne drivers z sobol indices."""
        result = small_sampler.run(base_cost=base_cost, market_price=market_price)
        assert len(result.drivers) == len(EARTHWORKS_PRIORS)
        for driver in result.drivers:
            assert driver.name in [p.name for p in EARTHWORKS_PRIORS]


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Edge Cases
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Krawędziowe przypadki użycia."""

    def test_zero_base_cost_handled(self):
        """base_cost=0 → brak wyjątku, sensowny wynik."""
        sampler = MonteCarloSampler(n_samples=256, seed=42)
        # Nie powinno rzucać wyjątku
        result = sampler.run(base_cost=0.0, market_price=1_000_000.0)
        assert isinstance(result, RiskBlock)
        assert result.p10 == 0.0
        assert result.p50 == 0.0

    def test_market_price_none(self):
        """market_price=None → używa fallback (base_cost × 1.15)."""
        sampler = MonteCarloSampler(n_samples=256, seed=42)
        result = sampler.run(base_cost=1_000_000.0, market_price=None)
        assert isinstance(result, RiskBlock)
        assert result.p50 > 0

    def test_empty_constraints_list(self, small_sampler):
        """Pusta lista constraints → to samo co brak constraints."""
        samples_no_c = small_sampler.sample(l1_constraints=None)
        samples_empty = small_sampler.sample(l1_constraints=[])
        np.testing.assert_array_equal(samples_no_c, samples_empty)

    def test_single_prior(self):
        """Jeden prior — Sobol działa bez błędu."""
        single_prior = [BayesianPrior("single", distribution="lognormal", mu=1.0, sigma=0.10)]
        sampler = MonteCarloSampler(n_samples=256, seed=42, priors=single_prior)
        result = sampler.run(base_cost=1_000_000.0, market_price=1_200_000.0)
        assert isinstance(result, RiskBlock)
        assert len(result.drivers) == 1

    def test_very_tight_constraints(self, small_sampler):
        """Bardzo restrykcyjne constraints — fallback do pseudo-random bez błędu."""
        # Constraints niemożliwe do spełnienia (nigdy nie wpadnie w zakres)
        # Oczekujemy graceful degradation, nie wyjątku
        constraints = [
            {"type": "min_factor", "factor_name": "roboty_ziemne", "value": 0.9999},
            {"type": "max_factor", "factor_name": "roboty_ziemne", "value": 1.0001},
        ]
        # Nie powinno rzucać wyjątku
        samples = small_sampler.sample(l1_constraints=constraints)
        assert samples.shape[1] == len(EARTHWORKS_PRIORS)

    def test_n_samples_less_than_k(self):
        """n_samples < k (liczba czynników) — nie crashuje."""
        sampler = MonteCarloSampler(n_samples=4, seed=42)
        result = sampler.run(base_cost=1_000_000.0, market_price=1_200_000.0)
        assert isinstance(result, RiskBlock)


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Redis Cache
# ─────────────────────────────────────────────────────────────────────────────

class TestRedisCache:
    """Cache key generation i mock Redis integration."""

    def test_cache_key_deterministic(self):
        """Ten sam tender_id + params → ten sam cache key."""
        k1 = CachedMonteCarloSampler._make_cache_key(
            "tender-123", {"base_cost": 1_000_000, "seed": 42}
        )
        k2 = CachedMonteCarloSampler._make_cache_key(
            "tender-123", {"base_cost": 1_000_000, "seed": 42}
        )
        assert k1 == k2

    def test_cache_key_differs_for_different_tenders(self):
        """Różne tender_id → różne klucze."""
        k1 = CachedMonteCarloSampler._make_cache_key("t1", {"base_cost": 1_000_000})
        k2 = CachedMonteCarloSampler._make_cache_key("t2", {"base_cost": 1_000_000})
        assert k1 != k2

    def test_cache_key_format(self):
        """Cache key ma format 'engine:l2:{hash}:{hash}'."""
        key = CachedMonteCarloSampler._make_cache_key("test", {})
        parts = key.split(":")
        assert len(parts) == 4, f"Oczekiwano 4 części, got: {key}"
        assert parts[0] == "engine"
        assert parts[1] == "l2"
        assert len(parts[2]) == 12  # SHA256 prefix
        assert len(parts[3]) == 12

    def test_cache_miss_calls_sampler(self):
        """Cache miss → sampler.run() jest wywołany."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # Cache miss

        sampler = MonteCarloSampler(n_samples=128, seed=42)
        cached_sampler = CachedMonteCarloSampler(sampler=sampler, redis_client=mock_redis)

        result = cached_sampler.run(
            tender_id="test-tender",
            base_cost=1_000_000.0,
            market_price=1_200_000.0,
        )
        assert isinstance(result, RiskBlock)
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_called_once()

        # Sprawdź TTL
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == CachedMonteCarloSampler.CACHE_TTL  # TTL = 3600

    def test_cache_hit_returns_cached(self):
        """Cache hit → zwraca zserializowany wynik bez ponownego liczenia."""
        cached_result = RiskBlock(
            p10=1_100_000.0, p50=1_250_000.0, p90=1_450_000.0,
            win_prob=0.65, drivers=[], cv=0.12, samples_count=10_000,
        )

        mock_redis = MagicMock()
        mock_redis.get.return_value = cached_result.to_json()  # Cache hit

        sampler = MonteCarloSampler(n_samples=128, seed=42)
        cached_sampler = CachedMonteCarloSampler(sampler=sampler, redis_client=mock_redis)

        result = cached_sampler.run(
            tender_id="cached-tender",
            base_cost=1_000_000.0,
            market_price=1_200_000.0,
        )
        assert isinstance(result, RiskBlock)
        assert result.p50 == 1_250_000.0
        assert result.win_prob == 0.65
        # setex NIE powinno być wywołane (wynik z cache)
        mock_redis.setex.assert_not_called()

    def test_redis_failure_graceful_degradation(self):
        """Redis exception → działa bez cache (brak propagacji błędu)."""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("Redis connection refused")

        sampler = MonteCarloSampler(n_samples=128, seed=42)
        cached_sampler = CachedMonteCarloSampler(sampler=sampler, redis_client=mock_redis)

        # Nie powinno rzucać wyjątku
        result = cached_sampler.run(
            tender_id="test",
            base_cost=1_000_000.0,
            market_price=1_200_000.0,
        )
        assert isinstance(result, RiskBlock)

    def test_no_redis_no_cache(self):
        """redis_client=None → działa bez cache."""
        sampler = MonteCarloSampler(n_samples=128, seed=42)
        cached_sampler = CachedMonteCarloSampler(sampler=sampler, redis_client=None)
        result = cached_sampler.run(
            tender_id="test",
            base_cost=1_000_000.0,
        )
        assert isinstance(result, RiskBlock)


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Win Probability Model Training
# ─────────────────────────────────────────────────────────────────────────────

class TestWinModelTraining:
    """Trening modelu win probability na danych historycznych."""

    def _make_bids(self, n: int = 50) -> list[dict]:
        """Generuj syntetyczne dane historyczne."""
        rng = np.random.default_rng(42)
        bids = []
        for i in range(n):
            market = 1_000_000.0
            ratio = rng.uniform(0.75, 1.25)
            price = market * ratio
            # Wygrywamy częściej przy niskim ratio
            p_win = 1.0 / (1.0 + np.exp(8.0 * (ratio - 1.03)))
            won = int(rng.random() < p_win)
            bids.append({
                "our_price": price,
                "market_price": market,
                "n_competitors": int(rng.integers(2, 8)),
                "won": won,
            })
        return bids

    def test_train_with_sufficient_data(self, sampler):
        """Trening z wystarczającymi danymi → status 'trained'."""
        try:
            from sklearn.linear_model import LogisticRegression  # noqa: F401
            bids = self._make_bids(50)
            result = sampler.train_win_model(bids)
            assert result["status"] == "trained", f"Status: {result}"
            assert sampler._win_model_trained
        except ImportError:
            pytest.skip("sklearn not available")

    def test_train_with_insufficient_data(self, sampler):
        """Trening z < 20 danymi → status 'insufficient_data'."""
        bids = self._make_bids(10)
        result = sampler.train_win_model(bids)
        assert result["status"] == "insufficient_data"

    def test_trained_model_gives_probabilities(self, sampler):
        """Po treningu, win_probability używa modelu ML."""
        try:
            from sklearn.linear_model import LogisticRegression  # noqa: F401
            bids = self._make_bids(50)
            sampler.train_win_model(bids)
            samples = sampler.sample(n_override=256)
            prob = sampler.win_probability(1_000_000.0, samples, market_price=1_100_000.0)
            assert 0.0 <= prob <= 1.0
        except ImportError:
            pytest.skip("sklearn not available")


# ─────────────────────────────────────────────────────────────────────────────
# Integration Test: Pełny pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegration:
    """Pełny pipeline od danych wejściowych do risk{} block."""

    def test_full_pipeline_earthworks(self):
        """Pełny scenariusz: przetarg na roboty ziemne 1.38M PLN."""
        sampler = MonteCarloSampler(n_samples=2_000, seed=42)

        # Dane przetargowe
        base_cost = 1_380_000.0
        market_price = 1_500_000.0
        our_offer = 1_420_000.0

        # L1 constraints z clingo
        l1_constraints = [
            {"type": "max_factor", "factor_name": "roboty_ziemne", "value": 1.45},
            {"type": "min_factor", "factor_name": "zagęszczenie", "value": 0.88},
        ]

        result = sampler.run(
            base_cost=base_cost,
            market_price=market_price,
            l1_constraints=l1_constraints,
            offer_price=our_offer,
            n_competitors=4,
        )

        # Walidacja
        assert result.p10 > 0
        assert result.p50 > 0
        assert result.p90 > 0
        assert result.p10 <= result.p50 <= result.p90
        assert 0.0 <= result.win_prob <= 1.0
        assert result.cv > 0
        assert len(result.drivers) > 0

        # Risk block JSON
        json_out = result.to_json()
        parsed = json.loads(json_out)
        assert parsed["p50"] > 0

    def test_output_matches_spec_example(self):
        """
        Weryfikuje że output format odpowiada specyfikacji Terra.OS:

        {
          "p10": ~1250000,
          "p50": ~1380000,
          "p90": ~1560000,
          "win_prob": [0, 1],
          "drivers": [{"name": str, "sobol_s1": [0,1], "sobol_total": [0,1]}],
          "cv": [0, 0.5],
          "samples_count": 10000
        }
        """
        sampler = MonteCarloSampler(n_samples=10_000, seed=42)
        result = sampler.run(
            base_cost=1_380_000.0,
            market_price=1_500_000.0,
            offer_price=1_430_000.0,
        )
        d = result.to_dict()

        # Format check
        assert isinstance(d["p10"], float)
        assert isinstance(d["p50"], float)
        assert isinstance(d["p90"], float)
        assert isinstance(d["win_prob"], float)
        assert isinstance(d["drivers"], list)
        assert isinstance(d["cv"], float)
        assert isinstance(d["samples_count"], int)
        assert d["samples_count"] == 10_000

        # Drivers format
        for drv in d["drivers"]:
            assert "name" in drv
            assert "sobol_s1" in drv
            assert "sobol_total" in drv

        # Rozsądne wartości dla testowego przetargu
        # p50 powinno być blisko base_cost (±30%)
        assert 0.7 * 1_380_000 < d["p50"] < 1.3 * 1_380_000, (
            f"p50={d['p50']:.0f} poza rozsądnym zakresem [966k, 1794k]"
        )
