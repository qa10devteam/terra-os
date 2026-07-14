"""C1-1 — Forecasting router coverage: routers/forecasting.py (15% → 55%+).

Tests for /api/v2/forecast/* endpoints using AsyncClient + ASGITransport.
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


# ─── /timeseries ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forecast_timeseries_200(app, auth_headers):
    """GET /api/v2/forecast/timeseries → 200 with series."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/timeseries", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "series" in data
    assert isinstance(data["series"], list)


@pytest.mark.asyncio
async def test_forecast_timeseries_granularity_quarter(app, auth_headers):
    """GET /api/v2/forecast/timeseries?granularity=quarter → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/timeseries?granularity=quarter", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["granularity"] == "quarter"


@pytest.mark.asyncio
async def test_forecast_timeseries_granularity_month(app, auth_headers):
    """GET /api/v2/forecast/timeseries?granularity=month → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/timeseries?granularity=month", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["granularity"] == "month"


@pytest.mark.asyncio
async def test_forecast_timeseries_cpv_filter(app, auth_headers):
    """GET /api/v2/forecast/timeseries?cpv_division=45 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/timeseries?cpv_division=45", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["cpv_division"] == "45"


@pytest.mark.asyncio
async def test_forecast_timeseries_invalid_granularity(app, auth_headers):
    """GET /api/v2/forecast/timeseries?granularity=year → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/timeseries?granularity=year", headers=auth_headers)
    assert resp.status_code == 422


# ─── /seasonality ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forecast_seasonality_200(app, auth_headers):
    """GET /api/v2/forecast/seasonality → 200 with months + insight."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/seasonality", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "months" in data
    assert "insight" in data
    assert isinstance(data["months"], list)


@pytest.mark.asyncio
async def test_forecast_seasonality_cpv_filter(app, auth_headers):
    """GET /api/v2/forecast/seasonality?cpv_division=45 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/seasonality?cpv_division=45", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["cpv_division"] == "45"
    assert "peak_months" in data
    assert "trough_months" in data


# ─── /predict ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forecast_predict_200(app, auth_headers):
    """GET /api/v2/forecast/predict → 200 with forecasts."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/predict", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "forecasts" in data


@pytest.mark.asyncio
async def test_forecast_predict_linear_method(app, auth_headers):
    """GET /api/v2/forecast/predict?method=linear → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/predict?method=linear", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "forecasts" in data


@pytest.mark.asyncio
async def test_forecast_predict_holt_winters_method(app, auth_headers):
    """GET /api/v2/forecast/predict?method=holt_winters → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/predict?method=holt_winters", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "forecasts" in data


@pytest.mark.asyncio
async def test_forecast_predict_periods_param(app, auth_headers):
    """GET /api/v2/forecast/predict?periods=3 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/predict?periods=3", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "forecasts" in data


@pytest.mark.asyncio
async def test_forecast_predict_cpv_filter(app, auth_headers):
    """GET /api/v2/forecast/predict?cpv_division=45&periods=6 → 200."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v2/forecast/predict?cpv_division=45&periods=6",
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "method" in data


@pytest.mark.asyncio
async def test_forecast_predict_invalid_method(app, auth_headers):
    """GET /api/v2/forecast/predict?method=prophet → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/predict?method=prophet", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_forecast_predict_periods_out_of_range(app, auth_headers):
    """GET /api/v2/forecast/predict?periods=99 → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v2/forecast/predict?periods=99", headers=auth_headers)
    assert resp.status_code == 422
