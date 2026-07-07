"""Faza 4 — API v2: Estimates router."""
from __future__ import annotations

import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/estimates", tags=["estimates-v2"])


class EstimateCreate(BaseModel):
    tender_id: str
    variant: str = "doc"  # doc | owner
    total_net_pln: float | None = None
    overhead_pct: float | None = None
    profit_pct: float | None = None
    params: dict = {}


class EstimateUpdate(BaseModel):
    total_net_pln: float | None = None
    overhead_pct: float | None = None
    profit_pct: float | None = None
    params: dict | None = None


class PredictRequest(BaseModel):
    cpv: str = "45"
    region: str = "mazowieckie"
    area_m2: float = 1000.0
    floors: int = 1
    description: str = ""


def _row_to_dict(row: Any) -> dict:
    return {
        "id": str(row.id),
        "tender_id": str(row.tender_id),
        "variant": row.variant,
        "total_net_pln": float(row.total_net_pln) if row.total_net_pln else None,
        "overhead_pct": float(row.overhead_pct) if row.overhead_pct else None,
        "profit_pct": float(row.profit_pct) if row.profit_pct else None,
        "params": row.params if isinstance(row.params, dict) else {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("")
def list_estimates(tender_id: str, user: AuthUser) -> dict:
    """Lista wycen dla przetargu."""
    engine = get_engine()
    tenant_id = user.org_id

    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                """SELECT id, tender_id, variant, total_net_pln, overhead_pct,
                          profit_pct, params, created_at
                   FROM estimate
                   WHERE tenant_id = :tenant_id AND tender_id = :tender_id
                   ORDER BY created_at DESC"""
            ),
            {"tenant_id": tenant_id, "tender_id": tender_id},
        ).fetchall()

    return {"items": [_row_to_dict(r) for r in rows], "total": len(rows)}


@router.post("")
def create_estimate(body: EstimateCreate, user: AuthUser) -> dict:
    """Utwórz wycenę."""
    engine = get_engine()
    tenant_id = user.org_id

    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    if body.variant not in ("doc", "owner"):
        raise HTTPException(status_code=422, detail={"error": "invalid_variant", "message": "variant musi być 'doc' lub 'owner'"})

    # Sprawdź czy przetarg należy do tenanta
    with engine.connect() as conn:
        tender = conn.execute(
            sa.text("SELECT id FROM tender WHERE id = :id AND tenant_id = :tid"),
            {"id": body.tender_id, "tid": tenant_id},
        ).fetchone()

    if not tender:
        raise HTTPException(status_code=404, detail={"error": "tender_not_found", "message": "Przetarg nie znaleziony"})

    import json
    new_id = str(uuid.uuid4())
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                """INSERT INTO estimate
                       (id, tenant_id, tender_id, variant, total_net_pln, overhead_pct, profit_pct, params, created_at)
                   VALUES
                       (:id, :tid, :tender_id, :variant, :total_net_pln, :overhead_pct, :profit_pct,
                        CAST(:params AS jsonb), NOW())
                   RETURNING id, tender_id, variant, total_net_pln, overhead_pct, profit_pct, params, created_at"""
            ),
            {
                "id": new_id,
                "tid": tenant_id,
                "tender_id": body.tender_id,
                "variant": body.variant,
                "total_net_pln": body.total_net_pln,
                "overhead_pct": body.overhead_pct,
                "profit_pct": body.profit_pct,
                "params": json.dumps(body.params),
            },
        ).fetchone()

    return _row_to_dict(result)


@router.get("/predict")
def predict_cost(
    cpv: str = "45",
    region: str = "mazowieckie",
    area_m2: float = 1000.0,
    floors: int = 1,
    description: str = "",
    user: AuthUser = None,
) -> dict:
    """Szacuj koszty na podstawie modelu ML/benchmark."""
    from ..analytics.cost_estimation import get_estimator

    estimator = get_estimator()
    pred = estimator.predict({"cpv": cpv, "region": region, "area_m2": area_m2, "floors": floors})

    return {
        "benchmark": pred["benchmark"],
        "ai_estimate": pred["estimate"],
        "confidence_interval": {"low95": pred["low95"], "high95": pred["high95"]},
        "method": pred["method"],
        "similar_projects": [],
    }


@router.get("/{estimate_id}")
def get_estimate(estimate_id: str, user: AuthUser) -> dict:
    """Szczegóły wyceny z pozycjami kosztorysu."""
    engine = get_engine()
    tenant_id = user.org_id

    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                """SELECT id, tender_id, variant, total_net_pln, overhead_pct,
                          profit_pct, params, created_at
                   FROM estimate
                   WHERE id = :id AND tenant_id = :tenant_id"""
            ),
            {"id": estimate_id, "tenant_id": tenant_id},
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Wycena nie znaleziona"})

        lines = conn.execute(
            sa.text(
                """SELECT id, description, unit, quantity, unit_price,
                          labor_pln, material_pln, equipment_pln, line_total_pln
                   FROM estimate_line
                   WHERE estimate_id = :eid AND tenant_id = :tid
                   ORDER BY created_at"""
            ),
            {"eid": estimate_id, "tid": tenant_id},
        ).fetchall()

    result = _row_to_dict(row)
    result["lines"] = [
        {
            "id": str(l.id),
            "description": l.description,
            "unit": l.unit,
            "quantity": float(l.quantity) if l.quantity else None,
            "unit_price": float(l.unit_price) if l.unit_price else None,
            "labor_pln": float(l.labor_pln) if l.labor_pln else None,
            "material_pln": float(l.material_pln) if l.material_pln else None,
            "equipment_pln": float(l.equipment_pln) if l.equipment_pln else None,
            "line_total_pln": float(l.line_total_pln) if l.line_total_pln else None,
        }
        for l in lines
    ]
    return result


@router.put("/{estimate_id}")
def update_estimate(estimate_id: str, body: EstimateUpdate, user: AuthUser) -> dict:
    """Aktualizuj wycenę."""
    engine = get_engine()
    tenant_id = user.org_id

    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_org", "message": "Brak org_id"})

    updates = []
    params: dict = {"id": estimate_id, "tenant_id": tenant_id}

    if body.total_net_pln is not None:
        updates.append("total_net_pln = :total_net_pln")
        params["total_net_pln"] = body.total_net_pln
    if body.overhead_pct is not None:
        updates.append("overhead_pct = :overhead_pct")
        params["overhead_pct"] = body.overhead_pct
    if body.profit_pct is not None:
        updates.append("profit_pct = :profit_pct")
        params["profit_pct"] = body.profit_pct
    if body.params is not None:
        import json
        updates.append("params = CAST(:params AS jsonb)")
        params["params"] = json.dumps(body.params)

    if not updates:
        raise HTTPException(status_code=422, detail={"error": "no_fields", "message": "Brak pól do aktualizacji"})

    set_clause = ", ".join(updates)
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                f"""UPDATE estimate SET {set_clause}
                   WHERE id = :id AND tenant_id = :tenant_id
                   RETURNING id, tender_id, variant, total_net_pln, overhead_pct, profit_pct, params, created_at"""
            ),
            params,
        ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Wycena nie znaleziona"})

    return _row_to_dict(result)
