"""C1-5 — OLAP analytics router coverage: routers/olap.py (24% → 55%+).

Tests for /api/v2/analytics/* OLAP endpoints.
"""
from __future__ import annotations

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


# ─── GET /api/v2/analytics/olap ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_olap_market_200(app, auth_headers):
    """GET /api/v2/analytics/olap → 200, returns a list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/olap", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_olap_market_group_by_quarter(app, auth_headers):
    """GET /api/v2/analytics/olap?group_by=quarter → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/olap?group_by=quarter", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_olap_market_group_by_month(app, auth_headers):
    """GET /api/v2/analytics/olap?group_by=month → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/olap?group_by=month", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_olap_market_invalid_group_by(app, auth_headers):
    """GET /api/v2/analytics/olap?group_by=week → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/olap?group_by=week", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_olap_market_cpv_filter(app, auth_headers):
    """GET /api/v2/analytics/olap?cpv_division=45 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/olap?cpv_division=45", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_olap_market_year_filter(app, auth_headers):
    """GET /api/v2/analytics/olap?year=2024 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/olap?year=2024", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── GET /api/v2/analytics/price-index ───────────────────────────────────────

@pytest.mark.asyncio
async def test_olap_price_index_200(app, auth_headers):
    """GET /api/v2/analytics/price-index → 200, returns list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/price-index", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_olap_price_index_cpv_filter(app, auth_headers):
    """GET /api/v2/analytics/price-index?cpv_group=45 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/price-index?cpv_group=45", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── GET /api/v2/analytics/buyer-trajectory ──────────────────────────────────

@pytest.mark.asyncio
async def test_olap_buyer_trajectory_200(app, auth_headers):
    """GET /api/v2/analytics/buyer-trajectory → 200, returns list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/buyer-trajectory", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_olap_buyer_trajectory_buyer_filter(app, auth_headers):
    """GET /api/v2/analytics/buyer-trajectory?buyer=Urząd → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v2/analytics/buyer-trajectory?buyer=Urz%C4%85d",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── GET /api/v2/analytics/seasonal ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_olap_seasonal_200(app, auth_headers):
    """GET /api/v2/analytics/seasonal → 200, returns list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/seasonal", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── GET /api/v2/analytics/cohort ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_olap_cohort_200(app, auth_headers):
    """GET /api/v2/analytics/cohort → 200, returns list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/analytics/cohort", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
