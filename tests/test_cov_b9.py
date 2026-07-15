"""BLOK-9 coverage push:
    routers/gantt.py
    routers/mv_scoring.py
    routers/forecasting.py
    routers/olap.py
    routers/billing.py  (plans, checkout, portal, webhook — mocked stripe)
    routers/integrations.py  (n8n, slack stubs)
    routers/pwa.py  (manifest, service-worker, push-subscribe)

All DB / HTTP / stripe calls are fully mocked — no real external service needed.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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


DEMO_ORG = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
DEMO_TENANT = "c4879c87-016c-4580-b913-212c904c20fd"
DEMO_TENDER = str(uuid.uuid4())
DEMO_TASK = str(uuid.uuid4())


# ─── DB / engine mock helpers ─────────────────────────────────────────────────

def _mock_engine(scalar=0, fetchone=None, fetchall=None, mappings=None):
    """Build a mock SQLAlchemy engine + connection."""
    conn = MagicMock()
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    conn.commit = MagicMock()

    result = MagicMock()
    result.fetchall.return_value = fetchall or []
    result.fetchone.return_value = fetchone
    result.scalar.return_value = scalar
    result.rowcount = 1
    if mappings is not None:
        result.mappings.return_value.fetchall.return_value = mappings
    else:
        result.mappings.return_value.fetchall.return_value = []

    conn.execute.return_value = result

    engine = MagicMock()
    engine.connect.return_value.__enter__ = lambda s: conn
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value.__enter__ = lambda s: conn
    engine.begin.return_value.__exit__ = MagicMock(return_value=False)
    return engine, conn


# ═══════════════════════════════════════════════════════════════════════════════
# routers/gantt.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestGantt:
    """Coverage for /api/v2/gantt/*"""

    PATCH_ENGINE = "services.api.services.api.routers.gantt.get_engine"

    @pytest.mark.asyncio
    async def test_list_gantt_projects_200(self, app, auth_headers):
        engine, _ = _mock_engine(mappings=[{"tender_id": DEMO_TENDER, "start_date": "2026-01-01", "end_date": "2026-12-31", "task_count": 3}])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/gantt/list", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_list_gantt_projects_empty_200(self, app, auth_headers):
        engine, _ = _mock_engine(mappings=[])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/gantt/list", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_get_gantt_200(self, app, auth_headers):
        row = {"id": DEMO_TASK, "tender_id": DEMO_TENDER, "parent_id": None,
               "name": "Task", "start_date": "2026-01-01", "end_date": "2026-01-31",
               "progress": 0, "color": "#3b82f6", "position": 0, "created_at": "2026-01-01"}
        engine, _ = _mock_engine(mappings=[row])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(f"/api/v2/gantt/{DEMO_TENDER}", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_get_gantt_empty_200(self, app, auth_headers):
        engine, _ = _mock_engine(mappings=[])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(f"/api/v2/gantt/{DEMO_TENDER}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_add_gantt_task_200(self, app, auth_headers):
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"/api/v2/gantt/{DEMO_TENDER}/tasks",
                    json={"name": "Phase 1", "start_date": "2026-06-01", "end_date": "2026-06-30",
                          "progress": 0, "color": "#3b82f6", "position": 1},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json()["status"] == "created"

    @pytest.mark.asyncio
    async def test_add_gantt_task_minimal_200(self, app, auth_headers):
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"/api/v2/gantt/{DEMO_TENDER}/tasks",
                    json={},
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_auto_generate_gantt_404(self, app, auth_headers):
        engine, _ = _mock_engine(fetchone=None)
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(f"/api/v2/gantt/{DEMO_TENDER}/auto-generate", headers=auth_headers)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_auto_generate_gantt_200(self, app, auth_headers):
        from datetime import datetime
        # tender row with deadline_at
        tender_row = MagicMock()
        tender_row.deadline_at = datetime(2026, 12, 31)
        engine, _ = _mock_engine(fetchone=tender_row)
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(f"/api/v2/gantt/{DEMO_TENDER}/auto-generate", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["phases_created"] == 3

    @pytest.mark.asyncio
    async def test_delete_gantt_task_200(self, app, auth_headers):
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.delete(
                    f"/api/v2/gantt/{DEMO_TENDER}/tasks/{DEMO_TASK}",
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_gantt_no_auth_401(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/gantt/list")
        assert r.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# routers/mv_scoring.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestMVScoring:
    """Coverage for /api/v2/mv/* and /api/v2/scoring/v3/*"""

    PATCH_ENGINE = "services.api.services.api.routers.mv_scoring.get_engine"

    @pytest.mark.asyncio
    async def test_pipeline_kpi_empty_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchone=None)
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(f"/api/v2/mv/pipeline-kpi?tenant_id={DEMO_TENANT}", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["active_count"] == 0
        assert data["win_rate_pct"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_kpi_with_data_200(self, app, auth_headers):
        # Row: tenant_id, active_count, pipeline_value, won_mtd, decided_mtd, avg_deal_size, total_won_value
        engine, _ = _mock_engine(fetchone=(DEMO_TENANT, 5, 1000000, 2, 4, 250000, 500000))
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(f"/api/v2/mv/pipeline-kpi?tenant_id={DEMO_TENANT}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["win_rate_pct"] == 50.0

    @pytest.mark.asyncio
    async def test_cpv_heatmap_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[("45000", "Mazowieckie", 10, 100000.0, 1000000.0)])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/mv/cpv-heatmap", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_cpv_heatmap_filtered_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/mv/cpv-heatmap?cpv5=45000&voivodeship=Mazowieckie", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_market_forecast_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[("2026-01-01", "45000", 5, 500000.0, 100000.0)])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/mv/market-forecast?limit=6", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_mvs_200(self, app, auth_headers):
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/mv/refresh", headers=auth_headers)
        assert r.status_code == 200
        assert "refreshed" in r.json()

    @pytest.mark.asyncio
    async def test_scoring_percentile_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[
            (uuid.uuid4(), "Test tender", 0.85, 1, 50, 2.0)
        ])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(f"/api/v2/scoring/v3/percentile?tenant_id={DEMO_TENANT}", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_hot_tenders_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(f"/api/v2/scoring/v3/hot-tenders?tenant_id={DEMO_TENANT}&days=14", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_market_median_empty_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchone=(0, None, None, None, None))
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/scoring/v3/market-median?cpv5=45000", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_market_median_with_data_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchone=(100, 50000.0, 100000.0, 200000.0, 120000.0))
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/scoring/v3/market-median?cpv5=45000", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["median"] == 100000.0


# ═══════════════════════════════════════════════════════════════════════════════
# routers/forecasting.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestForecasting:
    """Coverage for /api/v2/forecast/*"""

    PATCH_ENGINE = "services.api.services.api.routers.forecasting.get_engine"

    @pytest.mark.asyncio
    async def test_timeseries_200(self, app, auth_headers):
        from datetime import datetime
        engine, _ = _mock_engine(fetchall=[
            (datetime(2025, 1, 1), 10, 1000000.0, 100000.0),
            (datetime(2025, 4, 1), 12, 1200000.0, 100000.0),
            (datetime(2025, 7, 1), 8, 800000.0, 100000.0),
        ])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/forecast/timeseries", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "series" in data
        assert data["granularity"] == "quarter"

    @pytest.mark.asyncio
    async def test_timeseries_month_granularity_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/forecast/timeseries?granularity=month", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_timeseries_invalid_granularity_422(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/forecast/timeseries?granularity=week", headers=auth_headers)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_timeseries_with_cpv_200(self, app, auth_headers):
        from datetime import datetime
        engine, _ = _mock_engine(fetchall=[
            (datetime(2025, 1, 1), 5, 500000.0, 100000.0),
        ])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/forecast/timeseries?cpv_division=45", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_seasonality_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[
            (1, 10, 100000.0),
            (3, 20, 200000.0),
            (6, 5, 50000.0),
            (9, 15, 150000.0),
            (12, 8, 80000.0),
        ])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/forecast/seasonality", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "months" in data
        assert "peak_months" in data

    @pytest.mark.asyncio
    async def test_seasonality_with_cpv_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/forecast/seasonality?cpv_division=45", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_predict_no_data_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/forecast/predict", headers=auth_headers)
        assert r.status_code == 200
        assert "error" in r.json()

    @pytest.mark.asyncio
    async def test_predict_holt_winters_200(self, app, auth_headers):
        from datetime import datetime
        rows = [(datetime(2024, q * 3 - 2, 1), 10 + q) for q in range(1, 13)]
        engine, _ = _mock_engine(fetchall=rows)
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/forecast/predict?method=holt_winters&periods=6", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "forecasts" in data
        assert len(data["forecasts"]) == 6

    @pytest.mark.asyncio
    async def test_predict_linear_200(self, app, auth_headers):
        from datetime import datetime
        rows = [(datetime(2024, 1, 1), 10), (datetime(2024, 4, 1), 15)]
        engine, _ = _mock_engine(fetchall=rows)
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/forecast/predict?method=linear&periods=3", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_predict_invalid_method_422(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/forecast/predict?method=prophet", headers=auth_headers)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_periods_out_of_range_422(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/forecast/predict?periods=99", headers=auth_headers)
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# routers/olap.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestOLAP:
    """Coverage for /api/v2/analytics/*"""

    PATCH_ENGINE = "services.api.services.api.routers.olap.get_engine"

    @pytest.mark.asyncio
    async def test_market_olap_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[
            (2025, 1, "45", 100, 10000000.0, 100000.0, 90000.0, 30, 0.3)
        ])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/olap", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_market_olap_filtered_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/olap?cpv_division=45&year=2025&group_by=month", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_market_olap_invalid_group_422(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/analytics/olap?group_by=week", headers=auth_headers)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_price_index_200(self, app, auth_headers):
        from datetime import datetime
        engine, _ = _mock_engine(fetchall=[
            ("45", datetime(2025, 1, 1), 150000.0, 20, 140000.0, 7.1)
        ])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/price-index", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_price_index_with_cpv_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/price-index?cpv_group=45", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_buyer_trajectory_200(self, app, auth_headers):
        from datetime import datetime
        engine, _ = _mock_engine(fetchall=[
            ("Urząd Gminy X", datetime(2025, 3, 1), 3, 10, 200000.0)
        ])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/buyer-trajectory", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_buyer_trajectory_with_buyer_200(self, app, auth_headers):
        from datetime import datetime
        engine, _ = _mock_engine(fetchall=[
            ("Urząd Gminy X", datetime(2025, 3, 1), 3, 10, 200000.0)
        ])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/buyer-trajectory?buyer=Gmina", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_seasonal_patterns_200(self, app, auth_headers):
        engine, _ = _mock_engine(fetchall=[
            ("45", 1, 10, 100000.0, 0.9),
            ("45", 3, 20, 200000.0, 1.8),
        ])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/seasonal", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_seasonal_fallback_200(self, app, auth_headers):
        """Triggers the fallback branch when primary query returns empty."""
        engine, conn = _mock_engine(fetchall=[])
        # First call returns [], second call returns data (fallback)
        conn.execute.return_value.fetchall.side_effect = [
            [],
            [("45", 1, 10, 100000.0, 0.9)],
        ]
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/seasonal", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_buyer_cohort_200(self, app, auth_headers):
        from datetime import datetime
        engine, _ = _mock_engine(fetchall=[
            (datetime(2024, 1, 1), 0, 10, 30, 3000000.0),
            (datetime(2024, 1, 1), 1, 7, 20, 2000000.0),
        ])
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/analytics/cohort", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ═══════════════════════════════════════════════════════════════════════════════
# routers/billing.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestBilling:
    """Coverage for /api/v2/billing/* — stripe mocked."""

    PATCH_ENGINE = "services.api.services.api.routers.billing.get_engine"

    @pytest.mark.asyncio
    async def test_list_plans_200(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/api/v2/billing/plans", headers=auth_headers)
        assert r.status_code == 200
        plans = r.json()
        assert isinstance(plans, list)
        plan_ids = [p["id"] for p in plans]
        assert "free" in plan_ids
        assert "pro" in plan_ids

    @pytest.mark.asyncio
    async def test_checkout_free_plan_200(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/billing/checkout",
                             json={"plan_id": "free"},
                             headers=auth_headers)
        assert r.status_code == 200
        assert "redirect_url" in r.json()

    @pytest.mark.asyncio
    async def test_checkout_enterprise_plan_200(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/billing/checkout",
                             json={"plan_id": "enterprise"},
                             headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_checkout_invalid_plan_400(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/billing/checkout",
                             json={"plan_id": "nonexistent"},
                             headers=auth_headers)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_checkout_pro_no_stripe_503_or_200(self, app, auth_headers):
        """Pro plan without STRIPE_SECRET_KEY — placeholder branch."""
        import os
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "", "STRIPE_PRICE_PRO": "price_pro_placeholder"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/checkout",
                                 json={"plan_id": "pro"},
                                 headers=auth_headers)
        # Placeholder price IDs cause 503
        assert r.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_get_subscription_no_org_200(self, app, auth_headers):
        """get_subscription for user without org returns free plan."""
        from services.api.services.api.auth.deps import get_current_user, CurrentUser
        no_org_user = CurrentUser(
            user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
            email="demo@terra-os.pl",
            org_id=None,
            role="owner",
        )
        engine, _ = _mock_engine()
        app.dependency_overrides[get_current_user] = lambda: no_org_user
        try:
            with patch(self.PATCH_ENGINE, return_value=engine):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    r = await c.get("/api/v2/billing/subscription", headers=auth_headers)
            assert r.status_code == 200
            assert r.json()["plan"] == "free"
        finally:
            from services.api.services.api.main import app as _app
            from services.api.services.api.auth.deps import get_current_user as gcu
            from services.api.services.api.auth.deps import CurrentUser as CU
            _demo = CU(
                user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
                email="demo@terra-os.pl",
                org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
                role="owner",
            )
            _app.dependency_overrides[gcu] = lambda: _demo

    @pytest.mark.asyncio
    async def test_get_subscription_with_org_200(self, app, auth_headers):
        """get_subscription — org has subscription row."""
        sub_row = MagicMock()
        sub_row._mapping = {
            "org_id": DEMO_ORG, "plan": "pro", "status": "active",
            "stripe_customer_id": "cus_test", "stripe_subscription_id": "sub_test",
            "stripe_price_id": "price_pro_placeholder", "current_period_start": None,
            "current_period_end": None, "trial_end": None, "payment_failed": False,
            "cancel_at_period_end": False, "grace_until": None,
        }
        engine, conn = _mock_engine(fetchone=sub_row)
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/billing/subscription", headers=auth_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_cancel_no_org_400(self, app, auth_headers):
        from services.api.services.api.auth.deps import get_current_user, CurrentUser
        no_org_user = CurrentUser(
            user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
            email="demo@terra-os.pl",
            org_id=None,
            role="owner",
        )
        engine, _ = _mock_engine()
        app.dependency_overrides[get_current_user] = lambda: no_org_user
        try:
            with patch(self.PATCH_ENGINE, return_value=engine):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    r = await c.post("/api/v2/billing/cancel", headers=auth_headers)
            assert r.status_code == 400
        finally:
            from services.api.services.api.main import app as _app
            from services.api.services.api.auth.deps import get_current_user as gcu, CurrentUser as CU
            _demo = CU(
                user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
                email="demo@terra-os.pl",
                org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
                role="owner",
            )
            _app.dependency_overrides[gcu] = lambda: _demo

    @pytest.mark.asyncio
    async def test_cancel_free_plan_400(self, app, auth_headers):
        sub_row = MagicMock()
        sub_row._mapping = {
            "org_id": DEMO_ORG, "plan": "free", "status": "active",
            "stripe_customer_id": None, "stripe_subscription_id": None,
            "stripe_price_id": None, "current_period_start": None,
            "current_period_end": None, "trial_end": None, "payment_failed": False,
            "cancel_at_period_end": False, "grace_until": None,
        }
        engine, _ = _mock_engine(fetchone=sub_row)
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/cancel", headers=auth_headers)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_cancel_paid_plan_200(self, app, auth_headers):
        """Cancel pro plan — no stripe key → sets flag locally."""
        import os
        sub_row = MagicMock()
        sub_row._mapping = {
            "org_id": DEMO_ORG, "plan": "pro", "status": "active",
            "stripe_customer_id": "cus_test", "stripe_subscription_id": "sub_test",
            "stripe_price_id": "price_pro", "current_period_start": None,
            "current_period_end": None, "trial_end": None, "payment_failed": False,
            "cancel_at_period_end": False, "grace_until": None,
        }
        engine, _ = _mock_engine(fetchone=sub_row)
        with patch(self.PATCH_ENGINE, return_value=engine), \
             patch.dict(os.environ, {"STRIPE_SECRET_KEY": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/cancel", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["cancel_at_period_end"] is True

    @pytest.mark.asyncio
    async def test_webhook_invalid_json_400(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post("/api/v2/billing/webhook",
                             content=b"not json",
                             headers={"content-type": "application/json"})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_valid_checkout_completed_200(self, app):
        """Webhook checkout.session.completed — no sig required when no secret configured."""
        import os
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "mode": "subscription",
                    "customer": "cus_test",
                    "subscription": "sub_test",
                    "metadata": {"org_id": DEMO_ORG},
                    "line_items": {"data": []},
                }
            }
        }
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine), \
             patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/webhook",
                                 content=json.dumps(event).encode(),
                                 headers={"content-type": "application/json"})
        assert r.status_code == 200
        assert r.json()["received"] is True

    @pytest.mark.asyncio
    async def test_webhook_subscription_updated_200(self, app):
        import os
        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test",
                    "customer": "cus_test",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "items": {"data": []},
                    "current_period_start": None,
                    "current_period_end": None,
                    "trial_end": None,
                }
            }
        }
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine), \
             patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/webhook",
                                 content=json.dumps(event).encode(),
                                 headers={"content-type": "application/json"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_subscription_deleted_200(self, app):
        import os
        event = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_test"}}
        }
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine), \
             patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/webhook",
                                 content=json.dumps(event).encode(),
                                 headers={"content-type": "application/json"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_payment_succeeded_200(self, app):
        import os
        event = {
            "type": "invoice.payment_succeeded",
            "data": {"object": {"customer": "cus_test", "lines": {"data": [{"period": {"end": None}}]}, "period_end": None}}
        }
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine), \
             patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/webhook",
                                 content=json.dumps(event).encode(),
                                 headers={"content-type": "application/json"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_payment_failed_200(self, app):
        import os
        event = {
            "type": "invoice.payment_failed",
            "data": {"object": {"customer": "cus_test", "attempt_count": 1, "amount_due": 49900}}
        }
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine), \
             patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/webhook",
                                 content=json.dumps(event).encode(),
                                 headers={"content-type": "application/json"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_unknown_event_200(self, app):
        import os
        event = {"type": "customer.created", "data": {"object": {}}}
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine), \
             patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/webhook",
                                 content=json.dumps(event).encode(),
                                 headers={"content-type": "application/json"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_sig_required_missing_400(self, app):
        import os
        event = {"type": "customer.created", "data": {"object": {}}}
        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_test_secret"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/api/v2/billing/webhook",
                                 content=json.dumps(event).encode(),
                                 headers={"content-type": "application/json"})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_checkout_url_no_stripe_200(self, app, auth_headers):
        import os
        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/billing/checkout-url?plan=pro", headers=auth_headers)
        assert r.status_code == 200
        assert "url" in r.json()

    @pytest.mark.asyncio
    async def test_list_invoices_no_org_403(self, app, auth_headers):
        from services.api.services.api.auth.deps import get_current_user, CurrentUser
        no_org_user = CurrentUser(
            user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
            email="demo@terra-os.pl",
            org_id=None,
            role="owner",
        )
        engine, _ = _mock_engine(scalar=0)
        app.dependency_overrides[get_current_user] = lambda: no_org_user
        try:
            with patch(self.PATCH_ENGINE, return_value=engine):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    r = await c.get("/api/v2/billing/invoices", headers=auth_headers)
            assert r.status_code == 403
        finally:
            from services.api.services.api.main import app as _app
            from services.api.services.api.auth.deps import get_current_user as gcu, CurrentUser as CU
            _demo = CU(
                user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
                email="demo@terra-os.pl",
                org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
                role="owner",
            )
            _app.dependency_overrides[gcu] = lambda: _demo

    @pytest.mark.asyncio
    async def test_list_invoices_table_missing_200(self, app, auth_headers):
        """invoices table doesn't exist → returns empty list."""
        engine, conn = _mock_engine(scalar=0)
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get("/api/v2/billing/invoices", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["invoices"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# routers/integrations.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrations:
    """Coverage for /api/v2/integrations/* — httpx mocked."""

    @pytest.mark.asyncio
    async def test_webhook_fire_200(self, app, auth_headers):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("services.api.services.api.routers.integrations.httpx.post",
                   return_value=mock_response):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/integrations/webhook/fire",
                    json={"url": "https://example.com/hook", "payload": {"key": "val"}},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json()["status"] == 200

    @pytest.mark.asyncio
    async def test_webhook_fire_ssrf_blocked_400(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/integrations/webhook/fire",
                json={"url": "http://localhost:8080/internal", "payload": {}},
                headers=auth_headers,
            )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_fire_ssrf_10_blocked_400(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/integrations/webhook/fire",
                json={"url": "http://10.0.0.1/admin", "payload": {}},
                headers=auth_headers,
            )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_fire_no_auth_401(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/integrations/webhook/fire",
                json={"url": "https://example.com/hook", "payload": {}},
            )
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_slack_test_no_webhook_200(self, app, auth_headers):
        """No SLACK_WEBHOOK_URL → returns skipped."""
        import os
        with patch.dict(os.environ, {"SLACK_WEBHOOK_URL": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/integrations/slack/test",
                    json={"message": "hello terra"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json()["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_slack_test_with_webhook_200(self, app, auth_headers):
        import os
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("services.api.services.api.integrations.slack.httpx.post",
                   return_value=mock_response), \
             patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/integrations/slack/test",
                    json={"message": "hello terra"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_pipedrive_sync_no_key_200(self, app, auth_headers):
        import os
        with patch.dict(os.environ, {"PIPEDRIVE_API_KEY": ""}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/integrations/pipedrive/sync",
                    json={"offer_id": str(uuid.uuid4()), "title": "Test deal"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json()["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_pipedrive_sync_with_key_200(self, app, auth_headers):
        import os
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"id": 42}}
        with patch("services.api.services.api.integrations.pipedrive.httpx.post",
                   return_value=mock_response), \
             patch.dict(os.environ, {"PIPEDRIVE_API_KEY": "test_key_123"}):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/integrations/pipedrive/sync",
                    json={"offer_id": str(uuid.uuid4()), "title": "Deal X"},
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json()["status"] == "synced"


# ═══════════════════════════════════════════════════════════════════════════════
# routers/pwa.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestPWA:
    """Coverage for /api/v2/pwa/*"""

    PATCH_ENGINE = "services.api.services.api.routers.pwa.get_engine"

    @pytest.mark.asyncio
    async def test_pwa_subscribe_200(self, app, auth_headers):
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/pwa/subscribe",
                    json={
                        "push_endpoint": "https://fcm.googleapis.com/fcm/send/test123",
                        "p256dh": "BKtest==",
                        "auth": "authtoken==",
                    },
                    headers=auth_headers,
                )
        assert r.status_code == 200
        assert r.json()["status"] == "subscribed"

    @pytest.mark.asyncio
    async def test_pwa_subscribe_minimal_200(self, app, auth_headers):
        """Only push_endpoint provided."""
        engine, _ = _mock_engine()
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/pwa/subscribe",
                    json={"push_endpoint": "https://fcm.googleapis.com/send/abc"},
                    headers=auth_headers,
                )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_pwa_subscribe_missing_endpoint_422(self, app, auth_headers):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/pwa/subscribe",
                json={"p256dh": "BKtest==", "auth": "authtoken=="},
                headers=auth_headers,
            )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_pwa_subscribe_no_auth_401(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                "/api/v2/pwa/subscribe",
                json={"push_endpoint": "https://fcm.googleapis.com/send/abc"},
            )
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_pwa_subscribe_db_error_500(self, app, auth_headers):
        """DB failure → 500."""
        engine = MagicMock()
        conn = MagicMock()
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        conn.execute.side_effect = Exception("DB connection refused")
        engine.connect.return_value.__enter__ = lambda s: conn
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        with patch(self.PATCH_ENGINE, return_value=engine):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    "/api/v2/pwa/subscribe",
                    json={"push_endpoint": "https://fcm.googleapis.com/send/err"},
                    headers=auth_headers,
                )
        assert r.status_code == 500


# ─── Internal unit tests (no HTTP) ───────────────────────────────────────────

class TestBillingInternals:
    """Unit-test billing helper functions."""

    def test_verify_stripe_signature_valid(self):
        from services.api.services.api.routers.billing import _verify_stripe_signature
        secret = "whsec_test"
        ts = str(int(time.time()))
        payload = b'{"type":"test"}'
        signed = f"{ts}.".encode() + payload
        sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        header = f"t={ts},v1={sig}"
        assert _verify_stripe_signature(payload, header, secret) is True

    def test_verify_stripe_signature_invalid(self):
        from services.api.services.api.routers.billing import _verify_stripe_signature
        assert _verify_stripe_signature(b"payload", "t=123,v1=bad", "secret") is False

    def test_verify_stripe_signature_malformed(self):
        from services.api.services.api.routers.billing import _verify_stripe_signature
        assert _verify_stripe_signature(b"payload", "malformed", "secret") is False

    def test_plan_from_price_known(self):
        from services.api.services.api.routers.billing import _plan_from_price, PRICE_ID_TO_PLAN
        # Whatever is mapped
        for price_id, plan in PRICE_ID_TO_PLAN.items():
            assert _plan_from_price(price_id) == plan

    def test_plan_from_price_unknown(self):
        from services.api.services.api.routers.billing import _plan_from_price
        assert _plan_from_price("price_unknown_xyz") == "pro"

    def test_plan_from_price_none(self):
        from services.api.services.api.routers.billing import _plan_from_price
        assert _plan_from_price(None) == "free"

    def test_ts_converts_unix(self):
        from services.api.services.api.routers.billing import _ts
        from datetime import timezone
        result = _ts(1700000000)
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_ts_none(self):
        from services.api.services.api.routers.billing import _ts
        assert _ts(None) is None


class TestForecastingInternals:
    """Unit-test forecasting math functions."""

    def test_linear_forecast_basic(self):
        from services.api.services.api.routers.forecasting import _linear_forecast
        result = _linear_forecast([10.0, 12.0, 14.0, 16.0], periods=3)
        assert len(result) == 3
        for f in result:
            assert "forecast" in f
            assert "lower_ci" in f
            assert "upper_ci" in f
            assert f["confidence"] == 0.95

    def test_linear_forecast_single_point(self):
        from services.api.services.api.routers.forecasting import _linear_forecast
        result = _linear_forecast([5.0], periods=2)
        assert len(result) == 2

    def test_holt_winters_with_enough_data(self):
        from services.api.services.api.routers.forecasting import _holt_winters_forecast
        values = [10.0, 12.0, 8.0, 11.0, 13.0, 9.0, 12.0, 14.0, 10.0, 13.0]
        result = _holt_winters_forecast(values, periods=4, season_length=4)
        assert len(result) == 4

    def test_holt_winters_fallback_to_linear(self):
        from services.api.services.api.routers.forecasting import _holt_winters_forecast
        # < 2*season_length → linear fallback
        result = _holt_winters_forecast([10.0, 12.0], periods=3)
        assert len(result) == 3
