"""T3-1 — Billing router coverage: billing.py (33% → 70%+).

Tests for /api/v2/billing/* endpoints using AsyncClient + ASGITransport.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ─── App fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


@pytest.fixture(scope="module")
def auth_headers():
    from services.api.services.api.auth.utils import create_access_token
    token = create_access_token(
        user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
        email="demo@terra-os.pl",
        org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
        role="owner",
    )
    return {"Authorization": f"Bearer {token}"}


# ─── Unit tests for plans (public endpoint, no auth needed) ─────────────────

class TestListPlansUnit:
    def test_returns_list(self):
        from services.api.services.api.routers.billing import list_plans
        result = list_plans()
        assert isinstance(result, list)
        assert len(result) >= 3

    def test_free_plan_exists(self):
        from services.api.services.api.routers.billing import list_plans
        plans = list_plans()
        ids = [p["id"] for p in plans]
        assert "free" in ids

    def test_pro_plan_exists_with_price(self):
        from services.api.services.api.routers.billing import list_plans
        plans = list_plans()
        pro = next((p for p in plans if p["id"] == "pro"), None)
        assert pro is not None
        assert pro["price_pln"] > 0

    def test_enterprise_plan_exists(self):
        from services.api.services.api.routers.billing import list_plans
        plans = list_plans()
        ids = [p["id"] for p in plans]
        assert "enterprise" in ids

    def test_all_plans_have_required_fields(self):
        from services.api.services.api.routers.billing import list_plans
        for plan in list_plans():
            assert "id" in plan
            assert "name" in plan
            assert "price_label" in plan


# ─── Integration tests via ASGI ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_plans_http_200(app, auth_headers):
    """GET /api/v2/billing/plans → 200 with list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/billing/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_plans_contain_free(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/billing/plans")
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert "free" in ids


@pytest.mark.asyncio
async def test_plans_contain_enterprise(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/billing/plans")
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert "enterprise" in ids


@pytest.mark.asyncio
async def test_get_subscription_returns_plan_and_status(app, auth_headers):
    """GET /api/v2/billing/subscription → 200 with plan + status fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/billing/subscription", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "plan" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_get_subscription_with_auth_has_plan(app, auth_headers):
    """GET /api/v2/billing/subscription with auth returns plan field."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/billing/subscription", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "plan" in data
    # plan_details should contain id
    assert "plan_details" in data


@pytest.mark.asyncio
async def test_checkout_free_plan_returns_redirect(app, auth_headers):
    """POST /api/v2/billing/checkout with free plan → contact redirect."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v2/billing/checkout",
            json={"plan_id": "free", "success_url": "/billing/success", "cancel_url": "/pricing"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "redirect_url" in data


@pytest.mark.asyncio
async def test_checkout_enterprise_plan_returns_redirect(app, auth_headers):
    """POST /api/v2/billing/checkout with enterprise plan → contact redirect."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v2/billing/checkout",
            json={"plan_id": "enterprise"},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "redirect_url" in data


@pytest.mark.asyncio
async def test_checkout_unknown_plan_400(app, auth_headers):
    """POST /api/v2/billing/checkout with invalid plan_id → 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v2/billing/checkout",
            json={"plan_id": "nonexistent_plan"},
            headers=auth_headers,
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_checkout_invalid_body_422(app, auth_headers):
    """POST /api/v2/billing/checkout with completely missing body → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v2/billing/checkout",
            content="not json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_checkout_url_endpoint(app, auth_headers):
    """GET /api/v2/billing/checkout-url → 200 with url field."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/billing/checkout-url?plan=pro", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data


@pytest.mark.asyncio
async def test_checkout_pro_placeholder_returns_503_or_fallback(app, auth_headers):
    """POST /api/v2/billing/checkout for pro plan without configured Stripe → 503 or fallback."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v2/billing/checkout",
            json={"plan_id": "pro"},
            headers=auth_headers,
        )
    # With placeholder price IDs → 503; without Stripe configured → fallback 200
    assert resp.status_code in (200, 503)


# ─── Unit tests for subscription and cancel ─────────────────────────────────

class TestSubscriptionUnit:
    def _user(self, org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d"):
        u = MagicMock()
        u.org_id = org_id
        u.user_id = "40a71ef6-d6eb-48a3-b62e-7da3df5f0a17"
        return u

    def test_no_org_id_returns_free(self):
        from services.api.services.api.routers.billing import get_subscription
        result = get_subscription(self._user(org_id=None), MagicMock())
        assert result["plan"] == "free"
        assert "status" in result

    def test_subscription_with_org_has_plan_details(self):
        from services.api.services.api.routers.billing import get_subscription
        db = MagicMock()
        # Simulate fetchone returning None → create free sub
        db.execute.return_value.fetchone.return_value = None
        result = get_subscription(self._user(), db)
        assert "plan" in result
        assert "plan_details" in result


class TestCancelUnit:
    def _user(self, org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d"):
        u = MagicMock()
        u.org_id = org_id
        u.user_id = "40a71ef6-d6eb-48a3-b62e-7da3df5f0a17"
        return u

    def test_cancel_no_org_raises_400(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.billing import cancel_subscription
        with pytest.raises(HTTPException) as exc:
            cancel_subscription(self._user(org_id=None), MagicMock())
        assert exc.value.status_code == 400

    def test_cancel_free_plan_raises_400(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.billing import cancel_subscription
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None  # → creates free sub
        with pytest.raises(HTTPException) as exc:
            cancel_subscription(self._user(), db)
        assert exc.value.status_code == 400

    def test_cancel_pro_sets_flag(self):
        from services.api.services.api.routers.billing import cancel_subscription
        db = MagicMock()
        pro_sub = {
            "plan": "pro",
            "status": "active",
            "org_id": "ec3d1e16-2139-48c2-93b5-ffe0defd606d",
            "grace_until": None,
            "stripe_subscription_id": None,
            "stripe_customer_id": None,
            "current_period_end": None,
        }
        with patch(
            "services.api.services.api.routers.billing._get_or_create_subscription",
            return_value=pro_sub,
        ):
            with patch.dict("os.environ", {"STRIPE_SECRET_KEY": ""}, clear=False):
                result = cancel_subscription(self._user(), db)
        assert result.get("cancel_at_period_end") is True
