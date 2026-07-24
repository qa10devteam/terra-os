"""
BudOS Workflow Engine — silnik stanów + instancje per przetarg.

Endpoints:
  GET    /api/v2/workflows                         — lista definicji
  POST   /api/v2/workflows                         — utwórz definicję
  PUT    /api/v2/workflows/{id}                    — aktualizuj
  DELETE /api/v2/workflows/{id}                    — usuń
  GET    /api/v2/workflows/budos                   — domyślny przepływ BudOS
  POST   /api/v2/workflow-instances                — start instancji per tender
  GET    /api/v2/workflow-instances                — lista ?tender_id=X
  GET    /api/v2/workflow-instances/{id}           — szczegóły + log
  POST   /api/v2/workflow-instances/{id}/transition — przejście do kroku
  POST   /api/v2/workflow-instances/{id}/complete  — zamknij instancję
"""
from __future__ import annotations

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth.deps import get_current_user, CurrentUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["workflows"])

# ─── BudOS Default Workflow ──────────────────────────────────────────────────

BUDOS_WORKFLOW_ID = "00000000-0000-0000-0000-000000000001"  # stały UUID

BUDOS_STEPS = [
    {
        "id": "zwiad",
        "label": "Zwiad",
        "description": "Pobierz dokumentację, sprawdź CPV, oceń ryzyko wstępne",
        "icon": "Search",
        "color": "indigo",
        "required_actions": ["pobierz_dokumenty", "sprawdz_cpv"],
        "transitions": ["kosztorys", "rezygnacja"],
        "is_terminal": False,
    },
    {
        "id": "kosztorys",
        "label": "Kosztorys",
        "description": "Utwórz kosztorys ICB lub własny, zweryfikuj stawki R/M/S",
        "icon": "Calculator",
        "color": "violet",
        "required_actions": ["kosztorys_icb"],
        "transitions": ["decyzja", "rezygnacja"],
        "is_terminal": False,
    },
    {
        "id": "decyzja",
        "label": "Decyzja",
        "description": "Idę / Nie idę — ocena marży, ryzyk, konkurencji",
        "icon": "GitBranch",
        "color": "warn",
        "required_actions": ["decyzja_go_nogo"],
        "transitions": ["oferta", "rezygnacja"],
        "is_terminal": False,
    },
    {
        "id": "oferta",
        "label": "Oferta",
        "description": "Przygotuj dokumenty ofertowe, uzupełnij formularze",
        "icon": "FileText",
        "color": "em",
        "required_actions": ["dokumenty_oferty"],
        "transitions": ["zlozenie", "rezygnacja"],
        "is_terminal": False,
    },
    {
        "id": "zlozenie",
        "label": "Złożenie",
        "description": "Złóż ofertę w platformie e-zamówień",
        "icon": "Send",
        "color": "go",
        "required_actions": ["zloz_oferte"],
        "transitions": ["wynik", "rezygnacja"],
        "is_terminal": False,
    },
    {
        "id": "wynik",
        "label": "Wynik",
        "description": "Wynik otwarcia ofert — wygrana / przegrana / unieważnienie",
        "icon": "Trophy",
        "color": "go",
        "required_actions": [],
        "transitions": [],
        "is_terminal": True,
    },
    {
        "id": "rezygnacja",
        "label": "Rezygnacja",
        "description": "Zdecydowano o rezygnacji z przetargu",
        "icon": "XCircle",
        "color": "nogo",
        "required_actions": [],
        "transitions": [],
        "is_terminal": True,
    },
]

BUDOS_WORKFLOW = {
    "id": BUDOS_WORKFLOW_ID,
    "name": "BudOS — Domyślny przepływ przetargu",
    "steps": BUDOS_STEPS,
    "initial_step": "zwiad",
    "version": "1.0",
}


# ─── Models ──────────────────────────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    definition: dict = Field(default_factory=dict)
    is_active: bool = True


class WorkflowUpdate(BaseModel):
    name: str | None = None
    definition: dict | None = None
    is_active: bool | None = None


class InstanceCreate(BaseModel):
    tender_id: str
    workflow_id: str | None = None   # None = BudOS default


class TransitionIn(BaseModel):
    to_step: str
    note: str | None = None
    metadata: dict = Field(default_factory=dict)


class CompleteIn(BaseModel):
    outcome: str = "completed"   # completed | cancelled | won | lost
    note: str | None = None


# ─── DB setup ────────────────────────────────────────────────────────────────

_TABLES_CREATED = False


def _ensure_tables() -> None:
    global _TABLES_CREATED
    if _TABLES_CREATED:
        return
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS workflow_definition (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                name TEXT NOT NULL,
                definition JSONB NOT NULL DEFAULT '{}',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS workflow_instance (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                tender_id UUID NOT NULL,
                workflow_id TEXT NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
                current_step TEXT NOT NULL DEFAULT 'zwiad',
                status TEXT NOT NULL DEFAULT 'active',
                outcome TEXT,
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ,
                UNIQUE (tenant_id, tender_id)
            )
        """))
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS workflow_step_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                instance_id UUID NOT NULL REFERENCES workflow_instance(id) ON DELETE CASCADE,
                from_step TEXT,
                to_step TEXT NOT NULL,
                note TEXT,
                metadata JSONB NOT NULL DEFAULT '{}',
                actor_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(sa.text("""
            CREATE INDEX IF NOT EXISTS idx_wf_instance_tender ON workflow_instance(tenant_id, tender_id);
            CREATE INDEX IF NOT EXISTS idx_wf_step_log_instance ON workflow_step_log(instance_id);
        """))
    _TABLES_CREATED = True


def _resolve_tenant(user: CurrentUser) -> str:
    engine = get_engine()
    org_id = str(user.org_id)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text("SELECT tenant_id FROM organizations WHERE id = :oid LIMIT 1"),
                {"oid": org_id},
            ).fetchone()
        if row and row.tenant_id:
            return str(row.tenant_id)
    except Exception:
        pass
    return org_id


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _step_meta(step_id: str) -> dict:
    for s in BUDOS_STEPS:
        if s["id"] == step_id:
            return s
    return {"id": step_id, "label": step_id, "icon": "Circle", "color": "slate"}


def _step_index(step_id: str) -> int:
    visible = [s for s in BUDOS_STEPS if s["id"] not in ("rezygnacja",)]
    for i, s in enumerate(visible):
        if s["id"] == step_id:
            return i
    return -1


def _row_to_instance(row) -> dict:
    step = _step_meta(row.current_step)
    visible_steps = [s for s in BUDOS_STEPS if s["id"] not in ("rezygnacja",)]
    progress_pct = 0
    idx = _step_index(row.current_step)
    if idx >= 0:
        progress_pct = round(idx / max(len(visible_steps) - 1, 1) * 100)
    return {
        "id": str(row.id),
        "tender_id": str(row.tender_id),
        "workflow_id": row.workflow_id,
        "current_step": row.current_step,
        "current_step_label": step.get("label", row.current_step),
        "current_step_icon": step.get("icon", "Circle"),
        "current_step_color": step.get("color", "slate"),
        "status": row.status,
        "outcome": row.outcome,
        "progress_pct": progress_pct,
        "transitions": step.get("transitions", []),
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


# ─── Workflow definitions ─────────────────────────────────────────────────────

@router.get("/workflows/budos")
def get_budos_workflow() -> dict:
    """GET /api/v2/workflows/budos — domyślny przepływ BudOS."""
    return BUDOS_WORKFLOW


@router.get("/workflows")
def list_workflows(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    _ensure_tables()
    tenant_id = _resolve_tenant(user)
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, tenant_id, name, definition, is_active, created_at, updated_at
            FROM workflow_definition
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
        """), {"tid": tenant_id}).fetchall()
    return [
        {
            "id": str(r.id),
            "tenant_id": str(r.tenant_id),
            "name": r.name,
            "definition": r.definition,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


@router.post("/workflows", status_code=201)
def create_workflow(body: WorkflowCreate, user: CurrentUser = Depends(get_current_user)) -> dict:
    _ensure_tables()
    tenant_id = _resolve_tenant(user)
    wf_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO workflow_definition (id, tenant_id, name, definition, is_active, created_at, updated_at)
            VALUES (:id, :tid, :name, CAST(:def AS jsonb), :active, :now, :now)
        """), {
            "id": wf_id, "tid": tenant_id, "name": body.name,
            "def": json.dumps(body.definition), "active": body.is_active, "now": now,
        })
    return {"id": wf_id, "name": body.name, "is_active": body.is_active, "created_at": now.isoformat()}


@router.put("/workflows/{wf_id}")
def update_workflow(wf_id: str, body: WorkflowUpdate, user: CurrentUser = Depends(get_current_user)) -> dict:
    _ensure_tables()
    tenant_id = _resolve_tenant(user)
    updates: list[str] = []
    params: dict[str, Any] = {"id": wf_id, "tid": tenant_id, "now": datetime.now(timezone.utc)}
    if body.name is not None:
        updates.append("name = :name"); params["name"] = body.name
    if body.definition is not None:
        updates.append("definition = CAST(:def AS jsonb)"); params["def"] = json.dumps(body.definition)
    if body.is_active is not None:
        updates.append("is_active = :active"); params["active"] = body.is_active
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates.append("updated_at = :now")
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(sa.text(
            f"UPDATE workflow_definition SET {', '.join(updates)} WHERE id = :id AND tenant_id = :tid"
        ), params)
        if result.rowcount == 0:
            raise HTTPException(404, "Workflow not found")
    return {"id": wf_id, "updated": True}


@router.delete("/workflows/{wf_id}", status_code=204)
def delete_workflow(wf_id: str, user: CurrentUser = Depends(get_current_user)) -> None:
    _ensure_tables()
    tenant_id = _resolve_tenant(user)
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(sa.text(
            "DELETE FROM workflow_definition WHERE id = :id AND tenant_id = :tid"
        ), {"id": wf_id, "tid": tenant_id})
        if result.rowcount == 0:
            raise HTTPException(404, "Workflow not found")


# ─── Workflow Instances ───────────────────────────────────────────────────────

@router.post("/workflow-instances", status_code=201)
def create_instance(body: InstanceCreate, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Start przepływu dla przetargu. Jeśli instancja już istnieje — zwróć istniejącą."""
    _ensure_tables()
    tenant_id = _resolve_tenant(user)
    workflow_id = body.workflow_id or BUDOS_WORKFLOW_ID
    engine = get_engine()

    # Check if already exists
    with engine.connect() as conn:
        existing = conn.execute(sa.text("""
            SELECT id, current_step, status FROM workflow_instance
            WHERE tenant_id = :tid AND tender_id = CAST(:tender_id AS UUID)
        """), {"tid": tenant_id, "tender_id": body.tender_id}).fetchone()

    if existing:
        # Jeśli zamknięta — pozwól stworzyć nową
        if existing.status in ("completed", "cancelled", "withdrawn"):
            pass  # fall through to create new
        else:
            return {"id": str(existing.id), "current_step": existing.current_step,
                    "status": existing.status, "created": False}

    instance_id = str(uuid.uuid4())
    initial_step = BUDOS_WORKFLOW["initial_step"]
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO workflow_instance
                (id, tenant_id, tender_id, workflow_id, current_step, status, started_at, updated_at)
            VALUES (:id, :tid, CAST(:tender_id AS UUID), :wf_id, :step, 'active', :now, :now)
        """), {
            "id": instance_id, "tid": tenant_id, "tender_id": body.tender_id,
            "wf_id": workflow_id, "step": initial_step, "now": now,
        })
        # Log initial step
        conn.execute(sa.text("""
            INSERT INTO workflow_step_log (id, instance_id, from_step, to_step, note, created_at)
            VALUES (:id, :iid, NULL, :step, 'Rozpoczęcie przepływu', :now)
        """), {"id": str(uuid.uuid4()), "iid": instance_id, "step": initial_step, "now": now})

    return {"id": instance_id, "current_step": initial_step, "status": "active", "created": True}


@router.get("/workflow-instances")
def list_instances(
    tender_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """GET /api/v2/workflow-instances?tender_id=X."""
    _ensure_tables()
    tenant_id = _resolve_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        if tender_id:
            try:
                rows = conn.execute(sa.text("""
                    SELECT id, tender_id, workflow_id, current_step, status, outcome,
                           started_at, updated_at, completed_at
                    FROM workflow_instance
                    WHERE tenant_id = :tid AND tender_id = CAST(:eid AS UUID)
                    ORDER BY started_at DESC
                """), {"tid": tenant_id, "eid": tender_id}).fetchall()
            except Exception:
                return {"items": []}
        else:
            rows = conn.execute(sa.text("""
                SELECT id, tender_id, workflow_id, current_step, status, outcome,
                       started_at, updated_at, completed_at
                FROM workflow_instance
                WHERE tenant_id = :tid
                ORDER BY updated_at DESC
                LIMIT 50
            """), {"tid": tenant_id}).fetchall()

    return {"items": [_row_to_instance(r) for r in rows]}


@router.get("/workflow-instances/{instance_id}")
def get_instance(instance_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    """GET szczegóły + historia kroków."""
    _ensure_tables()
    tenant_id = _resolve_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT id, tender_id, workflow_id, current_step, status, outcome,
                   started_at, updated_at, completed_at
            FROM workflow_instance
            WHERE id = CAST(:id AS UUID) AND tenant_id = :tid
        """), {"id": instance_id, "tid": tenant_id}).fetchone()

        if not row:
            raise HTTPException(404, "Instance not found")

        logs = conn.execute(sa.text("""
            SELECT id, from_step, to_step, note, metadata, actor_id, created_at
            FROM workflow_step_log
            WHERE instance_id = CAST(:iid AS UUID)
            ORDER BY created_at ASC
        """), {"iid": instance_id}).fetchall()

    inst = _row_to_instance(row)
    inst["log"] = [
        {
            "id": str(lg.id),
            "from_step": lg.from_step,
            "to_step": lg.to_step,
            "note": lg.note,
            "metadata": lg.metadata or {},
            "created_at": lg.created_at.isoformat() if lg.created_at else None,
        }
        for lg in logs
    ]
    # Attach all BudOS steps with status markers
    inst["steps"] = [
        {
            **s,
            "state": (
                "completed" if _step_index(s["id"]) < _step_index(row.current_step)
                else "active" if s["id"] == row.current_step
                else "pending"
            ) if row.status == "active" else (
                "completed" if _step_index(s["id"]) <= _step_index(row.current_step) else "pending"
            ),
        }
        for s in BUDOS_STEPS
        if s["id"] != "rezygnacja" or row.current_step == "rezygnacja"
    ]
    return inst


@router.post("/workflow-instances/{instance_id}/transition")
def transition_step(
    instance_id: str,
    body: TransitionIn,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Przejdź do następnego kroku workflow."""
    _ensure_tables()
    tenant_id = _resolve_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT id, current_step, status FROM workflow_instance
            WHERE id = CAST(:id AS UUID) AND tenant_id = :tid
        """), {"id": instance_id, "tid": tenant_id}).fetchone()

    if not row:
        raise HTTPException(404, "Instance not found")
    if row.status != "active":
        raise HTTPException(409, {"error": "instance_closed", "message": "Przepływ jest już zamknięty"})

    current_meta = _step_meta(row.current_step)
    valid_transitions = current_meta.get("transitions", [])

    if body.to_step not in valid_transitions:
        raise HTTPException(422, {
            "error": "invalid_transition",
            "message": f"Krok '{row.current_step}' nie może przejść do '{body.to_step}'. "
                       f"Dozwolone: {valid_transitions}",
        })

    now = datetime.now(timezone.utc)
    new_meta = _step_meta(body.to_step)
    # wynik: is_terminal oznacza ostatni krok procesu, ale outcome (won/lost) ustawia /complete
    # więc status pozostaje 'active' aż do jawnego wywołania /complete
    new_status = "active"

    with engine.begin() as conn:
        conn.execute(sa.text("""
            UPDATE workflow_instance
            SET current_step = :step, status = :status,
                updated_at = :now,
                completed_at = CASE WHEN :status != 'active' THEN :now ELSE NULL END
            WHERE id = CAST(:id AS UUID) AND tenant_id = :tid
        """), {"step": body.to_step, "status": new_status, "now": now,
               "id": instance_id, "tid": tenant_id})

        conn.execute(sa.text("""
            INSERT INTO workflow_step_log
                (id, instance_id, from_step, to_step, note, metadata, created_at)
            VALUES (:id, CAST(:iid AS UUID), :from_s, :to_s, :note, CAST(:meta AS jsonb), :now)
        """), {
            "id": str(uuid.uuid4()), "iid": instance_id,
            "from_s": row.current_step, "to_s": body.to_step,
            "note": body.note, "meta": json.dumps(body.metadata), "now": now,
        })

    step_meta = next((s for s in BUDOS_STEPS if s["id"] == body.to_step), {})
    visible = [s["id"] for s in BUDOS_STEPS if s["id"] != "rezygnacja"]
    try:
        idx = visible.index(body.to_step)
        progress_pct = round(idx / max(len(visible) - 1, 1) * 100)
    except ValueError:
        progress_pct = 0

    return {
        "previous_step": row.current_step,
        "current_step": body.to_step,
        "current_step_label": step_meta.get("label", body.to_step),
        "current_step_color": step_meta.get("color", "slate"),
        "current_step_icon":  step_meta.get("icon", "Circle"),
        "progress_pct": progress_pct,
        "status": new_status,
        "transitions": new_meta.get("transitions", []),
    }


@router.post("/workflow-instances/{instance_id}/complete")
def complete_instance(
    instance_id: str,
    body: CompleteIn,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Zamknij instancję (outcome: completed/won/lost/cancelled)."""
    _ensure_tables()
    tenant_id = _resolve_tenant(user)
    engine = get_engine()
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        result = conn.execute(sa.text("""
            UPDATE workflow_instance
            SET status = 'completed', outcome = :outcome,
                updated_at = :now, completed_at = :now
            WHERE id = CAST(:id AS UUID) AND tenant_id = :tid
              AND status = 'active'
        """), {"outcome": body.outcome, "now": now, "id": instance_id, "tid": tenant_id})
        if result.rowcount == 0:
            raise HTTPException(404, "Instance not found or already closed")

        if body.note:
            conn.execute(sa.text("""
                INSERT INTO workflow_step_log
                    (id, instance_id, from_step, to_step, note, created_at)
                VALUES (:id, CAST(:iid AS UUID), NULL, 'completed', :note, :now)
            """), {"id": str(uuid.uuid4()), "iid": instance_id, "note": body.note, "now": now})

    return {"id": instance_id, "status": "completed", "outcome": body.outcome}
