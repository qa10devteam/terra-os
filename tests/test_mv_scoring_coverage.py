"""C1-6 — MV Scoring router coverage: routers/mv_scoring.py (22% → 55%+).

Tests for /api/v2/mv/* and /api/v2/scoring/v3/* endpoints.
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


DEMO_TENANT = "c4879c87-016c-4580-b913-212c904c20fd"


# ─── GET /api/v2/mv/pipeline-kpi ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mv_pipeline_kpi_200(app, auth_headers):
    """GET /api/v2/mv/pipeline-kpi?tenant_id=... → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v2/mv/pipeline-kpi?tenant_id={DEMO_TENANT}",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "active_count" in data
    assert "pipeline_value" in data


@pytest.mark.asyncio
async def test_mv_pipeline_kpi_win_rate(app, auth_headers):
    """GET /api/v2/mv/pipeline-kpi → has win_rate_pct field."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v2/mv/pipeline-kpi?tenant_id={DEMO_TENANT}",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "win_rate_pct" in data


# ─── GET /api/v2/mv/cpv-heatmap ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mv_cpv_heatmap_200(app, auth_headers):
    """GET /api/v2/mv/cpv-heatmap → 200, returns list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/mv/cpv-heatmap", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_mv_cpv_heatmap_cpv5_filter(app, auth_headers):
    """GET /api/v2/mv/cpv-heatmap?cpv5=45000 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/mv/cpv-heatmap?cpv5=45000", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── GET /api/v2/mv/market-forecast ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_mv_market_forecast_200(app, auth_headers):
    """GET /api/v2/mv/market-forecast → 200, returns list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/mv/market-forecast", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_mv_market_forecast_limit_param(app, auth_headers):
    """GET /api/v2/mv/market-forecast?limit=6 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/mv/market-forecast?limit=6", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) <= 6


# ─── GET /api/v2/scoring/v3/percentile ───────────────────────────────────────

@pytest.mark.asyncio
async def test_scoring_percentile_200(app, auth_headers):
    """GET /api/v2/scoring/v3/percentile?tenant_id=... → 200, list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v2/scoring/v3/percentile?tenant_id={DEMO_TENANT}",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_scoring_percentile_with_tender_id(app, auth_headers):
    """GET /api/v2/scoring/v3/percentile?tenant_id=...&tender_id=fake → 200."""
    fake_tender = "00000000-0000-0000-0000-000000000099"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v2/scoring/v3/percentile?tenant_id={DEMO_TENANT}&tender_id={fake_tender}",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── GET /api/v2/scoring/v3/hot-tenders ──────────────────────────────────────

@pytest.mark.asyncio
async def test_scoring_hot_tenders_200(app, auth_headers):
    """GET /api/v2/scoring/v3/hot-tenders?tenant_id=... → 200, list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v2/scoring/v3/hot-tenders?tenant_id={DEMO_TENANT}",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_scoring_hot_tenders_days_param(app, auth_headers):
    """GET /api/v2/scoring/v3/hot-tenders?tenant_id=...&days=7 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v2/scoring/v3/hot-tenders?tenant_id={DEMO_TENANT}&days=7",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ─── GET /api/v2/scoring/v3/market-median ────────────────────────────────────

@pytest.mark.asyncio
async def test_scoring_market_median_200(app, auth_headers):
    """GET /api/v2/scoring/v3/market-median?cpv5=45000 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v2/scoring/v3/market-median?cpv5=45000",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "cpv5" in data
    assert "sample_size" in data


@pytest.mark.asyncio
async def test_scoring_market_median_empty_cpv(app, auth_headers):
    """GET /api/v2/scoring/v3/market-median?cpv5=00000 → 200 with sample_size=0."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v2/scoring/v3/market-median?cpv5=00000",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sample_size"] == 0
