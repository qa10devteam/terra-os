"""S125-S126 — Data Quality reporting endpoints."""
from __future__ import annotations

import logging
from typing import Any, Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v2/data-quality', tags=['data_quality'])


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


@router.get('/report')
def dq_report(user: AuthUser, db: DB):
    tid = str(user.org_id)
    total = db.execute(text('SELECT count(*) FROM tender WHERE tenant_id=:t'), {'t': tid}).scalar() or 0
    no_cpv = db.execute(text('SELECT count(*) FROM tender WHERE tenant_id=:t AND cpv_code IS NULL'), {'t': tid}).scalar() or 0
    no_val = db.execute(text('SELECT count(*) FROM tender WHERE tenant_id=:t AND value_pln IS NULL'), {'t': tid}).scalar() or 0
    no_dl = db.execute(text('SELECT count(*) FROM tender WHERE tenant_id=:t AND deadline_at IS NULL'), {'t': tid}).scalar() or 0
    complete = total - max(no_cpv, no_val, no_dl)
    return {
        'total': total,
        'no_cpv': no_cpv,
        'no_value': no_val,
        'no_deadline': no_dl,
        'completeness_score': round(complete / max(total, 1) * 100, 1),
    }


@router.get('/dashboard')
def dq_dashboard(user: AuthUser, db: DB):
    rows = db.execute(
        text('SELECT source, count(*) total, count(cpv_code) with_cpv, count(value_pln) with_value FROM tender GROUP BY source')
    ).fetchall()
    return [
        {
            'source': r.source,
            'total': r.total,
            'completeness_pct': round((r.with_cpv + r.with_value) / (r.total * 2) * 100, 1),
        }
        for r in rows
    ]


@router.get('/score')
def dq_score(user: AuthUser, db: DB):
    """GET /api/v2/data-quality/score — overall data-quality score for current tenant."""
    tid = str(user.org_id)
    try:
        total = db.execute(text('SELECT count(*) FROM tender WHERE tenant_id=:t'), {'t': tid}).scalar() or 0
        no_cpv = db.execute(text('SELECT count(*) FROM tender WHERE tenant_id=:t AND cpv_code IS NULL'), {'t': tid}).scalar() or 0
        no_val = db.execute(text('SELECT count(*) FROM tender WHERE tenant_id=:t AND value_pln IS NULL'), {'t': tid}).scalar() or 0
        no_dl = db.execute(text('SELECT count(*) FROM tender WHERE tenant_id=:t AND deadline_at IS NULL'), {'t': tid}).scalar() or 0
        missing = max(no_cpv, no_val, no_dl)
        score = round((1 - missing / max(total, 1)) * 100, 1)
    except Exception:
        total, score = 0, 0.0
    return {'tenant_id': tid, 'total_tenders': total, 'score': score, 'grade': 'A' if score >= 90 else ('B' if score >= 70 else 'C')}

