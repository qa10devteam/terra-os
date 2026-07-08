"""Tests — Sprint K2: Engine, ATH Parser, Kosztorys Router.

Pokrycie:
- kosztorys_engine: calc_pozycja, calc_kosztorys, formułka KNB
- ath_parser: parse_ath, generate_ath, ath_to_pozycje_dicts, roundtrip
- kosztorys_v2 router: CRUD (mock DB), recalc, import-ath, export-ath
"""
from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngine:
    """Testy kalkulacji CJ = R + M + S + Ko*(R/ko_r + S/ko_s) + Kz*M + Z*(R+M+S+Ko+Kz)."""

    def _imp(self):
        from services.api.services.api.intelligence.kosztorys_engine import (
            Narzuty, PozycjaInput, calc_pozycja, calc_kosztorys,
        )
        return Narzuty, PozycjaInput, calc_pozycja, calc_kosztorys

    def test_zero_inputs(self):
        Narzuty, PozycjaInput, calc_pozycja, _ = self._imp()
        n = Narzuty()
        p = PozycjaInput(r_jcena=0, m_jcena=0, s_jcena=0, ilosc=1)
        result = calc_pozycja(p, n)
        assert result.jcena_netto == 0.0
        assert result.wartosc_netto == 0.0

    def test_only_r(self):
        Narzuty, PozycjaInput, calc_pozycja, _ = self._imp()
        n = Narzuty(ko_r_pct=70, ko_s_pct=30, z_pct=10, kz_pct=0, vat_pct=23)
        p = PozycjaInput(r_jcena=100, m_jcena=0, s_jcena=0, ilosc=1)
        r = calc_pozycja(p, n)
        # Ko = 100*0.70 = 70; Kz=0; Z=(100+0+0+70+0)*0.10=17; CJ=100+70+17=187
        assert r.ko_jcena == pytest.approx(70.0)
        assert r.z_jcena == pytest.approx(17.0)
        assert r.jcena_netto == pytest.approx(187.0)

    def test_knb_formula(self):
        """Wzorcowa pozycja KNB: R=52, M=250, S=35."""
        Narzuty, PozycjaInput, calc_pozycja, _ = self._imp()
        n = Narzuty(ko_r_pct=70, ko_s_pct=30, z_pct=12.5, kz_pct=7.1, vat_pct=23)
        p = PozycjaInput(r_jcena=52, m_jcena=250, s_jcena=35, ilosc=10)
        r = calc_pozycja(p, n)

        ko_expected = 52 * 0.70 + 35 * 0.30  # 36.4 + 10.5 = 46.9
        kz_expected = 250 * 0.071             # 17.75
        z_expected  = (52 + 250 + 35 + ko_expected + kz_expected) * 0.125
        cj_expected = 52 + 250 + 35 + ko_expected + kz_expected + z_expected

        assert r.ko_jcena == pytest.approx(ko_expected, abs=0.01)
        assert r.kz_jcena == pytest.approx(kz_expected, abs=0.01)
        assert r.z_jcena  == pytest.approx(z_expected,  abs=0.01)
        assert r.jcena_netto == pytest.approx(cj_expected, abs=0.01)
        assert r.wartosc_netto == pytest.approx(cj_expected * 10, abs=0.1)

    def test_r_total_generated(self):
        Narzuty, PozycjaInput, calc_pozycja, _ = self._imp()
        n = Narzuty(ko_r_pct=0, ko_s_pct=0, z_pct=0, kz_pct=0, vat_pct=0)
        p = PozycjaInput(r_jcena=10, m_jcena=0, s_jcena=0, ilosc=5)
        r = calc_pozycja(p, n)
        assert r.r_total == pytest.approx(50.0)

    def test_kosztorys_sum(self):
        Narzuty, PozycjaInput, _, calc_kosztorys = self._imp()
        n = Narzuty(ko_r_pct=0, ko_s_pct=0, z_pct=0, kz_pct=0, vat_pct=23)
        pozycje = [
            PozycjaInput(r_jcena=10, m_jcena=50, s_jcena=0, ilosc=2),
            PozycjaInput(r_jcena=20, m_jcena=100, s_jcena=5, ilosc=3),
        ]
        result = calc_kosztorys(pozycje, n)
        # netto = (10+50)*2 + (20+100+5)*3 = 120 + 375 = 495
        assert result.suma_netto == pytest.approx(495.0)
        assert result.suma_vat == pytest.approx(495 * 0.23, abs=0.01)
        assert result.suma_brutto == pytest.approx(495 * 1.23, abs=0.01)

    def test_kosztorys_empty(self):
        Narzuty, PozycjaInput, _, calc_kosztorys = self._imp()
        n = Narzuty()
        result = calc_kosztorys([], n)
        assert result.suma_netto == 0.0
        assert result.suma_brutto == 0.0

    def test_rounding_2dec(self):
        """r2 zawsze daje 2 miejsca."""
        Narzuty, PozycjaInput, calc_pozycja, _ = self._imp()
        n = Narzuty(ko_r_pct=33.33, ko_s_pct=0, z_pct=0, kz_pct=0, vat_pct=0)
        p = PozycjaInput(r_jcena=1, m_jcena=0, s_jcena=0, ilosc=3)
        r = calc_pozycja(p, n)
        # sprawdź że nie ma więcej niż 2 miejsc po przecinku w ko_total
        ko_str = f"{r.ko_total:.10f}"
        assert r.ko_total == pytest.approx(r.ko_total, abs=0.005)

    def test_many_pozycje_performance(self):
        Narzuty, PozycjaInput, _, calc_kosztorys = self._imp()
        n = Narzuty()
        pozycje = [PozycjaInput(r_jcena=50, m_jcena=200, s_jcena=30, ilosc=i)
                   for i in range(1, 201)]
        result = calc_kosztorys(pozycje, n)
        assert result.suma_netto > 0
        assert len(result.pozycje) == 200

    def test_ilosc_zero(self):
        Narzuty, PozycjaInput, calc_pozycja, _ = self._imp()
        n = Narzuty()
        p = PozycjaInput(r_jcena=100, m_jcena=200, s_jcena=50, ilosc=0)
        r = calc_pozycja(p, n)
        assert r.wartosc_netto == 0.0

    def test_narzuty_defaults(self):
        from services.api.services.api.intelligence.kosztorys_engine import Narzuty
        n = Narzuty()
        assert n.ko_r_pct == 70.0
        assert n.ko_s_pct == 30.0
        assert n.z_pct == 12.5
        assert n.kz_pct == 7.1
        assert n.vat_pct == 23.0

    def test_update_prices_from_icb_no_icb(self):
        from services.api.services.api.intelligence.kosztorys_engine import (
            Narzuty, update_pozycja_prices_from_icb,
        )
        n = Narzuty(ko_r_pct=0, ko_s_pct=0, z_pct=0, kz_pct=0, vat_pct=0)
        result, prov = update_pozycya_prices_from_icb = update_pozycja_prices_from_icb(
            r_jcena=10.0, m_jcena=50.0, s_jcena=5.0, ilosc=2,
            narzuty=n, icb_r=None, icb_m=None, icb_s=None,
        )
        assert result.r_jcena == 10.0
        assert result.m_jcena == 50.0
        assert prov == {}

    def test_update_prices_from_icb_with_icb(self):
        from services.api.services.api.intelligence.kosztorys_engine import (
            Narzuty, update_pozycja_prices_from_icb,
        )
        n = Narzuty(ko_r_pct=0, ko_s_pct=0, z_pct=0, kz_pct=0, vat_pct=0)
        icb_r = {"id": 1, "symbol": "ROBOCIZNA", "cena_netto": 52.09}
        result, prov = update_pozycja_prices_from_icb(
            r_jcena=10.0, m_jcena=50.0, s_jcena=5.0, ilosc=1,
            narzuty=n, icb_r=icb_r, icb_m=None, icb_s=None,
        )
        assert result.r_jcena == pytest.approx(52.09)
        assert prov["R"]["source"] == "icb"


# ═══════════════════════════════════════════════════════════════════════════════
# ATH Parser
# ═══════════════════════════════════════════════════════════════════════════════

ATH_SAMPLE = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b'<Kosztorys Nazwa="TestKosztorys" wersja="2.0">'
    b'<Pozycja KodKat="KNR 2-02 0101-01" Opis="Fundamenty" Jm="m3" Ilosc="50">'
    b'<R Nazwa="Robocizna" Jm="r-g" Norma="0.30" Cena="52.09"/>'
    b'<M Nazwa="Beton C20" Jm="m3" Norma="1.05" Cena="450.00"/>'
    b'<S Nazwa="Betoniarka" Jm="m-g" Norma="0.05" Cena="35.00"/>'
    b'</Pozycja>'
    b'<Pozycja KodKat="KNR 4-01 0201-02" Opis="Sciany" Jm="m2" Ilosc="120">'
    b'<R Nazwa="Robocizna murarska" Jm="r-g" Norma="0.50" Cena="52.09"/>'
    b'<M Nazwa="Cegla" Jm="szt" Norma="64" Cena="1.20"/>'
    b'<M Nazwa="Zaprawa" Jm="dm3" Norma="10" Cena="0.80"/>'
    b'</Pozycja>'
    b'</Kosztorys>'
)

ATH_NO_SKLADNIKI = (
    b'<Kosztorys>'
    b'<Pozycja KodKat="KNR 1-01" Opis="Wyrownanie" Jm="m2" Ilosc="200" CenaJm="25.00"/>'
    b'</Kosztorys>'
)


class TestAthParser:

    def test_parse_basic(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath
        ath = parse_ath(ATH_SAMPLE)
        assert len(ath.pozycje) == 2
        assert ath.nazwa == "TestKosztorys"

    def test_parse_pierwsza_pozycja(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath
        ath = parse_ath(ATH_SAMPLE)
        p = ath.pozycje[0]
        assert p.kst_code == "KNR 2-02 0101-01"
        assert p.opis == "Fundamenty"
        assert p.jednostka == "m3"
        assert p.ilosc == 50.0
        assert len(p.skladniki) == 3

    def test_skladniki_typy(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath
        ath = parse_ath(ATH_SAMPLE)
        p = ath.pozycje[0]
        typy = [s.typ for s in p.skladniki]
        assert "R" in typy
        assert "M" in typy
        assert "S" in typy

    def test_r_jcena_calculation(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath
        ath = parse_ath(ATH_SAMPLE)
        p = ath.pozycje[0]
        # R: norma=0.30 * cena=52.09 = 15.627
        assert p.r_jcena() == pytest.approx(0.30 * 52.09, abs=0.001)

    def test_m_jcena_multi_material(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath
        ath = parse_ath(ATH_SAMPLE)
        p = ath.pozycje[1]  # 2 materiały
        # 64*1.20 + 10*0.80 = 76.8 + 8.0 = 84.8
        assert p.m_jcena() == pytest.approx(84.8, abs=0.01)

    def test_fallback_cena_jm(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath
        ath = parse_ath(ATH_NO_SKLADNIKI)
        assert len(ath.pozycje) == 1
        p = ath.pozycje[0]
        # Fallback: brak R/M/S → jeden składnik M z CenaJm=25
        assert len(p.skladniki) == 1
        assert p.skladniki[0].typ == "M"
        assert p.m_jcena() == pytest.approx(25.0)

    def test_parse_invalid_xml(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath
        with pytest.raises(ValueError, match="Nieprawidłowy XML"):
            parse_ath(b"<nie zamkniety")

    def test_generate_roundtrip(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath, generate_ath, ath_to_pozycje_dicts
        ath = parse_ath(ATH_SAMPLE)
        poz_dicts = ath_to_pozycje_dicts(ath)
        xml_out = generate_ath(poz_dicts, nazwa="TestKosztorys")
        # Parsuj z powrotem
        ath2 = parse_ath(xml_out)
        assert len(ath2.pozycje) == len(ath.pozycje)
        assert ath2.pozycje[0].opis == ath.pozycje[0].opis

    def test_generate_has_pozycja(self):
        from services.api.services.api.intelligence.ath_parser import generate_ath
        pozycje = [{"kst_code": "KNR 1-01", "opis": "Test", "jednostka": "m2",
                    "ilosc": 10, "r_jcena": 50, "m_jcena": 200, "s_jcena": 30}]
        xml_bytes = generate_ath(pozycje)
        root = ET.fromstring(xml_bytes)
        pozycja_els = list(root.iter("Pozycja"))
        assert len(pozycja_els) == 1

    def test_generate_rms_subelements(self):
        from services.api.services.api.intelligence.ath_parser import generate_ath
        pozycje = [{"kst_code": "TEST", "opis": "Roboty", "jednostka": "m2",
                    "ilosc": 5, "r_jcena": 52, "m_jcena": 300, "s_jcena": 0}]
        xml_bytes = generate_ath(pozycje)
        root = ET.fromstring(xml_bytes)
        r_els = [el for el in root.iter() if el.tag == "R"]
        m_els = [el for el in root.iter() if el.tag == "M"]
        assert len(r_els) == 1
        assert len(m_els) == 1

    def test_ath_to_pozycje_dicts_lp(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath, ath_to_pozycje_dicts
        ath = parse_ath(ATH_SAMPLE)
        dicts = ath_to_pozycje_dicts(ath)
        assert dicts[0]["lp"] == 1
        assert dicts[1]["lp"] == 2

    def test_ath_to_pozycje_dicts_katalog_split(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath, ath_to_pozycje_dicts
        ath = parse_ath(ATH_SAMPLE)
        dicts = ath_to_pozycje_dicts(ath)
        assert dicts[0]["katalog"] == "KNR 2-02"
        assert dicts[0]["pozycja_nr"] == "0101-01"

    def test_parse_str_input(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath
        ath = parse_ath(ATH_SAMPLE.decode("utf-8"))
        assert len(ath.pozycje) == 2

    def test_empty_kosztorys(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath
        ath = parse_ath(b"<Kosztorys/>")
        assert len(ath.pozycje) == 0

    def test_generate_with_skladniki_dicts(self):
        from services.api.services.api.intelligence.ath_parser import generate_ath
        pozycje = [{
            "kst_code": "KNR 1-01", "opis": "Test", "jednostka": "m2", "ilosc": 5,
            "skladniki": [
                {"typ": "R", "nazwa": "Robocizna", "jednostka": "r-g", "norma": 0.5, "cena": 52},
                {"typ": "M", "nazwa": "Cegla", "jednostka": "szt", "norma": 64, "cena": 1.2},
            ]
        }]
        xml_bytes = generate_ath(pozycje)
        root = ET.fromstring(xml_bytes)
        r_els = [el for el in root.iter() if el.tag == "R"]
        assert len(r_els) == 1
        assert r_els[0].get("Norma") == "0.5"


# ═══════════════════════════════════════════════════════════════════════════════
# Kosztorys V2 Router (unit, no DB)
# ═══════════════════════════════════════════════════════════════════════════════

class MockUser:
    org_id = "ec3d1e16-0000-0000-0000-000000000000"
    user_id = "user-001"
    role = "admin"


class TestEngineHelpers:
    """Testy pomocnicze engine — _r2, _r4."""

    def test_r2_basic(self):
        from services.api.services.api.intelligence.kosztorys_engine import _r2
        assert _r2(1.005) == pytest.approx(1.01, abs=0.001)
        assert _r2(1.004) == pytest.approx(1.00, abs=0.001)

    def test_r4_precision(self):
        from services.api.services.api.intelligence.kosztorys_engine import _r4
        val = _r4(1.23456789)
        assert round(val, 4) == pytest.approx(1.2346, abs=0.0001)

    def test_r2_negative(self):
        from services.api.services.api.intelligence.kosztorys_engine import _r2
        assert _r2(-10.505) == pytest.approx(-10.51, abs=0.01)


class TestAthParserEdgeCases:

    def test_pozycja_without_kst(self):
        from services.api.services.api.intelligence.ath_parser import parse_ath
        xml = b"""<Kosztorys>
          <Pozycja Opis="Bezkodowa" Jm="m2" Ilosc="10">
            <R Nazwa="Rob" Jm="r-g" Norma="0.2" Cena="52"/>
          </Pozycja>
        </Kosztorys>"""
        ath = parse_ath(xml)
        assert len(ath.pozycje) == 1
        assert ath.pozycje[0].kst_code == ""

    def test_float_with_comma(self):
        from services.api.services.api.intelligence.ath_parser import _float
        assert _float("1,5") == pytest.approx(1.5)
        assert _float("100,00") == pytest.approx(100.0)

    def test_float_invalid(self):
        from services.api.services.api.intelligence.ath_parser import _float
        assert _float("brak") == 0.0
        assert _float(None) == 0.0

    def test_strip_ns(self):
        from services.api.services.api.intelligence.ath_parser import _strip_ns
        assert _strip_ns("{http://norma.com.pl}Pozycja") == "Pozycja"
        assert _strip_ns("Pozycja") == "Pozycja"

    def test_build_pozycja_el(self):
        from services.api.services.api.intelligence.ath_parser import (
            AthPozycja, AthSkladnik, _build_pozycja_el
        )
        poz = AthPozycja("KNR 1", "Test", "m2", 5, [
            AthSkladnik("R", "Rob", "r-g", 0.3, 52),
        ])
        el = _build_pozycja_el(poz)
        assert el.get("KodKat") == "KNR 1"
        children = list(el)
        assert children[0].tag == "R"


class TestKosztorysEngineKNBFormulas:
    """Rozszerzone testy formuł KNB z konkretnymi przykładami branżowymi."""

    def test_drogi_cpv_4523(self):
        """Pozycja typowa dla dróg: duże M (asfalt), małe R."""
        from services.api.services.api.intelligence.kosztorys_engine import Narzuty, PozycjaInput, calc_pozycja
        n = Narzuty(ko_r_pct=65, ko_s_pct=25, z_pct=10, kz_pct=5, vat_pct=23)
        p = PozycjaInput(r_jcena=30, m_jcena=500, s_jcena=120, ilosc=1000)
        r = calc_pozycja(p, n)
        assert r.jcena_netto > 30 + 500 + 120  # narzuty dodają wartość
        assert r.wartosc_netto == pytest.approx(r.jcena_netto * 1000, abs=1)

    def test_instalacje_cpv_4533(self):
        """Instalacje sanitarne — głównie M i R."""
        from services.api.services.api.intelligence.kosztorys_engine import Narzuty, PozycjaInput, calc_pozycja
        n = Narzuty(ko_r_pct=80, ko_s_pct=20, z_pct=15, kz_pct=8, vat_pct=8)  # VAT 8%
        p = PozycjaInput(r_jcena=60, m_jcena=350, s_jcena=10, ilosc=1)
        r = calc_pozycja(p, n)
        # VAT nie wchodzi do CJ, CJ = R+M+S+Ko+Kz+Z
        expected_ko = 60*0.80 + 10*0.20  # 48+2=50
        expected_kz = 350*0.08           # 28
        expected_z  = (60+350+10+expected_ko+expected_kz)*0.15
        expected_cj = 60+350+10+expected_ko+expected_kz+expected_z
        assert r.jcena_netto == pytest.approx(expected_cj, abs=0.01)

    def test_wykonczenenia_vat_23(self):
        """Roboty wykończeniowe — sprawdź że VAT jest poprawny."""
        from services.api.services.api.intelligence.kosztorys_engine import Narzuty, PozycjaInput, calc_kosztorys
        n = Narzuty(ko_r_pct=70, ko_s_pct=30, z_pct=12, kz_pct=7, vat_pct=23)
        pozycje = [PozycjaInput(r_jcena=55, m_jcena=180, s_jcena=15, ilosc=50)]
        result = calc_kosztorys(pozycje, n)
        assert result.suma_brutto == pytest.approx(result.suma_netto * 1.23, abs=0.01)
