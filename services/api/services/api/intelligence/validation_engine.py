"""
Bud.OS Validation Engine Service
47-point checklist covering PZP art. 275 requirements.
Categories: completeness, formal, financial, legal, technical.
"""
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


# ─── DB Connection ───────────────────────────────────────────────────────────

def get_db_conn():
    """Create a psycopg2 connection using env vars (or defaults)."""
    import psycopg2
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ.get("DB_NAME", "terraos"),
        user=os.environ.get("DB_USER", "terraos"),
        password=os.environ.get("DB_PASSWORD", "terra_dev_2026"),
        connect_timeout=5,
    )


# ─── Models ─────────────────────────────────────────────────────────────────

class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"


class CheckCategory(str, Enum):
    COMPLETENESS = "completeness"
    FORMAL = "formal"
    FINANCIAL = "financial"
    LEGAL = "legal"
    TECHNICAL = "technical"


@dataclass
class ValidationPoint:
    """Single validation checkpoint."""
    id: int
    category: CheckCategory
    description: str
    pzp_reference: Optional[str] = None
    status: CheckStatus = CheckStatus.PASS
    details: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class ValidationResult:
    """Complete validation result."""
    bid_id: UUID
    points: list[ValidationPoint] = field(default_factory=list)
    status: str = "passed"  # "passed" | "failed" | "warnings"
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    not_applicable: int = 0
    critical_issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)


# ─── 47-Point Checklist Definition ─────────────────────────────────────────

CHECKLIST_47: list[dict] = [
    # ═══ COMPLETENESS (1-12) ═══
    {"id": 1, "cat": "completeness", "desc": "Formularz Ofertowy — dokument istnieje", "pzp": "art. 63 ust. 1"},
    {"id": 2, "cat": "completeness", "desc": "Kosztorys Ofertowy — dokument istnieje", "pzp": None},
    {"id": 3, "cat": "completeness", "desc": "Oświadczenie o braku wykluczenia (Zał. 1)", "pzp": "art. 125 ust. 1"},
    {"id": 4, "cat": "completeness", "desc": "Wykaz robót budowlanych (Zał. 2)", "pzp": "art. 117"},
    {"id": 5, "cat": "completeness", "desc": "Wykaz osób (Zał. 3)", "pzp": "art. 116"},
    {"id": 6, "cat": "completeness", "desc": "Zobowiązanie podmiotu trzeciego (Zał. 4, jeśli dotyczy)", "pzp": "art. 118"},
    {"id": 7, "cat": "completeness", "desc": "Pełnomocnictwo (jeśli wymagane)", "pzp": "art. 58"},
    {"id": 8, "cat": "completeness", "desc": "Wadium — potwierdzenie wpłaty/gwarancja", "pzp": "art. 97"},
    {"id": 9, "cat": "completeness", "desc": "Odpis KRS/CEIDG", "pzp": "art. 109 ust. 1 pkt 4"},
    {"id": 10, "cat": "completeness", "desc": "Zaświadczenie ZUS (brak zaległości)", "pzp": "art. 109 ust. 1 pkt 1"},
    {"id": 11, "cat": "completeness", "desc": "Zaświadczenie US (brak zaległości)", "pzp": "art. 109 ust. 1 pkt 1"},
    {"id": 12, "cat": "completeness", "desc": "Polisa OC (jeśli wymagana)", "pzp": "art. 115"},

    # ═══ FORMAL (13-24) ═══
    {"id": 13, "cat": "formal", "desc": "Formularz podpisany kwalifikowanym podpisem elektronicznym", "pzp": "art. 63 ust. 1"},
    {"id": 14, "cat": "formal", "desc": "Oświadczenia podpisane (kwalifikowany e-podpis lub profil zaufany)", "pzp": "art. 63 ust. 2"},
    {"id": 15, "cat": "formal", "desc": "Data oferty nie późniejsza niż termin składania", "pzp": "art. 226 ust. 1 pkt 1"},
    {"id": 16, "cat": "formal", "desc": "Numeracja stron ciągła", "pzp": None},
    {"id": 17, "cat": "formal", "desc": "Spis treści zgodny z zawartością", "pzp": None},
    {"id": 18, "cat": "formal", "desc": "Podpis osoby upoważnionej (zgodność z KRS/pełnomocnictwem)", "pzp": "art. 58"},
    {"id": 19, "cat": "formal", "desc": "Oferta w języku polskim", "pzp": "art. 20 ust. 2"},
    {"id": 20, "cat": "formal", "desc": "Format plików zgodny z rozporządzeniem (PDF/DOCX/XML)", "pzp": "§2 rozp. RM"},
    {"id": 21, "cat": "formal", "desc": "Brak poprawek/skreśleń bez parafowania", "pzp": None},
    {"id": 22, "cat": "formal", "desc": "Nazwa plików czytelna i zgodna z opisem", "pzp": None},
    {"id": 23, "cat": "formal", "desc": "Termin związania ofertą wpisany prawidłowo", "pzp": "art. 307"},
    {"id": 24, "cat": "formal", "desc": "Oznaczenie postępowania (numer BZP/sygnatura) prawidłowe", "pzp": None},

    # ═══ FINANCIAL (25-34) ═══
    {"id": 25, "cat": "financial", "desc": "Cena w formularzu = suma kosztorysu", "pzp": "art. 226 ust. 1 pkt 10"},
    {"id": 26, "cat": "financial", "desc": "Stawka VAT prawidłowa (8% lub 23%)", "pzp": None},
    {"id": 27, "cat": "financial", "desc": "Cena netto + VAT = cena brutto (arytmetyka)", "pzp": "art. 223 ust. 2"},
    {"id": 28, "cat": "financial", "desc": "Kwota słownie = kwota liczbowo", "pzp": None},
    {"id": 29, "cat": "financial", "desc": "Wszystkie pozycje kosztorysu wypełnione (brak zerowych)", "pzp": None},
    {"id": 30, "cat": "financial", "desc": "Cena nie rażąco niska (> 30% poniżej szacunku zamawiającego)", "pzp": "art. 224 ust. 2"},
    {"id": 31, "cat": "financial", "desc": "Wadium w prawidłowej wysokości", "pzp": "art. 97 ust. 3"},
    {"id": 32, "cat": "financial", "desc": "Wadium ważne minimum do końca terminu związania", "pzp": "art. 97 ust. 5"},
    {"id": 33, "cat": "financial", "desc": "Waluta oferty = PLN", "pzp": None},
    {"id": 34, "cat": "financial", "desc": "Koszty pośrednie i zysk w akceptowalnym zakresie", "pzp": None},

    # ═══ LEGAL (35-41) ═══
    {"id": 35, "cat": "legal", "desc": "Oświadczenie art. 108 — brak przesłanek wykluczenia obligatoryjnych", "pzp": "art. 108 ust. 1"},
    {"id": 36, "cat": "legal", "desc": "Oświadczenie art. 109 — brak przesłanek fakultatywnych (jeśli wskazane)", "pzp": "art. 109 ust. 1"},
    {"id": 37, "cat": "legal", "desc": "Oświadczenie sankcyjne (ustawa z 13.04.2022)", "pzp": "art. 7 ust. 1"},
    {"id": 38, "cat": "legal", "desc": "Akceptacja warunków umowy (projekt umowy)", "pzp": "art. 436"},
    {"id": 39, "cat": "legal", "desc": "Klauzula RODO w oświadczeniach", "pzp": "art. 13 RODO"},
    {"id": 40, "cat": "legal", "desc": "Oświadczenie o zatrudnieniu na umowę o pracę (jeśli wymagane)", "pzp": "art. 95"},
    {"id": 41, "cat": "legal", "desc": "Zobowiązanie podmiotu trzeciego — zakres, sposób, okres (jeśli dotyczy)", "pzp": "art. 118 ust. 4"},

    # ═══ TECHNICAL (42-47) ═══
    {"id": 42, "cat": "technical", "desc": "Kadra — kierownik budowy z uprawnieniami wymaganymi w SWZ", "pzp": "art. 116"},
    {"id": 43, "cat": "technical", "desc": "Kadra — wymagane doświadczenie (lata/liczba realizacji)", "pzp": "art. 116"},
    {"id": 44, "cat": "technical", "desc": "Wykaz robót — wartość referencyjna >= próg z SWZ", "pzp": "art. 117"},
    {"id": 45, "cat": "technical", "desc": "Wykaz robót — zakres referencji pokrywa przedmiot zamówienia", "pzp": "art. 117"},
    {"id": 46, "cat": "technical", "desc": "Polisa OC — suma gwarancyjna >= wymagana kwota", "pzp": "art. 115"},
    {"id": 47, "cat": "technical", "desc": "Sprzęt/potencjał techniczny — wymagania SWZ spełnione", "pzp": "art. 116"},
]


# ─── DB-backed validation helpers ───────────────────────────────────────────

def _db_get_bid_data(bid_id: UUID) -> dict:
    """
    Fetch all relevant DB data for a bid_id in one pass.
    Returns a dict with keys: offer, kosztorys, tender_documents, tender_document.
    If bid_id doesn't exist, returns empty structures.
    """
    result = {
        "offer": None,
        "kosztorys": None,
        "tender_documents": [],
        "tender_document": [],
        "bid_intelligence": None,
    }
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        bid_str = str(bid_id)

        # 1. offers — look up by id or by tender_id
        cur.execute(
            """
            SELECT id, tenant_id, tender_id, estimate_id, title, status,
                   contractor_name, contractor_nip, price_gross_pln, vat_pct,
                   metadata, created_at, updated_at, payment_terms, delivery_days
            FROM offers
            WHERE id = %s OR tender_id::text = %s
            LIMIT 1
            """,
            (bid_str, bid_str),
        )
        row = cur.fetchone()
        if row:
            cols = [
                "id", "tenant_id", "tender_id", "estimate_id", "title", "status",
                "contractor_name", "contractor_nip", "price_gross_pln", "vat_pct",
                "metadata", "created_at", "updated_at", "payment_terms", "delivery_days",
            ]
            result["offer"] = dict(zip(cols, row))

        # 2. kosztorys — join by estimate_id if possible, else by tender_id
        estimate_id = (result["offer"] or {}).get("estimate_id")
        tender_id_from_offer = (result["offer"] or {}).get("tender_id")

        if estimate_id:
            cur.execute(
                """
                SELECT id, tender_id, nazwa, status, typ,
                       suma_netto, suma_vat, suma_brutto,
                       vat_pct, ko_r_pct, ko_s_pct, z_pct,
                       win_probability, benchmark_percentile, anomaly_score,
                       created_at, updated_at
                FROM kosztorys
                WHERE id = %s
                LIMIT 1
                """,
                (str(estimate_id),),
            )
        else:
            # Try by tender_id from offer or by bid_id itself treated as tender_id
            lookup_tid = str(tender_id_from_offer) if tender_id_from_offer else bid_str
            cur.execute(
                """
                SELECT id, tender_id, nazwa, status, typ,
                       suma_netto, suma_vat, suma_brutto,
                       vat_pct, ko_r_pct, ko_s_pct, z_pct,
                       win_probability, benchmark_percentile, anomaly_score,
                       created_at, updated_at
                FROM kosztorys
                WHERE tender_id::text = %s OR id::text = %s
                LIMIT 1
                """,
                (lookup_tid, bid_str),
            )
        krow = cur.fetchone()
        if krow:
            kcols = [
                "id", "tender_id", "nazwa", "status", "typ",
                "suma_netto", "suma_vat", "suma_brutto",
                "vat_pct", "ko_r_pct", "ko_s_pct", "z_pct",
                "win_probability", "benchmark_percentile", "anomaly_score",
                "created_at", "updated_at",
            ]
            result["kosztorys"] = dict(zip(kcols, krow))

        # 3. tender_documents (uploaded docs for the tender)
        t_id = str(tender_id_from_offer) if tender_id_from_offer else bid_str
        cur.execute(
            """
            SELECT id, tender_id, filename, status, analysis_result, cost_estimate, uploaded_at
            FROM tender_documents
            WHERE tender_id::text = %s
            ORDER BY uploaded_at DESC
            """,
            (t_id,),
        )
        td_cols = ["id", "tender_id", "filename", "status", "analysis_result", "cost_estimate", "uploaded_at"]
        result["tender_documents"] = [dict(zip(td_cols, r)) for r in cur.fetchall()]

        # 4. tender_document (parsed docs from BZP/SWZ)
        cur.execute(
            """
            SELECT id, tender_id, kind, filename, parsed_ok, pages, risk_level, risk_score, created_at
            FROM tender_document
            WHERE tender_id::text = %s
            ORDER BY created_at DESC
            """,
            (t_id,),
        )
        tdc_cols = ["id", "tender_id", "kind", "filename", "parsed_ok", "pages", "risk_level", "risk_score", "created_at"]
        result["tender_document"] = [dict(zip(tdc_cols, r)) for r in cur.fetchall()]

        # 5. bid_intelligence — by tender_id
        cur.execute(
            """
            SELECT id, tender_id, our_price, winning_price, n_competitors,
                   rank_position, won, price_ratio, market_benchmark_pct,
                   loss_reason, bid_date, created_at
            FROM bid_intelligence
            WHERE tender_id::text = %s OR id::text = %s
            LIMIT 1
            """,
            (t_id, bid_str),
        )
        birow = cur.fetchone()
        if birow:
            bi_cols = [
                "id", "tender_id", "our_price", "winning_price", "n_competitors",
                "rank_position", "won", "price_ratio", "market_benchmark_pct",
                "loss_reason", "bid_date", "created_at",
            ]
            result["bid_intelligence"] = dict(zip(bi_cols, birow))

        cur.close()
        conn.close()
    except Exception as exc:
        logger.warning("DB fetch for bid_id=%s failed: %s", bid_id, exc)

    return result


# ─── Synchronous validate_bid ────────────────────────────────────────────────

def validate_bid(bid_id: UUID, strict_mode: bool = False) -> "ValidationResult":
    """
    DB-backed 47-point validation for a single bid.
    Fetches real data from PostgreSQL and evaluates each checkpoint.
    """
    db = _db_get_bid_data(bid_id)
    offer = db["offer"]
    kosztorys = db["kosztorys"]
    tender_docs = db["tender_documents"]   # uploaded docs
    parsed_docs = db["tender_document"]    # BZP parsed docs
    bid_intel = db["bid_intelligence"]

    # Build quick lookup sets for document kinds/filenames
    parsed_kinds = {(d.get("kind") or "").lower() for d in parsed_docs}
    parsed_filenames = {(d.get("filename") or "").lower() for d in parsed_docs}
    td_filenames = {(d.get("filename") or "").lower() for d in tender_docs}
    all_filenames = parsed_filenames | td_filenames

    def _has_doc(*keywords) -> bool:
        """Return True if any parsed/uploaded doc filename/kind contains one of the keywords."""
        for kw in keywords:
            kw = kw.lower()
            if any(kw in f for f in all_filenames | parsed_kinds):
                return True
        return False

    result = ValidationResult(bid_id=bid_id)
    now = datetime.utcnow()

    for check_def in CHECKLIST_47:
        cid = check_def["id"]
        cat = check_def["cat"]
        point = ValidationPoint(
            id=cid,
            category=CheckCategory(cat),
            description=check_def["desc"],
            pzp_reference=check_def.get("pzp"),
        )

        # ══════════════════════════════════════════════════════════════════════
        # COMPLETENESS (1-12)
        # ══════════════════════════════════════════════════════════════════════
        if cat == "completeness":
            if cid == 1:
                # Formularz ofertowy
                if _has_doc("formularz", "ofertowy", "offer_form"):
                    point.status = CheckStatus.PASS
                elif offer is not None:
                    point.status = CheckStatus.WARNING
                    point.details = "Oferta w DB istnieje, brak pliku formularza — wymaga ręcznej weryfikacji"
                else:
                    point.status = CheckStatus.FAIL
                    point.details = "Brak formularza ofertowego i rekordu oferty w bazie"

            elif cid == 2:
                # Kosztorys
                if kosztorys is not None:
                    brutto = kosztorys.get("suma_brutto") or 0
                    if float(brutto) > 0:
                        point.status = CheckStatus.PASS
                        point.details = f"Kosztorys istnieje, suma brutto: {float(brutto):,.2f} PLN"
                    else:
                        point.status = CheckStatus.FAIL
                        point.details = "Kosztorys istnieje, ale suma_brutto = 0"
                        point.auto_fixable = False
                elif _has_doc("kosztorys"):
                    point.status = CheckStatus.WARNING
                    point.details = "Plik kosztorysu obecny, brak rekordu w tabeli kosztorys"
                else:
                    point.status = CheckStatus.FAIL
                    point.details = "Brak kosztorysu w bazie danych"

            elif cid == 3:
                if _has_doc("oswiadczenie", "wykluczenie", "zal_1", "zal1"):
                    point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — nie znaleziono pliku oświadczenia"

            elif cid == 4:
                if _has_doc("wykaz_robot", "wykaz robot", "zal_2", "zal2", "roboty"):
                    point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — nie znaleziono wykazu robót"

            elif cid == 5:
                if _has_doc("wykaz_osob", "wykaz osob", "zal_3", "zal3", "osoby"):
                    point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — nie znaleziono wykazu osób"

            elif cid == 6:
                # Zobowiązanie podmiotu trzeciego — conditional
                if _has_doc("zobowiazanie", "podmiot_trzeci", "zal_4", "zal4"):
                    point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.NOT_APPLICABLE
                    point.details = "Nie dotyczy lub wymaga ręcznej weryfikacji"

            elif cid == 7:
                # Pełnomocnictwo — conditional
                if _has_doc("pelnomocnictwo", "pełnomocnictwo"):
                    point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.NOT_APPLICABLE
                    point.details = "Nie dotyczy lub wymaga ręcznej weryfikacji"

            elif cid == 8:
                # Wadium
                if _has_doc("wadium", "gwarancja"):
                    point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak dokumentu wadium"

            elif cid == 9:
                if _has_doc("krs", "ceidg", "odpis"):
                    point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak odpisu KRS/CEIDG"

            elif cid == 10:
                if _has_doc("zus", "zaswiadczenie_zus"):
                    point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak zaświadczenia ZUS"

            elif cid == 11:
                if _has_doc("us_", "zaswiadczenie_us", "urzad_skarbowy"):
                    point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak zaświadczenia US"

            elif cid == 12:
                if _has_doc("polisa", "oc", "ubezpieczenie"):
                    point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.NOT_APPLICABLE
                    point.details = "Nie dotyczy lub wymaga ręcznej weryfikacji"

        # ══════════════════════════════════════════════════════════════════════
        # FORMAL (13-24)
        # ══════════════════════════════════════════════════════════════════════
        elif cat == "formal":
            if cid == 15:
                # Deadline check — use offer created_at vs tender deadline
                # If offer exists check created_at; no deadline field in offers table → WARNING
                if offer:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak pola deadline w ofercie"
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Brak oferty w bazie — nie można zweryfikować terminu"

            elif cid == 19:
                # Language — assumed Polish
                point.status = CheckStatus.PASS
                point.details = "Domyślnie: język polski"

            elif cid == 20:
                # File format check from parsed_docs
                if parsed_docs:
                    bad = [
                        d["filename"] for d in parsed_docs
                        if d.get("filename") and not any(
                            d["filename"].lower().endswith(ext)
                            for ext in (".pdf", ".docx", ".xml", ".zip", ".xlsx")
                        )
                    ]
                    if bad:
                        point.status = CheckStatus.FAIL
                        point.details = f"Niedozwolony format pliku: {', '.join(bad[:3])}"
                    else:
                        point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak dokumentów do analizy"

            elif cid == 22:
                # File naming — check parsed_ok flag
                if parsed_docs:
                    failed_parse = [d for d in parsed_docs if d.get("parsed_ok") is False]
                    if failed_parse:
                        point.status = CheckStatus.WARNING
                        point.details = f"{len(failed_parse)} dok. nie zostało sparsowanych poprawnie"
                    else:
                        point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji"

            else:
                point.status = CheckStatus.WARNING
                point.details = "Wymaga ręcznej weryfikacji"

        # ══════════════════════════════════════════════════════════════════════
        # FINANCIAL (25-34)
        # ══════════════════════════════════════════════════════════════════════
        elif cat == "financial":
            if cid == 25:
                # Cena w formularzu = suma kosztorysu
                if offer and kosztorys:
                    offer_price = float(offer.get("price_gross_pln") or 0)
                    kosz_brutto = float(kosztorys.get("suma_brutto") or 0)
                    if offer_price > 0 and kosz_brutto > 0:
                        diff = abs(offer_price - kosz_brutto)
                        if diff < 0.02:
                            point.status = CheckStatus.PASS
                        elif diff / max(offer_price, kosz_brutto) < 0.001:
                            point.status = CheckStatus.WARNING
                            point.details = f"Małe odchylenie: oferta={offer_price:,.2f}, kosztorys={kosz_brutto:,.2f}"
                        else:
                            point.status = CheckStatus.FAIL
                            point.details = f"Formularz: {offer_price:,.2f} PLN ≠ Kosztorys: {kosz_brutto:,.2f} PLN"
                            point.auto_fixable = True
                    else:
                        point.status = CheckStatus.WARNING
                        point.details = "Wymaga ręcznej weryfikacji — brak kwot"
                elif kosztorys:
                    point.status = CheckStatus.WARNING
                    point.details = "Brak oferty — nie można porównać ceny"
                else:
                    point.status = CheckStatus.FAIL
                    point.details = "Brak kosztorysu w bazie"

            elif cid == 26:
                # VAT rate 8% or 23%
                vat = None
                if kosztorys:
                    vat = float(kosztorys.get("vat_pct") or 0)
                elif offer:
                    vat = float(offer.get("vat_pct") or 0)
                if vat is not None:
                    if vat in (8.0, 23.0):
                        point.status = CheckStatus.PASS
                        point.details = f"VAT = {vat}%"
                    elif vat == 0:
                        point.status = CheckStatus.WARNING
                        point.details = "VAT = 0% — wymaga weryfikacji (ZW/odwrotne obciążenie?)"
                    else:
                        point.status = CheckStatus.FAIL
                        point.details = f"Nieoczekiwana stawka VAT: {vat}% (dozwolone: 8%, 23%)"
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak danych VAT"

            elif cid == 27:
                # netto + vat_amount = brutto
                if kosztorys:
                    netto = float(kosztorys.get("suma_netto") or 0)
                    vat_amt = float(kosztorys.get("suma_vat") or 0)
                    brutto = float(kosztorys.get("suma_brutto") or 0)
                    if netto > 0 and brutto > 0:
                        expected = netto + vat_amt
                        if abs(expected - brutto) < 0.02:
                            point.status = CheckStatus.PASS
                        else:
                            point.status = CheckStatus.FAIL
                            point.details = (
                                f"Netto ({netto:,.2f}) + VAT ({vat_amt:,.2f}) = {expected:,.2f} "
                                f"≠ Brutto ({brutto:,.2f})"
                            )
                            point.auto_fixable = True
                    else:
                        point.status = CheckStatus.WARNING
                        point.details = "Wymaga ręcznej weryfikacji — brak kwot kosztorysu"
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak kosztorysu"

            elif cid == 28:
                # Kwota słownie — nie da się sprawdzić automatycznie
                point.status = CheckStatus.WARNING
                point.details = "Wymaga ręcznej weryfikacji — porównanie kwoty słownie/liczbowo"

            elif cid == 29:
                # Zero-value positions in kosztorys — can check suma_r/m/s
                if kosztorys:
                    zeros = []
                    for col in ("suma_r", "suma_m", "suma_s"):
                        val = kosztorys.get(col)
                        if val is not None and float(val) == 0:
                            zeros.append(col)
                    if zeros:
                        point.status = CheckStatus.WARNING
                        point.details = f"Zerowe składniki: {', '.join(zeros)} — sprawdź pozycje kosztorysu"
                    else:
                        point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak kosztorysu"

            elif cid == 30:
                # Rażąco niska cena
                if bid_intel and kosztorys:
                    our = float(kosztorys.get("suma_brutto") or 0)
                    benchmark = float(bid_intel.get("market_benchmark_pct") or 0)
                    if our > 0 and benchmark > 0:
                        ratio = our / benchmark
                        if ratio < 0.70:
                            point.status = CheckStatus.FAIL
                            point.details = f"Cena = {ratio*100:.0f}% benchmarku — ryzyko odrzucenia"
                        elif ratio < 0.80:
                            point.status = CheckStatus.WARNING
                            point.details = f"Cena = {ratio*100:.0f}% benchmarku — możliwe wezwanie"
                        else:
                            point.status = CheckStatus.PASS
                    elif kosztorys.get("win_probability") is not None:
                        wp = float(kosztorys["win_probability"])
                        if wp < 0.2:
                            point.status = CheckStatus.WARNING
                            point.details = f"Niskie P(win) = {wp:.0%} — możliwa cena niekonkurencyjna"
                        else:
                            point.status = CheckStatus.PASS
                    else:
                        point.status = CheckStatus.WARNING
                        point.details = "Wymaga ręcznej weryfikacji — brak danych benchmarku"
                elif kosztorys and kosztorys.get("benchmark_percentile") is not None:
                    bp = float(kosztorys["benchmark_percentile"])
                    if bp < 20:
                        point.status = CheckStatus.WARNING
                        point.details = f"Percentyl benchmarku = {bp:.0f}% — niska cena względem rynku"
                    else:
                        point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak danych benchmarku"

            elif cid == 31:
                point.status = CheckStatus.WARNING
                point.details = "Wymaga ręcznej weryfikacji — wysokość wadium zależy od SWZ"

            elif cid == 32:
                point.status = CheckStatus.WARNING
                point.details = "Wymaga ręcznej weryfikacji — ważność wadium"

            elif cid == 33:
                # Currency — assumed PLN (no currency field in offers/kosztorys)
                if offer and offer.get("price_gross_pln") is not None:
                    point.status = CheckStatus.PASS
                    point.details = "Kwota w polu price_gross_pln — zakładamy PLN"
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji"

            elif cid == 34:
                # Kp i Z rates
                if kosztorys:
                    ko_r = float(kosztorys.get("ko_r_pct") or 0)
                    ko_s = float(kosztorys.get("ko_s_pct") or 0)
                    z = float(kosztorys.get("z_pct") or 0)
                    issues = []
                    if ko_r > 0 and not (50 <= ko_r <= 90):
                        issues.append(f"Ko_R={ko_r}% (norma: 50-90%)")
                    if ko_s > 0 and not (50 <= ko_s <= 90):
                        issues.append(f"Ko_S={ko_s}% (norma: 50-90%)")
                    if z > 0 and not (5 <= z <= 20):
                        issues.append(f"Z={z}% (norma: 5-20%)")
                    if issues:
                        point.status = CheckStatus.WARNING
                        point.details = "; ".join(issues)
                    else:
                        point.status = CheckStatus.PASS
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak kosztorysu"

        # ══════════════════════════════════════════════════════════════════════
        # LEGAL (35-41)
        # ══════════════════════════════════════════════════════════════════════
        elif cat == "legal":
            # Legal checks require document content analysis
            if cid == 35:
                if _has_doc("art_108", "wykluczenie_obligatoryjne", "oswiadczenie"):
                    point.status = CheckStatus.WARNING
                    point.details = "Dokument znaleziony — wymaga ręcznej weryfikacji treści"
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — oświadczenie art. 108"

            elif cid == 36:
                if _has_doc("art_109", "wykluczenie_fakultatywne"):
                    point.status = CheckStatus.WARNING
                    point.details = "Dokument znaleziony — wymaga ręcznej weryfikacji treści"
                else:
                    point.status = CheckStatus.NOT_APPLICABLE
                    point.details = "Nie dotyczy lub wymaga ręcznej weryfikacji"

            elif cid == 37:
                if _has_doc("sankcyjne", "ustawa_2022"):
                    point.status = CheckStatus.WARNING
                    point.details = "Dokument znaleziony — wymaga ręcznej weryfikacji treści"
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — oświadczenie sankcyjne"

            elif cid in (38, 39, 40, 41):
                point.status = CheckStatus.WARNING
                point.details = "Wymaga ręcznej weryfikacji"

        # ══════════════════════════════════════════════════════════════════════
        # TECHNICAL (42-47)
        # ══════════════════════════════════════════════════════════════════════
        elif cat == "technical":
            if cid == 42:
                if _has_doc("kierownik", "uprawnienia", "wykaz_osob"):
                    point.status = CheckStatus.WARNING
                    point.details = "Dokument znaleziony — wymaga weryfikacji uprawnień"
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — brak danych o kadrze"

            elif cid == 43:
                point.status = CheckStatus.WARNING
                point.details = "Wymaga ręcznej weryfikacji — doświadczenie kadry"

            elif cid == 44:
                point.status = CheckStatus.WARNING
                point.details = "Wymaga ręcznej weryfikacji — wartość referencyjna robót"

            elif cid == 45:
                point.status = CheckStatus.WARNING
                point.details = "Wymaga ręcznej weryfikacji — zakres referencji"

            elif cid == 46:
                if _has_doc("polisa", "oc"):
                    point.status = CheckStatus.WARNING
                    point.details = "Polisa znaleziona — wymaga weryfikacji sumy gwarancyjnej"
                else:
                    point.status = CheckStatus.WARNING
                    point.details = "Wymaga ręcznej weryfikacji — polisa OC"

            elif cid == 47:
                point.status = CheckStatus.WARNING
                point.details = "Wymaga ręcznej weryfikacji — potencjał techniczny"

        result.points.append(point)

    # ─── Statistics ────────────────────────────────────────────────────────
    result.passed = sum(1 for p in result.points if p.status == CheckStatus.PASS)
    result.failed = sum(1 for p in result.points if p.status == CheckStatus.FAIL)
    result.warnings = sum(1 for p in result.points if p.status == CheckStatus.WARNING)
    result.not_applicable = sum(1 for p in result.points if p.status == CheckStatus.NOT_APPLICABLE)

    if result.failed > 0:
        result.status = "failed"
    elif result.warnings > 0 and strict_mode:
        result.status = "failed"
    elif result.warnings > 0:
        result.status = "warnings"
    else:
        result.status = "passed"

    result.critical_issues = [
        f"[#{p.id}] {p.description}: {p.details}"
        for p in result.points
        if p.status == CheckStatus.FAIL
    ]

    result.recommendations = _generate_recommendations(result)

    return result


def _generate_recommendations(result: "ValidationResult") -> list[str]:
    """Generate actionable recommendations based on validation results."""
    recs = []

    failed_points = [p for p in result.points if p.status == CheckStatus.FAIL]
    auto_fixable = [p for p in failed_points if p.auto_fixable]

    if auto_fixable:
        recs.append(
            f"{len(auto_fixable)} błędów może być naprawionych automatycznie. "
            "Uruchom auto-fix."
        )

    missing_docs = [p for p in failed_points if p.category == CheckCategory.COMPLETENESS]
    if missing_docs:
        recs.append(
            f"Brakuje {len(missing_docs)} dokumentów. "
            "Użyj /v1/assembly/generate do wygenerowania."
        )

    financial_issues = [
        p for p in result.points
        if p.category == CheckCategory.FINANCIAL
        and p.status in (CheckStatus.FAIL, CheckStatus.WARNING)
    ]
    if financial_issues:
        recs.append("Sprawdź kalkulację cenową — wykryto niespójności finansowe.")

    warning_count = sum(1 for p in result.points if p.status == CheckStatus.WARNING)
    if warning_count > 10:
        recs.append(
            f"{warning_count} punktów wymaga ręcznej weryfikacji — "
            "zalecamy przegląd dokumentacji przed złożeniem oferty."
        )

    if not recs and result.status == "passed":
        recs.append("Oferta przeszła walidację pomyślnie. Gotowa do złożenia.")

    return recs


# ─── Validation Engine (async, original interface — preserved) ───────────────

class ValidationEngine:
    """
    Runs 47-point validation checklist on a bid package.

    Checks:
    - Document existence and completeness
    - Formal requirements (signatures, dates, format)
    - Financial consistency (arithmetic, VAT, price matching)
    - Legal compliance (PZP declarations)
    - Technical qualification (personnel, experience)

    async validate() — original interface (accepts dicts, no DB).
    validate_bid()   — new DB-backed synchronous interface.
    """

    async def validate(
        self,
        bid_id: UUID,
        documents: list[dict],
        estimate: dict,
        company: dict,
        tender: dict,
        strict_mode: bool = True,
        categories: Optional[list[str]] = None,
    ) -> ValidationResult:
        """
        Run full 47-point validation.

        Args:
            bid_id: Bid UUID
            documents: List of generated documents with metadata
            estimate: Cost estimate data
            company: Company profile data
            tender: Tender requirements
            strict_mode: If True, warnings also count as failures
            categories: Run only specific categories (None = all)
        """
        result = ValidationResult(bid_id=bid_id)

        for check_def in CHECKLIST_47:
            # Filter by category if specified
            if categories and check_def["cat"] not in categories:
                continue

            point = ValidationPoint(
                id=check_def["id"],
                category=CheckCategory(check_def["cat"]),
                description=check_def["desc"],
                pzp_reference=check_def.get("pzp"),
            )

            # Run appropriate check
            await self._run_check(point, documents, estimate, company, tender)
            result.points.append(point)

        # Calculate stats
        result.passed = sum(1 for p in result.points if p.status == CheckStatus.PASS)
        result.failed = sum(1 for p in result.points if p.status == CheckStatus.FAIL)
        result.warnings = sum(1 for p in result.points if p.status == CheckStatus.WARNING)
        result.not_applicable = sum(1 for p in result.points if p.status == CheckStatus.NOT_APPLICABLE)

        # Determine overall status
        if result.failed > 0:
            result.status = "failed"
        elif result.warnings > 0 and strict_mode:
            result.status = "failed"
        elif result.warnings > 0:
            result.status = "warnings"
        else:
            result.status = "passed"

        # Collect critical issues
        result.critical_issues = [
            f"[#{p.id}] {p.description}: {p.details}"
            for p in result.points
            if p.status == CheckStatus.FAIL
        ]

        # Generate recommendations
        result.recommendations = _generate_recommendations(result)

        return result

    async def _run_check(
        self,
        point: ValidationPoint,
        documents: list[dict],
        estimate: dict,
        company: dict,
        tender: dict,
    ) -> None:
        """Run a single validation check and update point status."""

        # ─── COMPLETENESS checks ───────────────────────────────────────
        if point.category == CheckCategory.COMPLETENESS:
            await self._check_completeness(point, documents, tender)

        # ─── FORMAL checks ─────────────────────────────────────────────
        elif point.category == CheckCategory.FORMAL:
            await self._check_formal(point, documents, tender)

        # ─── FINANCIAL checks ──────────────────────────────────────────
        elif point.category == CheckCategory.FINANCIAL:
            await self._check_financial(point, estimate, tender)

        # ─── LEGAL checks ──────────────────────────────────────────────
        elif point.category == CheckCategory.LEGAL:
            await self._check_legal(point, documents, tender)

        # ─── TECHNICAL checks ──────────────────────────────────────────
        elif point.category == CheckCategory.TECHNICAL:
            await self._check_technical(point, company, tender)

    async def _check_completeness(
        self, point: ValidationPoint, documents: list[dict], tender: dict
    ) -> None:
        """Check document completeness."""
        doc_type_map = {
            1: "formularz_ofertowy",
            2: "kosztorys_ofertowy",
            3: "oswiadczenie_wykluczenie",
            4: "wykaz_robot",
            5: "wykaz_osob",
            6: "zobowiazanie_podmiotu",
            7: "pelnomocnictwo",
            8: "wadium_confirmation",
            9: "odpis_krs",
            10: "zaswiadczenie_zus",
            11: "zaswiadczenie_us",
            12: "polisa_oc",
        }

        required_type = doc_type_map.get(point.id)
        if not required_type:
            return

        # Check if document exists
        doc_exists = any(d.get("doc_type") == required_type for d in documents)

        # Some documents are conditional
        optional_ids = {6, 7, 12}  # conditional on tender requirements
        if point.id in optional_ids:
            # Check if tender requires it
            is_required = tender.get(f"requires_{required_type}", False)
            if not is_required:
                point.status = CheckStatus.NOT_APPLICABLE
                point.details = "Nie wymagane w tym postępowaniu"
                return

        # Check wadium
        if point.id == 8:
            wadium_required = tender.get("wadium", 0) > 0
            if not wadium_required:
                point.status = CheckStatus.NOT_APPLICABLE
                point.details = "Wadium nie jest wymagane"
                return

        if doc_exists:
            point.status = CheckStatus.PASS
        else:
            point.status = CheckStatus.FAIL
            point.details = f"Brak dokumentu: {required_type}"
            point.auto_fixable = point.id in {1, 2, 3, 4, 5}  # can be auto-generated

    async def _check_formal(
        self, point: ValidationPoint, documents: list[dict], tender: dict
    ) -> None:
        """Check formal requirements."""
        if point.id == 15:
            for doc in documents:
                doc_date = doc.get("created_at")
                deadline = tender.get("deadline")
                if doc_date and deadline and doc_date > deadline:
                    point.status = CheckStatus.FAIL
                    point.details = "Data dokumentu po terminie składania ofert"
                    return
            point.status = CheckStatus.PASS
        elif point.id == 19:
            point.status = CheckStatus.PASS
        elif point.id == 20:
            allowed_formats = {"pdf", "docx", "xml", "zip"}
            for doc in documents:
                ext = doc.get("filename", "").rsplit(".", 1)[-1].lower()
                if ext not in allowed_formats:
                    point.status = CheckStatus.FAIL
                    point.details = f"Niedozwolony format: .{ext}"
                    return
            point.status = CheckStatus.PASS
        else:
            point.status = CheckStatus.WARNING
            point.details = "Wymaga weryfikacji manualnej"

    async def _check_financial(
        self, point: ValidationPoint, estimate: dict, tender: dict
    ) -> None:
        """Check financial consistency."""
        if point.id == 25:
            form_price = estimate.get("total_gross_form", 0)
            calc_price = estimate.get("total_gross", 0)
            if form_price and calc_price and abs(form_price - calc_price) > 0.01:
                point.status = CheckStatus.FAIL
                point.details = f"Formularz: {form_price:.2f}, Kosztorys: {calc_price:.2f}"
                point.auto_fixable = True
            else:
                point.status = CheckStatus.PASS

        elif point.id == 27:
            net = estimate.get("total_net", 0)
            vat = estimate.get("total_vat", 0)
            gross = estimate.get("total_gross", 0)
            if net and gross and abs((net + vat) - gross) > 0.01:
                point.status = CheckStatus.FAIL
                point.details = f"Netto ({net:.2f}) + VAT ({vat:.2f}) ≠ Brutto ({gross:.2f})"
                point.auto_fixable = True
            else:
                point.status = CheckStatus.PASS

        elif point.id == 29:
            lines = estimate.get("lines", [])
            zero_lines = [l for l in lines if l.get("net_total", 0) == 0]
            if zero_lines:
                point.status = CheckStatus.WARNING
                point.details = f"{len(zero_lines)} pozycji z wartością 0 PLN"
            else:
                point.status = CheckStatus.PASS

        elif point.id == 30:
            estimated_value = tender.get("estimated_value", 0)
            our_price = estimate.get("total_gross", 0)
            if estimated_value and our_price:
                ratio = our_price / estimated_value
                if ratio < 0.70:
                    point.status = CheckStatus.FAIL
                    point.details = (
                        f"Cena ({our_price:,.0f} PLN) stanowi {ratio*100:.0f}% szacunku "
                        f"({estimated_value:,.0f} PLN) — ryzyko odrzucenia jako rażąco niska"
                    )
                elif ratio < 0.80:
                    point.status = CheckStatus.WARNING
                    point.details = f"Cena = {ratio*100:.0f}% szacunku — możliwe wezwanie do wyjaśnień"
                else:
                    point.status = CheckStatus.PASS
            else:
                point.status = CheckStatus.PASS

        elif point.id == 34:
            kp_rate = estimate.get("avg_kp_rate", 70)
            z_rate = estimate.get("avg_z_rate", 10)
            issues = []
            if kp_rate < 60 or kp_rate > 80:
                issues.append(f"Kp={kp_rate}% (norma: 65-75%)")
            if z_rate < 5 or z_rate > 18:
                issues.append(f"Z={z_rate}% (norma: 8-15%)")
            if issues:
                point.status = CheckStatus.WARNING
                point.details = "; ".join(issues)
            else:
                point.status = CheckStatus.PASS
        else:
            point.status = CheckStatus.PASS

    async def _check_legal(
        self, point: ValidationPoint, documents: list[dict], tender: dict
    ) -> None:
        """Check legal compliance."""
        point.status = CheckStatus.WARNING
        point.details = "Wymaga weryfikacji treści oświadczenia"

    async def _check_technical(
        self, point: ValidationPoint, company: dict, tender: dict
    ) -> None:
        """Check technical qualification requirements."""
        if point.id == 42:
            required_permits = tender.get("required_permits", [])
            company_permits = company.get("uprawnienia_budowlane", [])
            missing = set(required_permits) - set(company_permits)
            if missing:
                point.status = CheckStatus.FAIL
                point.details = f"Brak wymaganych uprawnień: {', '.join(missing)}"
            else:
                point.status = CheckStatus.PASS

        elif point.id == 44:
            required_value = tender.get("min_reference_value", 0)
            max_reference = company.get("max_reference_value", 0)
            if required_value and max_reference < required_value:
                point.status = CheckStatus.FAIL
                point.details = (
                    f"Wymagana referencja >= {required_value:,.0f} PLN, "
                    f"najwyższa posiadana: {max_reference:,.0f} PLN"
                )
            else:
                point.status = CheckStatus.PASS

        elif point.id == 46:
            required_oc = tender.get("min_polisa_oc", 0)
            company_oc = company.get("polisa_oc_kwota", 0)
            if required_oc and (not company_oc or company_oc < required_oc):
                point.status = CheckStatus.FAIL
                point.details = (
                    f"Wymagana polisa OC >= {required_oc:,.0f} PLN, "
                    f"posiadana: {company_oc:,.0f} PLN"
                )
            else:
                point.status = CheckStatus.PASS
        else:
            point.status = CheckStatus.WARNING
            point.details = "Wymaga weryfikacji manualnej"
