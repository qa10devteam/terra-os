"""Faza K17 — Cost Estimation: 3 metody szacowania kosztu przetargu.

Metoda 1 (swz)       — dokumentacja przetargowa: parsowanie przedmiaru z SWZ/PDF/XML
Metoda 2 (icb)       — baza Intercenbud: CPV + region + m² → agregat ICB cen średnich
Metoda 3 (user_rates) — stawki użytkownika: własny cennik per tenant (tabela user_rates)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ─── CPV → kategoria ICB ─────────────────────────────────────────────────────

CPV_TO_ICB_CATEGORY: dict[str, str] = {
    "45100": "ROBOTY PRZYGOTOWAWCZE",
    "45111": "ROBOTY ZIEMNE",
    "45112": "ROBOTY ZIEMNE",
    "45200": "ROBOTY BUDOWLANE",
    "45210": "ROBOTY BUDOWLANE KUBATUROWE",
    "45211": "ROBOTY BUDOWLANE KUBATUROWE",
    "45212": "ROBOTY BUDOWLANE KUBATUROWE",
    "45220": "OBIEKTY INZYNIERYJNE",
    "45221": "OBIEKTY INZYNIERYJNE",
    "45230": "ROBOTY DROGOWE",
    "45231": "SIECI PRZESYLOWE",
    "45232": "SIECI PRZESYLOWE",
    "45233": "ROBOTY DROGOWE",
    "45234": "ROBOTY DROGOWE",
    "45300": "INSTALACJE BUDOWLANE",
    "45310": "INSTALACJE ELEKTRYCZNE",
    "45311": "INSTALACJE ELEKTRYCZNE",
    "45312": "INSTALACJE ELEKTRYCZNE",
    "45315": "INSTALACJE ELEKTRYCZNE",
    "45316": "INSTALACJE ELEKTRYCZNE",
    "45320": "IZOLACJE",
    "45321": "IZOLACJE",
    "45330": "INSTALACJE SANITARNE",
    "45331": "INSTALACJE SANITARNE",
    "45332": "INSTALACJE SANITARNE",
    "45333": "INSTALACJE SANITARNE",
    "45340": "OGRODZENIA",
    "45400": "ROBOTY WYKONCZENIOWE",
    "45410": "TYNKOWANIE",
    "45420": "STOLARKA",
    "45421": "STOLARKA",
    "45430": "POSADZKI",
    "45431": "POSADZKI",
    "45440": "MALARSTWO",
    "45442": "MALARSTWO",
    "45450": "ROBOTY WYKONCZENIOWE",
}

# CPV → benchmark cena/m² (PLN netto) + std_pct
CPV_BENCHMARKS: dict[str, dict] = {
    "45":    {"label": "Roboty budowlane ogólne",  "price_per_m2": 2800, "std_pct": 0.35},
    "45100": {"label": "Przygotowanie terenu",      "price_per_m2": 180,  "std_pct": 0.40},
    "45111": {"label": "Roboty ziemne",             "price_per_m2": 210,  "std_pct": 0.38},
    "45112": {"label": "Kopanie i niwelacja",       "price_per_m2": 195,  "std_pct": 0.40},
    "45200": {"label": "Roboty budowlane",          "price_per_m2": 3200, "std_pct": 0.30},
    "45210": {"label": "Kubatura",                  "price_per_m2": 2800, "std_pct": 0.28},
    "45221": {"label": "Mosty i wiadukty",          "price_per_m2": 4500, "std_pct": 0.40},
    "45230": {"label": "Drogi i autostrady",        "price_per_m2": 650,  "std_pct": 0.25},
    "45231": {"label": "Sieci rurociągowe",         "price_per_m2": 650,  "std_pct": 0.35},
    "45233": {"label": "Drogi i chodniki",          "price_per_m2": 380,  "std_pct": 0.30},
    "45300": {"label": "Instalacje budowlane",      "price_per_m2": 450,  "std_pct": 0.30},
    "45310": {"label": "Instalacje elektryczne",    "price_per_m2": 280,  "std_pct": 0.22},
    "45330": {"label": "Instalacje sanitarne",      "price_per_m2": 320,  "std_pct": 0.24},
    "45400": {"label": "Roboty wykończeniowe",      "price_per_m2": 450,  "std_pct": 0.25},
}

REGION_COEFFICIENTS: dict[str, float] = {
    "mazowieckie": 1.15,
    "małopolskie": 1.05,
    "śląskie": 1.08,
    "dolnośląskie": 1.06,
    "wielkopolskie": 1.02,
    "pomorskie": 1.07,
    "łódzkie": 0.98,
    "lubelskie": 0.93,
    "podkarpackie": 0.91,
    "warmińsko-mazurskie": 0.92,
    "świętokrzyskie": 0.90,
    "opolskie": 0.96,
    "podlaskie": 0.91,
    "lubuskie": 0.95,
    "kujawsko-pomorskie": 0.97,
    "zachodniopomorskie": 1.00,
}

# ─── Modele wynikowe ──────────────────────────────────────────────────────────

@dataclass
class EstimateLine:
    name: str
    symbol: str | None
    unit: str
    qty: float
    unit_price: float
    total: float
    source: str  # "icb" | "user_rates" | "swz" | "benchmark"


@dataclass
class EstimateResult:
    method: str
    variant: str
    total_net_pln: float
    confidence_low: float
    confidence_high: float
    lines: list[EstimateLine] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "variant": self.variant,
            "total_net_pln": round(self.total_net_pln, 2),
            "confidence_low": round(self.confidence_low, 2),
            "confidence_high": round(self.confidence_high, 2),
            "lines": [
                {
                    "name": ln.name,
                    "symbol": ln.symbol,
                    "unit": ln.unit,
                    "qty": round(ln.qty, 3),
                    "unit_price": round(ln.unit_price, 2),
                    "total": round(ln.total, 2),
                    "source": ln.source,
                }
                for ln in self.lines
            ],
            "params": self.params,
            "notes": self.notes,
        }


# ─── Helpery ─────────────────────────────────────────────────────────────────

def _resolve_cpv_benchmark(cpv: str | None) -> dict:
    """Zwraca benchmark dla najdłuższego pasującego prefiksu CPV."""
    if not cpv:
        return CPV_BENCHMARKS["45"]
    key = cpv[:5]
    for length in (5, 4, 3, 2):
        prefix = cpv[:length]
        if prefix in CPV_BENCHMARKS:
            return CPV_BENCHMARKS[prefix]
    return CPV_BENCHMARKS["45"]


def _region_coeff(region: str | None) -> float:
    if not region:
        return 1.0
    return REGION_COEFFICIENTS.get(region.lower().strip(), 1.0)


def _latest_quarter() -> tuple[int, int]:
    """Zwraca (kwartalnr, kwartalrok) dla bieżącego kwartału."""
    now = datetime.now()
    q = (now.month - 1) // 3 + 1
    return q, now.year


# ─── Metoda 1: SWZ / dokumentacja przetargowa ────────────────────────────────

# Wzorce do wyodrębnienia pozycji kosztorysowych z tekstu przedmiaru
_PRZEDMIAR_PATTERNS = [
    # "1.1  Roboty ziemne  m³  120,00  45.00  5400.00"
    re.compile(
        r"(?P<lp>\d+[\.\d]*)\s+"
        r"(?P<name>[A-ZĄĆĘŁŃÓŚŹŻ][^0-9\n]{5,80}?)\s+"
        r"(?P<unit>m[²³23]?|szt|kpl|mb|t|kg|Mg|km|ha)\s+"
        r"(?P<qty>[\d\s]+[,.][\d]+)\s+"
        r"(?P<unit_price>[\d\s]+[,.][\d]+)",
        re.IGNORECASE | re.UNICODE,
    ),
    # "Roboty ziemne  120.00 m³  @ 45.00 PLN"
    re.compile(
        r"(?P<name>[A-ZĄĆĘŁŃÓŚŹŻ][^0-9\n]{5,60}?)\s+"
        r"(?P<qty>[\d]+[,.][\d]*)\s+"
        r"(?P<unit>m[²³23]?|szt|kpl|mb|t|kg|Mg)\s+"
        r"[@x×]\s*(?P<unit_price>[\d]+[,.][\d]*)",
        re.IGNORECASE | re.UNICODE,
    ),
]

_SECTION_HEADERS = re.compile(
    r"^\s*(dzia[łl]|rozdzia[łl]|element|pozycja|poz\.|lp\.?)\s",
    re.IGNORECASE,
)


def _parse_number(s: str) -> float:
    """Konwertuje '1 234,56' lub '1234.56' na float."""
    s = s.strip().replace(" ", "").replace("\xa0", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def estimate_from_swz(text: str, region: str | None = None) -> EstimateResult:
    """Metoda 1 — parsuje tekst przedmiaru robót z dokumentacji SWZ/PDF.

    Wyodrębnia pozycje kosztorysowe: nazwę, jednostkę, ilość, cenę jednostkową.
    Jeśli cena jednostkowa jest nieznana (tylko ilość), uzupełnia z benchmarku CPV.
    """
    lines: list[EstimateLine] = []
    found_positions: set[str] = set()

    for pattern in _PRZEDMIAR_PATTERNS:
        for m in pattern.finditer(text):
            name = m.group("name").strip()
            if name in found_positions:
                continue
            found_positions.add(name)

            unit = m.group("unit").lower()
            qty = _parse_number(m.group("qty"))
            try:
                unit_price = _parse_number(m.group("unit_price"))
            except IndexError:
                unit_price = 0.0

            if qty <= 0:
                continue

            # Fallback cenowy z benchmarku gdy brak ceny
            if unit_price <= 0:
                bm = _resolve_cpv_benchmark(None)
                unit_price = bm["price_per_m2"] * _region_coeff(region)

            total = qty * unit_price
            lines.append(EstimateLine(
                name=name[:120],
                symbol=None,
                unit=unit,
                qty=qty,
                unit_price=unit_price,
                total=total,
                source="swz",
            ))

    if not lines:
        # Fallback — brak rozpoznanych pozycji → zwracamy informację
        return EstimateResult(
            method="swz",
            variant="Dokumentacja przetargowa",
            total_net_pln=0.0,
            confidence_low=0.0,
            confidence_high=0.0,
            notes="Nie znaleziono pozycji kosztorysowych w tekście dokumentacji. "
                  "Upewnij się, że przesłany dokument zawiera przedmiar robót.",
        )

    total_net = sum(ln.total for ln in lines)
    coeff = _region_coeff(region)
    total_net *= coeff

    # Popraw wartości linii o współczynnik regionalny
    for ln in lines:
        ln.total = round(ln.total * coeff, 2)
        ln.unit_price = round(ln.unit_price * coeff, 2)

    std_pct = 0.20  # 20% przedział ufności dla SWZ (zależy od kompletności)
    return EstimateResult(
        method="swz",
        variant="Dokumentacja przetargowa",
        total_net_pln=round(total_net, 2),
        confidence_low=round(total_net * (1 - std_pct), 2),
        confidence_high=round(total_net * (1 + std_pct), 2),
        lines=lines,
        params={"region": region, "positions_found": len(lines)},
        notes=f"Wyodrębniono {len(lines)} pozycji z dokumentacji. "
              f"Współczynnik regionalny: {coeff:.2f}.",
    )


# ─── Metoda 2: Intercenbud (ICB) ─────────────────────────────────────────────

def estimate_from_icb(
    cpv: str | None,
    area_m2: float,
    region: str | None = None,
    kwartalnr: int | None = None,
    kwartalrok: int | None = None,
    engine: Any = None,
) -> EstimateResult:
    """Metoda 2 — szacowanie z bazy Intercenbud (icb_ceny_srednie).

    Pobiera reprezentatywne pozycje (R+M+S) dla kategorii CPV i liczy
    zagregowany koszt na podstawie area_m2.
    """
    if kwartalnr is None or kwartalrok is None:
        kwartalnr, kwartalrok = _latest_quarter()

    # Kategoria ICB dla CPV
    icb_category = None
    if cpv:
        for prefix_len in (5, 4, 3, 2):
            prefix = cpv[:prefix_len]
            if prefix in CPV_TO_ICB_CATEGORY:
                icb_category = CPV_TO_ICB_CATEGORY[prefix]
                break

    benchmark = _resolve_cpv_benchmark(cpv)
    coeff = _region_coeff(region)
    lines: list[EstimateLine] = []
    icb_used = False

    if engine is not None and area_m2 > 0:
        try:
            from sqlalchemy import text as sa_text
            with engine.connect() as conn:
                # Pobierz top-20 pozycji dla kategorii lub globalnie, najnowszy kwartał
                if icb_category:
                    rows = conn.execute(sa_text("""
                        SELECT symbol, nazwa, jednostka, typ_rms,
                               AVG(cena_netto) as avg_cena
                        FROM icb_ceny_srednie
                        WHERE category ILIKE :cat
                          AND kwartalrok = :rok
                          AND kwartalnr = :nr
                          AND cena_netto > 0
                        GROUP BY symbol, nazwa, jednostka, typ_rms
                        ORDER BY typ_rms, avg_cena DESC
                        LIMIT 20
                    """), {"cat": f"%{icb_category}%", "rok": kwartalrok, "nr": kwartalnr}).fetchall()
                else:
                    rows = []

                if not rows:
                    # Fallback: pobierz najpopularniejsze pozycje R+M+S
                    rows = conn.execute(sa_text("""
                        SELECT symbol, nazwa, jednostka, typ_rms,
                               AVG(cena_netto) as avg_cena
                        FROM icb_ceny_srednie
                        WHERE kwartalrok = :rok
                          AND kwartalnr = :nr
                          AND cena_netto > 0
                          AND typ_rms IN ('R','M','S')
                        GROUP BY symbol, nazwa, jednostka, typ_rms
                        ORDER BY avg_cena DESC
                        LIMIT 15
                    """), {"rok": kwartalrok, "nr": kwartalnr}).fetchall()

            if rows:
                icb_used = True
                # Rozkład ICB: R=40%, M=40%, S=20% wartości
                type_weights = {"R": 0.40, "M": 0.40, "S": 0.20}
                total_target = benchmark["price_per_m2"] * area_m2 * coeff

                # Grupuj po typ_rms
                by_type: dict[str, list] = {}
                for row in rows:
                    t = str(row[3]).strip()
                    by_type.setdefault(t, []).append(row)

                for typ, type_rows in by_type.items():
                    weight = type_weights.get(typ, 0.15)
                    type_total = total_target * weight
                    per_row = type_total / len(type_rows) if type_rows else 0

                    for row in type_rows:
                        symbol = row[0]
                        nazwa = row[1] or symbol
                        jednostka = row[2] or "m²"
                        avg_cena = float(row[4]) if row[4] else 1.0
                        qty = per_row / avg_cena if avg_cena > 0 else 0
                        total = qty * avg_cena

                        lines.append(EstimateLine(
                            name=nazwa[:120],
                            symbol=symbol,
                            unit=jednostka,
                            qty=round(qty, 3),
                            unit_price=round(avg_cena * coeff, 2),
                            total=round(total, 2),
                            source="icb",
                        ))

        except Exception as exc:
            logger.warning("ICB query failed: %s — fallback benchmark", exc)

    if not lines:
        # Benchmark fallback — gdy brak ICB lub silnik niedostępny
        price_m2 = benchmark["price_per_m2"] * coeff
        total = price_m2 * area_m2
        lines.append(EstimateLine(
            name=benchmark["label"],
            symbol=None,
            unit="m²",
            qty=area_m2,
            unit_price=round(price_m2, 2),
            total=round(total, 2),
            source="benchmark",
        ))

    total_net = sum(ln.total for ln in lines)
    std_pct = benchmark["std_pct"]

    return EstimateResult(
        method="icb",
        variant=f"Intercenbud {kwartalrok} Q{kwartalnr}",
        total_net_pln=round(total_net, 2),
        confidence_low=round(total_net * (1 - std_pct), 2),
        confidence_high=round(total_net * (1 + std_pct), 2),
        lines=lines,
        params={
            "cpv": cpv,
            "area_m2": area_m2,
            "region": region,
            "kwartalnr": kwartalnr,
            "kwartalrok": kwartalrok,
            "icb_category": icb_category,
            "icb_rows_used": len(lines) if icb_used else 0,
            "region_coeff": coeff,
        },
        notes=(
            f"Szacowanie ICB: {len(lines)} pozycji, {kwartalrok} Q{kwartalnr}, "
            f"obszar {area_m2} m², region {region or 'brak'} (coeff {coeff:.2f})."
            + (" Użyto benchmarku CPV (brak danych ICB)." if not icb_used else "")
        ),
    )


# ─── Metoda 3: Stawki użytkownika ─────────────────────────────────────────────

def estimate_from_user_rates(
    tenant_id: str,
    area_m2: float,
    cpv: str | None = None,
    region: str | None = None,
    engine: Any = None,
) -> EstimateResult:
    """Metoda 3 — szacowanie na podstawie własnych stawek tenanta (user_rates).

    Jeśli tenant nie ma żadnych stawek → zwraca komunikat z instrukcją dodania.
    """
    lines: list[EstimateLine] = []
    coeff = _region_coeff(region)

    if engine is not None:
        try:
            from sqlalchemy import text as sa_text
            with engine.connect() as conn:
                rows = conn.execute(sa_text("""
                    SELECT symbol, nazwa, jednostka, typ_rms, cena_netto
                    FROM user_rates
                    WHERE tenant_id = :tid
                    ORDER BY typ_rms, symbol
                    LIMIT 50
                """), {"tid": tenant_id}).fetchall()

            if rows:
                benchmark = _resolve_cpv_benchmark(cpv)
                total_target = benchmark["price_per_m2"] * area_m2 * coeff
                type_weights = {"R": 0.40, "M": 0.40, "S": 0.20}

                by_type: dict[str, list] = {}
                for row in rows:
                    t = str(row[3]).strip()
                    by_type.setdefault(t, []).append(row)

                for typ, type_rows in by_type.items():
                    weight = type_weights.get(typ, 0.15)
                    type_total = total_target * weight
                    per_row = type_total / len(type_rows) if type_rows else 0

                    for row in type_rows:
                        symbol = row[0]
                        nazwa = row[1] or symbol
                        jednostka = row[2] or "m²"
                        cena = float(row[4]) if row[4] else 1.0
                        qty = per_row / cena if cena > 0 else 0
                        total = qty * cena * coeff

                        lines.append(EstimateLine(
                            name=nazwa[:120],
                            symbol=symbol,
                            unit=jednostka,
                            qty=round(qty, 3),
                            unit_price=round(cena * coeff, 2),
                            total=round(total, 2),
                            source="user_rates",
                        ))
        except Exception as exc:
            logger.warning("user_rates query failed: %s", exc)

    if not lines:
        return EstimateResult(
            method="user_rates",
            variant="Stawki własne",
            total_net_pln=0.0,
            confidence_low=0.0,
            confidence_high=0.0,
            notes="Brak stawek własnych. Dodaj pozycje cennika w ustawieniach "
                  "modułu (Ustawienia → Stawki własne) lub wybierz metodę ICB.",
        )

    total_net = sum(ln.total for ln in lines)
    return EstimateResult(
        method="user_rates",
        variant="Stawki własne",
        total_net_pln=round(total_net, 2),
        confidence_low=round(total_net * 0.90, 2),
        confidence_high=round(total_net * 1.10, 2),
        lines=lines,
        params={
            "cpv": cpv,
            "area_m2": area_m2,
            "region": region,
            "region_coeff": coeff,
            "rates_count": len(lines),
        },
        notes=f"Szacowanie wg {len(lines)} stawek własnych tenanta. "
              f"Obszar {area_m2} m², współczynnik regionalny {coeff:.2f}.",
    )


# ─── Fasada — wszystkie 3 metody naraz ───────────────────────────────────────

def estimate_all(
    *,
    tenant_id: str,
    cpv: str | None = None,
    area_m2: float = 0.0,
    region: str | None = None,
    swz_text: str | None = None,
    kwartalnr: int | None = None,
    kwartalrok: int | None = None,
    engine: Any = None,
) -> list[dict]:
    """Zwraca listę do 3 estymacji (SWZ, ICB, user_rates).

    Metoda SWZ pomijana gdy brak swz_text.
    Metoda user_rates pomijana gdy brak tenanta.
    """
    results = []

    if swz_text and swz_text.strip():
        try:
            r = estimate_from_swz(swz_text, region=region)
            results.append(r.to_dict())
        except Exception as exc:
            logger.error("estimate_from_swz failed: %s", exc)

    if area_m2 > 0:
        try:
            r = estimate_from_icb(
                cpv=cpv,
                area_m2=area_m2,
                region=region,
                kwartalnr=kwartalnr,
                kwartalrok=kwartalrok,
                engine=engine,
            )
            results.append(r.to_dict())
        except Exception as exc:
            logger.error("estimate_from_icb failed: %s", exc)

        if tenant_id:
            try:
                r = estimate_from_user_rates(
                    tenant_id=tenant_id,
                    area_m2=area_m2,
                    cpv=cpv,
                    region=region,
                    engine=engine,
                )
                results.append(r.to_dict())
            except Exception as exc:
                logger.error("estimate_from_user_rates failed: %s", exc)

    return results


# ─── CostEstimator (compatibility wrapper) ───────────────────────────────────

class CostEstimator:
    """Kompatybilny wrapper — zachowuje stary interfejs train/predict."""

    def __init__(self) -> None:
        self._is_trained = False
        # Warm-up: trigger first ICB query so subsequent /predict calls are fast
        try:
            from terra_db.session import get_engine
            estimate_from_icb(cpv="45", area_m2=100.0, region="mazowieckie", engine=get_engine())
        except Exception:
            pass

    def train(self, data: list[dict]) -> dict:
        if len(data) < 10:
            return {"status": "insufficient_data", "samples": len(data)}
        self._is_trained = True
        return {"status": "ok", "samples": len(data)}

    def predict(self, features: dict) -> dict:
        """Predykcja przez estimate_from_icb (bez ML — statystyczny benchmark)."""
        cpv = features.get("cpv")
        area_m2 = float(features.get("area_m2", 0) or 0)
        region = features.get("region")
        r = estimate_from_icb(cpv=cpv, area_m2=area_m2, region=region)
        return r.to_dict()


_estimator_instance: CostEstimator | None = None


def get_estimator() -> CostEstimator:
    global _estimator_instance
    if _estimator_instance is None:
        _estimator_instance = CostEstimator()
    return _estimator_instance
