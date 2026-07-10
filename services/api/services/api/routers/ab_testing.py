"""S133 — A/B Testing experiments endpoints."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v2/ab', tags=['ab_testing'])


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


class ExperimentCreate(BaseModel):
    name: str
    variant_a_config: dict = {}
    variant_b_config: dict = {}
    traffic_split: float = 0.5


@router.post('/experiments')
def create_experiment(body: ExperimentCreate, user: AuthUser, db: DB):
    db.execute(
        text(
            'INSERT INTO ab_experiments(name, tenant_id, variant_a_config, variant_b_config, traffic_split) '
            'VALUES(:n, :t, :a, :b, :s)'
        ),
        {
            'n': body.name,
            't': str(user.org_id),
            'a': json.dumps(body.variant_a_config),
            'b': json.dumps(body.variant_b_config),
            's': body.traffic_split,
        }
    )
    db.commit()
    return {'status': 'created'}


@router.get('/experiments/{exp_id}/assignment')
def get_assignment(exp_id: str, user_id: str, user: AuthUser, db: DB):
    exp = db.execute(
        text('SELECT traffic_split FROM ab_experiments WHERE id=:id'),
        {'id': exp_id}
    ).fetchone()
    if not exp:
        return {'variant': 'A', 'note': 'experiment not found'}
    bucket = int(hashlib.md5(f'{exp_id}:{user_id}'.encode()).hexdigest(), 16) % 100 / 100
    return {'variant': 'A' if bucket < exp.traffic_split else 'B', 'user_id': user_id}
