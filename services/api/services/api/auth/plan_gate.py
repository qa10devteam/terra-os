"""Plan gating — FastAPI Depends() dla ochrony endpointów per plan.

Hierarchia planów: free < starter < pro < business < enterprise
Użycie:
    from ..auth.plan_gate import require_plan, PlanLevel
    @router.get("/foo")
    async def foo(user: AuthUser, _gate: None = require_plan(PlanLevel.PRO)):
        ...
"""
from __future__ import annotations
from enum import IntEnum
from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from terra_db.session import get_engine
from ..auth.deps import AuthUser


class PlanLevel(IntEnum):
    FREE = 0
    STARTER = 1
    PRO = 2
    BUSINESS = 3
    ENTERPRISE = 4


PLAN_RANK: dict[str, PlanLevel] = {
    "free": PlanLevel.FREE,
    "starter": PlanLevel.STARTER,
    "pro": PlanLevel.PRO,
    "business": PlanLevel.BUSINESS,
    "enterprise": PlanLevel.ENTERPRISE,
}


def _get_org_plan(org_id: str) -> str:
    """Pobiera plan z tabeli subscription lub organizations (fallback)."""
    try:
        with get_engine().connect() as conn:
            row = conn.execute(
                text("SELECT plan FROM subscription WHERE org_id = :oid"),
                {"oid": org_id},
            ).fetchone()
            if row:
                return str(row.plan)
            # fallback — organizations.plan
            row2 = conn.execute(
                text("SELECT plan FROM organizations WHERE id = :oid"),
                {"oid": org_id},
            ).fetchone()
            return str(row2.plan) if row2 else "free"
    except Exception:
        return "free"


def require_plan(minimum: PlanLevel):
    """Dependency factory — raises 403 gdy plan użytkownika < minimum."""
    def _check(user: AuthUser) -> None:
        plan_str = _get_org_plan(str(user.org_id)) if user.org_id else "free"
        user_level = PLAN_RANK.get(plan_str, PlanLevel.FREE)
        if user_level < minimum:
            plan_names = {v: k for k, v in PLAN_RANK.items()}
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "plan_upgrade_required",
                    "current_plan": plan_str,
                    "required_plan": plan_names.get(minimum, "pro"),
                    "upgrade_url": "/pricing",
                    "message": f"Ta funkcja wymaga planu {plan_names.get(minimum, 'pro').upper()} lub wyższego.",
                },
            )
    return Depends(_check)
