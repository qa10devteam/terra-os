"""Kosztorys Engine — kalkulacja CJ = R + M + S + Ko*(R+S) + Z*(R+M+S+Ko) + Kz*M.

Implementacja zgodna z Normą PRO / KNB (Katalog Nakładów Budowlanych).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


# ─── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Narzuty:
    """Narzuty kosztorysowe (%)."""
    ko_r_pct: float = 70.0   # koszty pośrednie od R
    ko_s_pct: float = 30.0   # koszty pośrednie od S
    z_pct:    float = 12.5   # zysk od (R+M+S+Ko)
    kz_pct:   float = 7.1    # koszty zakupu materiałów od M
    vat_pct:  float = 23.0


@dataclass
class PozycjaInput:
    """Dane wejściowe pozycji kosztorysowej."""
    r_jcena: float = 0.0    # stawka robocizny [zł/r-g]
    m_jcena: float = 0.0    # cena materiału [zł/jm]
    s_jcena: float = 0.0    # stawka sprzętu [zł/m-g]
    ilosc:   float = 1.0


@dataclass
class PozycjaResult:
    """Wynik kalkulacji jednej pozycji."""
    r_jcena:      float
    m_jcena:      float
    s_jcena:      float
    ilosc:        float
    # Narzuty per jednostkę
    ko_jcena:     float = 0.0
    z_jcena:      float = 0.0
    kz_jcena:     float = 0.0
    # Cena jednostkowa netto
    jcena_netto:  float = 0.0
    # Wartości
    r_total:      float = 0.0
    m_total:      float = 0.0
    s_total:      float = 0.0
    ko_total:     float = 0.0
    z_total:      float = 0.0
    kz_total:     float = 0.0
    wartosc_netto: float = 0.0


@dataclass
class KosztorysResult:
    """Wynik kalkulacji całego kosztorysu."""
    suma_r:      float = 0.0
    suma_m:      float = 0.0
    suma_s:      float = 0.0
    suma_ko:     float = 0.0
    suma_z:      float = 0.0
    suma_kz:     float = 0.0
    suma_netto:  float = 0.0
    suma_vat:    float = 0.0
    suma_brutto: float = 0.0
    pozycje:     list[PozycjaResult] = field(default_factory=list)


# ─── Kalkulacja pozycji ────────────────────────────────────────────────────────

def calc_pozycja(poz: PozycjaInput, narzuty: Narzuty) -> PozycjaResult:
    """Oblicz ceny jednostkowe i wartości dla jednej pozycji.

    Formuła KNB:
        Ko = R * ko_r_pct/100 + S * ko_s_pct/100
        Kz = M * kz_pct/100
        Z  = (R + M + S + Ko + Kz) * z_pct/100
        CJ = R + M + S + Ko + Kz + Z
    """
    r = poz.r_jcena
    m = poz.m_jcena
    s = poz.s_jcena
    n = narzuty
    q = poz.ilosc

    ko = _r2(r * n.ko_r_pct / 100 + s * n.ko_s_pct / 100)
    kz = _r2(m * n.kz_pct / 100)
    z  = _r2((r + m + s + ko + kz) * n.z_pct / 100)
    cj = _r4(r + m + s + ko + kz + z)

    return PozycjaResult(
        r_jcena=r, m_jcena=m, s_jcena=s, ilosc=q,
        ko_jcena=ko, z_jcena=z, kz_jcena=kz,
        jcena_netto=cj,
        r_total=_r2(r * q),
        m_total=_r2(m * q),
        s_total=_r2(s * q),
        ko_total=_r2(ko * q),
        z_total=_r2(z * q),
        kz_total=_r2(kz * q),
        wartosc_netto=_r2(cj * q),
    )


def calc_kosztorys(pozycje: list[PozycjaInput], narzuty: Narzuty) -> KosztorysResult:
    """Przelicz cały kosztorys — suma R/M/S/Ko/Z/Kz/netto/vat/brutto."""
    results = [calc_pozycja(p, narzuty) for p in pozycje]

    suma_r   = _r2(sum(p.r_total   for p in results))
    suma_m   = _r2(sum(p.m_total   for p in results))
    suma_s   = _r2(sum(p.s_total   for p in results))
    suma_ko  = _r2(sum(p.ko_total  for p in results))
    suma_z   = _r2(sum(p.z_total   for p in results))
    suma_kz  = _r2(sum(p.kz_total  for p in results))
    suma_netto = _r2(sum(p.wartosc_netto for p in results))
    suma_vat   = _r2(suma_netto * narzuty.vat_pct / 100)
    suma_brutto = _r2(suma_netto + suma_vat)

    return KosztorysResult(
        suma_r=suma_r, suma_m=suma_m, suma_s=suma_s,
        suma_ko=suma_ko, suma_z=suma_z, suma_kz=suma_kz,
        suma_netto=suma_netto, suma_vat=suma_vat, suma_brutto=suma_brutto,
        pozycje=results,
    )


# ─── Aktualizacja cen wg ICB ──────────────────────────────────────────────────

def update_pozycja_prices_from_icb(
    r_jcena: float | None,
    m_jcena: float | None,
    s_jcena: float | None,
    ilosc: float,
    narzuty: Narzuty,
    icb_r: dict | None = None,
    icb_m: dict | None = None,
    icb_s: dict | None = None,
) -> tuple[PozycjaResult, dict]:
    """Zaktualizuj ceny pozycji z ICB i oblicz od nowa.

    Zwraca (PozycjaResult, provenance_dict) gdzie provenance opisuje skąd ceny.
    """
    provenance: dict[str, Any] = {}

    r = icb_r["cena_netto"] if icb_r else (r_jcena or 0.0)
    m = icb_m["cena_netto"] if icb_m else (m_jcena or 0.0)
    s = icb_s["cena_netto"] if icb_s else (s_jcena or 0.0)

    if icb_r:
        provenance["R"] = {"icb_id": icb_r.get("id"), "symbol": icb_r.get("symbol"),
                           "cena": r, "source": "icb"}
    if icb_m:
        provenance["M"] = {"icb_id": icb_m.get("id"), "symbol": icb_m.get("symbol"),
                           "cena": m, "source": "icb"}
    if icb_s:
        provenance["S"] = {"icb_id": icb_s.get("id"), "symbol": icb_s.get("symbol"),
                           "cena": s, "source": "icb"}

    poz = PozycjaInput(r_jcena=r, m_jcena=m, s_jcena=s, ilosc=ilosc)
    return calc_pozycja(poz, narzuty), provenance


# ─── DB recalc (SQLAlchemy) ───────────────────────────────────────────────────

def recalc_kosztorys_db(kosztorys_id: str, tenant_id: str, db_engine: Any) -> KosztorysResult:
    """Przelicz kosztorys z bazy — pobierz pozycje, przelicz, zapisz sumy.

    Używa narzutów z nagłówka kosztorysu.
    """
    import sqlalchemy as sa
    engine = db_engine

    with engine.connect() as conn:
        # Pobierz nagłówek
        hdr = conn.execute(sa.text("""
            SELECT ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct
            FROM kosztorys
            WHERE id = :kid AND tenant_id = :tid
        """), {"kid": kosztorys_id, "tid": tenant_id}).fetchone()

        if not hdr:
            raise ValueError(f"Kosztorys {kosztorys_id} nie znaleziony")

        narzuty = Narzuty(
            ko_r_pct=float(hdr.ko_r_pct),
            ko_s_pct=float(hdr.ko_s_pct),
            z_pct=float(hdr.z_pct),
            kz_pct=float(hdr.kz_pct),
            vat_pct=float(hdr.vat_pct),
        )

        # Pobierz pozycje
        rows = conn.execute(sa.text("""
            SELECT id, r_jcena, m_jcena, s_jcena, ilosc
            FROM kosztorys_pozycja
            WHERE kosztorys_id = :kid AND tenant_id = :tid
            ORDER BY lp
        """), {"kid": kosztorys_id, "tid": tenant_id}).fetchall()

        pozycje_input = [
            PozycjaInput(
                r_jcena=float(r.r_jcena or 0),
                m_jcena=float(r.m_jcena or 0),
                s_jcena=float(r.s_jcena or 0),
                ilosc=float(r.ilosc or 1),
            )
            for r in rows
        ]

    result = calc_kosztorys(pozycje_input, narzuty)

    # Zapisz wyliczone wartości per pozycja i sumy nagłówka
    with engine.begin() as conn:
        for row, poz_result in zip(rows, result.pozycje):
            conn.execute(sa.text("""
                UPDATE kosztorys_pozycja SET
                    ko_total      = :ko,
                    z_total       = :z,
                    kz_total      = :kz,
                    jcena_netto   = :cj,
                    wartosc_netto = :wn,
                    updated_at    = NOW()
                WHERE id = :id AND tenant_id = :tid
            """), {
                "ko": poz_result.ko_total,
                "z":  poz_result.z_total,
                "kz": poz_result.kz_total,
                "cj": poz_result.jcena_netto,
                "wn": poz_result.wartosc_netto,
                "id": str(row.id),
                "tid": tenant_id,
            })

        # Aktualizuj sumy w nagłówku
        conn.execute(sa.text("""
            UPDATE kosztorys SET
                suma_r       = :sr,
                suma_m       = :sm,
                suma_s       = :ss,
                suma_ko      = :sko,
                suma_z       = :sz,
                suma_kz      = :skz,
                suma_netto   = :sn,
                suma_vat     = :sv,
                suma_brutto  = :sb,
                updated_at   = NOW()
            WHERE id = :kid AND tenant_id = :tid
        """), {
            "sr": result.suma_r, "sm": result.suma_m, "ss": result.suma_s,
            "sko": result.suma_ko, "sz": result.suma_z, "skz": result.suma_kz,
            "sn": result.suma_netto, "sv": result.suma_vat, "sb": result.suma_brutto,
            "kid": kosztorys_id, "tid": tenant_id,
        })

    return result


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _r2(val: float) -> float:
    """Zaokrąglij do 2 miejsc po przecinku (bankierskie)."""
    return float(Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _r4(val: float) -> float:
    """Zaokrąglij do 4 miejsc po przecinku."""
    return float(Decimal(str(val)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
