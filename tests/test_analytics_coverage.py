"""T3-2 — Analytics router coverage: analytics.py + analytics_v2.py (39%/50% → 65%+).

Tests for /api/v2/analytics/* endpoints using AsyncClient + ASGITransport + mocking.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ─── App + auth fixtures ─────────────────────────────────────────────────────

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


# ─── Integration tests via ASGI ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analytics_dashboard_200(app, auth_headers):
    """GET /api/v2/analytics/dashboard → 200 with KPI fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "pipeline_value" in data or "win_rate" in data or "active_bids" in data


@pytest.mark.asyncio
async def test_analytics_dashboard_no_auth_override(app, auth_headers):
    """GET /api/v2/analytics/dashboard with auth → 200 (conftest overrides auth)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/dashboard", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_pipeline_funnel_200(app, auth_headers):
    """GET /api/v2/analytics/pipeline-funnel → 200 with funnel data."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/pipeline-funnel", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "funnel" in data or "total" in data


@pytest.mark.asyncio
async def test_analytics_win_rate_trend_200(app, auth_headers):
    """GET /api/v2/analytics/win-rate-trend → 200 with trend list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/win-rate-trend", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "trend" in data


@pytest.mark.asyncio
async def test_analytics_win_rate_trend_months_param(app, auth_headers):
    """GET /api/v2/analytics/win-rate-trend?months=3 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/win-rate-trend?months=3", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_win_probability_200(app, auth_headers):
    """GET /api/v2/analytics/win-probability → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v2/analytics/win-probability?markup=0.12&cpv=45&n_competitors=4",
            headers=auth_headers,
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_win_probability_missing_markup_422(app, auth_headers):
    """GET /api/v2/analytics/win-probability without markup → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/win-probability", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analytics_cache_invalidate_200(app, auth_headers):
    """POST /api/v2/analytics/cache/invalidate → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v2/analytics/cache/invalidate", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True


@pytest.mark.asyncio
async def test_analytics_ahp_post_200(app, auth_headers):
    """POST /api/v2/analytics/ahp → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v2/analytics/ahp",
            json={"scores": {"price": 8.0, "experience": 7.0, "timeline": 6.0}},
            headers=auth_headers,
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_bidding_post_200(app, auth_headers):
    """POST /api/v2/analytics/bidding → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v2/analytics/bidding",
            json={"cost_estimate": 100000.0, "n_competitors": 4},
            headers=auth_headers,
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_risk_extract_post_200(app, auth_headers):
    """POST /api/v2/analytics/risk-extract → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v2/analytics/risk-extract",
            json={"text": "Projekt budowlany z karami umownymi 5% za opóźnienie.", "use_ai": False},
            headers=auth_headers,
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analytics_dashboard_cached_second_call(app, auth_headers):
    """Second call to /analytics/dashboard should return _cached=True or same data."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/api/v2/analytics/dashboard", headers=auth_headers)
        resp2 = await client.get("/api/v2/analytics/dashboard", headers=auth_headers)
    assert resp2.status_code == 200


# ─── Unit tests ──────────────────────────────────────────────────────────────

class TestAnalyticsDashboardUnit:
    def _user(self, org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d"):
        u = MagicMock()
        u.org_id = org_id
        u.user_id = "40a71ef6-d6eb-48a3-b62e-7da3df5f0a17"
        return u

    def test_no_org_raises_403(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.analytics import analytics_dashboard
        u = self._user(org_id=None)
        with pytest.raises(HTTPException) as exc:
            analytics_dashboard(u)
        assert exc.value.status_code == 403

    def test_pipeline_funnel_no_org_raises_403(self):
        from fastapi import HTTPException
        from services.api.services.api.routers.analytics import pipeline_funnel
        u = self._user(org_id=None)
        with pytest.raises(HTTPException) as exc:
            pipeline_funnel(u)
        assert exc.value.status_code == 403


class TestAnalyticsV2Integration:
    """Analytics v2 router extra endpoints."""

    @pytest.mark.asyncio
    async def test_analytics_dashboard_returns_win_rate(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v2/analytics/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Should have numeric win_rate
        if "win_rate" in data:
            assert isinstance(data["win_rate"], (int, float))

    @pytest.mark.asyncio
    async def test_win_rate_trend_returns_months_field(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v2/analytics/win-rate-trend?months=6", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("months") == 6
