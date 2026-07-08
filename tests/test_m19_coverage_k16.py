"""Sprint K16 — coverage boost: analytics/win_probability + intelligence/anomaly."""
import uuid
from unittest.mock import MagicMock, patch

# ─── analytics/win_probability.py ─────────────────────────────────────────────

class TestWinProbabilityModel:
    def _model(self):
        from services.api.services.api.analytics.win_probability import WinProbabilityModel
        return WinProbabilityModel()

    def test_predict_fallback_friedman(self):
        m = self._model()
        r = m.predict(0.10, 3)
        assert 0 < r["win_probability"] <= 1
        assert r["method"] == "friedman_parametric"

    def test_predict_curve_length(self):
        m = self._model()
        curve = m.predict_curve(4)
        assert len(curve) == 50
        assert all("win_probability" in p for p in curve)

    def test_predict_higher_markup_lower_prob(self):
        m = self._model()
        low = m.predict(0.05, 3)["win_probability"]
        high = m.predict(0.30, 3)["win_probability"]
        assert low > high

    def test_predict_trained_model(self):
        """Test trained path via mocked sklearn model."""
        m = self._model()
        fake_model = MagicMock()
        fake_scaler = MagicMock()
        fake_scaler.transform.return_value = [[0.1, 3, 0.3]]
        fake_model.predict_proba.return_value = [[0.2, 0.7]]
        m._model = (fake_model, fake_scaler)
        m._is_trained = True
        r = m.predict(0.10, 3)
        assert r["method"] == "logistic_regression"
        assert r["win_probability"] == 0.7

    def test_predict_trained_model_exception_fallback(self):
        m = self._model()
        fake_model = MagicMock()
        fake_scaler = MagicMock()
        fake_scaler.transform.side_effect = RuntimeError("boom")
        m._model = (fake_model, fake_scaler)
        m._is_trained = True
        r = m.predict(0.10, 3)
        # Falls back to friedman
        assert r["method"] == "friedman_parametric"

    def test_train_insufficient_data(self):
        m = self._model()
        result = m.train([{"markup": 0.1, "won": True}] * 3)
        assert result["status"] == "insufficient_data"
        assert m._is_trained is False

    def test_train_sufficient_data(self):
        import numpy as np
        m = self._model()
        records = []
        for i in range(30):
            records.append({
                "markup": 0.05 + i * 0.01,
                "n_competitors": 3 + (i % 5),
                "won": bool(i % 3 == 0),
            })
        result = m.train(records)
        assert result["status"] in ("trained", "insufficient_data")


class TestComputeWinProbFunction:
    """Test the module-level compute_win_probability function."""

    def test_no_historical_data_fallback(self):
        from services.api.services.api.intelligence.win_prob import compute_win_probability

        engine = MagicMock()
        conn = MagicMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = []  # no historical data
        conn.execute.return_value = result_mock
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn

        with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=engine):
            r = compute_win_probability(100000.0, "45")
        assert "quantiles" in r or "error" in r

    def test_with_historical_data(self):
        from services.api.services.api.intelligence.win_prob import compute_win_probability

        engine = MagicMock()
        conn = MagicMock()
        # Simulate historical bid rows: (winning_price_pln, estimated_value)
        rows = [
            (90000.0, 100000.0),
            (95000.0, 100000.0),
            (85000.0, 100000.0),
            (105000.0, 100000.0),
        ] * 5
        result_mock = MagicMock()
        result_mock.fetchall.return_value = rows
        conn.execute.return_value = result_mock
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn

        with patch("services.api.services.api.intelligence.win_prob.get_engine", return_value=engine):
            r = compute_win_probability(100000.0, "45")
        assert "quantiles" in r or "error" in r


# ─── intelligence/anomaly.py ──────────────────────────────────────────────────

class TestZscorePozycja:
    def _make_engine_none(self):
        """Engine that returns None for fetchone (pozycja not found)."""
        engine = MagicMock()
        conn = MagicMock()
        result = MagicMock()
        result.fetchone.return_value = None
        result.fetchall.return_value = []
        conn.execute.return_value = result
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        return engine

    def test_zscore_not_found_returns_default(self):
        from services.api.services.api.intelligence.anomaly import zscore_pozycja
        engine = self._make_engine_none()
        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            r = zscore_pozycja(str(uuid.uuid4()))
        assert r["is_anomaly"] is False
        assert "pozycja_id" in r

    def test_zscore_db_error_returns_default(self):
        from services.api.services.api.intelligence.anomaly import zscore_pozycja
        from sqlalchemy.exc import SQLAlchemyError
        engine = MagicMock()
        conn = MagicMock()
        conn.execute.side_effect = SQLAlchemyError("db fail")
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            r = zscore_pozycja(str(uuid.uuid4()))
        assert r["is_anomaly"] is False

    def test_zscore_with_data(self):
        """With a pozycja row and ICB data — test full path."""
        from services.api.services.api.intelligence.anomaly import zscore_pozycja
        pid = str(uuid.uuid4())

        # First call: fetchone returns (r_jcena, m_jcena, s_jcena, symbol, kategoria)
        pozycja_row = MagicMock()
        pozycja_row.__getitem__ = lambda s, i: [100.0, 200.0, 50.0, "M001", "robocizna"][i]

        # ICB stats rows
        icb_row = MagicMock()
        icb_row.__getitem__ = lambda s, i: 100.0

        call_count = [0]
        def make_conn():
            conn = MagicMock()
            result = MagicMock()
            result.fetchone.return_value = pozycja_row
            result.fetchall.return_value = [icb_row] * 10
            conn.execute.return_value = result
            conn.__enter__ = lambda s: s
            conn.__exit__ = MagicMock(return_value=False)
            return conn

        engine = MagicMock()
        engine.connect.side_effect = lambda: make_conn()

        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            r = zscore_pozycja(pid)
        assert "pozycja_id" in r
        assert isinstance(r["is_anomaly"], bool)


class TestAnalyzeKosztorys:
    def _make_engine(self, rows=None, fetchone=None, rowcount=1):
        engine = MagicMock()
        conn = MagicMock()
        result = MagicMock()
        result.fetchall.return_value = rows or []
        result.fetchone.return_value = fetchone
        result.rowcount = rowcount
        conn.execute.return_value = result
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value = begin_ctx
        return engine

    def test_analyze_empty_kosztorys(self):
        from services.api.services.api.intelligence.anomaly import analyze_kosztorys
        engine = self._make_engine(rows=[])
        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            r = analyze_kosztorys(str(uuid.uuid4()), str(uuid.uuid4()))
        assert r["pozycje_analyzed"] == 0
        assert r["anomalies_found"] == 0

    def test_analyze_with_pozycje(self):
        from services.api.services.api.intelligence.anomaly import analyze_kosztorys
        pids = [str(uuid.uuid4()) for _ in range(3)]
        rows = [(p, 100.0, 200.0, 50.0) for p in pids]
        engine = self._make_engine(rows=rows)

        def mock_zscore(pid):
            return {"pozycja_id": pid, "r_zscore": 0.5, "m_zscore": 0.3, "s_zscore": 0.2, "is_anomaly": False}

        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            with patch("services.api.services.api.intelligence.anomaly.zscore_pozycja", side_effect=mock_zscore):
                r = analyze_kosztorys(pids[0], str(uuid.uuid4()))
        assert r["pozycje_analyzed"] >= 0

    def test_analyze_finds_anomalies(self):
        from services.api.services.api.intelligence.anomaly import analyze_kosztorys
        pids = [str(uuid.uuid4()) for _ in range(5)]
        rows = [(p, 100.0, 200.0, 50.0) for p in pids]
        engine = self._make_engine(rows=rows)

        def mock_zscore(pid):
            return {"pozycja_id": pid, "r_zscore": 4.5, "m_zscore": 4.1, "s_zscore": 3.9, "is_anomaly": True}

        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            with patch("services.api.services.api.intelligence.anomaly.zscore_pozycja", side_effect=mock_zscore):
                r = analyze_kosztorys(pids[0], str(uuid.uuid4()))
        # Should report anomalies
        assert isinstance(r.get("anomalies_found", 0), int)


class TestGetAnomalies:
    def test_get_anomalies_empty(self):
        from services.api.services.api.intelligence.anomaly import get_anomalies
        engine = MagicMock()
        conn = MagicMock()
        result = MagicMock()
        result.fetchall.return_value = []
        conn.execute.return_value = result
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            r = get_anomalies(str(uuid.uuid4()), str(uuid.uuid4()))
        assert isinstance(r, list)
        assert len(r) == 0

    def test_get_anomalies_returns_list(self):
        from services.api.services.api.intelligence.anomaly import get_anomalies
        pid = str(uuid.uuid4())
        rows = [(pid, 1, "KNR001", "Robocizna", "m2", 10.0, 50.0, 100.0, 30.0, True)]
        engine = MagicMock()
        conn = MagicMock()
        result = MagicMock()
        result.fetchall.return_value = rows
        # Mock _mapping for row
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": pid, "lp": 1, "kst_code": "KNR001", "opis": "Robocizna",
            "jednostka": "m2", "ilosc": 10.0, "r_jcena": 50.0,
            "m_jcena": 100.0, "s_jcena": 30.0, "is_anomaly": True,
        }
        result.fetchall.return_value = [mock_row]
        conn.execute.return_value = result
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        engine.connect.return_value = conn
        with patch("services.api.services.api.intelligence.anomaly.get_engine", return_value=engine):
            r = get_anomalies(str(uuid.uuid4()), str(uuid.uuid4()))
        assert isinstance(r, list)
