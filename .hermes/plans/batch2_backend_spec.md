# Terra.OS — Batch 2 Backend Implementation Spec
**Backend Architect 🏗️ | Agency Agents**
**Data analizy:** 2026-07-07
**Repo:** `/home/ubuntu/terra-os/services/api/`

---

## 📋 Spis treści
1. [Analiza istniejącego kodu](#1-analiza-istniejącego-kodu)
2. [M5 Engine L2 — Monte Carlo Spec](#2-m5-engine-l2--monte-carlo-spec)
3. [Multi-tenancy RLS Spec](#3-multi-tenancy-rls-spec)
4. [Stripe Billing Spec](#4-stripe-billing-spec)
5. [Security Hardening Checklist](#5-security-hardening-checklist)

---

## 1. Analiza istniejącego kodu

### 1.1 `routers/engine.py` — kluczowe obserwacje

| Aspekt | Stan obecny | Gap / Issue |
|--------|-------------|-------------|
| `run_engine()` | Działa L1 + L2, `n_samples=2000` domyślnie | Target to 10 000 próbek; brak Sobol QMC |
| `run_risk()` | Standalone L2 bez cache | Brak Redis cache — każde wywołanie re-liczy |
| `_load_tender_data()` | Raw SQL `sa.text()` | Brak `set_config` dla RLS tenant isolation |
| `_store_risk_run()` | Persystuje JSONB drivers | `samples` ≠ Sobol sensitivity S1/ST per driver |
| Schematy Pydantic | `RiskSchema`, `DriverSchema` | Brakuje `sobol_indices`, `p10/p50/p90` w `risk{}` |
| Auth | Brak middleware authn/authz w routerze | Każdy endpoint publiczny (brak `Depends(get_current_user)`) |
| Error handling | `HTTPException 404/422` | Brak `500` guard, brak tracing ID |

### 1.2 `routers/rfq.py` — kluczowe obserwacje

| Aspekt | Stan obecny | Issue |
|--------|-------------|-------|
| Approval gate | Poprawny wzorzec CQRS-lite | `decided_by='system'` hardcoded — brak user ID z JWT |
| `_parse_offer_from_email()` | Regex heurystyki | Podatność na ReDoS w `r"(\d[\d\s]*[\d])"` |
| `list_approvals()` | Brak filtrowania tenant | IDOR — Tenant A widzi approval Tenant B |
| `get_rfq()` | Brak auth check `tenant_id == current_tenant` | Data leak cross-tenant |
| Rate limiting | Brak | Bez limitu — endpoint `POST /rfq` podatny na spam |

### 1.3 Modele DB — kluczowe obserwacje

**Architektura tenancy:**
- Tabela `tenant` → `organizations.tenant_id` (bridge w migration `0003_bridge`)
- Wszystkie główne tabele mają `tenant_id UUID NOT NULL REFERENCES tenant(id)`
- **Wyjątki (brak tenant_id):** `ted_tenders`, `gus_indicators`, `entity_verifications`, `bzp_documents` — tabele referencyjne/globalne
- `users` → `org_id` → `organizations.tenant_id` — ścieżka auth do tenant

**Tabele wysokiego ryzyka bez RLS:**
`tender`, `estimate`, `risk_run`, `discrepancy`, `rfq`, `rfq_message`, `approval_request`, `audit_log`, `agent_run`, `axiom`, `document_chunk`

**Brak tabeli billing:**
Kolumna `plan text DEFAULT 'free'` w `organizations` — brak osobnej tabeli subscriptions, brak Stripe customer_id

---

## 2. M5 Engine L2 — Monte Carlo Spec

### 2.1 Architektura komponentów

```
POST /tenders/{id}/engine/run
        │
        ▼
  L1 SymbolicEngine (clingo)
        │ violations[]
        ▼
  L2 MonteCarloEngine
        ├── MonteCarloSampler (Sobol QMC, 10_000 próbek)
        ├── BayesianPriorRegistry (6 kategorii robót)
        ├── L1ConstraintEnforcer (hard reject / soft clip)
        ├── WinProbEstimator (logistic regression)
        └── SobolSensitivityAnalyzer (S1, S2, ST)
        │
        ▼
  Redis Cache (TTL 3600s, key = sha256(tender_id+params))
        │
        ▼
  risk_run table (margin_p10/p50/p90, win_prob_at_price, drivers)
```

### 2.2 Klasa `MonteCarloSampler`

```python
# services/engine/l2_monte_carlo.py
# PSEUDOKOD — nie implementacja

from dataclasses import dataclass, field
from typing import Protocol
import numpy as np
# scipy.stats.qmc dla Sobol
# SALib.analyze.sobol dla Sobol indices

@dataclass
class CostCategory:
    """6 kategorii robót ziemnych z priorami Bayesowskimi."""
    key: str                    # np. "roboty_ziemne", "beton", "stal", "izolacja", "instalacje", "wykonczenie"
    mean_pct: float             # % całkowitego kosztu (prior mean)
    std_pct: float              # odchylenie std (epistemic uncertainty)
    dist: str = "lognormal"     # "lognormal" | "triangular" | "uniform"
    bounds: tuple[float, float] = (0.5, 2.0)  # multiplikator (min, max)

ROBOTY_ZIEMNE_CATEGORIES = [
    CostCategory("roboty_ziemne",  mean_pct=0.12, std_pct=0.04, dist="lognormal",  bounds=(0.6, 1.8)),
    CostCategory("beton_zbrojenie",mean_pct=0.28, std_pct=0.06, dist="lognormal",  bounds=(0.7, 1.5)),
    CostCategory("stal_konstrukcja",mean_pct=0.18,std_pct=0.07, dist="lognormal",  bounds=(0.65, 1.6)),
    CostCategory("izolacja_hydro",  mean_pct=0.08, std_pct=0.03, dist="triangular", bounds=(0.5, 1.7)),
    CostCategory("instalacje",      mean_pct=0.22, std_pct=0.05, dist="lognormal",  bounds=(0.75, 1.4)),
    CostCategory("wykonczenie",     mean_pct=0.12, std_pct=0.04, dist="uniform",    bounds=(0.8,  1.3)),
]
# Walidacja: sum(mean_pct) == 1.0 ✓

@dataclass
class SamplerConfig:
    n_samples: int = 10_000
    seed: int = 42
    scramble: bool = True          # Scrambled Sobol = lepsza uniformność
    n_dims: int = 6                # = len(CATEGORIES)
    skip_first: int = 0            # Sobol skip-ahead

class MonteCarloSampler:
    """
    Generuje 10 000 próbek kosztu używając Sobol Quasi-Monte Carlo.
    Sobol QMC > Random MC — niższa wariancja przy tej samej liczbie próbek.
    Scipy implementacja: scipy.stats.qmc.Sobol
    """

    def __init__(self, config: SamplerConfig, categories: list[CostCategory]):
        self.config = config
        self.categories = categories

    def generate_unit_cube(self) -> np.ndarray:
        """
        Zwraca macierz (n_samples, n_dims) w [0, 1]^n_dims.
        Używa Sobol sequence (scrambled).

        PSEUDOKOD:
            sampler = scipy.stats.qmc.Sobol(d=config.n_dims, scramble=True, seed=config.seed)
            unit_samples = sampler.random(n=config.n_samples)  # shape: (10000, 6)
            return unit_samples
        """
        ...

    def apply_marginals(self, unit_samples: np.ndarray) -> np.ndarray:
        """
        Transformuje [0,1] → właściwe rozkłady per kategoria.
        Używa Inverse CDF (scipy.stats.lognorm.ppf, triangular.ppf, uniform.ppf).

        PSEUDOKOD:
            result = np.zeros_like(unit_samples)
            for i, cat in enumerate(self.categories):
                u = unit_samples[:, i]
                if cat.dist == "lognormal":
                    # parametry z mean/std → mu/sigma log-space
                    sigma = sqrt(log(1 + (std/mean)^2))
                    mu = log(mean) - sigma^2 / 2
                    result[:, i] = scipy.stats.lognorm(s=sigma, scale=exp(mu)).ppf(u)
                elif cat.dist == "triangular":
                    ...
                elif cat.dist == "uniform":
                    a, b = cat.bounds
                    result[:, i] = a + u * (b - a)
            return result  # shape: (10000, 6) — multiplikatory per kategoria
        """
        ...

    def compute_total_costs(
        self,
        multipliers: np.ndarray,
        owner_cost: float,
    ) -> np.ndarray:
        """
        Oblicza total cost per próbka.
        cost_i = owner_cost * sum(cat.mean_pct * multiplier_i_j for j in categories)

        PSEUDOKOD:
            weights = np.array([c.mean_pct for c in self.categories])  # (6,)
            # Hadamard: multipliers * weights → sum po dim=1
            total_costs = owner_cost * (multipliers * weights).sum(axis=1)  # (10000,)
            return total_costs
        """
        ...

    def sample(self, owner_cost: float) -> np.ndarray:
        """Entry point — zwraca (10000,) array kosztów."""
        unit = self.generate_unit_cube()
        mults = self.apply_marginals(unit)
        return self.compute_total_costs(mults, owner_cost)
```

### 2.3 Klasa `BayesianPriorRegistry`

```python
class BayesianPriorRegistry:
    """
    Przechowuje i aktualizuje Bayesian priors per kategoria.
    Priors są aktualizowane po każdym zakończonym kontrakcie (historical_bids).

    Update reguła (conjugate normal-normal):
        prior:      (μ₀, σ₀²) per kategoria
        likelihood: dane z historical_bids.actual_cost / estimate
        posterior:  μ₁ = (μ₀/σ₀² + x̄/σₗ²) / (1/σ₀² + n/σₗ²)

    Storage: calibration_coeff tabela (klucz = category.key)
    """

    def __init__(self, db_engine, tenant_id: str):
        self.db_engine = db_engine
        self.tenant_id = tenant_id

    def load_priors(self) -> dict[str, tuple[float, float]]:
        """
        Ładuje (mean_multiplier, variance) z calibration_coeff.
        Fallback: ROBOTY_ZIEMNE_CATEGORIES defaults.

        PSEUDOKOD:
            rows = SELECT key, coeff, variance FROM calibration_coeff
                   WHERE tenant_id = :tid
            return {row.key: (row.coeff, row.variance) for row in rows}
        """
        ...

    def update_from_historical(self, bid_id: str) -> None:
        """
        Bayesian update po zakończeniu kontraktu.
        Wywołane przez: POST /contracts/{id}/close z actual_cost

        PSEUDOKOD:
            actual_vs_estimated = actual_cost / estimated_cost  # ratio
            category_breakdown = self._estimate_category_split(bid_id)
            for category, actual_ratio in category_breakdown.items():
                prior_mean, prior_var = self.load_priors()[category]
                # Conjugate update
                posterior_mean = bayesian_update(prior_mean, prior_var, actual_ratio)
                UPDATE calibration_coeff SET coeff=posterior_mean WHERE key=category AND tenant_id=:tid
        """
        ...
```

### 2.4 Klasa `L1ConstraintEnforcer`

```python
class L1ConstraintEnforcer:
    """
    Filtruje próbki Monte Carlo naruszające L1 hard axioms.
    
    Strategia:
    1. HARD REJECT — próbki gdzie cost < L1.min_cost lub cost > L1.max_cost
    2. SOFT CLIP — próbki w "gray zone" są rescaled, nie odrzucane
    3. MAX REJECT RATE — jeśli >50% próbek odrzucone → raise EngineWarning
    
    L1 axioms z clingo (kody A001-A010):
    - A001: cost_total > 0
    - A002: cost_total <= 3 * market_price (anty-absurd górny)
    - A003: cost_total >= 0.3 * market_price (anty-dumping dolny)
    - A004: labor_pct in [0.15, 0.60] (KNR constraints)
    - A005: material_pct in [0.20, 0.65]
    - A006: overhead + profit <= 0.35
    """

    def __init__(self, violations: list[Violation], market_price: float):
        self.violations = violations
        self.market_price = market_price
        self._build_constraint_set()

    def _build_constraint_set(self) -> dict:
        """
        Przekształca L1 violations na numeryczne bounds per axiom code.
        Axiom A002: upper_bound = 3 * market_price
        Axiom A003: lower_bound = 0.3 * market_price
        etc.
        """
        ...

    def enforce(self, cost_samples: np.ndarray) -> tuple[np.ndarray, int]:
        """
        Filtruje tablicę kosztów.
        Returns: (filtered_samples, n_rejected)

        PSEUDOKOD:
            lower = constraints.get('lower_bound', 0)
            upper = constraints.get('upper_bound', inf)
            mask = (cost_samples >= lower) & (cost_samples <= upper)
            n_rejected = (~mask).sum()
            if n_rejected / len(cost_samples) > 0.5:
                logger.warning(f"High rejection rate: {n_rejected/len(cost_samples):.1%}")
            return cost_samples[mask], n_rejected
        """
        ...
```

### 2.5 Klasa `WinProbEstimator`

```python
class WinProbEstimator:
    """
    Estymuje prawdopodobieństwo wygrania przetargu jako funkcję price_ratio.
    
    Model: Logistic Regression
        P(win | price_ratio) = σ(β₀ + β₁ × price_ratio + β₂ × n_competitors)
    
    Gdzie:
        price_ratio = our_price / market_price
        Treningowe dane: historical_bids tabela (org_id filtered)
    
    Fallback (brak danych): sigmoid heurystyka
        P(win | ratio) = 1 / (1 + exp(10 * (ratio - 0.95)))
        → ~85% przy ratio=0.85, ~50% przy ratio=0.95, ~5% przy ratio=1.05
    
    Price grid: [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10] × market_price
    """

    def __init__(self, db_engine, tenant_id: str):
        self.db_engine = db_engine
        self.tenant_id = tenant_id
        self._model = None

    def fit_or_load(self) -> None:
        """
        Próbuje załadować model z cache (Redis) lub trenuje od nowa.

        PSEUDOKOD:
            cached = redis.get(f"win_prob_model:{tenant_id}")
            if cached:
                self._model = pickle.loads(cached)
                return
            
            rows = SELECT our_price, winning_price, n_competitors, won
                   FROM historical_bids WHERE org_id IN (
                       SELECT id FROM organizations WHERE tenant_id = :tid
                   )
            if len(rows) >= 20:  # minimum do treningu
                X = [(r.our_price/r.winning_price, r.n_competitors) for r in rows]
                y = [r.won for r in rows]
                self._model = LogisticRegression().fit(X, y)
                redis.setex(f"win_prob_model:{tenant_id}", 86400, pickle.dumps(self._model))
            else:
                self._model = None  # → fallback heurystyka
        """
        ...

    def predict_curve(
        self,
        market_price: float,
        price_grid_ratios: list[float] | None = None,
    ) -> list[dict]:
        """
        Zwraca listę {price_pln, win_prob, margin_p50} dla grid cen.

        PSEUDOKOD:
            if price_grid_ratios is None:
                price_grid_ratios = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10]
            
            results = []
            for ratio in price_grid_ratios:
                price = market_price * ratio
                if self._model:
                    prob = self._model.predict_proba([[ratio, avg_n_competitors]])[0][1]
                else:
                    prob = 1.0 / (1.0 + exp(10.0 * (ratio - 0.95)))  # fallback
                results.append({
                    "price_pln": price,
                    "win_prob": round(prob, 4),
                    "margin_p50": (price - owner_cost_p50) / price,
                })
            return results
        """
        ...
```

### 2.6 Klasa `SobolSensitivityAnalyzer`

```python
class SobolSensitivityAnalyzer:
    """
    Analiza wrażliwości Sobola na totalny koszt.
    Identyfikuje które kategorie kosztów dominują wariancję wyniku.
    
    Indeksy:
        S1  — first-order (główny efekt kategorii i)
        S2  — second-order (interakcje par kategorii)
        ST  — total-order (S1 + wszystkie interakcje z i)
    
    Biblioteka: SALib (pip install SALib)
    Metoda: SALib.analyze.sobol.analyze()
    
    WYMAGANIE: n_samples musi być potęgą 2 dla Sobol.
    Przy n=10000 → zaokrąglić do 8192 (2^13) lub 16384 (2^14).
    Alternatywnie: używać n=10240 = 10×1024
    
    UWAGA: SALib Sobol wymaga specjalnego layoutu próbek: N*(2D+2)
    → MonteCarloSampler musi generować 2 niezależne macierze A i B.
    """

    def __init__(self, categories: list[CostCategory], n_samples: int = 8192):
        self.categories = categories
        self.n_samples = n_samples
        self.problem = {
            "num_vars": len(categories),
            "names": [c.key for c in categories],
            "bounds": [list(c.bounds) for c in categories],
        }

    def generate_salib_samples(self, seed: int = 42) -> np.ndarray:
        """
        Generuje próbki w formacie SALib: shape (N*(2D+2), D).
        Używa SALib.sample.sobol.sample()

        PSEUDOKOD:
            from SALib.sample import sobol as sobol_sampler
            X = sobol_sampler.sample(self.problem, N=self.n_samples, seed=seed)
            return X  # shape: (n*(2*6+2), 6) = (n*14, 6)
        """
        ...

    def analyze(self, Y: np.ndarray) -> list[dict]:
        """
        Oblicza indeksy Sobola dla wektora wyników Y.

        PSEUDOKOD:
            from SALib.analyze import sobol
            Si = sobol.analyze(self.problem, Y, calc_second_order=True, print_to_console=False)
            
            drivers = []
            for i, name in enumerate(self.problem["names"]):
                drivers.append({
                    "factor": name,
                    "S1": round(float(Si["S1"][i]), 4),
                    "S1_conf": round(float(Si["S1_conf"][i]), 4),
                    "ST": round(float(Si["ST"][i]), 4),
                    "ST_conf": round(float(Si["ST_conf"][i]), 4),
                })
            # Sort by ST descending
            return sorted(drivers, key=lambda d: d["ST"], reverse=True)
        """
        ...
```

### 2.7 Struktura `risk{}` block w `EngineResult`

```python
# Rozszerzony RiskSchema (Pydantic v2)
class SobolIndexSchema(BaseModel):
    factor: str
    S1: float
    S1_conf: float
    ST: float
    ST_conf: float

class WinProbSchema(BaseModel):
    price_pln: float
    win_prob: float
    margin_p50: float

class RiskSchema(BaseModel):
    # Percentyle marginu (margin = (price - cost) / price)
    margin_p10: float           # pesymistyczny
    margin_p50: float           # mediana
    margin_p90: float           # optymistyczny
    
    # Cost percentyle
    cost_p10: float             # NOWE: percentyl kosztu
    cost_p50: float
    cost_p90: float
    
    # Win probability curve
    win_prob_at_price: list[WinProbSchema]
    
    # Sobol sensitivity (nazwane "drivers" dla backward compat)
    drivers: list[SobolIndexSchema]
    
    # Metadata
    n_samples_used: int
    n_rejected: int
    rejection_rate: float       # NOWE: n_rejected / (n_samples_used + n_rejected)
    model_type: str             # NOWE: "sobol_qmc" | "random_mc"
    seed: int
    computed_at: str            # ISO timestamp
```

### 2.8 Redis Caching Strategy

```python
# services/engine/l2_cache.py

import hashlib, json, pickle
import redis

REDIS_URL = "redis://localhost:6379/1"  # DB 1 (DB 0 = session cache)
TTL_SECONDS = 3600  # 1 godzina

def make_cache_key(tender_id: str, owner_cost: float, market_price: float,
                   n_samples: int, seed: int) -> str:
    """
    Deterministyczny klucz cache.
    Nie cachujemy jeśli params się zmienią (nowy kosztorys = nowy owner_cost).
    
    PSEUDOKOD:
        payload = json.dumps({
            "tid": tender_id,
            "cost": round(owner_cost, 2),
            "market": round(market_price, 2),
            "n": n_samples,
            "seed": seed,
        }, sort_keys=True)
        return f"l2_risk:{hashlib.sha256(payload.encode()).hexdigest()[:32]}"
    """
    ...

def get_cached_risk(key: str) -> RiskResult | None:
    """
    PSEUDOKOD:
        r = redis.Redis.from_url(REDIS_URL)
        raw = r.get(key)
        if raw:
            return pickle.loads(raw)
        return None
    """
    ...

def set_cached_risk(key: str, result: RiskResult) -> None:
    """
    PSEUDOKOD:
        r = redis.Redis.from_url(REDIS_URL)
        r.setex(key, TTL_SECONDS, pickle.dumps(result))
    """
    ...

# Invalidation: przy nowym kosztorysie (POST /estimate) invalidate wszystkie klucze
# Pattern: SCAN "l2_risk:*{tender_id}*" → DELETE
# Alternatywnie: klucz zawiera hash(owner_cost) → auto-invalidacja przy zmianie kosztu
```

**Cache invalidation flow:**
```
POST /tenders/{id}/estimate  →  invalidate l2_risk keys dla tender_id
POST /tenders/{id}/engine/run  →  check cache → HIT: return cached | MISS: compute + store
POST /tenders/{id}/risk  →  check cache → HIT: return cached | MISS: compute + store
```

### 2.9 Performance Target: ≤2s dla 10,000 próbek

| Operacja | Estymowany czas | Strategia optymalizacji |
|----------|----------------|------------------------|
| Sobol sampling (scipy) | ~50ms | Wbudowana numpy optymalizacja |
| Apply marginals (vectorized) | ~30ms | Wszystko na numpy, zero pętli Python |
| L1 constraint filter (numpy mask) | ~10ms | Boolean mask O(n) |
| Percentile computation (np.percentile) | ~5ms | np.nanpercentile |
| Win prob curve (9 punktów) | ~20ms | Vectorized logistic |
| SALib Sobol analysis | ~400ms | Bottleneck — równoległy z win_prob? |
| Redis get/set | ~5ms | Pipeline |
| **Łącznie** | **~520ms** | **≪ 2s target ✓** |

**Optymalizacje jeśli przekroczy 2s:**
1. Użyj `numba.jit` dla `apply_marginals()` → ~5× speedup
2. SALib `calc_second_order=False` jeśli S2 nie potrzebny → ~2× szybszy
3. `n_samples=8192` zamiast 10000 (nearest power of 2, Sobol wymaga 2^n)
4. Parallel: asyncio + `run_in_executor` dla SALib

### 2.10 Unit Test Cases (spec, nie implementacja)

```python
# tests/engine/test_l2_monte_carlo.py

class TestMonteCarloSampler:
    def test_sobol_generates_correct_shape():
        """sampler.sample(owner_cost=1_000_000) → shape (10000,)"""
        
    def test_sobol_better_uniformity_than_random():
        """
        Sobol discrepancy < Random discrepancy.
        scipy.stats.qmc.discrepancy(sobol_samples) < discrepancy(random_samples)
        """
        
    def test_costs_strictly_positive():
        """all(costs > 0)"""
        
    def test_reproducible_with_same_seed():
        """sample(seed=42) == sample(seed=42) — deterministyczne"""
        
    def test_different_seeds_different_results():
        """sample(seed=42) != sample(seed=99)"""

class TestL1ConstraintEnforcer:
    def test_rejects_below_lower_bound():
        """costs < 0.3 * market_price → odrzucone"""
        
    def test_rejects_above_upper_bound():
        """costs > 3.0 * market_price → odrzucone"""
        
    def test_high_rejection_rate_warning():
        """n_rejected > 50% → logger.warning wywołany"""
        
    def test_empty_violations_no_filtering():
        """violations=[] → wszystkie próbki przechodzą"""

class TestWinProbEstimator:
    def test_fallback_sigmoid_monotonic():
        """P(win|ratio=0.7) > P(win|ratio=1.1) — malejąca z ceną"""
        
    def test_win_prob_bounded_01():
        """all(0 <= p <= 1 for p in win_prob_curve)"""
        
    def test_price_pln_matches_ratio_times_market():
        """result[i]['price_pln'] ≈ market_price * ratios[i]"""
        
    def test_fits_logistic_with_sufficient_history():
        """≥20 historical bids → używa sklearn LogisticRegression, nie fallback"""

class TestSobolSensitivityAnalyzer:
    def test_s1_indices_sum_approx_one():
        """sum(S1) ≈ 1.0 ± 0.2 (additive model)"""
        
    def test_st_gte_s1():
        """all(ST[i] >= S1[i]) — total ≥ first-order zawsze"""
        
    def test_returns_all_six_categories():
        """len(drivers) == 6"""
        
    def test_sorted_by_st_descending():
        """drivers[0]['ST'] >= drivers[1]['ST'] >= ..."""

class TestRedisCaching:
    def test_cache_hit_returns_same_result():
        """Drugi call z tymi samymi params → Redis hit, wynik identyczny"""
        
    def test_cache_miss_on_changed_owner_cost():
        """owner_cost zmieniony → nowy klucz → cache miss"""
        
    def test_ttl_set_to_3600():
        """redis.ttl(key) ≈ 3600s po zapisie"""
        
    def test_cache_key_deterministic():
        """make_cache_key(same_args) == make_cache_key(same_args)"""

class TestPerformance:
    def test_10k_samples_under_2_seconds():
        """
        import time
        start = time.perf_counter()
        run_l2(RiskInput(n_samples=10_000, ...))
        assert time.perf_counter() - start < 2.0
        """
```

---

## 3. Multi-tenancy RLS Spec

### 3.1 Strategia RLS — które tabele wymagają RLS

**Klasy tabel:**

| Klasa | Opis | RLS wymagany |
|-------|------|-------------|
| **Tenant-owned** | Mają `tenant_id`, dane biznesowe | ✅ TAK |
| **Global/reference** | Brak tenant_id (TED, GUS, BZP, entity_verifications) | ❌ NIE (read-only dla wszystkich) |
| **Audit (append-only)** | `audit_log` — trigger blokuje UPDATE/DELETE | ✅ TAK (SELECT policy) |
| **System** | `tenant`, `organizations`, `users` — zarządzane przez admin | ⚠️ PARTIAL |

**Top-10 tabel z RLS (priorytetyzowane wg danych wrażliwości):**

1. `tender` — core business data
2. `estimate` / `estimate_line` — dane finansowe
3. `risk_run` — wyniki analiz
4. `discrepancy` — wyniki audytu
5. `rfq` / `rfq_message` — komunikacja z podwykonawcami
6. `approval_request` — gated actions
7. `audit_log` — logi (read-only per tenant)
8. `document_chunk` — embeddings + content dokumentów
9. `agent_run` — AI agent runs
10. `axiom` — reguły biznesowe per tenant

### 3.2 `CREATE POLICY` SQL dla top-10 tabel

```sql
-- ════════════════════════════════════════════════════════════════════════
-- Migration: 0006_rls.sql
-- Row Level Security dla Terra.OS
-- ════════════════════════════════════════════════════════════════════════

-- KROK 1: Funkcja pomocnicza pobierająca current tenant_id z session config
-- Ustawiana przez FastAPI middleware: SET LOCAL app.current_tenant = 'uuid'

CREATE OR REPLACE FUNCTION app_tenant_id() RETURNS uuid AS $$
    SELECT NULLIF(current_setting('app.current_tenant', true), '')::uuid;
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- KROK 2: Włącz RLS na wszystkich tabelach tenant-owned
ALTER TABLE tender              ENABLE ROW LEVEL SECURITY;
ALTER TABLE tender_document     ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunk      ENABLE ROW LEVEL SECURITY;
ALTER TABLE przedmiar_item      ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis            ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimate            ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimate_line       ENABLE ROW LEVEL SECURITY;
ALTER TABLE discrepancy         ENABLE ROW LEVEL SECURITY;
ALTER TABLE axiom               ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_run            ENABLE ROW LEVEL SECURITY;
ALTER TABLE rfq                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE rfq_message         ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_request    ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_run           ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log           ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_card           ENABLE ROW LEVEL SECURITY;
ALTER TABLE calibration_coeff   ENABLE ROW LEVEL SECURITY;
ALTER TABLE owner_profile       ENABLE ROW LEVEL SECURITY;

-- KROK 3: FORCE RLS dla superuser (bez FORCE — superuser omija RLS)
ALTER TABLE tender              FORCE ROW LEVEL SECURITY;
ALTER TABLE estimate            FORCE ROW LEVEL SECURITY;
ALTER TABLE risk_run            FORCE ROW LEVEL SECURITY;
ALTER TABLE rfq                 FORCE ROW LEVEL SECURITY;
ALTER TABLE approval_request    FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_log           FORCE ROW LEVEL SECURITY;

-- ════════════════════════════════════════════════════════════════════════
-- POLICIES — wzorzec: USING (tenant_id = app_tenant_id())
-- ════════════════════════════════════════════════════════════════════════

-- 1. TENDER
CREATE POLICY tenant_isolation_tender ON tender
    AS PERMISSIVE
    FOR ALL
    TO terraos_app  -- dedykowany DB role (nie superuser)
    USING (tenant_id = app_tenant_id())
    WITH CHECK (tenant_id = app_tenant_id());

-- 2. ESTIMATE
CREATE POLICY tenant_isolation_estimate ON estimate
    AS PERMISSIVE FOR ALL TO terraos_app
    USING (tenant_id = app_tenant_id())
    WITH CHECK (tenant_id = app_tenant_id());

-- 3. ESTIMATE_LINE
CREATE POLICY tenant_isolation_estimate_line ON estimate_line
    AS PERMISSIVE FOR ALL TO terraos_app
    USING (tenant_id = app_tenant_id())
    WITH CHECK (tenant_id = app_tenant_id());

-- 4. RISK_RUN
CREATE POLICY tenant_isolation_risk_run ON risk_run
    AS PERMISSIVE FOR ALL TO terraos_app
    USING (tenant_id = app_tenant_id())
    WITH CHECK (tenant_id = app_tenant_id());

-- 5. DISCREPANCY
CREATE POLICY tenant_isolation_discrepancy ON discrepancy
    AS PERMISSIVE FOR ALL TO terraos_app
    USING (tenant_id = app_tenant_id())
    WITH CHECK (tenant_id = app_tenant_id());

-- 6. RFQ
CREATE POLICY tenant_isolation_rfq ON rfq
    AS PERMISSIVE FOR ALL TO terraos_app
    USING (tenant_id = app_tenant_id())
    WITH CHECK (tenant_id = app_tenant_id());

-- 7. RFQ_MESSAGE
CREATE POLICY tenant_isolation_rfq_message ON rfq_message
    AS PERMISSIVE FOR ALL TO terraos_app
    USING (tenant_id = app_tenant_id())
    WITH CHECK (tenant_id = app_tenant_id());

-- 8. APPROVAL_REQUEST
CREATE POLICY tenant_isolation_approval ON approval_request
    AS PERMISSIVE FOR ALL TO terraos_app
    USING (tenant_id = app_tenant_id())
    WITH CHECK (tenant_id = app_tenant_id());

-- 9. AUDIT_LOG — tylko SELECT (append-only, INSERT przez SECURITY DEFINER function)
CREATE POLICY tenant_isolation_audit_select ON audit_log
    AS PERMISSIVE FOR SELECT TO terraos_app
    USING (tenant_id = app_tenant_id());

CREATE POLICY tenant_isolation_audit_insert ON audit_log
    AS PERMISSIVE FOR INSERT TO terraos_app
    WITH CHECK (tenant_id = app_tenant_id());

-- 10. DOCUMENT_CHUNK
CREATE POLICY tenant_isolation_doc_chunk ON document_chunk
    AS PERMISSIVE FOR ALL TO terraos_app
    USING (tenant_id = app_tenant_id())
    WITH CHECK (tenant_id = app_tenant_id());

-- ════════════════════════════════════════════════════════════════════════
-- ADMIN BYPASS — dla migration scripts, background jobs
-- ════════════════════════════════════════════════════════════════════════
-- Utwórz role terraos_admin z BYPASSRLS
-- Alembic migrations używają terraos_admin
-- App używa terraos_app (poddany RLS)

CREATE ROLE IF NOT EXISTS terraos_app LOGIN PASSWORD '${APP_DB_PASSWORD}';
CREATE ROLE IF NOT EXISTS terraos_admin LOGIN PASSWORD '${ADMIN_DB_PASSWORD}' BYPASSRLS;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO terraos_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO terraos_app;
```

### 3.3 FastAPI Middleware — Tenant Injection

```python
# services/api/middleware/tenant.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import sqlalchemy as sa
from terra_db.session import get_engine

class TenantMiddleware(BaseHTTPMiddleware):
    """
    Dla każdego request:
    1. Ekstrahuje tenant_id z JWT claims
    2. Ustawia PostgreSQL session variable: SET LOCAL app.current_tenant = '{tenant_id}'
    3. RLS policies używają app_tenant_id() → automatyczna izolacja

    WAŻNE: SET LOCAL działa tylko w obrębie transakcji!
    Dlatego każdy request musi używać:
        async with db_session() as session:
            await session.execute("SET LOCAL app.current_tenant = :tid", {"tid": tenant_id})
            # ... business logic w tej samej sesji/transakcji
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Nie wymagaj auth dla health checku i swagger
        skip_paths = {"/health", "/docs", "/openapi.json", "/redoc"}
        if request.url.path in skip_paths:
            return await call_next(request)

        # Ekstrahuj tenant z JWT
        tenant_id = self._extract_tenant_from_jwt(request)
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Missing or invalid token")

        # Przechowaj w request state (dostępne dla endpointów)
        request.state.tenant_id = tenant_id

        return await call_next(request)

    def _extract_tenant_from_jwt(self, request: Request) -> str | None:
        """
        PSEUDOKOD:
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return None
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
                return payload.get("tenant_id")  # lub przez org_id lookup
            except jwt.InvalidTokenError:
                return None
        """
        ...


# Dependency injection dla endpointów
async def get_db_with_tenant(request: Request):
    """
    FastAPI Depends() — zwraca async session z ustawionym tenant_id w RLS.
    
    PSEUDOKOD:
        tenant_id = request.state.tenant_id
        async with AsyncSession(bind=engine) as session:
            async with session.begin():
                await session.execute(
                    sa.text("SELECT set_config('app.current_tenant', :tid, true)"),
                    {"tid": str(tenant_id)}
                )
                yield session
    """
    ...


# Użycie w endpoincie:
# @router.get("/tenders")
# async def list_tenders(db: AsyncSession = Depends(get_db_with_tenant)):
#     result = await db.execute(select(Tender))  # RLS auto-filtruje
#     return result.scalars().all()
```

### 3.4 Tenant Provisioning Flow

```python
# routers/tenants.py (NOWY router)

"""
POST /tenants — tworzy nowy tenant (tylko dla superadmin/platform owner)
Albo: POST /register — self-service onboarding
"""

# Request schema
class TenantCreate(BaseModel):
    company_name: str
    nip: str | None = None
    plan: Literal["starter", "pro", "enterprise"] = "starter"
    admin_email: str
    admin_name: str
    admin_password: str  # min 12 znaków, zwalidowany

# Flow (transakcja atomowa):
# 1. Walidacja: NIP unikalny, email unikalny
# 2. INSERT INTO tenant (id, name, created_at)
# 3. INSERT INTO organizations (id, name, nip, plan, tenant_id, settings)
# 4. hash_password(admin_password)  ← bcrypt/argon2
# 5. INSERT INTO users (id, email, name, password_hash, org_id, role='owner')
# 6. INSERT INTO owner_profile (id, tenant_id, company_name, ...)
# 7. INSERT INTO audit_log (action='tenant.created', ...)
# 8. Wyślij welcome email (celery task)
# 9. Jeśli plan != free → trigger Stripe Customer creation

# Response
class TenantCreated(BaseModel):
    tenant_id: str
    org_id: str
    user_id: str
    access_token: str   # JWT ważny 24h
    refresh_token: str

# SQL (atomowy, jeden BEGIN...COMMIT):
PROVISION_SQL = """
WITH new_tenant AS (
    INSERT INTO tenant (name) VALUES (:company_name)
    RETURNING id
),
new_org AS (
    INSERT INTO organizations (name, nip, plan, tenant_id)
    SELECT :company_name, :nip, :plan, id FROM new_tenant
    RETURNING id, tenant_id
),
new_user AS (
    INSERT INTO users (email, name, password_hash, org_id, role)
    SELECT :email, :admin_name, :pw_hash, new_org.id, 'owner'
    FROM new_org
    RETURNING id
)
SELECT
    (SELECT id FROM new_tenant) AS tenant_id,
    (SELECT id FROM new_org) AS org_id,
    (SELECT id FROM new_user) AS user_id;
"""
```

### 3.5 Performance Impact RLS

**Problem:** RLS dodaje predykat `WHERE tenant_id = app_tenant_id()` do każdego zapytania. To może:
- Uniemożliwić użycie composite index jeśli tenant_id nie jest leading column
- Powodować sequential scans na małych tabelach z złym planner estimate

**Mitigation:**

```sql
-- 1. INDEKSY: tenant_id jako LEADING column we wszystkich composite indexes
-- (już zrobione w 0001_initial.py — DOBRZE!)
CREATE INDEX ix_tender_tenant_status ON tender (tenant_id, status);      -- ✓
CREATE INDEX ix_tender_tenant_deadline ON tender (tenant_id, deadline_at); -- ✓

-- 2. STATISTICS: zwiększ n_distinct dla tenant_id (dużo tenantów = wysoka selektywność)
ALTER TABLE tender ALTER COLUMN tenant_id SET STATISTICS 500;

-- 3. PARTIAL INDEXES dla aktywnych tenantów (opcjonalne)
-- Dla hot tenants z >10k tenderów:
-- CREATE INDEX ix_tender_active_tenant ON tender (tenant_id, status)
--     WHERE status IN ('watching', 'analyzing', 'estimated');

-- 4. Connection pooling: PgBouncer w transaction mode
-- WAŻNE: SET LOCAL działa tylko w transaction mode, nie session mode!
-- W session mode: SET LOCAL reset po zakończeniu transakcji, ale zmienne zostają
-- → ZAWSZE używaj transaction mode PgBouncer + SET LOCAL (nie SET)

-- 5. EXPLAIN ANALYZE monitoring:
-- Oczekiwany plan: Index Scan using ix_tender_tenant_status
-- Red flag: Seq Scan on tender → brakujący index lub złe statistics
```

**Benchmark target:**
- `SELECT * FROM tender WHERE status='watching'` z RLS: ≤5ms (vs ≤3ms bez RLS)
- Overhead: <2ms dla typowych query z tenant index

### 3.6 Testy izolacji Tenant

```python
# tests/rls/test_tenant_isolation.py

class TestTenantIsolation:
    """
    Fixtures:
    - tenant_a, tenant_b — dwa różne tenants
    - db_session_a(tenant_a) — sesja z SET LOCAL app.current_tenant = tenant_a.id
    - db_session_b(tenant_b) — sesja z SET LOCAL app.current_tenant = tenant_b.id
    """

    def test_tender_cross_tenant_invisible():
        """
        1. Utwórz tender dla tenant_a
        2. Query tenders przez db_session_b
        3. Assert: tender NIE jest widoczny
        """

    def test_estimate_cross_tenant_invisible():
        """Analogicznie dla estimate."""

    def test_risk_run_cross_tenant_invisible():
        """Analogicznie dla risk_run."""

    def test_rfq_cross_tenant_invisible():
        """Analogicznie dla rfq i rfq_message."""

    def test_audit_log_cross_tenant_invisible():
        """audit_log — Tenant B nie widzi logów Tenant A."""

    def test_approval_request_cross_tenant_invisible():
        """approval_request — kluczowe dla bezpieczeństwa."""

    def test_no_tenant_set_returns_empty():
        """
        Sesja bez SET LOCAL app.current_tenant → app_tenant_id() = NULL
        → USING (tenant_id = NULL) → FALSE dla każdego wiersza
        → empty result set
        Assert: SELECT FROM tender returns [] gdy brak tenant w session
        """

    def test_insert_wrong_tenant_rejected():
        """
        Próba INSERT do tender z tenant_id = tenant_b.id
        przez sesję tenant_a → rejected przez WITH CHECK policy
        """

    def test_update_cross_tenant_noop():
        """
        UPDATE tender SET status='archived' WHERE id = tender_b.id
        przez sesję tenant_a → 0 rows affected (nie error, ale noop)
        """

    def test_superuser_bypassrls_works():
        """
        Sesja jako terraos_admin (BYPASSRLS) widzi wszystkie tenants.
        Potrzebne dla: migrations, background jobs, support tools.
        """
```

---

## 4. Stripe Billing Spec

### 4.1 Schemat DB — nowe tabele

```sql
-- Migration: 0007_billing.sql

-- Rozszerzenie organizations o Stripe fields
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS grace_period_until TIMESTAMPTZ;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'trialing';
-- subscription_status: trialing | active | past_due | grace_period | cancelled | paused

CREATE UNIQUE INDEX IF NOT EXISTS ix_org_stripe_customer ON organizations (stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

-- Tabela: plan definitions (statyczna, seed data)
CREATE TABLE IF NOT EXISTS billing_plans (
    id          TEXT PRIMARY KEY,  -- 'starter', 'pro', 'enterprise'
    name        TEXT NOT NULL,
    price_pln   NUMERIC(10,2) NOT NULL,
    price_eur   NUMERIC(10,2),
    stripe_price_id TEXT,          -- price_xxx z Stripe Dashboard
    tender_limit INT,              -- NULL = unlimited
    user_limit  INT,
    features    JSONB NOT NULL DEFAULT '[]',
    active      BOOLEAN DEFAULT TRUE
);

INSERT INTO billing_plans (id, name, price_pln, tender_limit, user_limit, features) VALUES
('starter',    'Starter',    299.00,  50,   3,  '["bzp_import","engine_l1","engine_l2"]'),
('pro',        'Pro',        799.00,  500,  10, '["bzp_import","engine_l1","engine_l2","rfq","ted_import","excel_export"]'),
('enterprise', 'Enterprise', 0,       NULL, NULL,'["all_features","dedicated_support","custom_axioms","sso"]');

-- Tabela: usage tracking (per tenant, per miesiąc)
CREATE TABLE IF NOT EXISTS usage_records (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID NOT NULL REFERENCES organizations(id),
    period_start DATE NOT NULL,
    period_end   DATE NOT NULL,
    tender_count INT NOT NULL DEFAULT 0,
    engine_runs  INT NOT NULL DEFAULT 0,
    rfq_count    INT NOT NULL DEFAULT 0,
    api_calls    BIGINT NOT NULL DEFAULT 0,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id, period_start)
);
CREATE INDEX IF NOT EXISTS ix_usage_org_period ON usage_records (org_id, period_start DESC);

-- Tabela: webhook event log (idempotency)
CREATE TABLE IF NOT EXISTS stripe_webhook_events (
    stripe_event_id TEXT PRIMARY KEY,
    event_type      TEXT NOT NULL,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload         JSONB,
    result          TEXT    -- 'ok' | 'error' | 'skipped'
);
```

### 4.2 Produkty i ceny Stripe

```python
# services/billing/stripe_setup.py

"""
JEDNORAZOWY SETUP script — tworzy produkty/ceny w Stripe.
Uruchomić: python -m services.billing.stripe_setup
"""

import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

PRODUCTS = [
    {
        "id_key": "starter",
        "name": "Terra.OS Starter",
        "description": "Do 50 przetargów, 3 użytkowników, Engine L1+L2",
        "price_pln": 29900,  # grosze → 299.00 PLN
        "stripe_product_id_env": "STRIPE_PRODUCT_STARTER",
        "stripe_price_id_env": "STRIPE_PRICE_STARTER",
    },
    {
        "id_key": "pro",
        "name": "Terra.OS Pro",
        "description": "Do 500 przetargów, 10 użytkowników, RFQ, TED, Excel",
        "price_pln": 79900,  # 799.00 PLN
        "stripe_product_id_env": "STRIPE_PRODUCT_PRO",
        "stripe_price_id_env": "STRIPE_PRICE_PRO",
    },
    {
        "id_key": "enterprise",
        "name": "Terra.OS Enterprise",
        "description": "Unlimited, dedykowane wsparcie, custom axioms, SSO",
        "price_pln": None,   # Custom — Stripe quote flow
        "stripe_product_id_env": "STRIPE_PRODUCT_ENTERPRISE",
    },
]

# PSEUDOKOD setup:
# for product in PRODUCTS:
#     stripe_product = stripe.Product.create(
#         name=product["name"],
#         description=product["description"],
#         metadata={"terra_plan": product["id_key"]}
#     )
#     if product["price_pln"]:
#         stripe_price = stripe.Price.create(
#             product=stripe_product.id,
#             unit_amount=product["price_pln"],
#             currency="pln",
#             recurring={"interval": "month"},
#             metadata={"terra_plan": product["id_key"]}
#         )
#         # Zapisz price_id do billing_plans tabeli lub .env
```

### 4.3 Checkout Session Flow

```python
# routers/billing.py

from fastapi import APIRouter, Depends, HTTPException, Request
import stripe

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

@router.post("/checkout")
async def create_checkout_session(
    plan: Literal["starter", "pro"],
    current_user = Depends(get_current_user),
):
    """
    Tworzy Stripe Checkout Session dla upgradu planu.
    
    PSEUDOKOD:
        org = get_org(current_user.org_id)
        
        # Jeśli nowy customer → utwórz w Stripe
        if not org.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=org.name,
                metadata={"org_id": str(org.id), "tenant_id": str(org.tenant_id)}
            )
            UPDATE organizations SET stripe_customer_id = customer.id WHERE id = org.id
        
        price_id = settings.STRIPE_PRICE_IDS[plan]  # z .env
        
        session = stripe.checkout.Session.create(
            customer=org.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/billing/cancel",
            subscription_data={
                "metadata": {
                    "org_id": str(org.id),
                    "tenant_id": str(org.tenant_id),
                    "plan": plan,
                }
            },
            locale="pl",
        )
        
        return {"checkout_url": session.url, "session_id": session.id}
    """
    ...

@router.get("/portal")
async def customer_portal(current_user = Depends(get_current_user)):
    """
    Stripe Customer Portal — self-service upgrade/downgrade/cancel.
    
    PSEUDOKOD:
        org = get_org(current_user.org_id)
        if not org.stripe_customer_id:
            raise HTTPException(404, "No active subscription")
        
        session = stripe.billing_portal.Session.create(
            customer=org.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/settings/billing",
        )
        return {"portal_url": session.url}
    """
    ...
```

### 4.4 Webhook Handlers

```python
# routers/billing_webhooks.py

@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db = Depends(get_db)):
    """
    Obsługuje Stripe webhooks.
    WAŻNE: nie używa Depends(get_current_user) — weryfikacja przez Stripe-Signature.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # 1. Weryfikacja sygnatury (OBOWIĄZKOWE)
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    # 2. Idempotency check
    existing = await db.execute(
        "SELECT stripe_event_id FROM stripe_webhook_events WHERE stripe_event_id = :eid",
        {"eid": event.id}
    )
    if existing.fetchone():
        return {"status": "already_processed"}

    # 3. Route do handlera
    handler = WEBHOOK_HANDLERS.get(event.type)
    if handler:
        result = await handler(event, db)
    else:
        result = "skipped"

    # 4. Zapisz event (idempotency store)
    await db.execute(
        "INSERT INTO stripe_webhook_events (stripe_event_id, event_type, payload, result) "
        "VALUES (:eid, :etype, :payload, :result)",
        {"eid": event.id, "etype": event.type, "payload": event.data, "result": result}
    )

    return {"status": "ok"}


async def handle_checkout_completed(event: stripe.Event, db) -> str:
    """
    checkout.session.completed — subscription aktywowana.
    
    PSEUDOKOD:
        session = event.data.object
        subscription = stripe.Subscription.retrieve(session.subscription)
        org_id = subscription.metadata.get("org_id")
        plan = subscription.metadata.get("plan")
        
        UPDATE organizations SET
            plan = :plan,
            stripe_subscription_id = :sub_id,
            subscription_status = 'active',
            plan_expires_at = to_timestamp(:current_period_end),
            grace_period_until = NULL
        WHERE id = :org_id
        
        INSERT INTO audit_log (tenant_id, actor, action, entity, detail)
        VALUES (org.tenant_id, 'stripe', 'subscription.activated', 'organization',
                '{"plan": plan, "amount_pln": subscription.plan.amount / 100}')
        
        return "ok"
    """
    ...


async def handle_invoice_payment_failed(event: stripe.Event, db) -> str:
    """
    invoice.payment_failed — płatność nieudana → grace period 7 dni.
    
    PSEUDOKOD:
        invoice = event.data.object
        customer_id = invoice.customer
        
        org = SELECT * FROM organizations WHERE stripe_customer_id = :customer_id
        if not org:
            return "skipped"
        
        grace_until = datetime.now(UTC) + timedelta(days=7)
        
        UPDATE organizations SET
            subscription_status = 'grace_period',
            grace_period_until = :grace_until
        WHERE id = :org_id
        
        # Wyślij email do admin użytkownika
        admin_user = SELECT * FROM users WHERE org_id = :org_id AND role = 'owner' LIMIT 1
        send_email(
            to=admin_user.email,
            template="payment_failed",
            data={
                "company_name": org.name,
                "amount_pln": invoice.amount_due / 100,
                "grace_until": grace_until.strftime("%d.%m.%Y"),
                "retry_url": settings.FRONTEND_URL + "/billing",
            }
        )
        
        INSERT INTO audit_log (..., action='subscription.payment_failed', ...)
        
        return "ok"
    """
    ...


async def handle_invoice_payment_succeeded(event: stripe.Event, db) -> str:
    """
    invoice.payment_succeeded — płatność OK, przedłuż subscrypcję.
    
    PSEUDOKOD:
        invoice = event.data.object
        subscription = stripe.Subscription.retrieve(invoice.subscription)
        
        UPDATE organizations SET
            subscription_status = 'active',
            plan_expires_at = to_timestamp(:current_period_end),
            grace_period_until = NULL
        WHERE stripe_customer_id = :customer_id
        
        return "ok"
    """
    ...


async def handle_subscription_deleted(event: stripe.Event, db) -> str:
    """
    customer.subscription.deleted — downgrade do free.
    
    PSEUDOKOD:
        UPDATE organizations SET
            plan = 'free',
            subscription_status = 'cancelled',
            stripe_subscription_id = NULL,
            plan_expires_at = NULL,
            grace_period_until = NULL
        WHERE stripe_customer_id = :customer_id
    """
    ...


WEBHOOK_HANDLERS = {
    "checkout.session.completed":     handle_checkout_completed,
    "invoice.payment_failed":         handle_invoice_payment_failed,
    "invoice.payment_succeeded":      handle_invoice_payment_succeeded,
    "customer.subscription.deleted":  handle_subscription_deleted,
    "customer.subscription.updated":  handle_subscription_updated,  # plan change
}
```

### 4.5 Grace Period 7 dni

```python
# services/billing/grace_period.py

"""
Grace period logic:
- Trigger: invoice.payment_failed → grace_period_until = now() + 7d
- Podczas grace period: user ma PEŁNY dostęp (nie degradowany)
- Po grace period: downgrade do FREE (hard limit)
- Email reminders: dzień 1, dzień 3, dzień 6, dzień 7

Cron job (celery beat lub cron endpoint):
    POST /internal/billing/expire-grace-periods  (co 1h)
    
    PSEUDOKOD:
        expired = SELECT * FROM organizations
                  WHERE subscription_status = 'grace_period'
                    AND grace_period_until < now()
        
        for org in expired:
            UPDATE organizations SET plan='free', subscription_status='cancelled' WHERE id=org.id
            stripe.Subscription.cancel(org.stripe_subscription_id)  # jeśli jeszcze aktywna
            send_email(admin, template="subscription_cancelled_grace_expired")
            INSERT INTO audit_log (action='subscription.grace_expired', ...)
"""

# Cron schedule (celery beat):
# billing_grace_check:
#   task: services.billing.tasks.expire_grace_periods
#   schedule: crontab(minute=0)  # co godzinę
```

### 4.6 Usage Tracking

```python
# services/billing/usage.py

"""
Zliczanie przetargów per tenant per miesiąc.
Increment przy: POST /tenders, POST /bzp/import, itd.
"""

async def increment_tender_count(org_id: str, db) -> None:
    """
    Upsert usage_records dla bieżącego miesiąca.
    Używa ON CONFLICT DO UPDATE — atomowe, bez race condition.
    
    SQL:
        INSERT INTO usage_records (org_id, period_start, period_end, tender_count)
        VALUES (
            :org_id,
            date_trunc('month', now()),
            date_trunc('month', now()) + interval '1 month' - interval '1 day',
            1
        )
        ON CONFLICT (org_id, period_start)
        DO UPDATE SET
            tender_count = usage_records.tender_count + 1,
            updated_at = now();
    """
    ...

async def check_tender_limit(org_id: str, db) -> tuple[bool, int, int]:
    """
    Sprawdza czy tenant przekroczył limit przetargów.
    Returns: (allowed: bool, current_count: int, limit: int)
    
    PSEUDOKOD:
        org = SELECT plan FROM organizations WHERE id = :org_id
        plan = SELECT tender_limit FROM billing_plans WHERE id = org.plan
        
        if plan.tender_limit is None:
            return (True, 0, -1)  # unlimited
        
        usage = SELECT tender_count FROM usage_records
                WHERE org_id = :org_id AND period_start = date_trunc('month', now())
        current = usage.tender_count if usage else 0
        
        return (current < plan.tender_limit, current, plan.tender_limit)
    """
    ...
```

### 4.7 Billing Middleware

```python
# middleware/billing.py

class BillingMiddleware(BaseHTTPMiddleware):
    """
    Sprawdza subscription status per request dla protected endpoints.
    Kolejność middleware: Auth → Tenant → Billing → Handler
    
    Endpoints wymagające aktywnej subskrypcji:
    - POST /tenders (sprawdź limit)
    - POST /tenders/*/engine/run (Pro feature)
    - POST /tenders/*/rfq (Pro feature)
    - GET /export/* (Pro feature)
    
    Endpoints dostępne na Free:
    - GET /tenders (przeglądanie)
    - GET /health
    """

    PLAN_REQUIRED = {
        "POST /api/v1/tenders": "starter",
        "POST /api/v1/tenders/*/engine/run": "starter",
        "POST /api/v1/tenders/*/rfq": "pro",
        "POST /api/v1/export/*": "pro",
        "GET /api/v1/tenders/*/engine": "starter",
    }

    async def dispatch(self, request: Request, call_next):
        tenant_id = getattr(request.state, "tenant_id", None)
        if not tenant_id:
            return await call_next(request)  # auth middleware odrzuci

        required_plan = self._get_required_plan(request.url.path, request.method)
        if not required_plan:
            return await call_next(request)  # endpoint nie wymaga planu

        org = await self._get_org(tenant_id)

        # Grace period = pełny dostęp
        if org.subscription_status == "grace_period":
            if org.grace_period_until > datetime.now(UTC):
                return await call_next(request)  # jeszcze ważny grace period

        # Sprawdź plan
        if not self._plan_allows(org.plan, required_plan):
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "subscription_required",
                    "required_plan": required_plan,
                    "current_plan": org.plan,
                    "upgrade_url": "/api/v1/billing/checkout",
                }
            )

        # Sprawdź limit (tylko dla POST /tenders)
        if request.url.path == "/api/v1/tenders" and request.method == "POST":
            allowed, current, limit = await check_tender_limit(org.id, db)
            if not allowed:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "error": "tender_limit_reached",
                        "current": current,
                        "limit": limit,
                        "upgrade_url": "/api/v1/billing/checkout?plan=pro",
                    }
                )

        return await call_next(request)
```

### 4.8 Customer Portal Flow

```
Użytkownik klika "Zarządzaj subskrypcją"
        │
        ▼
GET /api/v1/billing/portal
        │
        ├── Check: org.stripe_customer_id EXISTS?
        │       NO → redirect do /billing/checkout
        │
        ▼
stripe.billing_portal.Session.create(customer=org.stripe_customer_id)
        │
        ▼
Redirect do Stripe Customer Portal URL (expires 5min)
        │
Użytkownik może:
  ├── Zmienić plan (upgrade/downgrade) → webhook: customer.subscription.updated
  ├── Anulować subskrypcję → webhook: customer.subscription.deleted
  ├── Zaktualizować kartę płatniczą
  └── Pobrać faktury
        │
        ▼
Stripe wysyła webhook → Terra.OS obsługuje + aktualizuje organizations.plan
```

---

## 5. Security Hardening Checklist

### 5.1 OWASP Top 10 — Analiza per Router

| OWASP | Router(y) | Potencjalna luka | Rekomendacja |
|-------|-----------|-----------------|--------------|
| **A01 Broken Access Control** | `rfq.py:list_approvals()` | IDOR: brak filtrowania tenant w `SELECT * FROM approval_request WHERE status=:s` | Dodaj `AND tenant_id = app_tenant_id()` lub użyj RLS |
| **A01 Broken Access Control** | `rfq.py:get_rfq()` | Brak sprawdzenia `rfq.tenant_id == current_tenant` | `WHERE id=:id AND tenant_id=:tid` |
| **A01 Broken Access Control** | `engine.py:get_engine_result()` | Tender ownership nie zweryfikowany przed zwrotem risk_run | Dodaj `Depends(verify_tender_owner)` |
| **A02 Cryptographic Failures** | `0002_auth.py:users` | `password_hash` — nie wiadomo jaki algorytm | Wymuś argon2id (nie MD5/SHA1/bcrypt<12) |
| **A03 Injection** | `rfq.py:_parse_offer_from_email()` | ReDoS: `r"(\d[\d\s]*[\d])"` — catastrophic backtracking na złośliwym input | Użyj `re.fullmatch`, dodaj timeout lub zastąp parsowaniem token-based |
| **A03 Injection** | Wszystkie routery | Raw `sa.text()` z f-string formatting? | Audyt: NIE ma f-string, ale upewnić się przez grep |
| **A04 Insecure Design** | `billing_webhooks.py` | Brak weryfikacji Stripe-Signature → fałszywe eventy | `stripe.Webhook.construct_event()` OBOWIĄZKOWE |
| **A05 Security Misconfiguration** | Middleware kolejność | Billing middleware przed auth → 402 zamiast 401 | Auth → Tenant → Billing → Route |
| **A06 Vulnerable Components** | `requirements.txt` | Dependencje nie pinned do wersji z CVE-free | `pip-audit` w CI/CD |
| **A07 Auth Failures** | Wszystkie routery | Brak `Depends(get_current_user)` na endpointach | Każdy router MUSI mieć auth dependency |
| **A08 Software & Data Integrity** | `approvals_router` | `decided_by='system'` hardcoded — brak user ID | `decided_by=current_user.id` |
| **A09 Security Logging** | `audit_log` | Brak logowania failed auth attempts | Dodaj `INSERT INTO audit_log` przy 401/403 |
| **A10 SSRF** | Brak external HTTP calls w routerach | ✓ OK | Dodaj allowlist jeśli HTTP client dodany |

### 5.2 SQL Injection Audit

**Obecne wzorce w kodzie (z analizy):**

```python
# ✅ BEZPIECZNY — parametryzowane zapytanie
conn.execute(
    sa.text("SELECT id FROM tender WHERE id = :id"),
    {"id": tender_id}
)

# ✅ BEZPIECZNY — SQLAlchemy ORM
session.execute(select(Tender).where(Tender.tenant_id == tenant_id))

# ⚠️ DO SPRAWDZENIA — czy gdziekolwiek jest f-string?
# GREP: git grep -n "sa.text(f\"" services/
# GREP: git grep -n "execute(f\"" services/

# ❌ NIEBEZPIECZNY (przykład anti-pattern do unikania):
# conn.execute(sa.text(f"SELECT * FROM tender WHERE id = '{tender_id}'"))
# → SQL injection jeśli tender_id pochodzi od użytkownika
```

**Audit checklist:**
```bash
# Uruchomić w repo:
git grep -rn "sa\.text(f\"" services/       # f-string w sa.text
git grep -rn "execute(f\"" services/         # f-string w execute
git grep -rn "% tender_id" services/         # % formatting
git grep -rn "format(" services/             # .format() w SQL strings
git grep -rn "sqlalchemy.text" services/     # raw text bez params

# Oczekiwane: 0 trafień dla unsafe patterns
```

**SQLAlchemy safe patterns — whitelist:**
```python
# Pattern 1: sa.text + named params (używane w codebase ✓)
sa.text("SELECT id FROM tender WHERE tenant_id = :tid"), {"tid": tenant_id}

# Pattern 2: ORM select (preferowane)
select(Tender).where(
    Tender.tenant_id == tenant_id,
    Tender.status == status,
)

# Pattern 3: Column-safe dynamic sort
ALLOWED_SORT_COLS = {"created_at", "value_pln", "deadline_at", "status"}
if sort_by not in ALLOWED_SORT_COLS:
    raise HTTPException(400, "Invalid sort column")
stmt = stmt.order_by(text(f"{sort_by} {direction}"))  # direction = "ASC"|"DESC" enum

# Pattern 4: JSONB operators — safe z SQLAlchemy
Tender.raw["key"].astext == value  # SQLAlchemy JSONB accessor
```

### 5.3 JWT Security

**Obecny stan:** `refresh_tokens` tabela istnieje z `token_hash` i `revoked` — dobra podstawa.

```python
# services/auth/jwt.py — spec implementacji

JWT_ALGORITHM = "HS256"         # Zmień na RS256 dla produkcji (asymetryczny)
JWT_SECRET_KEY = settings.JWT_SECRET  # min 256-bit entropy

# Access Token — krótkotrwały
ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)  # 15 min (nie 24h!)

# Refresh Token — długotrwały
REFRESH_TOKEN_EXPIRES = timedelta(days=30)

def create_access_token(user_id: str, tenant_id: str, org_id: str, role: str) -> str:
    """
    Claims:
        sub: user_id
        tenant_id: dla TenantMiddleware
        org_id: dla BillingMiddleware
        role: dla RBAC
        exp: now + 15min
        iat: now
        jti: uuid4 (JWT ID — dla token blacklist jeśli potrzebne)
    
    PSEUDOKOD:
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "org_id": org_id,
            "role": role,
            "exp": datetime.now(UTC) + ACCESS_TOKEN_EXPIRES,
            "iat": datetime.now(UTC),
            "jti": str(uuid4()),
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    """
    ...

def create_refresh_token(user_id: str) -> tuple[str, str]:
    """
    Returns: (plain_token, token_hash)
    - plain_token → wysłany do klienta (httponly cookie lub secure storage)
    - token_hash → zapisany w DB (hashlib.sha256 lub bcrypt)
    
    PSEUDOKOD:
        plain = secrets.token_urlsafe(64)  # 64 bytes = 512 bits entropy
        h = hashlib.sha256(plain.encode()).hexdigest()
        return plain, h
    """
    ...

# Rotation flow:
# 1. POST /auth/refresh z refresh_token (httponly cookie)
# 2. Lookup token_hash w refresh_tokens WHERE revoked=false AND expires_at > now()
# 3. Verify token not expired
# 4. Revoke old token: UPDATE refresh_tokens SET revoked=true WHERE id=:id
# 5. Issue new access_token + new refresh_token (rotation)
# 6. Return {access_token: "...", refresh_token: "..."} + Set-Cookie: refresh_token=...

# Revocation checklist:
# - Logout → revoke all refresh_tokens for user
# - Password change → revoke all refresh_tokens for user
# - Admin ban → revoke all tokens + add user to short-lived blacklist (Redis, TTL=15min)

# Security headers (FastAPI middleware):
# - Strict-Transport-Security: max-age=63072000; includeSubDomains
# - X-Content-Type-Options: nosniff
# - X-Frame-Options: DENY
# - Content-Security-Policy: default-src 'self'
```

### 5.4 Rate Limiting per Endpoint

```python
# middleware/rate_limit.py
# Biblioteka: slowapi (pip install slowapi) — Redis backend

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

# Użyj tenant_id jako klucz (nie IP) — bezpieczniejsze dla multi-tenant
def get_tenant_id(request: Request) -> str:
    return getattr(request.state, "tenant_id", None) or get_remote_address(request)

limiter = Limiter(
    key_func=get_tenant_id,
    storage_uri="redis://localhost:6379/2",  # DB 2 dla rate limit counters
)

# Rate limits per endpoint:
RATE_LIMITS = {
    # Auth endpoints — chronić przed brute force
    "POST /auth/login":           "10/minute",
    "POST /auth/refresh":         "20/minute",
    "POST /auth/register":        "3/hour",

    # Engine — compute-heavy
    "POST /tenders/*/engine/run": "10/hour",    # Drogie obliczenia
    "POST /tenders/*/risk":       "20/hour",

    # RFQ — external sends
    "POST /tenders/*/rfq":        "30/hour",

    # BZP import — external API
    "POST /bzp/import":           "5/minute",

    # Search — może być abused
    "GET /search":                "60/minute",
    "GET /tenders":               "120/minute",

    # Billing — Stripe calls
    "POST /billing/checkout":     "5/hour",
    "GET /billing/portal":        "10/hour",

    # Default dla pozostałych
    "_default":                   "300/minute",
}

# Użycie z dekoratorem:
# @router.post("/tenders/{id}/engine/run")
# @limiter.limit("10/hour")
# async def run_engine(request: Request, ...):
#     ...

# 429 Response body:
# {"error": "rate_limit_exceeded", "retry_after": 3600, "limit": "10/hour"}
```

### 5.5 Input Validation — Pydantic v2 Migration Points

```python
# Obecny stan: mix Pydantic v1 i v2 patterns

# ─── MIGRACJA: Pydantic v2 breaking changes ───────────────────────────────

# v1 → v2: validator → field_validator
# BEFORE (v1):
class TenderCreate(BaseModel):
    value_pln: float
    @validator("value_pln")
    def value_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("value_pln must be positive")
        return v

# AFTER (v2):
from pydantic import field_validator, model_validator
class TenderCreate(BaseModel):
    value_pln: float
    @field_validator("value_pln")
    @classmethod
    def value_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("value_pln must be positive")
        return v

# ─── Dodatkowe walidacje per endpoint ──────────────────────────────────────

class RFQCreate(BaseModel):
    scope_desc: str
    counterparties: list[str] = []

    # DODAJ:
    model_config = ConfigDict(str_strip_whitespace=True, str_max_length=10000)

    @field_validator("scope_desc")
    @classmethod
    def scope_not_empty(cls, v: str) -> str:
        if len(v.strip()) < 10:
            raise ValueError("scope_desc must be at least 10 characters")
        return v

    @field_validator("counterparties")
    @classmethod
    def max_counterparties(cls, v: list[str]) -> list[str]:
        if len(v) > 50:
            raise ValueError("Maximum 50 counterparties per RFQ")
        # Waliduj format emaila
        import re
        email_re = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
        for cp in v:
            if not email_re.match(cp):
                raise ValueError(f"Invalid email: {cp}")
        return v

class RiskInput(BaseModel):
    owner_cost: float
    market_price: float
    n_samples: int = 10_000
    seed: int = 42

    # DODAJ:
    @field_validator("owner_cost", "market_price")
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Must be positive")
        if v > 1_000_000_000:  # 1 miliard PLN max
            raise ValueError("Unreasonably large value")
        return round(v, 2)

    @field_validator("n_samples")
    @classmethod
    def samples_range(cls, v: int) -> int:
        if not (100 <= v <= 100_000):
            raise ValueError("n_samples must be between 100 and 100_000")
        return v

# ─── Globalne zabezpieczenia ──────────────────────────────────────────────

# 1. Ustaw max request size w FastAPI
from fastapi import FastAPI
app = FastAPI()

# 2. Middleware: max body size (10MB)
from starlette.middleware.base import BaseHTTPMiddleware
class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB
    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            raise HTTPException(413, "Request body too large")
        return await call_next(request)

# 3. HTML escape dla text fields (XSS prevention w Markdown output)
import bleach
def sanitize_markdown(text: str) -> str:
    """Usuwa niebezpieczne HTML tagi z user-generated markdown."""
    ALLOWED_TAGS = ['b', 'i', 'u', 'p', 'br', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'pre']
    return bleach.clean(text, tags=ALLOWED_TAGS, strip=True)
```

### 5.6 Bezpieczeństwo plików (upload)

```python
# DOTYCZY: routers/documents_upload.py

# ─── Walidacja plików ─────────────────────────────────────────────────────
ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Weryfikacja MIME przez magic bytes (nie tylko Content-Type)
import magic  # python-magic
def verify_file_type(file_bytes: bytes) -> str:
    """Returns detected MIME type using libmagic."""
    return magic.from_buffer(file_bytes[:2048], mime=True)

# Path traversal prevention
import os, pathlib
def safe_filename(filename: str) -> str:
    """Usuwa path separatory i niebezpieczne znaki."""
    safe = pathlib.Path(filename).name  # basename only
    safe = re.sub(r"[^a-zA-Z0-9._\-]", "_", safe)
    return safe[:255]  # max filename length

# Storage: zapisuj poza document root
# local_path = /var/terraos/uploads/{tenant_id}/{uuid}/{safe_filename}
# Nie: /var/www/html/uploads/...
```

### 5.7 Security Headers Middleware

```python
# middleware/security_headers.py

from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # HSTS — tylko HTTPS
        response.headers["Strict-Transport-Security"] = \
            "max-age=63072000; includeSubDomains; preload"
        
        # Clickjacking prevention
        response.headers["X-Frame-Options"] = "DENY"
        
        # MIME sniffing prevention
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy
        response.headers["Permissions-Policy"] = \
            "geolocation=(), microphone=(), camera=()"
        
        # CSP (dostosuj do frontendu)
        response.headers["Content-Security-Policy"] = \
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
        
        return response
```

### 5.8 Middleware Stack Order (main.py)

```python
# services/api/main.py — kolejność middleware MA ZNACZENIE

from fastapi import FastAPI
app = FastAPI()

# Kolejność (zewnętrzna → wewnętrzna, execute from bottom):
app.add_middleware(SecurityHeadersMiddleware)       # 1. Security headers (outermost)
app.add_middleware(SlowAPIMiddleware)               # 2. Rate limiting
app.add_middleware(MaxBodySizeMiddleware)           # 3. Request size guard
app.add_middleware(CORSMiddleware, ...)             # 4. CORS
app.add_middleware(TenantMiddleware)                # 5. JWT → tenant_id
app.add_middleware(BillingMiddleware)               # 6. Subscription check (innermost)

# Request flow:
# SecurityHeaders → RateLimit → BodySize → CORS → Tenant(JWT) → Billing → Router
```

---

## 6. Priorytetyzacja implementacji

| # | Task | Priorytet | Szacunek (dni) | Bloker? |
|---|------|-----------|----------------|---------|
| 1 | RLS Migration `0006_rls.sql` | 🔴 Krytyczny | 2 | Blokuje prod data isolation |
| 2 | TenantMiddleware + `get_db_with_tenant()` | 🔴 Krytyczny | 1 | Zależność RLS |
| 3 | Stripe Billing DB + webhook handlers | 🟡 Wysoki | 3 | Monetyzacja |
| 4 | Auth Depends na wszystkich routerach | 🔴 Krytyczny | 1 | Security gap |
| 5 | Rate limiting (slowapi) | 🟡 Wysoki | 1 | DDoS protection |
| 6 | L2 Monte Carlo 10k + Redis cache | 🟡 Wysoki | 3 | Performance |
| 7 | Sobol sensitivity analysis (SALib) | 🟢 Normalny | 2 | Analytics |
| 8 | BayesianPriorRegistry | 🟢 Normalny | 2 | ML improvement |
| 9 | Pydantic v2 migration validators | 🟢 Normalny | 2 | Code quality |
| 10 | Security headers middleware | 🟡 Wysoki | 0.5 | Quick win |

---

## Appendix A: Zależności do dodania

```toml
# pyproject.toml / requirements.txt

scipy>=1.13.0          # Sobol QMC: scipy.stats.qmc.Sobol
SALib>=1.5.0           # Sobol sensitivity analysis
scikit-learn>=1.5.0    # LogisticRegression dla WinProbEstimator
stripe>=9.0.0          # Stripe API client
slowapi>=0.1.9         # FastAPI rate limiting
python-magic>=0.4.27   # MIME type verification
bleach>=6.1.0          # HTML sanitization
argon2-cffi>=23.1.0    # Password hashing (argon2id)
```

## Appendix B: Environment Variables

```bash
# .env.example — NOWE zmienne

# JWT
JWT_SECRET=<min-256-bit-random-string>
JWT_ALGORITHM=HS256

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRODUCT_STARTER=prod_xxx
STRIPE_PRODUCT_PRO=prod_xxx

# Redis (już istnieje)
REDIS_URL=redis://localhost:6379

# DB roles (dla RLS)
APP_DB_URL=postgresql+asyncpg://terraos_app:${APP_DB_PASSWORD}@localhost/terraos
ADMIN_DB_URL=postgresql+asyncpg://terraos_admin:${ADMIN_DB_PASSWORD}@localhost/terraos
```

---

*Dokument wygenerowany przez Backend Architect 🏗️ Agency Agents*
*Ostatnia aktualizacja: 2026-07-07*
*Status: SPEC ONLY — żadne pliki w repo nie zostały zmodyfikowane*
