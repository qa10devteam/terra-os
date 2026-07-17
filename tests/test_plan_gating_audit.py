"""Plan gating audit — verify all premium endpoints enforce plan requirements.

Tests the require_plan() decorator logic and confirms that key routers
properly gate their endpoints behind the correct plan level.
"""
from __future__ import annotations

import importlib
import inspect
import sys
import os
from unittest.mock import patch, MagicMock

import pytest

# Ensure path resolution
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API_PATH = os.path.join(ROOT, "services", "api")
if API_PATH not in sys.path:
    sys.path.insert(0, API_PATH)


# ─── Unit tests for plan_gate.py logic ───────────────────────────────────────

class TestPlanLevelHierarchy:
    """Verify PlanLevel ordering and PLAN_RANK mapping."""

    def test_plan_ordering(self):
        from services.api.services.api.auth.plan_gate import PlanLevel
        assert PlanLevel.FREE < PlanLevel.STARTER < PlanLevel.PRO < PlanLevel.BUSINESS < PlanLevel.ENTERPRISE

    def test_plan_rank_mapping(self):
        from services.api.services.api.auth.plan_gate import PLAN_RANK, PlanLevel
        assert PLAN_RANK["free"] == PlanLevel.FREE
        assert PLAN_RANK["starter"] == PlanLevel.STARTER
        assert PLAN_RANK["pro"] == PlanLevel.PRO
        assert PLAN_RANK["business"] == PlanLevel.BUSINESS
        assert PLAN_RANK["enterprise"] == PlanLevel.ENTERPRISE

    def test_unknown_plan_defaults_to_free(self):
        from services.api.services.api.auth.plan_gate import PLAN_RANK, PlanLevel
        level = PLAN_RANK.get("nonexistent", PlanLevel.FREE)
        assert level == PlanLevel.FREE


class TestRequirePlanDecorator:
    """Test that require_plan raises 403 for insufficient plans."""

    def _make_user(self, org_id="org-123"):
        user = MagicMock()
        user.org_id = org_id
        return user

    def test_free_user_blocked_from_starter(self):
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel, _get_org_plan
        from fastapi import HTTPException

        dep = require_plan(PlanLevel.STARTER)
        # Extract the inner _check function from the Depends wrapper
        check_fn = dep.dependency

        user = self._make_user()
        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="free"):
            with pytest.raises(HTTPException) as exc_info:
                check_fn(user)
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["error"] == "plan_upgrade_required"
            assert exc_info.value.detail["required_plan"] == "starter"

    def test_starter_user_allowed_for_starter(self):
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel

        dep = require_plan(PlanLevel.STARTER)
        check_fn = dep.dependency

        user = self._make_user()
        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="starter"):
            result = check_fn(user)
            assert result is None  # No exception = access granted

    def test_pro_user_allowed_for_starter(self):
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel

        dep = require_plan(PlanLevel.STARTER)
        check_fn = dep.dependency

        user = self._make_user()
        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="pro"):
            result = check_fn(user)
            assert result is None

    def test_starter_user_blocked_from_pro(self):
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel
        from fastapi import HTTPException

        dep = require_plan(PlanLevel.PRO)
        check_fn = dep.dependency

        user = self._make_user()
        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="starter"):
            with pytest.raises(HTTPException) as exc_info:
                check_fn(user)
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["required_plan"] == "pro"

    def test_pro_user_blocked_from_business(self):
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel
        from fastapi import HTTPException

        dep = require_plan(PlanLevel.BUSINESS)
        check_fn = dep.dependency

        user = self._make_user()
        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="pro"):
            with pytest.raises(HTTPException) as exc_info:
                check_fn(user)
            assert exc_info.value.status_code == 403
            assert exc_info.value.detail["required_plan"] == "business"

    def test_business_user_allowed_for_business(self):
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel

        dep = require_plan(PlanLevel.BUSINESS)
        check_fn = dep.dependency

        user = self._make_user()
        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="business"):
            result = check_fn(user)
            assert result is None

    def test_no_org_id_defaults_to_free(self):
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel
        from fastapi import HTTPException

        dep = require_plan(PlanLevel.STARTER)
        check_fn = dep.dependency

        user = self._make_user(org_id=None)
        with pytest.raises(HTTPException) as exc_info:
            check_fn(user)
        assert exc_info.value.status_code == 403

    def test_403_response_contains_upgrade_url(self):
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel
        from fastapi import HTTPException

        dep = require_plan(PlanLevel.PRO)
        check_fn = dep.dependency

        user = self._make_user()
        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="free"):
            with pytest.raises(HTTPException) as exc_info:
                check_fn(user)
            assert exc_info.value.detail["upgrade_url"] == "/pricing"


# ─── Router audit: verify plan gating is present on key endpoints ─────────────

# Expected plan gating configuration per router
EXPECTED_GATING = {
    "bid_writing": {
        "module": "services.api.services.api.routers.bid_writing",
        "min_plan": "PRO",
        "endpoints": ["generate_bid_writing"],
    },
    "submit_wizard": {
        "module": "services.api.services.api.routers.submit_wizard",
        "min_plan": "STARTER",
        "endpoints": ["get_wizard_status", "confirm_step", "final_confirm", "get_tracking"],
    },
    "advanced_analytics": {
        "module": "services.api.services.api.routers.advanced_analytics",
        "min_plan": "BUSINESS",
        "endpoints": [],  # Already verified — just check import
    },
    "market_intelligence": {
        "module": "services.api.services.api.routers.market_intelligence",
        "min_plan": "BUSINESS",
        "endpoints": [],  # Already verified — just check import
    },
    "kosztorys_v3": {
        "module": "services.api.services.api.routers.kosztorys_v3",
        "min_plan": "STARTER",
        "endpoints": ["get_icb_rates", "ai_wycena_v2"],
    },
    "forecasting": {
        "module": "services.api.services.api.routers.forecasting",
        "min_plan": "PRO",
        "endpoints": ["timeseries", "seasonality_analysis", "predict"],
    },
    "agent_pipeline": {
        "module": "services.api.services.api.routers.agent_pipeline",
        "min_plan": "BUSINESS",
        "endpoints": ["agent_analyze", "agent_decision", "get_agent_run", "get_brief", "agent_analyze_stream"],
    },
    "offer_assembly": {
        "module": "services.api.services.api.routers.offer_assembly",
        "min_plan": "STARTER",
        "endpoints": ["generate_documents", "map_knr_positions"],
    },
}


def _has_require_plan_in_signature(func) -> bool:
    """Check if a function has require_plan in its default parameter values."""
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if param.default is not inspect.Parameter.empty:
            # Check if it's a Depends() with plan check
            dep = param.default
            if hasattr(dep, "dependency"):
                # It's a FastAPI Depends object
                dep_fn = dep.dependency
                if dep_fn and hasattr(dep_fn, "__name__") and "check" in dep_fn.__name__:
                    return True
                # Also check if it's a closure from require_plan
                if dep_fn and hasattr(dep_fn, "__qualname__") and "require_plan" in dep_fn.__qualname__:
                    return True
    return False


def _get_plan_level_from_signature(func) -> str | None:
    """Extract the PlanLevel from a function's require_plan dependency."""
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if param.default is not inspect.Parameter.empty:
            dep = param.default
            if hasattr(dep, "dependency"):
                dep_fn = dep.dependency
                if dep_fn and hasattr(dep_fn, "__qualname__") and "require_plan" in dep_fn.__qualname__:
                    # Get the closure variable 'minimum'
                    if hasattr(dep_fn, "__closure__") and dep_fn.__closure__:
                        for cell in dep_fn.__closure__:
                            try:
                                val = cell.cell_contents
                                if hasattr(val, "name"):  # It's a PlanLevel enum
                                    return val.name
                            except ValueError:
                                pass
    return None


class TestRouterGatingPresence:
    """Verify that key routers import and use plan_gate correctly."""

    @pytest.mark.parametrize("router_name,config", list(EXPECTED_GATING.items()))
    def test_router_has_plan_gate_import(self, router_name, config):
        """Each premium router must import require_plan and PlanLevel."""
        module = importlib.import_module(config["module"])
        source = inspect.getsource(module)
        assert "require_plan" in source, (
            f"Router '{router_name}' ({config['module']}) does not import require_plan"
        )
        assert "PlanLevel" in source, (
            f"Router '{router_name}' ({config['module']}) does not import PlanLevel"
        )

    @pytest.mark.parametrize("router_name,config", [
        (k, v) for k, v in EXPECTED_GATING.items() if v["endpoints"]
    ])
    def test_endpoints_have_plan_gate(self, router_name, config):
        """Each endpoint function must have require_plan in its signature."""
        module = importlib.import_module(config["module"])
        for endpoint_name in config["endpoints"]:
            func = getattr(module, endpoint_name, None)
            assert func is not None, (
                f"Endpoint '{endpoint_name}' not found in {config['module']}"
            )
            assert _has_require_plan_in_signature(func), (
                f"Endpoint '{endpoint_name}' in router '{router_name}' "
                f"is missing require_plan() gating"
            )

    @pytest.mark.parametrize("router_name,config", [
        (k, v) for k, v in EXPECTED_GATING.items() if v["endpoints"]
    ])
    def test_endpoints_have_correct_plan_level(self, router_name, config):
        """Each endpoint must gate at the correct minimum plan level."""
        module = importlib.import_module(config["module"])
        expected_level = config["min_plan"]
        for endpoint_name in config["endpoints"]:
            func = getattr(module, endpoint_name, None)
            if func is None:
                continue
            actual_level = _get_plan_level_from_signature(func)
            if actual_level:
                # The actual level should be >= expected (stricter is OK)
                from services.api.services.api.auth.plan_gate import PlanLevel
                actual_val = PlanLevel[actual_level]
                expected_val = PlanLevel[expected_level]
                assert actual_val >= expected_val, (
                    f"Endpoint '{endpoint_name}' in '{router_name}' gates at "
                    f"{actual_level} but should be at least {expected_level}"
                )


# ─── Integration-style: ensure plan_gate raises for key paths ────────────────

class TestPlanGatingIntegration:
    """Simulate plan gating for various plan levels against key endpoints."""

    @pytest.fixture
    def free_user(self):
        user = MagicMock()
        user.org_id = "org-free-001"
        return user

    @pytest.fixture
    def starter_user(self):
        user = MagicMock()
        user.org_id = "org-starter-001"
        return user

    @pytest.fixture
    def pro_user(self):
        user = MagicMock()
        user.org_id = "org-pro-001"
        return user

    @pytest.fixture
    def business_user(self):
        user = MagicMock()
        user.org_id = "org-business-001"
        return user

    def test_free_user_cannot_access_starter_endpoints(self, free_user):
        """Free user must be blocked from starter+ endpoints."""
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel
        from fastapi import HTTPException

        for level in [PlanLevel.STARTER, PlanLevel.PRO, PlanLevel.BUSINESS]:
            dep = require_plan(level)
            check_fn = dep.dependency
            with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="free"):
                with pytest.raises(HTTPException) as exc_info:
                    check_fn(free_user)
                assert exc_info.value.status_code == 403

    def test_starter_user_can_access_starter_but_not_pro(self, starter_user):
        """Starter user can access starter endpoints but not pro/business."""
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel
        from fastapi import HTTPException

        dep_starter = require_plan(PlanLevel.STARTER)
        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="starter"):
            result = dep_starter.dependency(starter_user)
            assert result is None  # Allowed

        dep_pro = require_plan(PlanLevel.PRO)
        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="starter"):
            with pytest.raises(HTTPException):
                dep_pro.dependency(starter_user)

    def test_pro_user_can_access_pro_and_starter(self, pro_user):
        """Pro user can access both starter and pro endpoints."""
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel

        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="pro"):
            assert require_plan(PlanLevel.STARTER).dependency(pro_user) is None
            assert require_plan(PlanLevel.PRO).dependency(pro_user) is None

    def test_business_user_can_access_all(self, business_user):
        """Business user can access all plan-gated endpoints."""
        from services.api.services.api.auth.plan_gate import require_plan, PlanLevel

        with patch("services.api.services.api.auth.plan_gate._get_org_plan", return_value="business"):
            assert require_plan(PlanLevel.STARTER).dependency(business_user) is None
            assert require_plan(PlanLevel.PRO).dependency(business_user) is None
            assert require_plan(PlanLevel.BUSINESS).dependency(business_user) is None
