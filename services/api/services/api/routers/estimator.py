"""M3 — /estimates endpoints: POST, GET, PATCH params, compare."""
from __future__ import annotations

import json
import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from services.estimator import (
    RateCard, MarketPriceBase,
    compute_variant_a, compute_variant_b, compare_estimates,
    verify_sum_reconciliation,
)

router = APIRouter(prefix="/api/v1", tags=["estimator"])


# ─── Schemas ────────────────────────────────────────────────────────────────

class EstimateLineSchema(BaseModel):
    position_no: str
    description: str
    unit: str
    quantity: str
    unit_price: str
    labor_pln: str
    material_pln: str
    equipment_pln: str
    line_total_pln: str
    knr_code: str | None = None


class EstimateResponse(BaseModel):
    id: str
    variant: str
    total_net_pln: str
    lines: list[EstimateLineSchema]
    params: dict
    sum_reconciled: bool


class EstimatePair(BaseModel):
    estimate_doc_id: str    # Variant A (doc)
    estimate_owner_id: str  # Variant B (owner)


class CompareResponse(BaseModel):
    doc_total: str
    owner_total: str
    delta_pln: str
    margin_headroom_pct: str


class ParamsUpdate(BaseModel):
    params: dict[str, Any]


# ─── POST /tenders/{id}/estimate — build BOTH variants ─────────────────────

@router.post("/tenders/{tender_id}/estimate", response_model=EstimatePair)
def create_estimate(tender_id: str) -> EstimatePair:
    """Build Variant A + B from analyzed przedmiar. Returns both estimate IDs."""
    engine = get_engine()

    # Get analysis (must run /analyze first)
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT przedmiar_items FROM analysis WHERE tender_id = :tid"),
            {"tid": tender_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found. Run POST /tenders/{id}/analyze first.")

    items = row[0] or []
    if not items:
        raise HTTPException(status_code=422, detail="No przedmiar items found in analysis.")

    # Get owner rate_card if exists
    rate_card = _load_rate_card(engine, tender_id)

    # Compute both variants
    est_a = compute_variant_a(items)
    est_b = compute_variant_b(items, rate_card=rate_card)

    # Map variant names to DB enum values
    est_a.variant = "doc"
    est_b.variant = "owner"

    # Verify sum reconciliation — must be exact
    assert verify_sum_reconciliation(est_a), "Variant A sum reconciliation FAILED"
    assert verify_sum_reconciliation(est_b), "Variant B sum reconciliation FAILED"

    # Store
    id_a = _store_estimate(engine, tender_id, est_a)
    id_b = _store_estimate(engine, tender_id, est_b)

    return EstimatePair(estimate_doc_id=id_a, estimate_owner_id=id_b)


# ─── GET /estimates/{id} ─────────────────────────────────────────────────────

@router.get("/tenders/{tender_id}/estimates")
def list_estimates_for_tender(tender_id: str) -> list[dict]:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT id, variant, total_net_pln, lines, params FROM estimate WHERE tender_id = :tid ORDER BY variant"),
            {"tid": tender_id},
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No estimates found for this tender")
    results = []
    for row in rows:
        lines_raw = row[3] or []
        # Normalize lines to a consistent format regardless of seed data shape
        normalized_lines = []
        for i, l in enumerate(lines_raw):
            normalized_lines.append({
                "position_no": l.get("position_no", str(i + 1)),
                "description": l.get("description", ""),
                "unit": l.get("unit", ""),
                "quantity": str(l.get("quantity", "0")),
                "unit_price": str(l.get("unit_price", "0")),
                "line_total_pln": str(l.get("line_total_pln", l.get("total", "0"))),
                "knr_code": l.get("knr_code"),
                "chapter": l.get("chapter"),
            })
        results.append({
            "id": str(row[0]),
            "variant": row[1],
            "total_net_pln": str(row[2]),
            "lines": normalized_lines,
            "params": row[4] or {},
        })
    return results


@router.get("/estimates/{estimate_id}", response_model=EstimateResponse)
def get_estimate(estimate_id: str) -> EstimateResponse:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT id, variant, total_net_pln, lines, params FROM estimate WHERE id = :id"),
            {"id": estimate_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Estimate not found")

    lines_raw = row[3] or []
    lines = [EstimateLineSchema(**l) for l in lines_raw]
    from decimal import Decimal
    total = row[2]
    sum_lines = sum((Decimal(str(l.line_total_pln)) for l in lines), Decimal("0"))
    reconciled = sum_lines == Decimal(str(total)).quantize(Decimal("0.01"))

    return EstimateResponse(
        id=str(row[0]),
        variant=row[1],
        total_net_pln=str(row[2]),
        lines=lines,
        params=row[4] or {},
        sum_reconciled=reconciled,
    )


# ─── PATCH /estimates/{id}/params — recompute with new params ────────────────

@router.patch("/estimates/{estimate_id}/params", response_model=EstimateResponse)
def update_estimate_params(estimate_id: str, body: ParamsUpdate) -> EstimateResponse:
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT tender_id, variant, params FROM estimate WHERE id = :id"),
            {"id": estimate_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Estimate not found")

    tender_id, variant, current_params = str(row[0]), row[1], row[2] or {}
    merged_params = {**current_params, **body.params}

    # Get przedmiar
    with engine.connect() as conn:
        row2 = conn.execute(
            sa.text("SELECT przedmiar_items FROM analysis WHERE tender_id = :tid"),
            {"tid": tender_id},
        ).fetchone()
    if not row2:
        raise HTTPException(status_code=404, detail="Analysis not found")

    items = row2[0] or []
    from decimal import Decimal

    if variant == "A":
        est = compute_variant_a(items)
    else:
        # Apply params to rate_card
        rc = RateCard(
            kp_pct=Decimal(str(merged_params.get("kp_pct", "12.0"))),
            zysk_pct=Decimal(str(merged_params.get("zysk_pct", "8.0"))),
            robocizna_zl_rg=Decimal(str(merged_params.get("robocizna_zl_rg", "35.0"))),
            calibration_coeff=Decimal(str(merged_params.get("calibration_coeff", "1.00"))),
        )
        est = compute_variant_b(items, rate_card=rc)

    assert verify_sum_reconciliation(est)
    _update_estimate(engine, estimate_id, est, merged_params)

    return get_estimate(estimate_id)


# ─── GET /tenders/{id}/estimate/compare ────────────────────────────────────

@router.get("/tenders/{tender_id}/estimate/compare", response_model=CompareResponse)
def compare_estimate_endpoint(tender_id: str) -> CompareResponse:
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT variant, total_net_pln, lines, params FROM estimate "
                "WHERE tender_id = :tid ORDER BY created_at DESC"
            ),
            {"tid": tender_id},
        ).fetchall()

    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="Need both variants. Run POST /tenders/{id}/estimate first.")

    from services.estimator import Estimate, EstimateLine
    from decimal import Decimal

    estimates: dict[str, Any] = {}
    for row in rows:
        v = row[0]
        if v not in estimates:
            lines = [
                EstimateLine(
                    position_no=l.get("position_no", ""),
                    description=l.get("description", ""),
                    unit=l.get("unit", ""),
                    quantity=Decimal(str(l.get("quantity", "0"))),
                    line_total_pln=Decimal(str(l.get("line_total_pln", "0"))),
                )
                for l in (row[2] or [])
            ]
            estimates[v] = Estimate(
                variant=v,
                lines=lines,
                total_net_pln=Decimal(str(row[1] or "0")),
            )

    if "doc" not in estimates or "owner" not in estimates:
        raise HTTPException(status_code=404, detail="Both variants required (doc and owner).")

    cmp = compare_estimates(estimates["doc"], estimates["owner"])
    return CompareResponse(**cmp.to_dict())


# ─── Internal helpers ────────────────────────────────────────────────────────

def _get_tenant_id(engine) -> str:
    """Get or create default tenant."""
    with engine.connect() as conn:
        row = conn.execute(sa.text("SELECT id FROM tenant LIMIT 1")).fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="No tenant found in DB")
    return str(row[0])


def _store_estimate(engine, tender_id: str, estimate) -> str:
    tenant_id = _get_tenant_id(engine)
    # Upsert by (tenant_id, tender_id, variant)
    with engine.begin() as conn:
        row = conn.execute(
            sa.text("SELECT id FROM estimate WHERE tenant_id=:tid AND tender_id=:eid AND variant=:v"),
            {"tid": tenant_id, "eid": tender_id, "v": estimate.variant},
        ).fetchone()
        if row:
            new_id = str(row[0])
            conn.execute(
                sa.text("UPDATE estimate SET total_net_pln=:total, lines=cast(:lines as jsonb), "
                        "params=cast(:params as jsonb) WHERE id=:id"),
                {"id": new_id, "total": str(estimate.total_net_pln),
                 "lines": json.dumps([l.to_dict() for l in estimate.lines], ensure_ascii=False),
                 "params": json.dumps(estimate.params, ensure_ascii=False)},
            )
        else:
            new_id = str(uuid.uuid4())
            conn.execute(
                sa.text("INSERT INTO estimate (id, tenant_id, tender_id, variant, total_net_pln, "
                        "lines, params, created_at) VALUES "
                        "(:id, :tid, :eid, :v, :total, cast(:lines as jsonb), cast(:params as jsonb), now())"),
                {"id": new_id, "tid": tenant_id, "eid": tender_id,
                 "v": estimate.variant, "total": str(estimate.total_net_pln),
                 "lines": json.dumps([l.to_dict() for l in estimate.lines], ensure_ascii=False),
                 "params": json.dumps(estimate.params, ensure_ascii=False)},
            )
    return new_id


def _update_estimate(engine, estimate_id: str, estimate, params: dict) -> None:
    with engine.begin() as conn:
        conn.execute(
            sa.text("UPDATE estimate SET total_net_pln=:total, lines=cast(:lines as jsonb), "
                    "params=cast(:params as jsonb) WHERE id=:id"),
            {"id": estimate_id, "total": str(estimate.total_net_pln),
             "lines": json.dumps([l.to_dict() for l in estimate.lines], ensure_ascii=False),
             "params": json.dumps(params, ensure_ascii=False)},
        )


def _load_rate_card(engine, tender_id: str) -> RateCard | None:
    """Load owner rate_card from DB if exists."""
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT rate_card FROM owner_profile LIMIT 1"),
        ).fetchone()
    if row and row[0]:
        from decimal import Decimal
        rc_data = row[0]
        return RateCard(
            robocizna_zl_rg=Decimal(str(rc_data.get("robocizna_zl_rg", "35.00"))),
            kp_pct=Decimal(str(rc_data.get("kp_pct", "12.0"))),
            zysk_pct=Decimal(str(rc_data.get("zysk_pct", "8.0"))),
        )
    return None
