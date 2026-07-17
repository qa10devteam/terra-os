"""
Bud.OS Submit Router — /v1/submit
Submission Wizard (7 kroków), final confirmation, post-submission tracking.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class WizardStepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class WizardStep(BaseModel):
    step_nr: int
    title: str
    description: str
    status: WizardStepStatus
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    is_required: bool = True
    blockers: list[str] = []


class WizardResponse(BaseModel):
    bid_id: UUID
    tender_title: str
    deadline: datetime
    current_step: int
    total_steps: int = 7
    steps: list[WizardStep]
    overall_progress_pct: float
    can_submit: bool
    time_remaining: Optional[str] = None  # e.g. "2d 4h 15min"


class StepConfirmRequest(BaseModel):
    confirmed: bool = True
    notes: Optional[str] = None
    attachments: list[str] = Field(default=[], description="S3 keys of uploaded files")


class StepConfirmResponse(BaseModel):
    bid_id: UUID
    step_nr: int
    status: WizardStepStatus
    message: str
    next_step: Optional[int] = None


class FinalConfirmRequest(BaseModel):
    """Final confirmation before submission — requires explicit acknowledgements."""
    confirm_price_correct: bool = Field(..., description="Potwierdzam poprawność ceny ofertowej")
    confirm_documents_complete: bool = Field(..., description="Potwierdzam kompletność dokumentów")
    confirm_deadline_met: bool = Field(..., description="Potwierdzam złożenie przed terminem")
    confirm_authorized: bool = Field(..., description="Potwierdzam upoważnienie do złożenia oferty")
    electronic_signature_id: Optional[str] = Field(None, description="ID podpisu kwalifikowanego (jeśli wymagany)")


class FinalConfirmResponse(BaseModel):
    bid_id: UUID
    submission_status: str  # "confirmed" | "submitting" | "submitted" | "error"
    submission_id: Optional[str] = None  # e-Zamówienia submission ID
    submitted_at: Optional[datetime] = None
    confirmation_hash: Optional[str] = None  # SHA-256 of submitted package
    message: str


class TrackingEvent(BaseModel):
    timestamp: datetime
    event: str
    description: str
    source: str  # "system" | "e-zamowienia" | "zamawiajacy"


class TrackingResponse(BaseModel):
    bid_id: UUID
    tender_id: UUID
    submission_status: str  # "draft" | "confirmed" | "submitted" | "opened" | "evaluated" | "won" | "lost"
    submitted_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    result: Optional[str] = None  # "won" | "lost" | "pending"
    ranking_position: Optional[int] = None
    total_bidders: Optional[int] = None
    our_price: Optional[float] = None
    winning_price: Optional[float] = None
    events: list[TrackingEvent]
    next_expected_event: Optional[str] = None


# ─── Default wizard steps ───────────────────────────────────────────────────

WIZARD_STEPS = [
    WizardStep(
        step_nr=1,
        title="Kosztorys zatwierdzony",
        description="Sprawdź i zatwierdź kosztorys ofertowy (wszystkie pozycje, ceny, narzuty)",
        status=WizardStepStatus.PENDING,
        is_required=True,
    ),
    WizardStep(
        step_nr=2,
        title="Dokumenty wygenerowane",
        description="Wygeneruj komplet dokumentów ofertowych (Formularz, Załączniki 1-4, Kosztorys)",
        status=WizardStepStatus.PENDING,
        is_required=True,
    ),
    WizardStep(
        step_nr=3,
        title="Walidacja przeszła",
        description="47-point validation checklist — brak błędów krytycznych",
        status=WizardStepStatus.PENDING,
        is_required=True,
    ),
    WizardStep(
        step_nr=4,
        title="Podpis elektroniczny",
        description="Podpisz dokumenty podpisem kwalifikowanym (e-podpis / profil zaufany)",
        status=WizardStepStatus.PENDING,
        is_required=True,
    ),
    WizardStep(
        step_nr=5,
        title="Wadium wpłacone",
        description="Potwierdź wpłatę wadium (przelew / gwarancja bankowa / ubezpieczeniowa)",
        status=WizardStepStatus.PENDING,
        is_required=False,  # not all tenders require wadium
    ),
    WizardStep(
        step_nr=6,
        title="Przegląd końcowy",
        description="Ostateczny przegląd oferty — sprawdź cenę, termin, kompletność",
        status=WizardStepStatus.PENDING,
        is_required=True,
    ),
    WizardStep(
        step_nr=7,
        title="Złożenie oferty",
        description="Złóż ofertę na platformie e-Zamówienia / miniPortal",
        status=WizardStepStatus.PENDING,
        is_required=True,
    ),
]


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/wizard/{bid_id}", response_model=WizardResponse)
async def get_wizard_status(bid_id: UUID):
    """
    Status Submission Wizard — 7 kroków do złożenia oferty.
    
    Kroki:
    1. Kosztorys zatwierdzony
    2. Dokumenty wygenerowane
    3. Walidacja przeszła (47 points)
    4. Podpis elektroniczny
    5. Wadium wpłacone (jeśli wymagane)
    6. Przegląd końcowy
    7. Złożenie oferty
    
    Automatycznie sprawdza które kroki są completed na podstawie stanu w DB.
    """
    # TODO: fetch bid state, check which steps are done
    completed = 0
    progress = (completed / 7) * 100

    return WizardResponse(
        bid_id=bid_id,
        tender_title="Budowa drogi gminnej w m. Przykładowo",
        deadline=datetime(2025, 3, 15, 10, 0),
        current_step=1,
        steps=WIZARD_STEPS,
        overall_progress_pct=progress,
        can_submit=False,
        time_remaining="5d 12h 30min",
    )


@router.post("/wizard/{bid_id}/step/{step_nr}", response_model=StepConfirmResponse)
async def confirm_step(bid_id: UUID, step_nr: int, payload: StepConfirmRequest):
    """
    Potwierdź ukończenie kroku w wizard.
    
    Waliduje czy krok może być potwierdzony (zależności od poprzednich kroków).
    Np. krok 3 (walidacja) wymaga ukończenia kroku 2 (dokumenty).
    """
    if step_nr < 1 or step_nr > 7:
        raise HTTPException(status_code=400, detail="Step must be 1-7")

    if not payload.confirmed:
        return StepConfirmResponse(
            bid_id=bid_id,
            step_nr=step_nr,
            status=WizardStepStatus.PENDING,
            message="Krok nie potwierdzony.",
            next_step=step_nr,
        )

    # TODO: validate dependencies, update DB
    next_step = step_nr + 1 if step_nr < 7 else None
    return StepConfirmResponse(
        bid_id=bid_id,
        step_nr=step_nr,
        status=WizardStepStatus.COMPLETED,
        message=f"Krok {step_nr} potwierdzony.",
        next_step=next_step,
    )


@router.post("/confirm/{bid_id}", response_model=FinalConfirmResponse)
async def final_confirm(bid_id: UUID, payload: FinalConfirmRequest):
    """
    Final confirmation — ostatni krok przed złożeniem oferty.
    
    Wymagane potwierdzenia:
    - Cena ofertowa jest poprawna
    - Dokumenty są kompletne
    - Termin składania zostanie dotrzymany
    - Osoba składająca jest upoważniona
    
    Po potwierdzeniu: generuje paczkę ZIP, hashuje SHA-256, przygotowuje do uploadu.
    """
    # Validate all confirmations
    if not all([
        payload.confirm_price_correct,
        payload.confirm_documents_complete,
        payload.confirm_deadline_met,
        payload.confirm_authorized,
    ]):
        raise HTTPException(
            status_code=400,
            detail="Wszystkie potwierdzenia muszą być zaznaczone (true)."
        )

    # TODO: check all wizard steps completed, generate submission package
    return FinalConfirmResponse(
        bid_id=bid_id,
        submission_status="confirmed",
        message="Oferta potwierdzona i gotowa do złożenia. Paczka wygenerowana.",
        confirmation_hash="sha256:a1b2c3d4e5f6...",
    )


@router.get("/tracking/{bid_id}", response_model=TrackingResponse)
async def get_tracking(bid_id: UUID):
    """
    Post-submission tracking — śledzenie statusu złożonej oferty.
    
    Monitoruje:
    - Status na platformie e-Zamówienia
    - Otwarcie ofert
    - Wynik oceny (ranking, cena zwycięska)
    - Ewentualne wezwania do wyjaśnień
    """
    # TODO: fetch submission tracking from DB + e-Zamówienia API
    return TrackingResponse(
        bid_id=bid_id,
        tender_id=uuid4(),
        submission_status="submitted",
        submitted_at=datetime.utcnow(),
        events=[],
        next_expected_event="Otwarcie ofert (planowane: 2025-03-15 10:30)",
    )
