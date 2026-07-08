"""Tests — Intelligence Layer (K1 Sprint).

Testy dla:
- ICB Service: search, narzuty, regional_coefficient, robocizna_rates, trend
- Price Intelligence: inflation_index, material_risk, forecast, price_index
- Bid Intelligence: cpv_benchmark, anomaly detection, win_probability
- Intelligence Router: wszystkie GET/POST endpointy
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


# ─── Fixtures ──────────────────────────────────────────────────────────────────

ICB_SAMPLE = [
    {"id": 1, "nazwa": "Cegła pełna", "symbol": "CEG-001", "indeks_eto": "0411",
     "typ_rms": "M", "jednostka": "szt", "cena_netto": 2.5, "cena_narzut": 2.8, "category": "murarstwo"},
    {"id": 2, "nazwa": "Beton C20/25", "symbol": "BET-025", "indeks_eto": "0512",
     "typ_rms": "M", "jednostka": "m3", "cena_netto": 380.0, "cena_narzut": 420.0, "category": "beton_cement"},
    {"id": 3, "nazwa": "Robocizna ogólnobudowlana", "symbol": "ROB-001", "indeks_eto": "999",
     "typ_rms": "R", "jednostka": "r-g", "cena_netto": 52.09, "cena_narzut": 52.09, "category": "murarstwo"},
]

NARZUTY_SAMPLE = {
    "ko_pct": 70.1, "z_pct": 12.5, "kz_pct": 7.1,
    "branża": "roboty ogólnobudowlane", "source": "icb_narzuty",
}

WIN_RATIOS_SAMPLE = [0.85, 0.88, 0.91, 0.93, 0.95, 0.97, 0.98, 1.00, 1.02, 1.05,
                     0.87, 0.90, 0.92, 0.94, 0.96, 0.99, 1.01, 1.03, 0.96, 0.97]


# ─── ICB SERVICE TESTS ─────────────────────────────────────────────────────────

class TestICBService:
    """Test ICB Service — wyszukiwarka cen ICB."""

    def test_search_icb_returns_list(self):
        """search_icb zwraca listę wyników."""
        from services.api.services.api.intelligence.icb_service import search_icb
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            result = search_icb("cegła")
        assert isinstance(result, list)

    def test_get_narzuty_structure(self):
        """get_narzuty zwraca dict z ko_pct, z_pct, kz_pct."""
        from services.api.services.api.intelligence.icb_service import get_narzuty
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            # Symuluj brak danych → fallback
            mock_conn.execute.return_value.fetchone.return_value = None
            result = get_narzuty(2026, 2, "roboty ogólnobudowlane")
        assert "ko_pct" in result
        assert "z_pct" in result
        assert "kz_pct" in result
        assert result["ko_pct"] > 0

    def test_get_narzuty_fallback_values(self):
        """Fallback narzuty są realistyczne dla budownictwa PL 2026."""
        from services.api.services.api.intelligence.icb_service import get_narzuty
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchone.return_value = None
            result = get_narzuty(2026, 2)
        # Ko 60–120%, Z 8–25%, Kz 3–12%
        assert 50.0 <= result["ko_pct"] <= 130.0
        assert 5.0 <= result["z_pct"] <= 30.0
        assert 2.0 <= result["kz_pct"] <= 15.0

    def test_get_regional_coefficient_fallback(self):
        """Fallback = 1.0 gdy brak danych w bazie."""
        from services.api.services.api.intelligence.icb_service import get_regional_coefficient
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchone.return_value = None
            coeff = get_regional_coefficient("nieznane_województwo")
        assert coeff == 1.0

    def test_get_regional_coefficient_range(self):
        """Współczynnik regionalny w zakresie 0.8–1.4."""
        from services.api.services.api.intelligence.icb_service import get_regional_coefficient
        mock_row = MagicMock()
        mock_row.coefficient = 1.15
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchone.return_value = mock_row
            coeff = get_regional_coefficient("mazowieckie")
        assert 0.8 <= coeff <= 1.4

    def test_voivodeship_mapping(self):
        """Aliasy miast mapują na województwa."""
        from services.api.services.api.intelligence.icb_service import VOIVODESHIP_NAMES
        assert VOIVODESHIP_NAMES.get("warszawa") == "mazowieckie"
        assert VOIVODESHIP_NAMES.get("kraków") == "małopolskie"
        assert VOIVODESHIP_NAMES.get("katowice") == "śląskie"

    def test_get_price_trend_returns_list(self):
        """get_price_trend zwraca listę punktów trendu."""
        from services.api.services.api.intelligence.icb_service import get_price_trend
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            result = get_price_trend(category="murarstwo", typ_rms="M")
        assert isinstance(result, list)

    def test_robocizna_rates_fallback(self):
        """Fallback robocizna = 52.09 zł/r-g (ICB Q2-2026)."""
        from services.api.services.api.intelligence.icb_service import get_robocizna_rates
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchone.return_value = None
            result = get_robocizna_rates()
        assert result["stawka_r"] > 0
        assert result["source"] == "fallback_2026q2"


# ─── PRICE INTELLIGENCE TESTS ─────────────────────────────────────────────────

class TestPriceIntelligence:
    """Test Price Intelligence — risk, forecasting, index."""

    def test_material_risk_score_stable(self):
        """Stabilne ceny → niski risk score."""
        from services.api.services.api.intelligence.price_intelligence import get_material_risk_score
        stable_prices = [100.0] * 8  # całkowicie stabilne
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            rows = []
            for i, p in enumerate(stable_prices):
                r = MagicMock()
                r.kwartalrok = 2025 - i // 4
                r.kwartalnr = 4 - (i % 4)
                r.avg_price = p
                r.std_price = 0
                rows.append(r)
            mock_conn.execute.return_value.fetchall.return_value = rows
            result = get_material_risk_score("murarstwo")
        assert result["score"] <= 0.3
        assert result["level"] in ("low", "unknown")

    def test_material_risk_score_volatile(self):
        """Zmienne ceny → wysoki risk score."""
        from services.api.services.api.intelligence.price_intelligence import get_material_risk_score
        volatile_prices = [100, 150, 90, 200, 80, 170, 95, 185]
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            rows = []
            for i, p in enumerate(volatile_prices):
                r = MagicMock()
                r.kwartalrok = 2026 - i // 4
                r.kwartalnr = max(1, 4 - (i % 4))
                r.avg_price = float(p)
                r.std_price = 20.0
                rows.append(r)
            mock_conn.execute.return_value.fetchall.return_value = rows
            result = get_material_risk_score("stal_konstrukcyjna")
        assert result["score"] > 0.2
        assert "level" in result

    def test_material_risk_structure(self):
        """Material risk zwraca wymagane pola."""
        from services.api.services.api.intelligence.price_intelligence import get_material_risk_score
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            result = get_material_risk_score("xyz_nie_istnieje")
        assert "score" in result
        assert "level" in result

    def test_forecast_price_insufficient_data(self):
        """forecast_price z <4 kwartałami zwraca error."""
        from services.api.services.api.intelligence.price_intelligence import forecast_price
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            result = forecast_price(category="murarstwo")
        assert "error" in result

    def test_forecast_price_linear_trend(self):
        """forecast_price z wystarczającą historią zwraca forecasts."""
        from services.api.services.api.intelligence.price_intelligence import forecast_price
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            rows = []
            for i in range(8):
                r = MagicMock()
                r.kwartalrok = 2024 + i // 4
                r.kwartalnr = (i % 4) + 1
                r.avg_price = 100.0 + i * 5.0  # wzrost 5 zł/kwartał
                rows.append(r)
            mock_conn.execute.return_value.fetchall.return_value = rows
            result = forecast_price(category="murarstwo", horizon_quarters=4)
        assert "forecasts" in result
        assert len(result["forecasts"]) == 4
        # Prognoza rosnąca
        for fc in result["forecasts"]:
            assert fc["p50"] > 0
            assert fc["p10"] <= fc["p50"] <= fc["p90"]

    def test_forecast_price_slope_positive(self):
        """Dla rosnących cen slope > 0."""
        from services.api.services.api.intelligence.price_intelligence import forecast_price
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            rows = []
            for i in range(12):
                r = MagicMock()
                r.kwartalrok = 2020 + i // 4
                r.kwartalnr = (i % 4) + 1
                r.avg_price = 50.0 + i * 8.0
                rows.append(r)
            mock_conn.execute.return_value.fetchall.return_value = rows
            result = forecast_price(category="murarstwo")
        if "slope_per_quarter" in result:
            assert result["slope_per_quarter"] > 0


# ─── BID INTELLIGENCE TESTS ───────────────────────────────────────────────────

class TestBidIntelligence:
    """Test Bid Intelligence — anomaly detection, win probability, benchmark."""

    def test_benford_check_round_numbers(self):
        """Zaokrąglone ceny dostają wyższy Benford score."""
        from services.api.services.api.intelligence.bid_intelligence import _benford_check
        score_round = _benford_check(1_000_000.0)   # 1 mln — mocno zaokrąglona
        score_odd = _benford_check(1_234_567.0)     # losowa — naturalna
        assert score_round >= score_odd

    def test_benford_check_range(self):
        """Benford score zawsze 0.0–1.0."""
        from services.api.services.api.intelligence.bid_intelligence import _benford_check
        for val in [1, 100, 12345, 1000000, 999999, 0.5]:
            score = _benford_check(float(val))
            assert 0.0 <= score <= 1.0, f"Benford({val}) = {score} out of range"

    def test_detect_bid_anomaly_razaco_niska(self):
        """Oferta <70% szacunku → flaga PZP_ART224."""
        from services.api.services.api.intelligence.bid_intelligence import detect_bid_anomalies
        with patch("services.api.services.api.intelligence.bid_intelligence.get_cpv_benchmark") as mock_bm, \
             patch("services.api.services.api.intelligence.bid_intelligence._get_win_ratios_for_cpv") as mock_wr:
            mock_bm.return_value = {"win_ratio_median": 0.97, "win_ratio_p25": 0.88,
                                     "win_ratio_p75": 1.05, "n_market_results": 0}
            mock_wr.return_value = WIN_RATIOS_SAMPLE * 3  # 60 sampli
            result = detect_bid_anomalies(
                bid_price=600_000,
                estimated_value=1_000_000,
                cpv_prefix="45",
            )
        assert result["ratio"] == pytest.approx(0.6, abs=0.01)
        assert any("ART224" in f or "RAŻĄCO" in f or "VERY_LOW" in f for f in result["flags"])
        assert result["anomaly_score"] >= 0.5

    def test_detect_bid_anomaly_normal(self):
        """Oferta 97% szacunku → niski anomaly score."""
        from services.api.services.api.intelligence.bid_intelligence import detect_bid_anomalies
        with patch("services.api.services.api.intelligence.bid_intelligence.get_cpv_benchmark") as mock_bm, \
             patch("services.api.services.api.intelligence.bid_intelligence._get_win_ratios_for_cpv") as mock_wr:
            mock_bm.return_value = {"win_ratio_median": 0.97, "win_ratio_p25": 0.88,
                                     "win_ratio_p75": 1.05, "n_market_results": 20}
            mock_wr.return_value = WIN_RATIOS_SAMPLE * 3
            result = detect_bid_anomalies(
                bid_price=970_000,
                estimated_value=1_000_000,
                cpv_prefix="45",
            )
        assert result["ratio"] == pytest.approx(0.97, abs=0.01)
        assert result["anomaly_score"] < 0.5

    def test_detect_bid_anomaly_structure(self):
        """Wynik anomaly detection ma wymagane pola."""
        from services.api.services.api.intelligence.bid_intelligence import detect_bid_anomalies
        with patch("services.api.services.api.intelligence.bid_intelligence.get_cpv_benchmark") as mock_bm, \
             patch("services.api.services.api.intelligence.bid_intelligence._get_win_ratios_for_cpv") as mock_wr:
            mock_bm.return_value = {"win_ratio_median": 0.97, "win_ratio_p25": 0.88,
                                     "win_ratio_p75": 1.05, "n_market_results": 0}
            mock_wr.return_value = []
            result = detect_bid_anomalies(500_000, 500_000, "45")
        required = ["bid_price", "estimated_value", "ratio", "anomaly_score", "flags", "recommendation"]
        for field in required:
            assert field in result, f"Brakuje pola: {field}"

    def test_win_probability_below_sweet_spot(self):
        """Oferta znacznie poniżej mediany → wysoki P(win)."""
        from services.api.services.api.intelligence.bid_intelligence import estimate_win_probability
        with patch("services.api.services.api.intelligence.bid_intelligence._get_win_ratios_for_cpv") as mock_wr:
            mock_wr.return_value = WIN_RATIOS_SAMPLE * 5  # 100 sampli
            result = estimate_win_probability(
                our_price=850_000,
                estimated_value=1_000_000,
                cpv_prefix="45",
                n_competitors=4,
            )
        assert result["p_win"] > 0.3  # powinno być relatywnie wysokie
        assert "sweet_spot" in result

    def test_win_probability_above_estimate(self):
        """Oferta powyżej wartości szacunkowej → niski P(win)."""
        from services.api.services.api.intelligence.bid_intelligence import estimate_win_probability
        with patch("services.api.services.api.intelligence.bid_intelligence._get_win_ratios_for_cpv") as mock_wr:
            mock_wr.return_value = WIN_RATIOS_SAMPLE * 5
            result = estimate_win_probability(
                our_price=1_300_000,
                estimated_value=1_000_000,
                cpv_prefix="45",
                n_competitors=4,
            )
        assert result["p_win"] < 0.3

    def test_win_probability_structure(self):
        """Wynik win probability ma wymagane pola."""
        from services.api.services.api.intelligence.bid_intelligence import estimate_win_probability
        with patch("services.api.services.api.intelligence.bid_intelligence._get_win_ratios_for_cpv") as mock_wr:
            mock_wr.return_value = WIN_RATIOS_SAMPLE * 5
            result = estimate_win_probability(500_000, 500_000, "45")
        required = ["p_win", "our_ratio", "method", "recommendation"]
        for field in required:
            assert field in result, f"Brakuje pola: {field}"

    def test_win_probability_fallback_few_samples(self):
        """Mało sampli → fallback parametryczny."""
        from services.api.services.api.intelligence.bid_intelligence import estimate_win_probability
        with patch("services.api.services.api.intelligence.bid_intelligence._get_win_ratios_for_cpv") as mock_wr:
            mock_wr.return_value = [0.95, 0.97]  # za mało
            result = estimate_win_probability(970_000, 1_000_000, "45")
        assert result["method"] == "parametric_fallback"
        assert 0 <= result["p_win"] <= 1

    def test_cpv_benchmark_structure(self):
        """CPV benchmark ma wymagane pola."""
        from services.api.services.api.intelligence.bid_intelligence import get_cpv_benchmark
        with patch("services.api.services.api.intelligence.bid_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            result = get_cpv_benchmark("45")
        assert result["cpv_prefix"] == "45"
        # Fallback win_ratio_median
        assert "win_ratio_median" in result

    def test_detect_kosztorys_anomalies_empty(self):
        """Pusta lista pozycji → error."""
        from services.api.services.api.intelligence.bid_intelligence import detect_kosztorys_anomalies
        result = detect_kosztorys_anomalies([])
        assert "error" in result

    def test_detect_kosztorys_anomalies_structure(self):
        """Analiza kosztorysu zwraca n_items, anomaly_rate, all_items."""
        from services.api.services.api.intelligence.bid_intelligence import detect_kosztorys_anomalies
        items = [
            {"description": "Cegła pełna", "unit": "szt", "quantity": 1000,
             "unit_price": 2.5, "category": "murarstwo"},
            {"description": "Beton C20/25", "unit": "m3", "quantity": 50,
             "unit_price": 380.0, "category": "beton_cement"},
            {"description": "Robocizna", "unit": "r-g", "quantity": 200,
             "unit_price": 52.0, "category": "inne"},
        ]
        with patch("services.api.services.api.intelligence.bid_intelligence.get_engine") as mock_eng, \
             patch("services.api.services.api.intelligence.bid_intelligence._latest_quarter") as mock_q:
            mock_q.return_value = (2026, 2)
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            result = detect_kosztorys_anomalies(items)
        assert result["n_items"] == 3
        assert "anomaly_rate" in result
        assert "all_items" in result

    def test_detect_kosztorys_anomalies_total_value(self):
        """total_value = Σ(quantity × unit_price)."""
        from services.api.services.api.intelligence.bid_intelligence import detect_kosztorys_anomalies
        items = [
            {"description": "Poz 1", "unit": "m2", "quantity": 100.0, "unit_price": 50.0, "category": "inne"},
            {"description": "Poz 2", "unit": "m3", "quantity": 10.0, "unit_price": 200.0, "category": "inne"},
        ]
        with patch("services.api.services.api.intelligence.bid_intelligence.get_engine") as mock_eng, \
             patch("services.api.services.api.intelligence.bid_intelligence._latest_quarter") as mock_q:
            mock_q.return_value = (2026, 2)
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            result = detect_kosztorys_anomalies(items)
        assert result["total_value"] == pytest.approx(7000.0, abs=1.0)


# ─── INTELLIGENCE ROUTER TESTS ────────────────────────────────────────────────

class TestIntelligenceRouter:
    """Test HTTP endpointów Intelligence Router."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from services.api.services.api.routers.intelligence import router
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_categories_endpoint(self, client):
        """GET /api/v2/intelligence/categories → 200."""
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            r = client.get("/api/v2/intelligence/categories")
        assert r.status_code == 200
        assert "categories" in r.json()

    def test_prices_icb_requires_query(self, client):
        """GET /prices/icb bez q → 422."""
        r = client.get("/api/v2/intelligence/prices/icb")
        assert r.status_code == 422

    def test_prices_icb_with_query(self, client):
        """GET /prices/icb?q=cegla → 200."""
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            r = client.get("/api/v2/intelligence/prices/icb?q=cegla&year=2026&quarter=2")
        assert r.status_code == 200
        assert "results" in r.json()

    def test_material_risk_all(self, client):
        """GET /material-risk → 200."""
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            r = client.get("/api/v2/intelligence/material-risk")
        assert r.status_code == 200
        assert "risks" in r.json()

    def test_narzuty_all(self, client):
        """GET /narzuty?all=true → 200 + list."""
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            r = client.get("/api/v2/intelligence/narzuty?all=true")
        assert r.status_code == 200

    def test_anomaly_bid_razaco_niska(self, client):
        """POST /anomaly/bid z ofertą <70% → ART224 flag."""
        with patch("services.api.services.api.intelligence.bid_intelligence.get_cpv_benchmark") as mock_bm, \
             patch("services.api.services.api.intelligence.bid_intelligence._get_win_ratios_for_cpv") as mock_wr:
            mock_bm.return_value = {"win_ratio_median": 0.97, "win_ratio_p25": 0.88,
                                     "win_ratio_p75": 1.05, "n_market_results": 0}
            mock_wr.return_value = WIN_RATIOS_SAMPLE * 3
            r = client.post("/api/v2/intelligence/anomaly/bid", json={
                "bid_price": 600000,
                "estimated_value": 1000000,
                "cpv_prefix": "45",
            })
        assert r.status_code == 200
        data = r.json()
        assert data["anomaly_score"] >= 0.5

    def test_win_probability_endpoint(self, client):
        """POST /win-probability → 200 z p_win."""
        with patch("services.api.services.api.intelligence.bid_intelligence._get_win_ratios_for_cpv") as mock_wr:
            mock_wr.return_value = WIN_RATIOS_SAMPLE * 5
            r = client.post("/api/v2/intelligence/win-probability", json={
                "our_price": 970000,
                "estimated_value": 1000000,
                "cpv_prefix": "45",
                "n_competitors": 4,
            })
        assert r.status_code == 200
        data = r.json()
        assert "p_win" in data
        assert 0.0 <= data["p_win"] <= 1.0

    def test_anomaly_kosztorys_endpoint(self, client):
        """POST /anomaly/kosztorys → 200."""
        with patch("services.api.services.api.intelligence.bid_intelligence.get_engine") as mock_eng, \
             patch("services.api.services.api.intelligence.bid_intelligence._latest_quarter") as mock_q:
            mock_q.return_value = (2026, 2)
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            r = client.post("/api/v2/intelligence/anomaly/kosztorys", json={
                "items": [
                    {"description": "Cegła", "unit": "szt", "quantity": 1000,
                     "unit_price": 2.5, "category": "murarstwo"}
                ],
                "cpv_prefix": "45",
            })
        assert r.status_code == 200

    def test_benchmark_endpoint(self, client):
        """GET /benchmark?cpv_prefix=45 → 200."""
        with patch("services.api.services.api.intelligence.bid_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            r = client.get("/api/v2/intelligence/benchmark?cpv_prefix=45")
        assert r.status_code == 200
        assert "cpv_prefix" in r.json()

    def test_prices_index_endpoint(self, client):
        """GET /prices/index → 200."""
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            r = client.get("/api/v2/intelligence/prices/index")
        assert r.status_code == 200

    def test_robocizna_rates_endpoint(self, client):
        """GET /robocizna-rates → 200."""
        with patch("services.api.services.api.intelligence.icb_service.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchone.return_value = None
            r = client.get("/api/v2/intelligence/robocizna-rates?voivodeship=śląskie")
        assert r.status_code == 200

    def test_prices_forecast_endpoint(self, client):
        """GET /prices/forecast?category=murarstwo → 200 lub error w polu."""
        with patch("services.api.services.api.intelligence.price_intelligence.get_engine") as mock_eng:
            mock_conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s, *a: mock_conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_conn.execute.return_value.fetchall.return_value = []
            r = client.get("/api/v2/intelligence/prices/forecast?category=murarstwo")
        assert r.status_code == 200


# ─── EDGE CASES ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Przypadki brzegowe i odporność na błędy."""

    def test_percentile_empty(self):
        """_percentile na pustej liście → 0.0."""
        from services.api.services.api.intelligence.bid_intelligence import _percentile
        assert _percentile([], 0.5) == 0.0

    def test_percentile_single(self):
        """_percentile na jednoelementowej liście."""
        from services.api.services.api.intelligence.bid_intelligence import _percentile
        assert _percentile([100.0], 0.5) == 100.0

    def test_percentile_median(self):
        """_percentile(0.5) na liście 5 el = środkowy."""
        from services.api.services.api.intelligence.bid_intelligence import _percentile
        vals = sorted([10.0, 20.0, 30.0, 40.0, 50.0])
        result = _percentile(vals, 0.5)
        assert result == pytest.approx(30.0, abs=1.0)

    def test_competition_factor_range(self):
        """_competition_factor zawsze 0–1."""
        from services.api.services.api.intelligence.bid_intelligence import _competition_factor
        for p_base in [0.1, 0.3, 0.5, 0.7, 0.9]:
            for n in [1, 2, 4, 8]:
                r = _competition_factor(p_base, n)
                assert 0 <= r <= 1, f"competition_factor({p_base}, {n}) = {r}"

    def test_anomaly_score_range(self):
        """anomaly_score zawsze 0.0–1.0."""
        from services.api.services.api.intelligence.bid_intelligence import detect_bid_anomalies
        test_cases = [
            (200_000, 1_000_000),   # bardzo niska
            (970_000, 1_000_000),   # normalna
            (2_000_000, 1_000_000), # bardzo wysoka
            (0.01, 1_000_000),      # ekstremalnie niska
        ]
        with patch("services.api.services.api.intelligence.bid_intelligence.get_cpv_benchmark") as mock_bm, \
             patch("services.api.services.api.intelligence.bid_intelligence._get_win_ratios_for_cpv") as mock_wr:
            mock_bm.return_value = {"win_ratio_median": 0.97, "win_ratio_p25": 0.88,
                                     "win_ratio_p75": 1.05, "n_market_results": 0}
            mock_wr.return_value = WIN_RATIOS_SAMPLE * 3
            for bid, est in test_cases:
                result = detect_bid_anomalies(bid, est, "45")
                assert 0.0 <= result["anomaly_score"] <= 1.0, \
                    f"anomaly_score({bid}/{est}) = {result['anomaly_score']}"

    def test_infer_rms_from_unit(self):
        """_infer_rms wykrywa R i S z jednostki."""
        from services.api.services.api.intelligence.bid_intelligence import _infer_rms
        assert _infer_rms({"description": "praca", "unit": "r-g", "category": "inne"}) == "R"
        assert _infer_rms({"description": "koparka", "unit": "m-g", "category": "inne"}) == "S"
        assert _infer_rms({"description": "beton", "unit": "m3", "category": "beton_cement"}) == "M"
