"""ICB Service — wyszukiwanie cen R/M/S z icb_ceny_srednie + narzuty + korekty regionalne.

Zastępuje hardcoded CPV_BENCHMARKS w cost_estimation.py realną bazą 784k wierszy.
"""
from __future__ import annotations

import logging
from typing import Any

import sqlalchemy as sa

from terra_db.session import get_engine

logger = logging.getLogger(__name__)

# Mapowanie województw → nazwy w intercenbud_regional_rates
VOIVODESHIP_NAMES: dict[str, str] = {
    "mazowieckie": "mazowieckie",
    "śląskie": "śląskie",
    "dolnośląskie": "dolnośląskie",
    "małopolskie": "małopolskie",
    "wielkopolskie": "wielkopolskie",
    "pomorskie": "pomorskie",
    "łódzkie": "łódzkie",
    "kujawsko-pomorskie": "kujawsko-pomorskie",
    "lubelskie": "lubelskie",
    "podkarpackie": "podkarpackie",
    "warmińsko-mazurskie": "warmińsko-mazurskie",
    "zachodniopomorskie": "zachodniopomorskie",
    "opolskie": "opolskie",
    "świętokrzyskie": "świętokrzyskie",
    "podlaskie": "podlaskie",
    "lubuskie": "lubuskie",
    # aliasy aglomeracyjne używane w ICB
    "aglomeracja warszawska": "mazowieckie",
    "warszawa": "mazowieckie",
    "kraków": "małopolskie",
    "wrocław": "dolnośląskie",
    "gdańsk": "pomorskie",
    "poznań": "wielkopolskie",
    "katowice": "śląskie",
}

# Mapowanie kategorii ICB → typ robót (dla narzutów)
CATEGORY_TO_NARZUT: dict[str, str] = {
    "murarstwo": "roboty ogólnobudowlane",
    "beton_cement": "roboty ogólnobudowlane",
    "stal_konstrukcyjna": "roboty ogólnobudowlane",
    "dach_pokrycia": "roboty ogólnobudowlane",
    "drewno": "roboty ogólnobudowlane",
    "kruszywa_ziemne": "roboty ogólnobudowlane",
    "nawierzchnie": "roboty inżynieryjne",
    "instalacje_wod_kan": "instalacje sanitarne",
    "ogrzewanie": "instalacje sanitarne",
    "wentylacja_klima": "instalacje sanitarne",
    "elektryka": "instalacje elektryczne",
    "izolacja_termo": "roboty ogólnobudowlane",
    "malowanie": "roboty ogólnobudowlane",
    "plytki_ceramiczne": "roboty ogólnobudowlane",
    "stolarka": "roboty ogólnobudowlane",
    "inne": "roboty ogólnobudowlane",
}


def get_latest_quarter() -> tuple[int, int]:
    """Zwraca najnowszy dostępny kwartał z icb_ceny_srednie."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT kwartalrok, kwartalnr
            FROM icb_ceny_srednie
            ORDER BY kwartalrok DESC, kwartalnr DESC
            LIMIT 1
        """)).fetchone()
    if row:
        return row.kwartalrok, row.kwartalnr
    return 2026, 2


def search_icb(
    query: str,
    typ_rms: str | None = None,
    kwartalrok: int = 2026,
    kwartalnr: int = 2,
    category: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Wyszukiwanie pozycji z icb_ceny_srednie po nazwie (pg_trgm lub ILIKE)."""
    engine = get_engine()
    filters = ["kwartalrok = :rok", "kwartalnr = :nr"]
    params: dict[str, Any] = {"rok": kwartalrok, "nr": kwartalnr, "limit": limit}

    if typ_rms:
        filters.append("typ_rms = :typ")
        params["typ"] = typ_rms.upper()
    if category:
        filters.append("category = :cat")
        params["cat"] = category

    where = " AND ".join(filters)

    # Użyj pg_trgm jeśli dostępne, fallback do ILIKE
    try:
        rows = _search_trgm(query, where, params, limit)
    except Exception:
        rows = _search_ilike(query, where, params, limit)

    return rows


def _search_trgm(query: str, where: str, params: dict, limit: int) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text(f"""
            SELECT id, nazwa, symbol, indeks_eto, typ_rms, jednostka,
                   cena_netto, cena_narzut, category,
                   similarity(nazwa, :q) AS sim
            FROM icb_ceny_srednie
            WHERE {where}
              AND similarity(nazwa, :q) > 0.1
            ORDER BY sim DESC
            LIMIT :limit
        """), {**params, "q": query}).fetchall()
    return [_row_to_dict(r) for r in rows]


def _search_ilike(query: str, where: str, params: dict, limit: int) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text(f"""
            SELECT id, nazwa, symbol, indeks_eto, typ_rms, jednostka,
                   cena_netto, cena_narzut, category
            FROM icb_ceny_srednie
            WHERE {where}
              AND nazwa ILIKE :q
            ORDER BY nazwa
            LIMIT :limit
        """), {**params, "q": f"%{query}%"}).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(r: Any) -> dict:
    return {
        "id": r.id,
        "nazwa": r.nazwa,
        "symbol": r.symbol,
        "indeks_eto": r.indeks_eto,
        "typ_rms": r.typ_rms,
        "jednostka": r.jednostka,
        "cena_netto": float(r.cena_netto) if r.cena_netto else 0.0,
        "cena_narzut": float(r.cena_narzut) if r.cena_narzut else 0.0,
        "category": r.category,
    }


def get_narzuty(
    kwartalrok: int = 2026,
    kwartalnr: int = 2,
    branża: str = "roboty ogólnobudowlane",
) -> dict:
    """Pobierz % narzutów Ko/Z/Kz z icb_narzuty dla danego kwartału i branży."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT nazwa, koszty_posrednie, zysk, koszty_zakupu
            FROM icb_narzuty
            WHERE kwartalrok = :rok AND kwartalnr = :nr
              AND lower(nazwa) ILIKE :branza
            ORDER BY id LIMIT 1
        """), {"rok": kwartalrok, "nr": kwartalnr, "branza": f"%{branża.lower()}%"}).fetchone()

        if not row:
            # Fallback: najnowsze dostępne
            row = conn.execute(sa.text("""
                SELECT nazwa, koszty_posrednie, zysk, koszty_zakupu
                FROM icb_narzuty
                WHERE lower(nazwa) ILIKE :branza
                ORDER BY kwartalrok DESC, kwartalnr DESC
                LIMIT 1
            """), {"branza": f"%{branża.lower()}%"}).fetchone()

        if not row:
            # Ostateczny fallback — wartości rynkowe 2026
            return {"ko_pct": 70.1, "z_pct": 12.5, "kz_pct": 7.1, "source": "fallback"}

    return {
        "ko_pct": float(row.koszty_posrednie),
        "z_pct": float(row.zysk),
        "kz_pct": float(row.koszty_zakupu),
        "branża": row.nazwa,
        "source": "icb_narzuty",
    }


def get_all_narzuty(kwartalrok: int = 2026, kwartalnr: int = 2) -> list[dict]:
    """Wszystkie branże narzutów dla danego kwartału."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT nazwa, koszty_posrednie, zysk, koszty_zakupu
            FROM icb_narzuty
            WHERE kwartalrok = :rok AND kwartalnr = :nr
            ORDER BY nazwa
        """), {"rok": kwartalrok, "nr": kwartalnr}).fetchall()
    return [
        {
            "branża": r.nazwa,
            "ko_pct": float(r.koszty_posrednie),
            "z_pct": float(r.zysk),
            "kz_pct": float(r.koszty_zakupu),
        }
        for r in rows
    ]


def get_regional_coefficient(
    voivodeship: str,
    rate_type: str = "Ogolne",
    kwartalrok: int = 2026,
    kwartalnr: int = 2,
) -> float:
    """Pobierz współczynnik regionalny z intercenbud_regional_rates."""
    normalized = VOIVODESHIP_NAMES.get(voivodeship.lower(), voivodeship)
    quarter_str = f"{kwartalrok}-{kwartalnr}"

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT coefficient FROM intercenbud_regional_rates
            WHERE lower(voivodeship) ILIKE :voi
              AND rate_type = :rt
              AND quarter = :q
            LIMIT 1
        """), {"voi": f"%{normalized}%", "rt": rate_type, "q": quarter_str}).fetchone()

        if not row:
            # Fallback: najnowszy kwartał
            row = conn.execute(sa.text("""
                SELECT coefficient FROM intercenbud_regional_rates
                WHERE lower(voivodeship) ILIKE :voi
                  AND rate_type = :rt
                ORDER BY quarter DESC
                LIMIT 1
            """), {"voi": f"%{normalized}%", "rt": rate_type}).fetchone()

    return float(row.coefficient) if row else 1.0


def get_icb_price(
    symbol: str,
    kwartalrok: int = 2026,
    kwartalnr: int = 2,
) -> dict | None:
    """Pobierz konkretną pozycję ICB po symbolu."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT id, nazwa, symbol, typ_rms, jednostka, cena_netto, cena_narzut, category
            FROM icb_ceny_srednie
            WHERE symbol = :sym AND kwartalrok = :rok AND kwartalnr = :nr
            LIMIT 1
        """), {"sym": symbol, "rok": kwartalrok, "nr": kwartalnr}).fetchone()
    return _row_to_dict(row) if row else None


def get_robocizna_rates(
    voivodeship: str | None = None,
    kwartalrok: int = 2026,
    kwartalnr: int = 2,
) -> dict:
    """Stawki robocizny kosztorysowej [zł/r-g] — z ICB + korekta regionalna."""
    engine = get_engine()
    with engine.connect() as conn:
        # ICB trzyma stawki R per region jako osobne rekordy
        if voivodeship:
            normalized = VOIVODESHIP_NAMES.get(voivodeship.lower(), voivodeship)
            row = conn.execute(sa.text("""
                SELECT nazwa, cena_netto, category
                FROM icb_ceny_srednie
                WHERE typ_rms = 'R'
                  AND kwartalrok = :rok AND kwartalnr = :nr
                  AND (lower(nazwa) ILIKE :voi OR lower(nazwa) ILIKE '%ogólnobudowlana%')
                ORDER BY
                  CASE WHEN lower(nazwa) ILIKE :voi THEN 0 ELSE 1 END,
                  cena_netto DESC
                LIMIT 1
            """), {"rok": kwartalrok, "nr": kwartalnr, "voi": f"%{normalized.lower()}%"}).fetchone()

            if row:
                return {
                    "stawka_r": float(row.cena_netto),
                    "opis": row.nazwa,
                    "source": "icb_regional",
                }

        # Średnia krajowa z R
        row = conn.execute(sa.text("""
            SELECT round(avg(cena_netto)::numeric, 2) as avg_r,
                   round(min(cena_netto)::numeric, 2) as min_r,
                   round(max(cena_netto)::numeric, 2) as max_r
            FROM icb_ceny_srednie
            WHERE typ_rms = 'R' AND kwartalrok = :rok AND kwartalnr = :nr
        """), {"rok": kwartalrok, "nr": kwartalnr}).fetchone()

    if row and row.avg_r:
        coeff = get_regional_coefficient(voivodeship or "mazowieckie", "Ogolne", kwartalrok, kwartalnr)
        return {
            "stawka_r": round(float(row.avg_r) * coeff, 2),
            "min_r": float(row.min_r),
            "max_r": float(row.max_r),
            "coeff_regionalny": coeff,
            "source": "icb_avg_with_regional",
        }

    return {"stawka_r": 52.09, "source": "fallback_2026q2"}


def get_categories() -> list[str]:
    """Lista dostępnych kategorii w icb_ceny_srednie."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT DISTINCT category FROM icb_ceny_srednie
            WHERE category IS NOT NULL ORDER BY category
        """)).fetchall()
    return [r.category for r in rows]


def get_price_trend(
    symbol: str | None = None,
    category: str | None = None,
    typ_rms: str = "M",
    from_year: int = 2019,
) -> list[dict]:
    """Trend cen danej pozycji/kategorii od from_year do teraz."""
    engine = get_engine()
    params: dict[str, Any] = {"typ": typ_rms, "from_year": from_year}
    filters = ["typ_rms = :typ", "kwartalrok >= :from_year"]

    if symbol:
        filters.append("symbol = :sym")
        params["sym"] = symbol
        agg = "avg(cena_netto)"
    elif category:
        filters.append("category = :cat")
        params["cat"] = category
        agg = "avg(cena_netto)"
    else:
        agg = "avg(cena_netto)"

    where = " AND ".join(filters)
    with engine.connect() as conn:
        rows = conn.execute(sa.text(f"""
            SELECT kwartalrok, kwartalnr,
                   round({agg}::numeric, 4) as avg_price,
                   count(*) as n
            FROM icb_ceny_srednie
            WHERE {where}
            GROUP BY kwartalrok, kwartalnr
            ORDER BY kwartalrok, kwartalnr
        """), params).fetchall()

    return [
        {
            "year": r.kwartalrok,
            "quarter": r.kwartalnr,
            "period": f"{r.kwartalrok}-Q{r.kwartalnr}",
            "avg_price": float(r.avg_price) if r.avg_price else None,
            "n": r.n,
        }
        for r in rows
    ]
