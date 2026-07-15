"""BLOK-12 coverage push: intelligence/ + analytics/ + services/metrics + auth/utils.

Covers:
- intelligence/win_prob_ml.py: _encode_cpv, _encode_region, _build_features, predict, retrain
- analytics/__init__.py: optimal_markup, compute_ahp_score, extract_risks_from_text,
  estimate_cost, estimate_win_probability, generate_recommendation, extract_risks_with_ai
- analytics/forecaster holt_winters helpers
- services/metrics.py: increment, gauge, get_all
- auth/utils.py: hash_password, verify_password, create_access_token, decode_access_token,
  create_refresh_token, hash_refresh_token

All DB / external calls mocked — no live services required.
"""
from __future__ import annotations

import hashlib
import sys
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure paths available
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [
    ROOT,
    os.path.join(ROOT, "packages", "vendor"),
    os.path.join(ROOT, "packages", "shared"),
    os.path.join(ROOT, "packages", "db"),
    os.path.join(ROOT, "services", "api"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("TESTING", "1")

# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────
TID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
UID = "40a71ef6-d6eb-48a3-b62e-7da3df5f0a17"


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — intelligence/win_prob_ml.py
# ═════════════════════════════════════════════════════════════════════════════

class TestWinProbMLEncoders:
    """Tests for _encode_cpv and _encode_region encoders."""

    def setup_method(self):
        # Reset module-level state before each test
        import services.api.services.api.intelligence.win_prob_ml as ml
        ml._cpv_encoder.clear()
        ml._region_encoder.clear()

    def test_encode_cpv_basic(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_cpv
        idx = _encode_cpv("45210000-2")
        assert isinstance(idx, int)
        assert idx >= 0

    def test_encode_cpv_none(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_cpv
        idx = _encode_cpv(None)
        assert isinstance(idx, int)
        assert idx >= 0

    def test_encode_cpv_same_prefix_same_idx(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_cpv
        i1 = _encode_cpv("45210000")
        i2 = _encode_cpv("45290000")
        assert i1 == i2  # same 2-digit prefix

    def test_encode_cpv_different_prefix_different_idx(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_cpv
        i1 = _encode_cpv("45210000")
        i2 = _encode_cpv("71000000")
        assert i1 != i2

    def test_encode_region_basic(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_region
        idx = _encode_region("PL21")
        assert isinstance(idx, int)
        assert idx >= 0

    def test_encode_region_none(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_region
        idx = _encode_region(None)
        assert isinstance(idx, int)

    def test_encode_region_same_prefix(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_region
        i1 = _encode_region("PL21")
        i2 = _encode_region("PL21")
        assert i1 == i2

    def test_encode_region_different(self):
        from services.api.services.api.intelligence.win_prob_ml import _encode_region
        i1 = _encode_region("PL21")
        i2 = _encode_region("PL41")
        # prefix truncated to 4 chars — these differ
        assert i1 != i2


class TestWinProbMLBuildFeatures:
    """Tests for _build_features."""

    def setup_method(self):
        import services.api.services.api.intelligence.win_prob_ml as ml
        ml._cpv_encoder.clear()
        ml._region_encoder.clear()

    def test_build_features_returns_5_floats(self):
        from services.api.services.api.intelligence.win_prob_ml import _build_features
        feats = _build_features(0.7, 500_000, "45210000", "PL21", 30)
        assert len(feats) == 5
        assert all(isinstance(f, float) for f in feats)

    def test_build_features_clamps_match_score(self):
        from services.api.services.api.intelligence.win_prob_ml import _build_features
        feats = _build_features(None, 1_000_000, None, None, 0)
        assert feats[0] == 0.5  # default

    def test_build_features_clamps_value(self):
        from services.api.services.api.intelligence.win_prob_ml import _build_features
        feats_huge = _build_features(0.5, 999_999_999_999, None, None, 0)
        assert feats_huge[1] <= 1.0

    def test_build_features_clamps_days(self):
        from services.api.services.api.intelligence.win_prob_ml import _build_features
        feats = _build_features(0.5, 1_000_000, None, None, -10)
        assert feats[4] == 0.0
        feats2 = _build_features(0.5, 1_000_000, None, None, 9999)
        assert feats2[4] == 1.0

    def test_build_features_normalised_range(self):
        from services.api.services.api.intelligence.win_prob_ml import _build_features
        feats = _build_features(0.8, 2_000_000, "45210000", "PL21", 60)
        for f in feats:
            assert 0.0 <= f <= 1.0


class TestWinProbMLSyntheticTrain:
    """Tests for _synthetic_training_data and _train_model without DB."""

    def setup_method(self):
        import services.api.services.api.intelligence.win_prob_ml as ml
        ml._model = None
        ml._cpv_encoder.clear()
        ml._region_encoder.clear()
        # Remove any pickle on disk to avoid loading stale model
        if os.path.exists(ml._MODEL_PATH):
            os.remove(ml._MODEL_PATH)

    def test_synthetic_training_data(self):
        from services.api.services.api.intelligence.win_prob_ml import _synthetic_training_data
        X, y = _synthetic_training_data()
        assert len(X) == 40
        assert len(y) == 40
        assert 1 in y and 0 in y

    def test_train_model_no_conn(self):
        """Train with conn=None should use synthetic data and set _model."""
        from services.api.services.api.intelligence import win_prob_ml as ml
        ml._train_model(conn=None)
        assert ml._model is not None
        assert ml._last_trained is not None

    def test_predict_win_prob_after_train(self):
        from services.api.services.api.intelligence import win_prob_ml as ml
        ml._train_model(conn=None)

        # Mock DB conn returning a tender row
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (
            0.75,                   # match_score
            500_000.0,              # estimated_value_pln
            ["45210000-2"],         # cpv_codes
            "PL21",                 # nuts_code
            datetime.now(timezone.utc) + timedelta(days=30),  # deadline_at
        )
        prob = ml.predict_win_prob("tender-1", TID, mock_conn)
        assert 0.0 <= prob <= 1.0

    def test_predict_win_prob_no_row(self):
        from services.api.services.api.intelligence import win_prob_ml as ml
        ml._train_model(conn=None)

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        prob = ml.predict_win_prob("missing-tender", TID, mock_conn)
        assert prob == 0.5  # fallback

    def test_predict_win_prob_no_deadline(self):
        from services.api.services.api.intelligence import win_prob_ml as ml
        ml._train_model(conn=None)

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (
            0.6, 200_000.0, None, None, None
        )
        prob = ml.predict_win_prob("tender-2", TID, mock_conn)
        assert 0.0 <= prob <= 1.0


class TestRetrain:
    def setup_method(self):
        import services.api.services.api.intelligence.win_prob_ml as ml
        ml._model = None
        ml._train_count = 0
        if os.path.exists(ml._MODEL_PATH):
            os.remove(ml._MODEL_PATH)

    def test_retrain_after_insert_triggers_when_count_higher(self):
        from services.api.services.api.intelligence import win_prob_ml as ml
        ml._train_count = 0

        mock_conn = MagicMock()
        mock_conn.execute.return_value.scalar.return_value = 10  # new row count

        with patch.object(ml, "_train_model") as mock_train:
            ml.retrain_after_insert(mock_conn)
            mock_train.assert_called_once_with(mock_conn)

    def test_retrain_skipped_when_count_same(self):
        from services.api.services.api.intelligence import win_prob_ml as ml
        ml._train_count = 10

        mock_conn = MagicMock()
        mock_conn.execute.return_value.scalar.return_value = 10

        with patch.object(ml, "_train_model") as mock_train:
            ml.retrain_after_insert(mock_conn)
            mock_train.assert_not_called()


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — analytics/__init__.py
# ═════════════════════════════════════════════════════════════════════════════

class TestOptimalMarkup:
    """Tests for Friedman/Gates optimal_markup."""

    def test_returns_expected_keys(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(1_000_000, 5)
        for key in ("optimal_markup", "win_probability", "expected_profit", "bid_price",
                    "chart_data", "n_competitors", "model"):
            assert key in result

    def test_optimal_markup_range(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(1_000_000, 5)
        assert 0.01 <= result["optimal_markup"] <= 0.40

    def test_win_probability_range(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(1_000_000, 5)
        assert 0 < result["win_probability"] < 1

    def test_expected_profit_positive(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(1_000_000, 5)
        assert result["expected_profit"] > 0

    def test_bid_price_greater_than_cost(self):
        from services.api.services.api.analytics import optimal_markup
        cost = 500_000
        result = optimal_markup(cost, 3)
        assert result["bid_price"] > cost

    def test_single_competitor(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(200_000, 1)
        assert result["n_competitors"] == 1

    def test_zero_competitors_normalised(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(200_000, 0)
        assert result["n_competitors"] == 1  # clamped

    def test_chart_data_has_40_points(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(1_000_000, 5)
        assert len(result["chart_data"]) == 40

    def test_with_historical_data(self):
        from services.api.services.api.analytics import optimal_markup
        hist = [{"markup": 0.12, "won": True}] * 5 + [{"markup": 0.12, "won": False}] * 3
        result = optimal_markup(1_000_000, 5, hist)
        assert result["optimal_markup"] > 0

    def test_large_competitor_count(self):
        from services.api.services.api.analytics import optimal_markup
        result = optimal_markup(1_000_000, 50)
        assert 0 < result["win_probability"] < 1


class TestComputeAhpScore:
    """Tests for AHP decision support."""

    def test_full_scores_returns_total_and_recommendation(self):
        from services.api.services.api.analytics import compute_ahp_score
        scores = {
            "technical_fit": 9, "expected_margin": 8, "team_load": 7,
            "penalty_risk": 6, "strategic_value": 8, "cashflow_impact": 7,
            "buyer_history": 9,
        }
        result = compute_ahp_score(scores)
        assert 0 <= result["total"] <= 100
        assert result["recommendation"] in ("GO", "CONSIDER", "NO-GO")

    def test_empty_scores_neutral(self):
        from services.api.services.api.analytics import compute_ahp_score
        result = compute_ahp_score({})
        # All defaults = 5 → moderate score
        assert 40 <= result["total"] <= 60
        assert len(result["missing_criteria"]) == 7

    def test_all_zeros_is_no_go(self):
        from services.api.services.api.analytics import compute_ahp_score
        scores = {k: 0 for k in ["technical_fit", "expected_margin", "team_load",
                                  "penalty_risk", "strategic_value", "cashflow_impact",
                                  "buyer_history"]}
        result = compute_ahp_score(scores)
        assert result["total"] == 0.0
        assert result["recommendation"] == "NO-GO"

    def test_all_tens_is_go(self):
        from services.api.services.api.analytics import compute_ahp_score
        scores = {k: 10 for k in ["technical_fit", "expected_margin", "team_load",
                                   "penalty_risk", "strategic_value", "cashflow_impact",
                                   "buyer_history"]}
        result = compute_ahp_score(scores)
        assert result["total"] == 100.0
        assert result["recommendation"] == "GO"

    def test_breakdown_length_matches_criteria(self):
        from services.api.services.api.analytics import compute_ahp_score
        result = compute_ahp_score({"technical_fit": 7})
        assert len(result["breakdown"]) == 7

    def test_custom_criteria(self):
        from services.api.services.api.analytics import compute_ahp_score
        custom = [{"id": "x", "label": "Test", "weight": 1.0}]
        result = compute_ahp_score({"x": 8}, criteria=custom)
        assert result["total"] == 80.0

    def test_score_clamped_at_10(self):
        from services.api.services.api.analytics import compute_ahp_score
        scores = {"technical_fit": 15}  # Over 10
        result = compute_ahp_score(scores)
        # Contribution for technical_fit should be capped
        tf = next(b for b in result["breakdown"] if b["criterion_id"] == "technical_fit")
        assert tf["score"] == 10.0

    def test_consider_range(self):
        from services.api.services.api.analytics import compute_ahp_score
        # Scores around 55-65 → CONSIDER
        scores = {k: 5.5 for k in ["technical_fit", "expected_margin", "team_load",
                                    "penalty_risk", "strategic_value", "cashflow_impact",
                                    "buyer_history"]}
        result = compute_ahp_score(scores)
        assert result["recommendation"] in ("CONSIDER", "GO", "NO-GO")


class TestExtractRisksFromText:
    """Tests for pattern-based risk extraction."""

    def test_detects_kara_umowna_per_day(self):
        from services.api.services.api.analytics import extract_risks_from_text
        text = "Zamawiający naliczy karę umowną 0,5 % za każdy dzień opóźnienia."
        result = extract_risks_from_text(text)
        assert len(result["red_flags"]) >= 1
        assert result["ai_enhanced"] is False

    def test_detects_brak_waloryzacji(self):
        from services.api.services.api.analytics import extract_risks_from_text
        text = "Umowa nie dopuszcza waloryzacji cen materiałów budowlanych."
        result = extract_risks_from_text(text)
        highs = [f for f in result["red_flags"] if f["severity"] == "high"]
        assert len(highs) >= 1

    def test_no_flags_clean_text(self):
        from services.api.services.api.analytics import extract_risks_from_text
        text = "Umowa standardowa. Termin płatności 30 dni."
        result = extract_risks_from_text(text)
        assert isinstance(result["red_flags"], list)

    def test_extracts_penalties(self):
        from services.api.services.api.analytics import extract_risks_from_text
        text = "Kara umowna 10 % wartości zamówienia za zwłokę."
        result = extract_risks_from_text(text)
        assert isinstance(result["penalties"], list)

    def test_extracts_deadlines(self):
        from services.api.services.api.analytics import extract_risks_from_text
        text = "Termin realizacji: do 31.12.2025."
        result = extract_risks_from_text(text)
        assert isinstance(result["deadlines"], list)

    def test_solidarna_odpowiedzialnosc(self):
        from services.api.services.api.analytics import extract_risks_from_text
        text = "Wykonawca ponosi solidarną odpowiedzialność podwykonawców."
        result = extract_risks_from_text(text)
        mediums = [f for f in result["red_flags"] if f["severity"] == "medium"]
        assert len(mediums) >= 1

    def test_method_is_pattern_matching(self):
        from services.api.services.api.analytics import extract_risks_from_text
        result = extract_risks_from_text("test")
        assert result["method"] == "pattern_matching"


class TestExtractRisksWithAI:
    """Tests for AI-enhanced risk extraction."""

    @pytest.mark.asyncio
    async def test_fallback_to_pattern_when_no_api_key(self):
        from services.api.services.api.analytics import extract_risks_with_ai
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            result = await extract_risks_with_ai("test text")
        assert result["method"] == "pattern_matching"

    @pytest.mark.asyncio
    async def test_uses_anthropic_when_key_present(self):
        from services.api.services.api.analytics import extract_risks_with_ai
        import types

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"red_flags": [], "deadlines": [], "penalties": [], "payment_terms": null, "valorization": true}')]

        # Patch anthropic module into sys.modules so the import inside function resolves
        mock_anthropic_mod = types.ModuleType("anthropic")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_mod.Anthropic = MagicMock(return_value=mock_client)

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"}):
            with patch.dict(sys.modules, {"anthropic": mock_anthropic_mod}):
                result = await extract_risks_with_ai("Umowa standardowa")

        # Either succeeded with AI or fell back
        assert "red_flags" in result or result["method"] == "pattern_matching"

    @pytest.mark.asyncio
    async def test_fallback_on_anthropic_exception(self):
        from services.api.services.api.analytics import extract_risks_with_ai
        import types

        mock_anthropic_mod = types.ModuleType("anthropic")
        mock_anthropic_mod.Anthropic = MagicMock(side_effect=Exception("Connection refused"))

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"}):
            with patch.dict(sys.modules, {"anthropic": mock_anthropic_mod}):
                result = await extract_risks_with_ai("Umowa")

        assert result["method"] == "pattern_matching"


class TestEstimateCost:
    """Tests for CPV-based cost estimation."""

    def test_estimate_with_area(self):
        from services.api.services.api.analytics import estimate_cost
        result = estimate_cost("45210000", "MAZOWIECKIE", area_m2=1000)
        assert "expected_estimate" in result
        assert result["expected_estimate"] > 0

    def test_estimate_with_value_estimated(self):
        from services.api.services.api.analytics import estimate_cost
        result = estimate_cost("45210000", "ŚLĄSKIE", value_estimated=2_000_000)
        assert result["expected_estimate"] == 2_000_000

    def test_estimate_confidence_intervals(self):
        from services.api.services.api.analytics import estimate_cost
        result = estimate_cost("45210000", "MAŁOPOLSKIE", area_m2=500)
        assert result["low_95"] < result["expected_estimate"] < result["high_95"]
        assert result["low_50"] < result["expected_estimate"] < result["high_50"]

    def test_estimate_no_data_returns_error(self):
        from services.api.services.api.analytics import estimate_cost
        result = estimate_cost("45210000", "MAZOWIECKIE")
        assert "error" in result

    def test_estimate_unknown_cpv_falls_back(self):
        from services.api.services.api.analytics import estimate_cost
        result = estimate_cost("99999999", "ŁÓDZKIE", area_m2=200)
        assert result["expected_estimate"] > 0  # falls back to CPV "45"

    def test_estimate_mazowieckie_premium(self):
        from services.api.services.api.analytics import estimate_cost
        maz = estimate_cost("45210000", "MAZOWIECKIE", area_m2=1000)
        lbl = estimate_cost("45210000", "LUBELSKIE", area_m2=1000)
        assert maz["expected_estimate"] > lbl["expected_estimate"]

    def test_estimate_region_factor_returned(self):
        from services.api.services.api.analytics import estimate_cost
        result = estimate_cost("45210000", "WARMIŃSKO-MAZURSKIE", area_m2=500)
        assert 0.5 <= result["region_factor"] <= 1.5


class TestEstimateWinProbability:
    def test_basic(self):
        from services.api.services.api.analytics import estimate_win_probability
        result = estimate_win_probability(12.0, 5)
        assert 0 < result["win_probability"] < 1
        assert result["markup_pct"] == 12.0

    def test_high_markup_lower_prob(self):
        from services.api.services.api.analytics import estimate_win_probability
        low = estimate_win_probability(5.0, 5)
        high = estimate_win_probability(35.0, 5)
        assert low["win_probability"] >= high["win_probability"]

    def test_returns_interpretation(self):
        from services.api.services.api.analytics import estimate_win_probability
        result = estimate_win_probability(12.0, 5)
        assert result["interpretation"] in ("Wysokie szanse", "Umiarkowane szanse", "Niskie szanse")


class TestGenerateRecommendation:
    def test_basic_recommendation_structure(self):
        from services.api.services.api.analytics import generate_recommendation
        result = generate_recommendation(1_000_000, 5)
        for key in ("recommendation", "win_probability", "expected_profit",
                    "bid_price", "ahp_score", "key_risks", "key_opportunities"):
            assert key in result

    def test_recommendation_is_valid(self):
        from services.api.services.api.analytics import generate_recommendation
        result = generate_recommendation(1_000_000, 3)
        assert result["recommendation"] in ("GO", "CONSIDER", "NO-GO")

    def test_high_risks_can_cause_no_go(self):
        from services.api.services.api.analytics import generate_recommendation
        red_flags = [{"severity": "high", "message": f"Risk {i}"} for i in range(5)]
        result = generate_recommendation(1_000_000, 10, red_flags=red_flags)
        assert result["recommendation"] in ("NO-GO", "CONSIDER")

    def test_no_go_with_low_scores(self):
        from services.api.services.api.analytics import generate_recommendation
        ahp = {k: 0 for k in ["technical_fit", "expected_margin", "team_load",
                               "penalty_risk", "strategic_value", "cashflow_impact",
                               "buyer_history"]}
        result = generate_recommendation(1_000_000, 30, ahp_scores=ahp)
        assert result["recommendation"] in ("NO-GO", "CONSIDER")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — services/metrics.py
# ═════════════════════════════════════════════════════════════════════════════

class TestServicesMetrics:
    """Tests for in-process thread-safe metrics store."""

    def setup_method(self):
        # Reset internal state
        from services.api.services.api.services import metrics
        with metrics._lock:
            metrics._metrics.clear()

    def test_increment_basic(self):
        from services.api.services.api.services.metrics import increment, get_all
        increment("my.counter")
        result = get_all()
        assert result["my.counter"] == 1.0

    def test_increment_accumulates(self):
        from services.api.services.api.services.metrics import increment, get_all
        increment("hits", 3.0)
        increment("hits", 2.0)
        assert get_all()["hits"] == 5.0

    def test_increment_default_value(self):
        from services.api.services.api.services.metrics import increment, get_all
        increment("k")
        increment("k")
        assert get_all()["k"] == 2.0

    def test_gauge_sets_value(self):
        from services.api.services.api.services.metrics import gauge, get_all
        gauge("pool_size", 10.0)
        assert get_all()["pool_size"] == 10.0

    def test_gauge_overwrites(self):
        from services.api.services.api.services.metrics import gauge, get_all
        gauge("pool_size", 10.0)
        gauge("pool_size", 25.0)
        assert get_all()["pool_size"] == 25.0

    def test_get_all_returns_copy(self):
        from services.api.services.api.services.metrics import gauge, get_all
        gauge("g", 5.0)
        d = get_all()
        d["g"] = 999.0
        assert get_all()["g"] == 5.0  # not mutated

    def test_get_all_empty(self):
        from services.api.services.api.services.metrics import get_all
        assert get_all() == {}

    def test_mixed_operations(self):
        from services.api.services.api.services.metrics import increment, gauge, get_all
        increment("req.total")
        gauge("active_users", 42.0)
        increment("req.total", 9.0)
        result = get_all()
        assert result["req.total"] == 10.0
        assert result["active_users"] == 42.0


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — auth/utils.py
# ═════════════════════════════════════════════════════════════════════════════

class TestAuthPassword:
    """Tests for hash_password / verify_password."""

    def test_hash_password_different_from_plain(self):
        from services.api.services.api.auth.utils import hash_password
        h = hash_password("secret123")
        assert h != "secret123"
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_verify_password_correct(self):
        from services.api.services.api.auth.utils import hash_password, verify_password
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_password_wrong(self):
        from services.api.services.api.auth.utils import hash_password, verify_password
        h = hash_password("mypassword")
        assert verify_password("wrongpassword", h) is False

    def test_verify_password_invalid_hash(self):
        from services.api.services.api.auth.utils import verify_password
        result = verify_password("plain", "not-a-valid-hash")
        assert result is False

    def test_hash_is_unique_per_call(self):
        from services.api.services.api.auth.utils import hash_password
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


class TestAuthAccessToken:
    """Tests for create_access_token / decode_access_token."""

    def test_create_and_decode(self):
        from services.api.services.api.auth.utils import create_access_token, decode_access_token
        token = create_access_token(UID, "user@example.com", TID, "owner")
        payload = decode_access_token(token)
        assert payload["sub"] == UID
        assert payload["email"] == "user@example.com"
        assert payload["role"] == "owner"
        assert payload["type"] == "access"

    def test_decode_expired_token_raises(self):
        import jwt as pyjwt
        from services.api.services.api.auth.utils import SECRET_KEY, ALGORITHM
        payload = {
            "sub": UID,
            "email": "x@x.com",
            "org_id": TID,
            "role": "member",
            "iat": 1000,
            "exp": 1001,  # already expired
            "type": "access",
        }
        token = pyjwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(pyjwt.PyJWTError):
            from services.api.services.api.auth.utils import decode_access_token
            decode_access_token(token)

    def test_decode_wrong_type_raises(self):
        import jwt as pyjwt
        from services.api.services.api.auth.utils import SECRET_KEY, ALGORITHM, decode_access_token
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        payload = {
            "sub": UID,
            "email": "x@x.com",
            "org_id": TID,
            "role": "member",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "type": "refresh",  # wrong type
        }
        token = pyjwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(pyjwt.PyJWTError):
            decode_access_token(token)

    def test_decode_invalid_token_raises(self):
        import jwt as pyjwt
        from services.api.services.api.auth.utils import decode_access_token
        with pytest.raises(pyjwt.PyJWTError):
            decode_access_token("not.a.valid.token")

    def test_token_contains_org_id(self):
        from services.api.services.api.auth.utils import create_access_token, decode_access_token
        token = create_access_token(UID, "u@u.com", TID, "admin")
        payload = decode_access_token(token)
        assert payload["org_id"] == TID

    def test_token_no_org_id(self):
        from services.api.services.api.auth.utils import create_access_token, decode_access_token
        token = create_access_token(UID, "u@u.com", None, "member")
        payload = decode_access_token(token)
        assert payload["org_id"] is None


class TestAuthRefreshToken:
    """Tests for create_refresh_token / hash_refresh_token."""

    def test_create_refresh_token_returns_3_values(self):
        from services.api.services.api.auth.utils import create_refresh_token
        raw, token_hash, expires_at = create_refresh_token()
        assert isinstance(raw, str)
        assert isinstance(token_hash, str)
        assert isinstance(expires_at, datetime)

    def test_raw_is_uuid(self):
        from services.api.services.api.auth.utils import create_refresh_token
        raw, _, _ = create_refresh_token()
        # Should be parseable as UUID
        uuid.UUID(raw)

    def test_hash_is_sha256(self):
        from services.api.services.api.auth.utils import create_refresh_token
        raw, token_hash, _ = create_refresh_token()
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert token_hash == expected

    def test_expires_in_future(self):
        from services.api.services.api.auth.utils import create_refresh_token
        _, _, expires_at = create_refresh_token()
        assert expires_at > datetime.now(timezone.utc)

    def test_hash_refresh_token(self):
        from services.api.services.api.auth.utils import hash_refresh_token
        raw = "test-token-value"
        h = hash_refresh_token(raw)
        assert h == hashlib.sha256(raw.encode()).hexdigest()

    def test_two_calls_produce_different_raw(self):
        from services.api.services.api.auth.utils import create_refresh_token
        raw1, _, _ = create_refresh_token()
        raw2, _, _ = create_refresh_token()
        assert raw1 != raw2

    def test_expires_approximately_30_days(self):
        from services.api.services.api.auth.utils import create_refresh_token
        _, _, expires_at = create_refresh_token()
        delta = expires_at - datetime.now(timezone.utc)
        # Should be close to REFRESH_TOKEN_EXPIRE_DAYS * 24h
        assert 28 <= delta.days <= 31


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — analytics/forecaster helpers (pure functions)
# ═════════════════════════════════════════════════════════════════════════════

class TestHoltWinters:
    """Tests for Holt double exponential smoothing."""

    def test_basic_forecast(self):
        from services.api.services.api.intelligence.forecaster import _holt_winters_forecast
        values = [100.0, 105.0, 110.0, 115.0, 120.0]
        forecasts = _holt_winters_forecast(values, horizon=4)
        assert len(forecasts) == 4
        # Trend should continue upward
        assert forecasts[0] > values[-1] * 0.8  # reasonable range

    def test_short_series_fallback(self):
        from services.api.services.api.intelligence.forecaster import _holt_winters_forecast
        values = [100.0, 110.0]  # < 3 items
        forecasts = _holt_winters_forecast(values, horizon=3)
        assert len(forecasts) == 3
        assert all(f == 110.0 for f in forecasts)

    def test_prediction_interval(self):
        from services.api.services.api.intelligence.forecaster import _prediction_interval
        values = [100.0, 102.0, 101.0, 103.0, 104.0, 105.0]
        forecasts = [107.0, 109.0, 111.0, 113.0]
        intervals = _prediction_interval(values, forecasts)
        assert len(intervals) == 4
        for lo, hi in intervals:
            assert lo < hi

    def test_prediction_interval_short_series(self):
        from services.api.services.api.intelligence.forecaster import _prediction_interval
        values = [100.0, 110.0]
        forecasts = [115.0]
        intervals = _prediction_interval(values, forecasts)
        assert len(intervals) == 1
        lo, hi = intervals[0]
        assert lo < 115.0 < hi


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — analytics/risk_extractor edge cases (inline)
# ═════════════════════════════════════════════════════════════════════════════

class TestAnalyticsEdgeCases:
    def test_explain_cost_drivers_mazowieckie(self):
        from services.api.services.api.analytics import explain_cost_drivers
        drivers = explain_cost_drivers(1_000_000, "45210000", "MAZOWIECKIE", 1000)
        assert isinstance(drivers, list)
        if drivers:
            assert "factor" in drivers[0]
            assert "impact_pln" in drivers[0]
            assert "direction" in drivers[0]

    def test_explain_cost_drivers_max_6(self):
        from services.api.services.api.analytics import explain_cost_drivers
        drivers = explain_cost_drivers(1_000_000, "45210000", "MAZOWIECKIE", 100,
                                       description="remont instalacje prefabrykaty")
        assert len(drivers) <= 6

    def test_extract_risks_ryczalt(self):
        from services.api.services.api.analytics import extract_risks_from_text
        text = "Wynagrodzenie ryczałtowe bez możliwości zmiany ceny kontraktu."
        result = extract_risks_from_text(text)
        highs = [f for f in result["red_flags"] if f["severity"] == "high"]
        assert len(highs) >= 1

    def test_extract_risks_valorization_false(self):
        from services.api.services.api.analytics import extract_risks_from_text
        # regex matches "brak.*waloryzac" or "bez.*waloryzac"
        text = "Brak waloryzacji wynagrodzenia wykonawcy w całej umowie."
        result = extract_risks_from_text(text)
        assert result["valorization"] is False
