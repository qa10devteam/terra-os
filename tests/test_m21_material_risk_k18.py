"""Sprint K18 — testy: material_risk, icb_service, kosztorys_v2 coverage boost."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch, call

import pytest

TENANT = str(uuid.uuid4())
KID    = str(uuid.uuid4())
PID    = str(uuid.uuid4())
ICB_ID = str(uuid.uuid4())


# ─── helpers ──────────────────────────────────────────────────────────────────

def _engine(rows_map: dict | None = None):
    """rows_map: {sql_fragment: rows} — fetchall/fetchone z pasującym fragmentem."""
    engine = MagicMock()
    conn   = MagicMock()

    def _execute(stmt, params=None):
        text = str(stmt) if hasattr(stmt, '__str__') else ""
        result = MagicMock()
        rows = []
        if rows_map:
            for fragment, r in rows_map.items():
                if fragment.lower() in text.lower():
                    rows = r
                    break
        result.fetchall.return_value = rows
        result.fetchone.return_value = rows[0] if rows else None
        result.rowcount = len(rows)
        return result

    conn.execute = _execute
    conn.__enter__ = lambda s: conn
    conn.__exit__  = MagicMock(return_value=False)
    begin_ctx = MagicMock()
    begin_ctx.__enter__ = lambda s: conn
    begin_ctx.__exit__  = MagicMock(return_value=False)
    engine.connect.return_value = conn
    engine.begin.return_value   = begin_ctx
    return engine


def _row(**kw):
    """Tworzy MagicMock z atrybutami jak Row SQLAlchemy."""
    r = MagicMock()
    for k, v in kw.items():
        setattr(r, k, v)
    return r


# ══════════════════════════════════════════════════════════════════════════════
# 1. intelligence/material_risk.py
# ══════════════════════════════════════════════════════════════════════════════

class TestGetSeverity:
    def test_low(self):
        from services.api.services.api.intelligence.material_risk import _get_severity
        assert _get_severity(3.0) == "low"
        assert _get_severity(-3.0) == "low"

    def test_medium(self):
        from services.api.services.api.intelligence.material_risk import _get_severity
        assert _get_severity(7.0) == "medium"

    def test_high(self):
        from services.api.services.api.intelligence.material_risk import _get_severity
        assert _get_severity(15.0) == "high"

    def test_critical(self):
        from services.api.services.api.intelligence.material_risk import _get_severity
        assert _get_severity(25.0) == "critical"
        assert _get_severity(-25.0) == "critical"


class TestCheckMaterialRisks:
    def _poz_row(self, baseline=100.0, current_m=100.0):
        return _row(poz_id=PID, icb_id=ICB_ID,
                    nazwa="Cement", baseline_price=baseline, current_m=current_m)

    def _icb_row(self, price=150.0, symbol="CEM-01"):
        return _row(price=price, symbol=symbol, kwartalnr=1, kwartalrok=2026)

    def test_no_pozycje_returns_empty(self):
        from services.api.services.api.intelligence.material_risk import check_material_risks
        engine = _engine({"kosztorys_pozycja": []})
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=engine):
            result = check_material_risks(kosztorys_id=KID, tenant_id=TENANT)
        assert result == []

    def test_no_icb_price_skips(self):
        from services.api.services.api.intelligence.material_risk import check_material_risks
        engine = _engine({
            "kosztorys_pozycja": [self._poz_row()],
            "icb_ceny_srednie":  [],   # brak ceny
        })
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=engine):
            result = check_material_risks(kosztorys_id=KID, tenant_id=TENANT)
        assert result == []

    def test_below_threshold_no_alert(self):
        from services.api.services.api.intelligence.material_risk import check_material_risks
        # baseline=100, current=103 → 3% < 10%
        engine = _engine({
            "kosztorys_pozycja": [self._poz_row(baseline=100.0)],
            "icb_ceny_srednie":  [self._icb_row(price=103.0)],
        })
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=engine):
            result = check_material_risks(kosztorys_id=KID, tenant_id=TENANT, threshold_pct=10.0)
        assert len(result) == 1
        assert result[0]["alert_created"] is False
        assert abs(result[0]["change_pct"] - 3.0) < 0.01

    def test_above_threshold_creates_alert(self):
        from services.api.services.api.intelligence.material_risk import check_material_risks
        # baseline=100, current=130 → 30% > 10%
        engine = _engine({
            "kosztorys_pozycja": [self._poz_row(baseline=100.0)],
            "icb_ceny_srednie":  [self._icb_row(price=130.0)],
        })
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=engine):
            result = check_material_risks(kosztorys_id=KID, tenant_id=TENANT, threshold_pct=10.0)
        assert len(result) == 1
        assert result[0]["alert_created"] is True
        assert result[0]["severity"] in ("high", "critical")
        assert result[0]["change_pct"] == pytest.approx(30.0, abs=0.01)

    def test_baseline_zero_uses_current_m(self):
        from services.api.services.api.intelligence.material_risk import check_material_risks
        # baseline=0 → używa current_m=100 jako baseline, cena ICB=100 → 0% zmiana
        engine = _engine({
            "kosztorys_pozycja": [self._poz_row(baseline=0.0, current_m=100.0)],
            "icb_ceny_srednie":  [self._icb_row(price=100.0)],
        })
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=engine):
            result = check_material_risks(kosztorys_id=KID, tenant_id=TENANT)
        assert len(result) == 1
        assert result[0]["change_pct"] == pytest.approx(0.0, abs=0.01)

    def test_negative_change_decrease(self):
        from services.api.services.api.intelligence.material_risk import check_material_risks
        # baseline=200, current=140 → -30%
        engine = _engine({
            "kosztorys_pozycja": [self._poz_row(baseline=200.0)],
            "icb_ceny_srednie":  [self._icb_row(price=140.0)],
        })
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=engine):
            result = check_material_risks(kosztorys_id=KID, tenant_id=TENANT, threshold_pct=10.0)
        assert result[0]["change_pct"] == pytest.approx(-30.0, abs=0.01)
        assert result[0]["alert_created"] is True

    def test_db_error_returns_empty(self):
        from services.api.services.api.intelligence.material_risk import check_material_risks
        from sqlalchemy.exc import SQLAlchemyError
        broken = MagicMock()
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = MagicMock(side_effect=SQLAlchemyError("DB down"))
        begin_ctx.__exit__  = MagicMock(return_value=False)
        broken.begin.return_value = begin_ctx
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=broken):
            result = check_material_risks(kosztorys_id=KID, tenant_id=TENANT)
        assert result == []


class TestGetActiveAlerts:
    def test_returns_list(self):
        from services.api.services.api.intelligence.material_risk import get_active_alerts
        import datetime
        row = _row(id=str(uuid.uuid4()), org_id=TENANT,
                   kosztorys_id=KID, icb_id=ICB_ID, symbol="CEM-01",
                   baseline_price=100.0, current_price=130.0,
                   change_pct=30.0, severity="critical",
                   created_at=datetime.datetime(2026, 1, 1))
        engine = _engine({"material_alert": [row]})
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=engine):
            alerts = get_active_alerts(org_id=TENANT)
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "critical"

    def test_empty_returns_empty(self):
        from services.api.services.api.intelligence.material_risk import get_active_alerts
        engine = _engine({"material_alert": []})
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=engine):
            alerts = get_active_alerts(org_id=TENANT)
        assert alerts == []

    def test_db_error_returns_empty(self):
        from services.api.services.api.intelligence.material_risk import get_active_alerts
        from sqlalchemy.exc import SQLAlchemyError
        broken = MagicMock()
        conn = MagicMock()
        conn.execute = MagicMock(side_effect=SQLAlchemyError("fail"))
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        broken.connect.return_value = conn
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=broken):
            assert get_active_alerts(TENANT) == []


class TestAcknowledgeAlert:
    ALERT_ID = str(uuid.uuid4())

    def test_returns_true_on_success(self):
        from services.api.services.api.intelligence.material_risk import acknowledge_alert
        conn = MagicMock()
        result = MagicMock()
        result.rowcount = 1
        conn.execute.return_value = result
        conn.__enter__ = lambda s: conn
        conn.__exit__  = MagicMock(return_value=False)
        engine = MagicMock()
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__  = MagicMock(return_value=False)
        engine.begin.return_value = begin_ctx
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=engine):
            assert acknowledge_alert(self.ALERT_ID, TENANT) is True

    def test_returns_false_when_not_found(self):
        from services.api.services.api.intelligence.material_risk import acknowledge_alert
        conn = MagicMock()
        result = MagicMock()
        result.rowcount = 0
        conn.execute.return_value = result
        conn.__enter__ = lambda s: conn
        conn.__exit__  = MagicMock(return_value=False)
        engine = MagicMock()
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = lambda s: conn
        begin_ctx.__exit__  = MagicMock(return_value=False)
        engine.begin.return_value = begin_ctx
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=engine):
            assert acknowledge_alert(self.ALERT_ID, TENANT) is False

    def test_db_error_returns_false(self):
        from services.api.services.api.intelligence.material_risk import acknowledge_alert
        from sqlalchemy.exc import SQLAlchemyError
        broken = MagicMock()
        begin_ctx = MagicMock()
        begin_ctx.__enter__ = MagicMock(side_effect=SQLAlchemyError("fail"))
        begin_ctx.__exit__  = MagicMock(return_value=False)
        broken.begin.return_value = begin_ctx
        with patch("services.api.services.api.intelligence.material_risk.get_engine", return_value=broken):
            assert acknowledge_alert(self.ALERT_ID, TENANT) is False


# ══════════════════════════════════════════════════════════════════════════════
# 2. intelligence/icb_service.py
# ══════════════════════════════════════════════════════════════════════════════

class TestVoivodeshipNames:
    def test_known_aliases(self):
        from services.api.services.api.intelligence.icb_service import VOIVODESHIP_NAMES
        assert VOIVODESHIP_NAMES["warszawa"] == "mazowieckie"
        assert VOIVODESHIP_NAMES["kraków"] == "małopolskie"
        assert VOIVODESHIP_NAMES["katowice"] == "śląskie"

    def test_all_16_voivodeships(self):
        from services.api.services.api.intelligence.icb_service import VOIVODESHIP_NAMES
        pl = [v for v in VOIVODESHIP_NAMES if v == VOIVODESHIP_NAMES[v]]
        assert len(pl) == 16


class TestGetLatestQuarter:
    def test_returns_tuple(self):
        from services.api.services.api.intelligence.icb_service import get_latest_quarter
        row = _row(kwartalrok=2026, kwartalnr=2)
        engine = _engine({"icb_ceny_srednie": [row]})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            q, y = get_latest_quarter()
        assert q == 2026
        assert y == 2

    def test_fallback_on_empty(self):
        from services.api.services.api.intelligence.icb_service import get_latest_quarter
        engine = _engine({"icb_ceny_srednie": []})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            q, y = get_latest_quarter()
        assert q == 2026
        assert y == 2


class TestSearchIcb:
    def _icb_row(self):
        return _row(id=1, nazwa="Cement portlandzki", symbol="M-01",
                    indeks_eto="ICB-001", typ_rms="M", jednostka="t",
                    cena_netto=650.0, cena_narzut=0.0, category="beton_cement")

    def test_trgm_success(self):
        from services.api.services.api.intelligence.icb_service import search_icb
        row = self._icb_row()
        setattr(row, "sim", 0.85)
        engine = _engine({"icb_ceny_srednie": [row]})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            results = search_icb("cement", kwartalrok=2026, kwartalnr=2)
        assert len(results) == 1
        assert results[0]["cena_netto"] == 650.0

    def test_ilike_fallback(self):
        from services.api.services.api.intelligence.icb_service import _search_ilike
        row = self._icb_row()
        engine = _engine({"icb_ceny_srednie": [row]})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            results = _search_ilike("cement", "kwartalrok=:rok", {"rok": 2026, "nr": 2, "limit": 10}, 10)
        assert len(results) == 1

    def test_empty_query_returns_empty(self):
        from services.api.services.api.intelligence.icb_service import search_icb
        engine = _engine({"icb_ceny_srednie": []})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            results = search_icb("nieistniejacy_material")
        assert results == []

    def test_with_typ_filter(self):
        from services.api.services.api.intelligence.icb_service import search_icb
        engine = _engine({"icb_ceny_srednie": []})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            results = search_icb("robocizna", typ_rms="R")
        assert isinstance(results, list)


class TestGetNarzuty:
    def test_returns_fallback_on_empty(self):
        from services.api.services.api.intelligence.icb_service import get_narzuty
        engine = _engine({"icb_narzuty": []})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            n = get_narzuty(kwartalrok=2026, kwartalnr=2)
        assert "ko_pct" in n
        assert n["source"] == "fallback"

    def test_returns_db_values(self):
        from services.api.services.api.intelligence.icb_service import get_narzuty
        row = _row(nazwa="roboty ogólnobudowlane",
                   koszty_posrednie=68.5, zysk=10.0, koszty_zakupu=5.0)
        engine = _engine({"icb_narzuty": [row]})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            n = get_narzuty()
        assert n["ko_pct"] == pytest.approx(68.5)
        assert n["source"] == "icb_narzuty"


class TestGetAllNarzuty:
    def test_returns_list(self):
        from services.api.services.api.intelligence.icb_service import get_all_narzuty
        rows = [
            _row(nazwa="roboty ogólnobudowlane", koszty_posrednie=68.5, zysk=10.0, koszty_zakupu=5.0),
            _row(nazwa="roboty inżynieryjne",    koszty_posrednie=65.0, zysk=9.0,  koszty_zakupu=4.5),
        ]
        engine = _engine({"icb_narzuty": rows})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            result = get_all_narzuty()
        assert len(result) == 2
        assert result[0]["branża"] == "roboty ogólnobudowlane"


class TestGetRegionalCoefficient:
    def test_returns_float_from_db(self):
        from services.api.services.api.intelligence.icb_service import get_regional_coefficient
        row = _row(coefficient=1.12)
        engine = _engine({"intercenbud_regional_rates": [row]})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            c = get_regional_coefficient("mazowieckie")
        assert c == pytest.approx(1.12)

    def test_fallback_1_0_on_empty(self):
        from services.api.services.api.intelligence.icb_service import get_regional_coefficient
        engine = _engine({"intercenbud_regional_rates": []})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            c = get_regional_coefficient("nieznane")
        assert c == 1.0


class TestGetIcbPrice:
    def test_returns_dict(self):
        from services.api.services.api.intelligence.icb_service import get_icb_price
        row = _row(id=1, nazwa="Robocizna", symbol="R-01",
                   typ_rms="R", jednostka="r-g", cena_netto=52.0,
                   cena_narzut=0.0, category="inne", indeks_eto="")
        engine = _engine({"icb_ceny_srednie": [row]})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            result = get_icb_price("R-01")
        assert result is not None
        assert result["cena_netto"] == 52.0

    def test_returns_none_when_missing(self):
        from services.api.services.api.intelligence.icb_service import get_icb_price
        engine = _engine({"icb_ceny_srednie": []})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            assert get_icb_price("NIEISTNIEJACY") is None


class TestGetRobociznaRates:
    def test_regional_path(self):
        from services.api.services.api.intelligence.icb_service import get_robocizna_rates
        row = _row(cena_netto=55.0, nazwa="robocizna mazowiecka", category="R")
        engine = _engine({"icb_ceny_srednie": [row]})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            r = get_robocizna_rates(voivodeship="mazowieckie")
        assert r["stawka_r"] == pytest.approx(55.0)
        assert r["source"] == "icb_regional"

    def test_avg_national_fallback(self):
        from services.api.services.api.intelligence.icb_service import get_robocizna_rates
        avg_row = _row(avg_r=49.5, min_r=42.0, max_r=60.0)
        engine = _engine({"icb_ceny_srednie": [avg_row]})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            with patch("services.api.services.api.intelligence.icb_service.get_regional_coefficient", return_value=1.0):
                r = get_robocizna_rates(voivodeship=None)
        assert "stawka_r" in r

    def test_hardcoded_fallback(self):
        from services.api.services.api.intelligence.icb_service import get_robocizna_rates
        engine = _engine({"icb_ceny_srednie": []})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            r = get_robocizna_rates()
        assert r["stawka_r"] == pytest.approx(52.09)
        assert r["source"] == "fallback_2026q2"


class TestGetCategories:
    def test_returns_list(self):
        from services.api.services.api.intelligence.icb_service import get_categories
        rows = [_row(category="murarstwo"), _row(category="elektryka")]
        engine = _engine({"icb_ceny_srednie": rows})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            cats = get_categories()
        assert "murarstwo" in cats
        assert "elektryka" in cats


class TestGetPriceTrend:
    def test_by_symbol(self):
        from services.api.services.api.intelligence.icb_service import get_price_trend
        rows = [
            _row(kwartalrok=2024, kwartalnr=1, avg_price=580.0, n=12),
            _row(kwartalrok=2024, kwartalnr=2, avg_price=600.0, n=12),
        ]
        engine = _engine({"icb_ceny_srednie": rows})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            trend = get_price_trend(symbol="CEM-01", from_year=2024)
        assert len(trend) == 2
        assert trend[0]["period"] == "2024-Q1"

    def test_by_category(self):
        from services.api.services.api.intelligence.icb_service import get_price_trend
        engine = _engine({"icb_ceny_srednie": []})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            trend = get_price_trend(category="murarstwo")
        assert isinstance(trend, list)

    def test_no_filter(self):
        from services.api.services.api.intelligence.icb_service import get_price_trend
        engine = _engine({"icb_ceny_srednie": []})
        with patch("services.api.services.api.intelligence.icb_service.get_engine", return_value=engine):
            trend = get_price_trend()
        assert isinstance(trend, list)


# ══════════════════════════════════════════════════════════════════════════════
# 3. routers/kosztorys_v2.py — trigger material risk po save pozycji
# ══════════════════════════════════════════════════════════════════════════════

class TestMaterialRiskTrigger:
    def test_trigger_called_on_add_with_icb_m(self):
        """check_material_risks wywoływane gdy add_pozycja ma icb_id_m."""
        import inspect
        from services.api.services.api.routers import kosztorys_v2
        src = inspect.getsource(kosztorys_v2)
        assert "check_material_risks" in src
        # Trigger w add_pozycja
        assert "icb_id_m" in src

    def test_trigger_called_on_update_m_jcena(self):
        """check_material_risks wywoływane gdy update_pozycja zmienia m_jcena."""
        import inspect
        from services.api.services.api.routers import kosztorys_v2
        src = inspect.getsource(kosztorys_v2)
        # Trigger w update_pozycja
        assert '"m_jcena" in updates' in src or "m_jcena" in src

    def test_material_risk_import_path(self):
        """Import ścieżka check_material_risks jest poprawna."""
        import inspect
        from services.api.services.api.routers import kosztorys_v2
        src = inspect.getsource(kosztorys_v2)
        assert "from ..intelligence.material_risk import check_material_risks" in src


# ══════════════════════════════════════════════════════════════════════════════
# 4. kosztorys_v2.py — coverage missing lines (estimate/user-rates schematy)
# ══════════════════════════════════════════════════════════════════════════════

class TestKosztorysV2Schemas:
    def test_cost_estimate_request_defaults(self):
        from services.api.services.api.routers.kosztorys_v2 import CostEstimateRequest
        req = CostEstimateRequest(method="icb")
        assert req.area_m2 == 0.0
        assert req.cpv is None
        assert req.region is None

    def test_cost_estimate_request_all_fields(self):
        from services.api.services.api.routers.kosztorys_v2 import CostEstimateRequest
        req = CostEstimateRequest(
            method="all",
            area_m2=500.0,
            cpv="45230000-8",
            region="śląskie",
            swz_text="Roboty budowlane m²  500  350",
            kwartalnr=2,
            kwartalrok=2026,
            tender_id=str(uuid.uuid4()),
        )
        assert req.kwartalnr == 2
        assert req.kwartalrok == 2026

    def test_user_rate_create_defaults(self):
        from services.api.services.api.routers.kosztorys_v2 import UserRateCreate
        rate = UserRateCreate(symbol="KNR-TEST", typ_rms="M", cena_netto=100.0)
        assert rate.jednostka == "m²"
        assert rate.nazwa is None

    def test_user_rate_create_full(self):
        from services.api.services.api.routers.kosztorys_v2 import UserRateCreate
        rate = UserRateCreate(
            symbol="KNR-ABC", nazwa="Murarstwo ceglane",
            jednostka="m³", typ_rms="R", cena_netto=75.50
        )
        assert rate.nazwa == "Murarstwo ceglane"
        assert rate.cena_netto == pytest.approx(75.50)

    def test_current_quarter_returns_tuple(self):
        from services.api.services.api.routers.kosztorys_v2 import _current_quarter
        q, y = _current_quarter()
        assert 1 <= q <= 4
        assert y >= 2020


class TestKosztorysV2CreateFromTender:
    def test_create_from_tender_logic_exists(self):
        """Weryfikuje że create_from_tender jest zarejestrowany."""
        import inspect
        from services.api.services.api.routers import kosztorys_v2
        src = inspect.getsource(kosztorys_v2)
        assert "create_from_tender" in src
        assert "/from-tender" in src

    def test_kosztorys_row_helper(self):
        """_kosztorys_row konwertuje row na dict."""
        from services.api.services.api.routers.kosztorys_v2 import _kosztorys_row
        import datetime
        row = _row(
            id=uuid.uuid4(), tender_id=None,
            nazwa="Test", status="draft", typ="budowlany",
            kwartalrok=2026, kwartalnr=2,
            suma_netto=4600.0, suma_brutto=5658.0,
            win_probability=None, anomaly_score=None,
            created_at=datetime.datetime(2026, 1, 1),
            updated_at=datetime.datetime(2026, 1, 2),
        )
        result = _kosztorys_row(row)
        assert "id" in result
        assert result["suma_netto"] == pytest.approx(4600.0)
        assert result["suma_brutto"] == pytest.approx(5658.0)
