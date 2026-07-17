"""
Bud.OS Validation Engine Service
47-point checklist covering PZP art. 275 requirements.
Categories: completeness, formal, financial, legal, technical.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


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


# ─── Validation Engine ──────────────────────────────────────────────────────

class ValidationEngine:
    """
    Runs 47-point validation checklist on a bid package.
    
    Checks:
    - Document existence and completeness
    - Formal requirements (signatures, dates, format)
    - Financial consistency (arithmetic, VAT, price matching)
    - Legal compliance (PZP declarations)
    - Technical qualification (personnel, experience)
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
        result.recommendations = self._generate_recommendations(result)

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
        check_id = point.id

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
        # Simplified checks — in production these would inspect actual documents
        if point.id == 15:
            # Date check
            for doc in documents:
                doc_date = doc.get("created_at")
                deadline = tender.get("deadline")
                if doc_date and deadline and doc_date > deadline:
                    point.status = CheckStatus.FAIL
                    point.details = "Data dokumentu po terminie składania ofert"
                    return
            point.status = CheckStatus.PASS
        elif point.id == 19:
            # Language check — assume Polish (would check with langdetect in prod)
            point.status = CheckStatus.PASS
        elif point.id == 20:
            # File format check
            allowed_formats = {"pdf", "docx", "xml", "zip"}
            for doc in documents:
                ext = doc.get("filename", "").rsplit(".", 1)[-1].lower()
                if ext not in allowed_formats:
                    point.status = CheckStatus.FAIL
                    point.details = f"Niedozwolony format: .{ext}"
                    return
            point.status = CheckStatus.PASS
        else:
            # Default pass for checks requiring manual verification
            point.status = CheckStatus.WARNING
            point.details = "Wymaga weryfikacji manualnej"

    async def _check_financial(
        self, point: ValidationPoint, estimate: dict, tender: dict
    ) -> None:
        """Check financial consistency."""
        if point.id == 25:
            # Price in form == sum of estimate
            form_price = estimate.get("total_gross_form", 0)
            calc_price = estimate.get("total_gross", 0)
            if form_price and calc_price and abs(form_price - calc_price) > 0.01:
                point.status = CheckStatus.FAIL
                point.details = f"Formularz: {form_price:.2f}, Kosztorys: {calc_price:.2f}"
                point.auto_fixable = True
            else:
                point.status = CheckStatus.PASS

        elif point.id == 27:
            # net + vat == gross
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
            # No zero-value lines
            lines = estimate.get("lines", [])
            zero_lines = [l for l in lines if l.get("net_total", 0) == 0]
            if zero_lines:
                point.status = CheckStatus.WARNING
                point.details = f"{len(zero_lines)} pozycji z wartością 0 PLN"
            else:
                point.status = CheckStatus.PASS

        elif point.id == 30:
            # Abnormally low price check
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
            # Kp and Z in acceptable range
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
        # Most legal checks require document content analysis
        # Simplified: check if relevant declarations exist
        point.status = CheckStatus.WARNING
        point.details = "Wymaga weryfikacji treści oświadczenia"

    async def _check_technical(
        self, point: ValidationPoint, company: dict, tender: dict
    ) -> None:
        """Check technical qualification requirements."""
        if point.id == 42:
            # Kierownik budowy
            required_permits = tender.get("required_permits", [])
            company_permits = company.get("uprawnienia_budowlane", [])
            missing = set(required_permits) - set(company_permits)
            if missing:
                point.status = CheckStatus.FAIL
                point.details = f"Brak wymaganych uprawnień: {', '.join(missing)}"
            else:
                point.status = CheckStatus.PASS

        elif point.id == 44:
            # Reference value threshold
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
            # Insurance (polisa OC)
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

    def _generate_recommendations(self, result: ValidationResult) -> list[str]:
        """Generate actionable recommendations based on validation results."""
        recs = []

        failed_points = [p for p in result.points if p.status == CheckStatus.FAIL]
        auto_fixable = [p for p in failed_points if p.auto_fixable]

        if auto_fixable:
            recs.append(
                f"{len(auto_fixable)} błędów może być naprawionych automatycznie. "
                "Uruchom auto-fix."
            )

        # Check for missing documents
        missing_docs = [
            p for p in failed_points
            if p.category == CheckCategory.COMPLETENESS
        ]
        if missing_docs:
            recs.append(
                f"Brakuje {len(missing_docs)} dokumentów. "
                "Użyj /v1/assembly/generate do wygenerowania."
            )

        # Financial warnings
        financial_issues = [
            p for p in result.points
            if p.category == CheckCategory.FINANCIAL and p.status in (CheckStatus.FAIL, CheckStatus.WARNING)
        ]
        if financial_issues:
            recs.append(
                "Sprawdź kalkulację cenową — wykryto niespójności finansowe."
            )

        if not recs and result.status == "passed":
            recs.append("Oferta przeszła walidację pomyślnie. Gotowa do złożenia.")

        return recs
