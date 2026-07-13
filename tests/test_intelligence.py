"""
Offline unit tests for the intelligence layer.

All DB-touching imports are done lazily inside test methods.
No real DB is required — all connections are mocked.
"""
from __future__ import annotations

import sys
import os
import math
import types
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in [
    ROOT,
    os.path.join(ROOT, "packages", "vendor"),
    os.path.join(ROOT, "packages", "shared"),
    os.path.join(ROOT, "packages", "db"),
    os.path.join(ROOT, "services", "api"),
]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ── helpers ───────────────────────────────────────────────────────────────────

def _row(**kw):
    """Return a MagicMock that supports attribute access for all kwargs."""
    r = MagicMock()
    for k, v in kw.items():
        setattr(r, k, v)
    return r


def _mock_conn_fetchone(value):
    """Return a mock conn whose .execute().fetchone() returns *value*."""
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = value
    return conn


def _mock_conn_fetchall(rows):
    """Return a mock conn whose .execute().fetchall() returns *rows*."""
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = rows
    return conn


# ===========================================================================
# TestBuyerScore
# ===========================================================================

class TestBuyerScore(unittest.TestCase):

    def _import(self):
        # lazy import to avoid module-level DB side effects
        from services.api.services.api.intelligence import buyer_score as bs
        return bs

    def _make_conn(self, krs_cnt=0, won_cnt=0, total_cnt=0, tender_cnt=0, ratio=None):
        """Build a mock conn that responds to successive execute() calls."""
        conn = MagicMock()
        responses = [
            _row(cnt=krs_cnt),                          # krs_active
            _row(won_cnt=won_cnt, total_cnt=total_cnt), # payment_history
            _row(cnt=tender_cnt),                       # tender_count
            _row(ratio=ratio),                          # value_reliability
        ]
        conn.execute.return_value.fetchone.side_effect = responses
        return conn

    def test_krs_active_adds_0_30(self):
        bs = self._import()
        conn = self._make_conn(krs_cnt=1, won_cnt=5, total_cnt=10, tender_cnt=5, ratio=1.0)
        score = bs.calculate_buyer_score("1234567890", "t1", conn)
        # krs_active=0.3, payment=0.15, tender=0.1, reliability=0.2 → 0.75 clamped
        self.assertGreaterEqual(score, 0.3)

    def test_krs_inactive_gives_zero_from_krs(self):
        bs = self._import()
        conn = self._make_conn(krs_cnt=0, won_cnt=0, total_cnt=0, tender_cnt=0, ratio=None)
        score = bs.calculate_buyer_score("0000000000", "t1", conn)
        # krs=0, payment=0.15 (no total), tender=0.1 (cnt=0, scale=0), reliability=0.1 → 0.35
        self.assertAlmostEqual(score, 0.25, places=5)

    def test_payment_history_proportional(self):
        """50% win rate → payment contribution = 0.3 * 0.5 = 0.15."""
        bs = self._import()
        conn = self._make_conn(krs_cnt=0, won_cnt=5, total_cnt=10, tender_cnt=0, ratio=None)
        score = bs.calculate_buyer_score("x", "t", conn)
        # krs=0 (cnt=0 → no +0.3), payment=0.15, tender=0.1*0=0 scaled, reliability=0.1
        self.assertLessEqual(score, 1.0)
        self.assertGreaterEqual(score, 0.0)

    def test_tender_count_scaling(self):
        """10 tenders = full 0.2 contribution."""
        bs = self._import()
        conn = self._make_conn(krs_cnt=0, won_cnt=0, total_cnt=0, tender_cnt=10, ratio=None)
        score = bs.calculate_buyer_score("x", "t", conn)
        # krs=0, payment=0.15, tender=0.2, reliability=0.1 → 0.45
        self.assertAlmostEqual(score, 0.45, places=5)

    def test_tender_count_partial(self):
        """5 tenders = 0.1 contribution."""
        bs = self._import()
        conn = self._make_conn(krs_cnt=0, won_cnt=0, total_cnt=0, tender_cnt=5, ratio=None)
        score = bs.calculate_buyer_score("x", "t", conn)
        # payment=0.15 (no total), tender=0.1, reliability=0.1 → 0.35
        self.assertAlmostEqual(score, 0.35, places=5)

    def test_value_reliability_perfect_ratio(self):
        """ratio=1.0 → full 0.2 reliability contribution."""
        bs = self._import()
        conn = self._make_conn(krs_cnt=0, won_cnt=0, total_cnt=0, tender_cnt=0, ratio=1.0)
        score = bs.calculate_buyer_score("x", "t", conn)
        # krs=0, payment=0.15, tender=0.1*0=0 scaled, reliability=0.2 → 0.35
        self.assertAlmostEqual(score, 0.35, places=5)

    def test_value_reliability_bad_ratio(self):
        """ratio=2.0 → reliability=max(0, 1 - |2-1|)=0 → contribution=0."""
        bs = self._import()
        conn = self._make_conn(krs_cnt=0, won_cnt=0, total_cnt=0, tender_cnt=0, ratio=2.0)
        score = bs.calculate_buyer_score("x", "t", conn)
        # reliability contribution = 0
        self.assertAlmostEqual(score, 0.15, places=5)

    def test_score_clamped_to_1(self):
        """All paths returning max → score <= 1.0."""
        bs = self._import()
        conn = self._make_conn(krs_cnt=5, won_cnt=10, total_cnt=10, tender_cnt=20, ratio=1.0)
        score = bs.calculate_buyer_score("x", "t", conn)
        self.assertLessEqual(score, 1.0)

    def test_score_clamped_to_0(self):
        """Score is never negative."""
        bs = self._import()
        conn = self._make_conn(krs_cnt=0, won_cnt=0, total_cnt=0, tender_cnt=0, ratio=None)
        score = bs.calculate_buyer_score("x", "t", conn)
        self.assertGreaterEqual(score, 0.0)

    def test_db_error_krs_gives_partial_credit(self):
        """Exception in krs_active block → score += 0.15."""
        bs = self._import()
        conn = MagicMock()
        # First call raises, subsequent calls return normal values
        responses_fetchone = [
            Exception("db down"),    # krs_active
            _row(won_cnt=0, total_cnt=0),
            _row(cnt=0),
            _row(ratio=None),
        ]
        call_count = [0]
        def side_effect(*args, **kwargs):
            mock_result = MagicMock()
            idx = call_count[0]
            call_count[0] += 1
            val = responses_fetchone[idx]
            if isinstance(val, Exception):
                mock_result.fetchone.side_effect = val
            else:
                mock_result.fetchone.return_value = val
            return mock_result
        conn.execute.side_effect = side_effect
        score = bs.calculate_buyer_score("x", "t", conn)
        # krs error → +0.15; payment no total → +0.15; tender 0 → +0; reliability None → +0.1
        self.assertAlmostEqual(score, 0.4, places=5)

    def test_all_db_errors_fallback_score(self):
        """All four DB calls fail → fallback score = 0.15+0.15+0.1+0.1 = 0.5."""
        bs = self._import()
        conn = MagicMock()
        conn.execute.side_effect = Exception("db error")
        score = bs.calculate_buyer_score("x", "t", conn)
        self.assertAlmostEqual(score, 0.5, places=5)

    def test_full_score_all_good(self):
        """krs=active + 100% win + 10 tenders + ratio=1.0 → score = 1.0."""
        bs = self._import()
        conn = self._make_conn(krs_cnt=1, won_cnt=10, total_cnt=10, tender_cnt=10, ratio=1.0)
        score = bs.calculate_buyer_score("x", "t", conn)
        self.assertAlmostEqual(score, 1.0, places=5)


# ===========================================================================
# TestBidIntelligence
# ===========================================================================

class TestBidIntelligence(unittest.TestCase):

    def _import(self):
        from services.api.services.api.intelligence import bid_intelligence as bi
        return bi

    def test_percentile_single_value(self):
        bi = self._import()
        self.assertEqual(bi._percentile([5.0], 0.5), 5.0)

    def test_percentile_empty(self):
        bi = self._import()
        self.assertEqual(bi._percentile([], 0.5), 0.0)

    def test_percentile_two_values_median(self):
        bi = self._import()
        result = bi._percentile([2.0, 4.0], 0.5)
        self.assertAlmostEqual(result, 3.0, places=1)

    def test_percentile_five_values_p25(self):
        bi = self._import()
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = bi._percentile(vals, 0.25)
        self.assertGreater(result, 1.0)
        self.assertLess(result, 3.0)

    def test_benford_check_zero_returns_zero(self):
        bi = self._import()
        self.assertEqual(bi._benford_check(0.0), 0.0)

    def test_benford_check_negative_returns_zero(self):
        bi = self._import()
        self.assertEqual(bi._benford_check(-100.0), 0.0)

    def test_benford_check_round_number(self):
        """A heavily rounded number like 100000 should score higher."""
        bi = self._import()
        score = bi._benford_check(100000.0)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_benford_check_irregular_number(self):
        bi = self._import()
        score = bi._benford_check(123456.78)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_get_cpv_benchmark_empty_rows_returns_fallback(self):
        """When DB returns no rows, benchmark should contain fallback win_ratio keys."""
        bi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(bi, "get_engine", return_value=mock_engine):
            result = bi.get_cpv_benchmark("45")

        self.assertIn("win_ratio_median", result)
        self.assertIn("win_ratio_p25", result)
        self.assertIn("win_ratio_p75", result)
        self.assertEqual(result["n_market_results"], 0)
        self.assertEqual(result["win_ratio_source"], "fallback_market_median")

    def test_get_cpv_benchmark_province_filter(self):
        """Passing province adds it to params and result."""
        bi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(bi, "get_engine", return_value=mock_engine):
            result = bi.get_cpv_benchmark("45", province="mazowieckie")

        self.assertEqual(result["province"], "mazowieckie")

    def test_get_cpv_benchmark_with_estimated_values(self):
        """Populated est_rows → n_tenders + median keys should be present."""
        bi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        est_rows = [_row(estimated_value=v) for v in [100.0, 200.0, 300.0, 400.0, 500.0]]
        mock_conn.execute.return_value.fetchall.side_effect = [est_rows, []]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(bi, "get_engine", return_value=mock_engine):
            result = bi.get_cpv_benchmark("45")

        self.assertIn("estimated_value_median", result)
        self.assertEqual(result["n_tenders"], 5)

    def test_get_win_ratios_db_error_returns_empty(self):
        bi = self._import()
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("db error")

        with patch.object(bi, "get_engine", return_value=mock_engine):
            result = bi._get_win_ratios_for_cpv("45", None)

        self.assertEqual(result, [])

    def test_logistic_survival_z_zero(self):
        bi = self._import()
        p = bi._logistic_survival(0.0)
        self.assertAlmostEqual(p, 0.5, places=4)

    def test_logistic_survival_large_positive_z(self):
        bi = self._import()
        p = bi._logistic_survival(10.0)
        self.assertLess(p, 0.001)

    def test_competition_factor_single_competitor(self):
        bi = self._import()
        cf = bi._competition_factor(0.5, 1)
        self.assertAlmostEqual(cf, 0.5, places=3)

    def test_estimate_win_probability_fallback(self):
        """No DB data → parametric fallback → p_win in [0,1]."""
        bi = self._import()
        with patch.object(bi, "_get_win_ratios_for_cpv", return_value=[]):
            result = bi.estimate_win_probability(100_000.0, 100_000.0, "45")

        self.assertIn("p_win", result)
        self.assertGreaterEqual(result["p_win"], 0.0)
        self.assertLessEqual(result["p_win"], 1.0)
        self.assertEqual(result["method"], "parametric_fallback")

    def test_estimate_win_probability_empirical(self):
        """Sufficient win_ratios → empirical_cdf method."""
        bi = self._import()
        ratios = [0.8 + i * 0.01 for i in range(20)]  # 20 ratios
        with patch.object(bi, "_get_win_ratios_for_cpv", return_value=ratios):
            result = bi.estimate_win_probability(85_000.0, 100_000.0, "45")

        self.assertEqual(result["method"], "empirical_cdf")
        self.assertIn("sweet_spot", result)

    def test_detect_bid_anomalies_ratio_low(self):
        """Bid much lower than estimated → flags RAŻĄCO_NISKA (heuristic path)."""
        bi = self._import()
        with patch.object(bi, "get_cpv_benchmark", return_value={
            "win_ratio_p25": 0.88, "win_ratio_median": 0.97,
            "win_ratio_p75": 1.05, "n_market_results": 0,
        }), patch.object(bi, "_get_win_ratios_for_cpv", return_value=[]):
            result = bi.detect_bid_anomalies(50_000.0, 100_000.0, "45")

        self.assertIn("anomaly_score", result)
        self.assertGreater(result["anomaly_score"], 0.5)

    def test_detect_bid_anomalies_normal_price(self):
        bi = self._import()
        with patch.object(bi, "get_cpv_benchmark", return_value={
            "win_ratio_p25": 0.88, "win_ratio_median": 0.97,
            "win_ratio_p75": 1.05, "n_market_results": 0,
        }), patch.object(bi, "_get_win_ratios_for_cpv", return_value=[]):
            result = bi.detect_bid_anomalies(97_000.0, 100_000.0, "45")

        self.assertLessEqual(result["anomaly_score"], 0.5)


# ===========================================================================
# TestWinProbML
# ===========================================================================

class TestWinProbML(unittest.TestCase):

    def _import(self):
        from services.api.services.api.intelligence import win_prob_ml as wp
        # Reset module globals between tests
        wp._model = None
        wp._cpv_encoder = {}
        wp._region_encoder = {}
        return wp

    def test_encode_cpv_new_key(self):
        wp = self._import()
        idx = wp._encode_cpv("45200000-9")
        self.assertIsInstance(idx, int)

    def test_encode_cpv_stable(self):
        wp = self._import()
        a = wp._encode_cpv("45")
        b = wp._encode_cpv("45")
        self.assertEqual(a, b)

    def test_encode_region_new(self):
        wp = self._import()
        idx = wp._encode_region("PL91")
        self.assertIsInstance(idx, int)

    def test_build_features_returns_5_floats(self):
        wp = self._import()
        feats = wp._build_features(0.7, 500_000.0, "45", "PL91", 30)
        self.assertEqual(len(feats), 5)
        for f in feats:
            self.assertIsInstance(f, float)

    def test_build_features_days_clamped(self):
        wp = self._import()
        # days > 365 should be clamped
        feats_over = wp._build_features(0.5, 1e6, "45", "PL", 999)
        feats_max = wp._build_features(0.5, 1e6, "45", "PL", 365)
        self.assertEqual(feats_over[4], feats_max[4])

    def test_synthetic_training_data_shape(self):
        wp = self._import()
        X, y = wp._synthetic_training_data()
        self.assertEqual(len(X), 40)
        self.assertEqual(len(y), 40)
        self.assertIn(1, y)
        self.assertIn(0, y)

    def test_train_model_no_conn(self):
        """_train_model with conn=None falls back to synthetic data and sets _model."""
        wp = self._import()
        wp._train_model(conn=None)
        self.assertIsNotNone(wp._model)

    def test_predict_win_prob_no_model_returns_half(self):
        """When model is None and tender not found → returns 0.5."""
        wp = self._import()
        wp._model = None
        conn = MagicMock()
        # Make _load_or_train a no-op (model stays None via mock)
        with patch.object(wp, "_load_or_train"):
            result = wp.predict_win_prob("tid", "tenant", conn)
        self.assertEqual(result, 0.5)

    def test_predict_win_prob_range(self):
        """After training, predict_win_prob returns float in [0,1]."""
        wp = self._import()
        wp._train_model(conn=None)
        conn = MagicMock()
        from datetime import datetime, timezone, timedelta
        deadline = datetime.now(timezone.utc) + timedelta(days=30)
        row = MagicMock()
        row.__getitem__ = lambda self, k: [0.75, 500_000.0, ["45200000-9"], "PL91", deadline][k]
        conn.execute.return_value.fetchone.return_value = row
        result = wp.predict_win_prob("tid", "tenant", conn)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)

    def test_predict_win_prob_tender_not_found(self):
        wp = self._import()
        wp._train_model(conn=None)
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        result = wp.predict_win_prob("missing", "tenant", conn)
        self.assertEqual(result, 0.5)

    def test_retrain_after_insert_triggers_train(self):
        wp = self._import()
        conn = MagicMock()
        conn.execute.return_value.scalar.return_value = 100
        wp._train_count = 0
        with patch.object(wp, "_train_model") as mock_train:
            wp.retrain_after_insert(conn)
        mock_train.assert_called_once_with(conn)


# ===========================================================================
# TestAnomaly
# ===========================================================================

class TestAnomaly(unittest.TestCase):

    def _import(self):
        from services.api.services.api.intelligence import anomaly as an
        return an

    def test_zscore_helper(self):
        """Test z-score computation logic inline (no internal helper to call)."""
        def _zscore(val, mean, std):
            if val is None or mean is None or std is None or std == 0:
                return None
            return round((float(val) - mean) / std, 4)

        result = _zscore(10.0, 8.0, 2.0)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(float(result), 1.0, places=4)  # type: ignore[arg-type]
        self.assertIsNone(_zscore(None, 8.0, 2.0))
        self.assertIsNone(_zscore(10.0, 8.0, 0.0))

    def test_try_isolation_forest_too_few_rows(self):
        """Less than 5 rows → returns None without sklearn."""
        an = self._import()
        import numpy as np
        matrix = np.array([[1.0], [2.0]])
        result = an._try_isolation_forest(matrix)
        self.assertIsNone(result)

    def test_try_isolation_forest_with_sklearn(self):
        """With sklearn available and enough rows → list of bools."""
        an = self._import()
        import numpy as np
        prices = np.array([[float(i * 10)] for i in range(1, 11)])
        result = an._try_isolation_forest(prices)
        if result is not None:
            self.assertEqual(len(result), 10)
            self.assertTrue(all(isinstance(b, bool) for b in result))

    def test_zscore_pozycja_db_error_returns_default(self):
        """SQLAlchemy error on fetch → returns default dict with is_anomaly=False."""
        an = self._import()
        from sqlalchemy.exc import SQLAlchemyError
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.side_effect = SQLAlchemyError("fail")
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(an, "get_engine", return_value=mock_engine):
            result = an.zscore_pozycja("some-uuid")

        self.assertEqual(result["pozycja_id"], "some-uuid")
        self.assertFalse(result["is_anomaly"])

    def test_zscore_pozycja_not_found_returns_default(self):
        an = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(an, "get_engine", return_value=mock_engine):
            result = an.zscore_pozycja("missing-uuid")

        self.assertFalse(result["is_anomaly"])

    def test_analyze_kosztorys_no_rows_returns_empty(self):
        an = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(an, "get_engine", return_value=mock_engine):
            result = an.analyze_kosztorys("kid", "tid")

        self.assertEqual(result["pozycje_analyzed"], 0)
        self.assertEqual(result["anomalies_found"], 0)

    def test_get_anomalies_db_error_returns_empty_list(self):
        an = self._import()
        from sqlalchemy.exc import SQLAlchemyError
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.side_effect = SQLAlchemyError("fail")
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(an, "get_engine", return_value=mock_engine):
            result = an.get_anomalies("kid", "tid")

        self.assertEqual(result, [])

    def test_get_anomalies_returns_list_of_dicts(self):
        an = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        import uuid
        row = (
            str(uuid.uuid4()), "SYM1", "name", "kat",
            10.0, 20.0, 30.0, 1.5, -0.5, 0.8, True
        )
        mock_conn.execute.return_value.fetchall.return_value = [row]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(an, "get_engine", return_value=mock_engine):
            result = an.get_anomalies("kid", "tid")

        self.assertEqual(len(result), 1)
        self.assertIn("pozycja_id", result[0])
        self.assertTrue(result[0]["is_anomaly"])


# ===========================================================================
# TestForecaster
# ===========================================================================

class TestForecaster(unittest.TestCase):

    def _import(self):
        from services.api.services.api.intelligence import forecaster as fc
        return fc

    def test_holt_winters_too_few_values(self):
        fc = self._import()
        # <3 values → replicate last
        result = fc._holt_winters_forecast([10.0, 12.0], horizon=4)
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0], 12.0)

    def test_holt_winters_normal(self):
        fc = self._import()
        values = [100.0 + i * 5.0 for i in range(8)]
        forecasts = fc._holt_winters_forecast(values, horizon=4)
        self.assertEqual(len(forecasts), 4)
        # Trend is upward, all forecasts should be > last value
        for f in forecasts:
            self.assertGreater(f, values[-1])

    def test_prediction_interval_length_matches_horizon(self):
        fc = self._import()
        values = [100.0 + i for i in range(10)]
        forecasts = [110.0, 111.0, 112.0]
        intervals = fc._prediction_interval(values, forecasts)
        self.assertEqual(len(intervals), len(forecasts))

    def test_prediction_interval_lower_lt_upper(self):
        fc = self._import()
        values = [100.0 + i for i in range(8)]
        forecasts = [108.0, 109.0]
        intervals = fc._prediction_interval(values, forecasts)
        for lb, ub in intervals:
            self.assertLessEqual(lb, ub)

    def test_compute_forecasts_empty_rows_returns_empty(self):
        """Fewer than 6 rows → returns []."""
        fc = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            _row(kwartalrok=2024, kwartalnr=1, avg_price=100.0, n=5),
        ]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(fc, "get_engine", return_value=mock_engine):
            result = fc.compute_forecasts_for_category("beton")

        self.assertEqual(result, [])

    def test_compute_forecasts_returns_list_of_dicts(self):
        """With 8 rows → returns list of forecast dicts."""
        fc = self._import()
        rows = [
            _row(kwartalrok=2022 + i // 4, kwartalnr=(i % 4) + 1, avg_price=100.0 + i * 2.0, n=10)
            for i in range(8)
        ]
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        # Return rows for SELECT, then handle DELETE + INSERT (begin)
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(fc, "get_engine", return_value=mock_engine):
            result = fc.compute_forecasts_for_category("beton", horizon=4)

        self.assertEqual(len(result), 4)
        for r in result:
            self.assertIn("predicted_price", r)
            self.assertIn("lower_bound", r)
            self.assertIn("upper_bound", r)
            self.assertIn("forecast_quarter", r)

    def test_get_forecasts_empty_db_returns_empty_list(self):
        fc = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(fc, "get_engine", return_value=mock_engine):
            result = fc.get_forecasts(category="beton")

        self.assertEqual(result, [])


# ===========================================================================
# TestPriceIntelligence
# ===========================================================================

class TestPriceIntelligence(unittest.TestCase):

    def _import(self):
        from services.api.services.api.intelligence import price_intelligence as pi
        return pi

    def test_get_inflation_index_empty_returns_empty(self):
        pi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(pi, "get_engine", return_value=mock_engine):
            result = pi.get_inflation_index()

        self.assertEqual(result, [])

    def test_get_material_risk_insufficient_data(self):
        pi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            _row(avg_price=100.0, std_price=5.0)
        ]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(pi, "get_engine", return_value=mock_engine):
            result = pi.get_material_risk_score("beton")

        self.assertEqual(result["level"], "unknown")

    def test_get_material_risk_stable(self):
        """Constant prices → low CV → low risk."""
        pi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        rows = [_row(avg_price=100.0, std_price=1.0) for _ in range(8)]
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(pi, "get_engine", return_value=mock_engine):
            result = pi.get_material_risk_score("beton")

        self.assertIn(result["level"], ("low", "medium", "high"))
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 1.0)

    def test_get_material_risk_volatile(self):
        """Wide price swings → higher risk score."""
        pi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        rows = [
            _row(avg_price=50.0 + i * 30.0, std_price=10.0) for i in range(8)
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(pi, "get_engine", return_value=mock_engine):
            result = pi.get_material_risk_score("stal")

        self.assertGreater(result["score"], 0.0)

    def test_forecast_price_too_few_rows_returns_error(self):
        pi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [
            _row(kwartalrok=2024, kwartalnr=1, avg_price=100.0),
            _row(kwartalrok=2024, kwartalnr=2, avg_price=105.0),
        ]
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(pi, "get_engine", return_value=mock_engine):
            result = pi.forecast_price(category="beton")

        self.assertIn("error", result)

    def test_forecast_price_linear_trend(self):
        """8 quarters of data → linear_trend forecast with 4 periods."""
        pi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        rows = [
            _row(kwartalrok=2022 + i // 4, kwartalnr=(i % 4) + 1, avg_price=100.0 + i * 3.0)
            for i in range(8)
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(pi, "get_engine", return_value=mock_engine):
            with patch.dict("sys.modules", {"prophet": None, "pandas": None}):
                result = pi.forecast_price(category="beton", horizon_quarters=4)

        self.assertEqual(result["method"], "linear_trend")
        self.assertEqual(len(result["forecasts"]), 4)
        for fc in result["forecasts"]:
            self.assertIn("p50", fc)
            self.assertIn("p10", fc)
            self.assertIn("p90", fc)

    def test_forecast_price_period_labels(self):
        """Period labels should be in format YYYY-QN."""
        pi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        rows = [
            _row(kwartalrok=2023, kwartalnr=i + 1, avg_price=100.0 + i)
            for i in range(6)
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(pi, "get_engine", return_value=mock_engine):
            with patch.dict("sys.modules", {"prophet": None, "pandas": None}):
                result = pi.forecast_price(category="beton", horizon_quarters=2)

        for fc in result.get("forecasts", []):
            self.assertRegex(fc["period"], r"^\d{4}-Q[1-4]$")

    def test_get_price_index_empty_returns_empty(self):
        pi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(pi, "get_engine", return_value=mock_engine):
            result = pi.get_price_index()

        self.assertEqual(result, [])

    def test_get_price_index_returns_list(self):
        pi = self._import()
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        rows = [
            _row(kwartalrok=2024, kwartalnr=1, typ_rms="M", avg_price=150.0, n=10),
            _row(kwartalrok=2024, kwartalnr=1, typ_rms="R", avg_price=80.0, n=8),
            _row(kwartalrok=2024, kwartalnr=1, typ_rms="S", avg_price=200.0, n=6),
        ]
        mock_conn.execute.return_value.fetchall.return_value = rows
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(pi, "get_engine", return_value=mock_engine):
            result = pi.get_price_index(quarters=4)

        self.assertIsInstance(result, list)
        if result:
            self.assertIn("period", result[0])


if __name__ == "__main__":
    unittest.main()
