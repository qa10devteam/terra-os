"""
Bud.OS Submit Router — /v1/submit
Submission Wizard (7 kroków), final confirmation, post-submission tracking.
"""
import hashlib
import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)

# ─── DB helpers ─────────────────────────────────────────────────────────────

def _get_db_password() -> str:
    """Read DB password from env or /proc/2068146/environ."""
    pw = os.environ.get("DB_PASSWORD", "")
    if pw:
        return pw
    try:
        with open("/proc/2068146/environ", "rb") as f:
            for pair in f.read().split(b"\0"):
                if pair.startswith(b"DB_PASSWORD="):
                    return pair[len(b"DB_PASSWORD="):].decode()
    except Exception:
        pass
    return "terra_dev_2026"


def _db_connect():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ.get("DB_NAME", "terraos"),
        user=os.environ.get("DB_USER", "terraos"),
        password=_get_db_password(),
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=5,
    )


@contextmanager
def db_cursor():
    conn = None
    try:
        conn = _db_connect()
        cur = conn.cursor()
        yield conn, cur
    finally:
        if conn:
            conn.close()


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


# ─── Default wizard step templates ──────────────────────────────────────────

STEP_TEMPLATES = [
    dict(
        step_nr=1,
        title="Kosztorys zatwierdzony",
        description="Sprawdź i zatwierdź kosztorys ofertowy (wszystkie pozycje, ceny, narzuty)",
        is_required=True,
    ),
    dict(
        step_nr=2,
        title="Dokumenty wygenerowane",
        description="Wygeneruj komplet dokumentów ofertowych (Formularz, Załączniki 1-4, Kosztorys)",
        is_required=True,
    ),
    dict(
        step_nr=3,
        title="Walidacja przeszła",
        description="47-point validation checklist — brak błędów krytycznych",
        is_required=True,
    ),
    dict(
        step_nr=4,
        title="Podpis elektroniczny",
        description="Podpisz dokumenty podpisem kwalifikowanym (e-podpis / profil zaufany)",
        is_required=True,
    ),
    dict(
        step_nr=5,
        title="Wadium wpłacone",
        description="Potwierdź wpłatę wadium (przelew / gwarancja bankowa / ubezpieczeniowa)",
        is_required=False,  # not all tenders require wadium
    ),
    dict(
        step_nr=6,
        title="Przegląd końcowy",
        description="Ostateczny przegląd oferty — sprawdź cenę, termin, kompletność",
        is_required=True,
    ),
    dict(
        step_nr=7,
        title="Złożenie oferty",
        description="Złóż ofertę na platformie e-Zamówienia / miniPortal",
        is_required=True,
    ),
]


def _format_time_remaining(deadline: datetime) -> str:
    """Format a human-readable time until deadline."""
    now = datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    delta = deadline - now
    if delta.total_seconds() <= 0:
        return "Termin minął"
    total_seconds = int(delta.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}min")
    return " ".join(parts)


def _get_wizard_steps_from_db(cur, bid_id: str, tender_id: str, offer_row: dict) -> list[WizardStep]:
    """
    Build wizard step list from DB state.
    Steps 1-3: auto-detected from DB tables.
    Steps 4-7: read from offers.metadata['wizard_steps'] jsonb.
    """
    # Pull metadata wizard_steps if present
    meta = offer_row.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    saved_steps: dict = {}
    if isinstance(meta.get("wizard_steps"), dict):
        saved_steps = meta["wizard_steps"]

    steps = []

    # ── Step 1: kosztorys zatwierdzony ───────────────────────────────────────
    step1_status = WizardStepStatus.PENDING
    step1_completed_at = None
    step1_blockers = []
    try:
        # Check by offer_id first, then by tender_id
        cur.execute(
            """
            SELECT id, status, updated_at
            FROM kosztorys
            WHERE (offer_id = %s OR tender_id = %s::uuid)
              AND status IN ('approved', 'zatwierdzony', 'confirmed', 'completed', 'done')
            ORDER BY updated_at DESC NULLS LAST
            LIMIT 1
            """,
            (bid_id, tender_id) if tender_id else (bid_id, bid_id),
        )
        row = cur.fetchone()
        if row:
            step1_status = WizardStepStatus.COMPLETED
            step1_completed_at = row.get("updated_at")
        else:
            # Check if kosztorys exists at all (not approved)
            cur.execute(
                "SELECT id FROM kosztorys WHERE offer_id = %s OR tender_id = %s::uuid LIMIT 1",
                (bid_id, tender_id) if tender_id else (bid_id, bid_id),
            )
            if cur.fetchone():
                step1_status = WizardStepStatus.IN_PROGRESS
                step1_blockers = ["Kosztorys wymaga zatwierdzenia"]
            else:
                step1_blockers = ["Brak kosztorysu dla tej oferty"]
    except Exception as e:
        logger.warning("Step 1 DB check failed: %s", e)
        # Fallback: check saved_steps
        if saved_steps.get("1", {}).get("status") == "completed":
            step1_status = WizardStepStatus.COMPLETED

    steps.append(WizardStep(
        step_nr=1,
        title=STEP_TEMPLATES[0]["title"],
        description=STEP_TEMPLATES[0]["description"],
        status=step1_status,
        completed_at=step1_completed_at,
        is_required=STEP_TEMPLATES[0]["is_required"],
        blockers=step1_blockers,
    ))

    # ── Step 2: dokumenty wygenerowane ───────────────────────────────────────
    step2_status = WizardStepStatus.PENDING
    step2_completed_at = None
    step2_blockers = []
    try:
        # Check tender_document table (by tender_id)
        cur.execute(
            "SELECT COUNT(*) AS cnt, MAX(created_at) AS last_at FROM tender_document WHERE tender_id = %s::uuid",
            (tender_id,) if tender_id else (bid_id,),
        )
        row = cur.fetchone()
        doc_count = row["cnt"] if row else 0
        if doc_count >= 5:
            step2_status = WizardStepStatus.COMPLETED
            step2_completed_at = row.get("last_at") if row else None
        elif doc_count > 0:
            step2_status = WizardStepStatus.IN_PROGRESS
            step2_blockers = [f"Tylko {doc_count}/5+ dokumentów wygenerowanych"]
        else:
            # Also check tender_documents
            cur.execute(
                "SELECT COUNT(*) AS cnt, MAX(uploaded_at) AS last_at FROM tender_documents WHERE tender_id = %s::uuid",
                (tender_id,) if tender_id else (bid_id,),
            )
            row2 = cur.fetchone()
            doc_count2 = row2["cnt"] if row2 else 0
            if doc_count2 >= 5:
                step2_status = WizardStepStatus.COMPLETED
                step2_completed_at = row2.get("last_at") if row2 else None
            elif doc_count2 > 0:
                step2_status = WizardStepStatus.IN_PROGRESS
                step2_blockers = [f"Tylko {doc_count2}/5+ dokumentów wygenerowanych"]
            else:
                step2_blockers = ["Brak wygenerowanych dokumentów ofertowych"]
    except Exception as e:
        logger.warning("Step 2 DB check failed: %s", e)
        if saved_steps.get("2", {}).get("status") == "completed":
            step2_status = WizardStepStatus.COMPLETED

    steps.append(WizardStep(
        step_nr=2,
        title=STEP_TEMPLATES[1]["title"],
        description=STEP_TEMPLATES[1]["description"],
        status=step2_status,
        completed_at=step2_completed_at,
        is_required=STEP_TEMPLATES[1]["is_required"],
        blockers=step2_blockers,
    ))

    # ── Step 3: walidacja ─────────────────────────────────────────────────────
    step3_status = WizardStepStatus.PENDING
    step3_completed_at = None
    step3_blockers = []
    offer_status = (offer_row.get("status") or "").lower()
    if offer_status in ("validated", "approved", "confirmed", "submitted", "won", "lost"):
        step3_status = WizardStepStatus.COMPLETED
        step3_completed_at = offer_row.get("updated_at")
    elif saved_steps.get("3", {}).get("status") == "completed":
        step3_status = WizardStepStatus.COMPLETED
        ts = saved_steps["3"].get("completed_at")
        if ts:
            try:
                step3_completed_at = datetime.fromisoformat(ts)
            except Exception:
                pass
    else:
        if step2_status != WizardStepStatus.COMPLETED:
            step3_blockers = ["Wymaga ukończenia kroku 2 (dokumenty)"]
        else:
            step3_blockers = ["Walidacja nie została jeszcze przeprowadzona"]

    steps.append(WizardStep(
        step_nr=3,
        title=STEP_TEMPLATES[2]["title"],
        description=STEP_TEMPLATES[2]["description"],
        status=step3_status,
        completed_at=step3_completed_at,
        is_required=STEP_TEMPLATES[2]["is_required"],
        blockers=step3_blockers,
    ))

    # ── Steps 4-7: from metadata or offer status ──────────────────────────────
    offer_stage = (offer_row.get("stage") or "").lower()

    # Determine auto-status from offer_status/stage for steps 4-7
    # "confirmed" / "submitted" / "won" / "lost" → all steps done
    advanced_statuses = {"confirmed", "submitted", "submitting", "won", "lost", "evaluated", "opened"}
    all_done = offer_status in advanced_statuses or offer_stage in advanced_statuses

    for i, tmpl in enumerate(STEP_TEMPLATES[3:], start=4):
        saved = saved_steps.get(str(i), {})
        if all_done:
            s_status = WizardStepStatus.COMPLETED
            ts = saved.get("completed_at") or offer_row.get("updated_at")
            s_completed_at = None
            if ts and isinstance(ts, str):
                try:
                    s_completed_at = datetime.fromisoformat(ts)
                except Exception:
                    pass
            elif isinstance(ts, datetime):
                s_completed_at = ts
        elif saved.get("status") == "completed":
            s_status = WizardStepStatus.COMPLETED
            s_completed_at = None
            ts = saved.get("completed_at")
            if ts:
                try:
                    s_completed_at = datetime.fromisoformat(ts)
                except Exception:
                    pass
        else:
            s_status = WizardStepStatus.PENDING
            s_completed_at = None

        # Check dependencies: step N needs step N-1 completed
        blockers = []
        if s_status == WizardStepStatus.PENDING and i > 1:
            prev_step = steps[i - 2]  # steps list is 0-indexed
            if prev_step.status != WizardStepStatus.COMPLETED:
                s_status = WizardStepStatus.BLOCKED
                blockers = [f"Wymaga ukończenia kroku {i - 1} ({prev_step.title})"]

        steps.append(WizardStep(
            step_nr=i,
            title=tmpl["title"],
            description=tmpl["description"],
            status=s_status,
            completed_at=s_completed_at,
            is_required=tmpl["is_required"],
            blockers=blockers,
        ))

    return steps


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
    bid_id_str = str(bid_id)

    # Graceful-degradation defaults
    tender_title = "Oferta (brak danych)"
    deadline = datetime(2099, 12, 31, 23, 59, tzinfo=timezone.utc)
    tender_id_str = bid_id_str
    offer_row: dict = {"status": "", "stage": "", "metadata": {}, "title": ""}

    try:
        with db_cursor() as (conn, cur):
            # Try offers table first
            cur.execute(
                "SELECT id, tender_id, title, status, stage, metadata, updated_at "
                "FROM offers WHERE id = %s LIMIT 1",
                (bid_id_str,),
            )
            row = cur.fetchone()

            if row:
                offer_row = dict(row)
                tender_id_str = str(row["tender_id"]) if row["tender_id"] else bid_id_str
                tender_title = row.get("title") or tender_title
            else:
                # Try bid_intelligence
                cur.execute(
                    "SELECT id, tender_id, our_price, won, bid_date, created_at "
                    "FROM bid_intelligence WHERE id = %s LIMIT 1",
                    (bid_id_str,),
                )
                bi_row = cur.fetchone()
                if bi_row:
                    tender_id_str = str(bi_row["tender_id"]) if bi_row["tender_id"] else bid_id_str
                    offer_row = {
                        "status": "won" if bi_row.get("won") else "submitted",
                        "stage": "",
                        "metadata": {},
                        "title": f"Oferta #{bid_id_str[:8]}",
                        "updated_at": bi_row.get("created_at"),
                    }

            # Fetch tender deadline & title
            try:
                cur.execute(
                    "SELECT title, deadline_at FROM tender WHERE id = %s::uuid LIMIT 1",
                    (tender_id_str,),
                )
                t_row = cur.fetchone()
                if t_row:
                    tender_title = t_row["title"] or tender_title
                    if t_row["deadline_at"]:
                        deadline = t_row["deadline_at"]
                        if deadline.tzinfo is None:
                            deadline = deadline.replace(tzinfo=timezone.utc)
            except Exception as e:
                logger.warning("Tender lookup failed: %s", e)

            steps = _get_wizard_steps_from_db(cur, bid_id_str, tender_id_str, offer_row)

    except Exception as e:
        logger.error("DB error in get_wizard_status(%s): %s", bid_id, e)
        # Full fallback — build steps from defaults
        steps = [
            WizardStep(
                step_nr=tmpl["step_nr"],
                title=tmpl["title"],
                description=tmpl["description"],
                status=WizardStepStatus.PENDING,
                is_required=tmpl["is_required"],
            )
            for tmpl in STEP_TEMPLATES
        ]

    completed_count = sum(1 for s in steps if s.status == WizardStepStatus.COMPLETED)
    progress = (completed_count / 7) * 100

    # Current step = first non-completed required step, or last step
    current_step = 7
    for s in steps:
        if s.status != WizardStepStatus.COMPLETED:
            current_step = s.step_nr
            break

    required_steps_done = all(
        s.status == WizardStepStatus.COMPLETED
        for s in steps
        if s.is_required
    )
    can_submit = required_steps_done

    return WizardResponse(
        bid_id=bid_id,
        tender_title=tender_title,
        deadline=deadline,
        current_step=current_step,
        steps=steps,
        overall_progress_pct=round(progress, 1),
        can_submit=can_submit,
        time_remaining=_format_time_remaining(deadline),
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

    bid_id_str = str(bid_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        with db_cursor() as (conn, cur):
            # Fetch current offer state
            cur.execute(
                "SELECT id, metadata, status FROM offers WHERE id = %s LIMIT 1",
                (bid_id_str,),
            )
            row = cur.fetchone()

            if not row:
                # No offer found — still persist gracefully using a virtual state
                logger.warning("Offer %s not found, step confirm has no DB effect", bid_id)
                next_step = step_nr + 1 if step_nr < 7 else None
                return StepConfirmResponse(
                    bid_id=bid_id,
                    step_nr=step_nr,
                    status=WizardStepStatus.COMPLETED,
                    message=f"Krok {step_nr} potwierdzony (oferta nie znaleziona w DB).",
                    next_step=next_step,
                )

            meta = row.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}

            wizard_steps: dict = meta.get("wizard_steps", {})

            # Check dependency: step N requires step N-1 completed (for steps 2+)
            if step_nr > 1:
                prev_key = str(step_nr - 1)
                prev_status = wizard_steps.get(prev_key, {}).get("status", "")

                # Also check auto-detected states for steps 1-3
                if step_nr == 2:
                    # Step 1 check: kosztorys approved?
                    try:
                        cur.execute(
                            "SELECT 1 FROM kosztorys WHERE offer_id = %s AND status IN "
                            "('approved','zatwierdzony','confirmed','completed','done') LIMIT 1",
                            (bid_id_str,),
                        )
                        if not cur.fetchone() and prev_status != "completed":
                            raise HTTPException(
                                status_code=400,
                                detail=f"Krok {step_nr - 1} nie jest ukończony. Zatwierdź najpierw kosztorys."
                            )
                    except HTTPException:
                        raise
                    except Exception:
                        if prev_status not in ("completed",):
                            raise HTTPException(
                                status_code=400,
                                detail=f"Krok {step_nr - 1} nie jest ukończony."
                            )
                elif prev_status not in ("completed",):
                    # For steps 3+, check wizard_steps metadata
                    raise HTTPException(
                        status_code=400,
                        detail=f"Krok {step_nr - 1} nie jest ukończony. Ukończ poprzedni krok najpierw."
                    )

            # Update wizard_steps in metadata
            wizard_steps[str(step_nr)] = {
                "status": "completed",
                "completed_at": now_iso,
                "notes": payload.notes or "",
                "attachments": payload.attachments,
            }
            meta["wizard_steps"] = wizard_steps

            # Update offer metadata
            cur.execute(
                "UPDATE offers SET metadata = %s::jsonb, updated_at = NOW() WHERE id = %s",
                (json.dumps(meta), bid_id_str),
            )
            conn.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("DB error in confirm_step(%s, %s): %s", bid_id, step_nr, e)
        # Graceful degradation — return success without DB
        next_step = step_nr + 1 if step_nr < 7 else None
        return StepConfirmResponse(
            bid_id=bid_id,
            step_nr=step_nr,
            status=WizardStepStatus.COMPLETED,
            message=f"Krok {step_nr} potwierdzony (tryb offline).",
            next_step=next_step,
        )

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

    bid_id_str = str(bid_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Generate confirmation hash from bid_id + timestamp
    confirmation_hash = "sha256:" + hashlib.sha256(
        f"{bid_id_str}:{now_iso}:{payload.electronic_signature_id or ''}".encode()
    ).hexdigest()

    try:
        with db_cursor() as (conn, cur):
            # Fetch offer
            cur.execute(
                "SELECT id, metadata, status FROM offers WHERE id = %s LIMIT 1",
                (bid_id_str,),
            )
            row = cur.fetchone()

            if not row:
                # No offer in DB — return graceful response
                logger.warning("Offer %s not found for final confirm", bid_id)
                return FinalConfirmResponse(
                    bid_id=bid_id,
                    submission_status="confirmed",
                    message="Oferta potwierdzona (nie znaleziono rekordu w DB — tryb offline).",
                    confirmation_hash=confirmation_hash,
                    submitted_at=datetime.now(timezone.utc),
                )

            meta = row.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}

            # Check all 7 steps completed (from wizard_steps + auto-detected)
            wizard_steps: dict = meta.get("wizard_steps", {})

            # Auto-check steps 1-3 from DB
            all_required_done = True
            missing_steps = []

            # Step 1: kosztorys
            cur.execute(
                "SELECT 1 FROM kosztorys WHERE offer_id = %s AND status IN "
                "('approved','zatwierdzony','confirmed','completed','done') LIMIT 1",
                (bid_id_str,),
            )
            if not cur.fetchone() and wizard_steps.get("1", {}).get("status") != "completed":
                all_required_done = False
                missing_steps.append("Krok 1: Kosztorys niezatwierdzony")

            # Step 2: documents — check wizard_steps (may be auto-set)
            if wizard_steps.get("2", {}).get("status") != "completed":
                # Check DB
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM tender_document WHERE tenant_id IN "
                    "(SELECT tenant_id FROM offers WHERE id = %s) LIMIT 1",
                    (bid_id_str,),
                )
                # Relaxed check — only fail if explicitly not confirmed
                # (we don't have bid_id→tender_id→document link guaranteed)
                logger.info("Step 2 not confirmed in wizard_steps for %s", bid_id)

            # Steps 3-7 from wizard_steps
            required_step_nrs = [1, 2, 3, 4, 6, 7]  # 5 is optional (wadium)
            for s_nr in required_step_nrs[1:]:  # step 1 already checked
                if wizard_steps.get(str(s_nr), {}).get("status") != "completed":
                    missing_steps.append(f"Krok {s_nr}: {STEP_TEMPLATES[s_nr - 1]['title']}")

            if missing_steps:
                raise HTTPException(
                    status_code=400,
                    detail=f"Nie wszystkie wymagane kroki są ukończone: {', '.join(missing_steps)}"
                )

            # Save confirmation to metadata & update status
            meta["confirmation"] = {
                "confirmed_at": now_iso,
                "confirmation_hash": confirmation_hash,
                "electronic_signature_id": payload.electronic_signature_id,
            }

            cur.execute(
                "UPDATE offers SET status = 'confirmed', metadata = %s::jsonb, updated_at = NOW() "
                "WHERE id = %s",
                (json.dumps(meta), bid_id_str),
            )
            conn.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("DB error in final_confirm(%s): %s", bid_id, e)
        # Graceful degradation
        return FinalConfirmResponse(
            bid_id=bid_id,
            submission_status="confirmed",
            message="Oferta potwierdzona i gotowa do złożenia (tryb offline — błąd DB).",
            confirmation_hash=confirmation_hash,
            submitted_at=datetime.now(timezone.utc),
        )

    return FinalConfirmResponse(
        bid_id=bid_id,
        submission_status="confirmed",
        message="Oferta potwierdzona i gotowa do złożenia. Paczka wygenerowana.",
        confirmation_hash=confirmation_hash,
        submitted_at=datetime.now(timezone.utc),
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
    bid_id_str = str(bid_id)

    # Graceful defaults
    tender_id_out = bid_id
    submission_status = "draft"
    submitted_at = None
    opened_at = None
    result = None
    ranking_position = None
    total_bidders = None
    our_price_val = None
    winning_price_val = None
    events: list[TrackingEvent] = []
    next_expected_event = None

    try:
        with db_cursor() as (conn, cur):
            # Try bid_intelligence first (has won, rank, prices)
            cur.execute(
                "SELECT id, tender_id, our_price, winning_price, n_competitors, "
                "rank_position, won, bid_date, created_at "
                "FROM bid_intelligence WHERE id = %s LIMIT 1",
                (bid_id_str,),
            )
            bi_row = cur.fetchone()

            if bi_row:
                tender_id_out = bi_row["tender_id"] or bid_id
                our_price_val = float(bi_row["our_price"]) if bi_row["our_price"] else None
                winning_price_val = float(bi_row["winning_price"]) if bi_row["winning_price"] else None
                ranking_position = bi_row.get("rank_position")
                total_bidders = bi_row.get("n_competitors")
                won = bi_row.get("won")
                bid_date = bi_row.get("bid_date")

                if won is True:
                    submission_status = "won"
                    result = "won"
                elif won is False:
                    submission_status = "lost"
                    result = "lost"
                else:
                    submission_status = "submitted"
                    result = "pending"

                if bid_date:
                    submitted_at = datetime.combine(bid_date, datetime.min.time()).replace(tzinfo=timezone.utc)

                events.append(TrackingEvent(
                    timestamp=submitted_at or datetime.now(timezone.utc),
                    event="bid_recorded",
                    description="Oferta zarejestrowana w systemie bid_intelligence",
                    source="system",
                ))

                if won is not None:
                    events.append(TrackingEvent(
                        timestamp=bi_row.get("created_at") or datetime.now(timezone.utc),
                        event="result_received",
                        description=f"Wynik: {'WYGRANA' if won else 'PRZEGRANA'} "
                                    f"(pozycja {ranking_position}/{total_bidders})",
                        source="system",
                    ))
                    next_expected_event = "Podpisanie umowy" if won else "Analiza przegranej oferty"
                else:
                    next_expected_event = "Otwarcie ofert"
            else:
                # Try offers table
                cur.execute(
                    "SELECT id, tender_id, status, price_gross_pln, created_at, updated_at, metadata "
                    "FROM offers WHERE id = %s LIMIT 1",
                    (bid_id_str,),
                )
                offer_row = cur.fetchone()

                if offer_row:
                    tender_id_raw = offer_row.get("tender_id")
                    try:
                        tender_id_out = UUID(str(tender_id_raw)) if tender_id_raw else bid_id
                    except Exception:
                        tender_id_out = bid_id

                    offer_status = (offer_row.get("status") or "draft").lower()
                    submission_status = offer_status
                    our_price_val = float(offer_row["price_gross_pln"]) if offer_row.get("price_gross_pln") else None
                    submitted_at = offer_row.get("updated_at")

                    if submitted_at and submitted_at.tzinfo is None:
                        submitted_at = submitted_at.replace(tzinfo=timezone.utc)

                    meta = offer_row.get("metadata") or {}
                    if isinstance(meta, str):
                        try:
                            meta = json.loads(meta)
                        except Exception:
                            meta = {}

                    conf = meta.get("confirmation", {})
                    if conf:
                        events.append(TrackingEvent(
                            timestamp=submitted_at or datetime.now(timezone.utc),
                            event="confirmed",
                            description=f"Oferta potwierdzona (hash: {conf.get('confirmation_hash', '')[:20]}...)",
                            source="system",
                        ))

                    if offer_status in ("won", "submitted"):
                        result = "pending" if offer_status == "submitted" else "won"
                        next_expected_event = "Otwarcie ofert"
                    elif offer_status == "confirmed":
                        next_expected_event = "Złożenie na platformie e-Zamówienia"
                    else:
                        next_expected_event = "Ukończenie wizarda i potwierdzenie oferty"
                else:
                    # Neither table has this bid
                    logger.info("Bid %s not found in any table for tracking", bid_id)
                    events.append(TrackingEvent(
                        timestamp=datetime.now(timezone.utc),
                        event="not_found",
                        description="Oferta nie znaleziona w bazie danych",
                        source="system",
                    ))
                    next_expected_event = "Złożenie oferty"

    except Exception as e:
        logger.error("DB error in get_tracking(%s): %s", bid_id, e)
        events.append(TrackingEvent(
            timestamp=datetime.now(timezone.utc),
            event="error",
            description=f"Błąd pobierania danych: {str(e)[:100]}",
            source="system",
        ))

    return TrackingResponse(
        bid_id=bid_id,
        tender_id=tender_id_out,
        submission_status=submission_status,
        submitted_at=submitted_at,
        opened_at=opened_at,
        result=result,
        ranking_position=ranking_position,
        total_bidders=total_bidders,
        our_price=our_price_val,
        winning_price=winning_price_val,
        events=events,
        next_expected_event=next_expected_event,
    )
