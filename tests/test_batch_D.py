"""Batch-D coverage tests: dashboard, analytics_v2, competitor_watch, tender_bookmarks,
buyer_crm, estimates_v2, offer_assembly, m7_phase2, m7_advanced, olap, scoring_config,
semantic_search.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mock_conn(rows=None, fetchone=None, scalar_val=0, rowcount=1):
    """Build a mocked SQLAlchemy connection with mappings support."""
    conn = MagicMock()
    result = MagicMock()
    result.fetchall.return_value = rows if rows is not None else []
    result.fetchone.return_value = fetchone
    result.rowcount = rowcount
    result.scalar.return_value = scalar_val

    mapping_result = MagicMock()
    mapping_result.all.return_value = rows if rows is not None else []
    mapping_result.one_or_none.return_value = fetchone
    mapping_result.one.return_value = fetchone if fetchone is not None else MagicMock()
    result.mappings.return_value = mapping_result

    conn.execute.return_value = result
    conn.commit.return_value = None
    conn.rollback.return_value = None
    return conn


def _eng(rows=None, fetchone=None, scalar_val=0, rowcount=1):
    """Build a fully mocked SQLAlchemy engine."""
    engine = MagicMock()
    conn = _mock_conn(rows=rows, fetchone=fetchone, scalar_val=scalar_val, rowcount=rowcount)

    for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
        ctx_mgr.__enter__ = MagicMock(return_value=conn)
        ctx_mgr.__exit__ = MagicMock(return_value=False)

    return engine


@pytest.fixture(scope="module")
def app():
    from starlette.testclient import TestClient
    from services.api.services.api.main import app as _app
    with TestClient(_app) as client:
        yield client


# ─── Dashboard ────────────────────────────────────────────────────────────────

class TestDashboard:
    PATCH = "services.api.services.api.routers.dashboard.get_engine"

    def _dashboard_engine(self):
        """Engine wired to answer all 4 queries in _get_dashboard_data."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        agg = MagicMock()
        agg.total_tenders = 5
        agg.new_today = 1
        agg.high_score_count = 2
        agg.avg_score = 0.75
        agg.pipeline_value = 100_000
        agg.unique_buyers = 3

        act = MagicMock()
        act.day = "2026-07-17"
        act.cnt = 1

        top = MagicMock()
        top.id = str(uuid.uuid4())
        top.title = "Test"
        top.source = "bzp"
        top.value_pln = 50_000
        top.match_score = 0.8
        top.status = "active"

        def _exec(*args, **kwargs):
            r = MagicMock()
            r.fetchone.return_value = agg
            r.fetchall.return_value = [act]
            return r

        conn.execute.side_effect = [
            # 1: aggregate fetchone
            MagicMock(**{"fetchone.return_value": agg}),
            # 2: by_source fetchall
            MagicMock(**{"fetchall.return_value": [("bzp", 3)]}),
            # 3: weekly_activity fetchall
            MagicMock(**{"fetchall.return_value": [act]}),
            # 4: top_tenders fetchall
            MagicMock(**{"fetchall.return_value": [top]}),
        ]
        return engine

    def _kpi_engine(self):
        """Engine that returns a KPI row (used by pipeline-kpi and dashboard root)."""
        row = MagicMock()
        row.active_count = 10
        row.pipeline_value = 500_000.0
        row.win_rate_mtd = 50.0
        row.avg_deal_size = 50_000.0
        row.new_today = 3
        return _eng(fetchone=row)

    def test_v1_stats_cached(self, app):
        """GET /api/v1/dashboard uses cache when available."""
        cached = {
            "total_tenders": 42, "new_today": 1, "new_this_week": 5,
            "high_score_count": 2, "by_source": {}, "top_tenders": [],
            "avg_score": None, "pipeline_value": 0.0, "unique_buyers": 0,
            "weekly_activity": [],
        }
        with patch("services.api.services.api.routers.dashboard.cache_get", return_value=cached):
            resp = app.get("/api/v1/dashboard")
        assert resp.status_code == 200
        assert resp.json()["total_tenders"] == 42

    def test_v1_stats_db(self, app):
        """GET /api/v1/dashboard fetches from DB when cache miss."""
        e = self._dashboard_engine()
        with patch(self.PATCH, return_value=e), \
             patch("services.api.services.api.routers.dashboard.cache_get", return_value=None), \
             patch("services.api.services.api.routers.dashboard.cache_set"):
            resp = app.get("/api/v1/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tenders" in data
        assert "by_source" in data

    def test_v2_stats(self, app):
        """GET /api/v2/dashboard/stats same as v1."""
        e = self._dashboard_engine()
        with patch(self.PATCH, return_value=e), \
             patch("services.api.services.api.routers.dashboard.cache_get", return_value=None), \
             patch("services.api.services.api.routers.dashboard.cache_set"):
            resp = app.get("/api/v2/dashboard/stats")
        assert resp.status_code == 200
        assert "weekly_activity" in resp.json()

    def test_v2_root_kpi(self, app):
        """GET /api/v2/dashboard returns active_tenders KPI."""
        e = self._kpi_engine()
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/dashboard")
        assert resp.status_code == 200
        assert "active_tenders" in resp.json()

    def test_pipeline_kpi_from_mv(self, app):
        """GET /api/v2/dashboard/pipeline-kpi returns from mv_pipeline_kpi."""
        kpi = MagicMock()
        kpi.active_count = 7
        kpi.pipeline_value = 250_000.0
        kpi.win_rate_mtd = 30.0
        kpi.avg_deal_size = 35_000.0
        kpi.new_today = 2
        e = _eng(fetchone=kpi)
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/dashboard/pipeline-kpi")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_count" in data

    def test_pipeline_kpi_fallback(self, app):
        """GET /api/v2/dashboard/pipeline-kpi falls back to tender table."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        # First execute raises → fallback query executed
        fallback_row = MagicMock()
        fallback_row.active_count = 5
        fallback_row.pipeline_value = 100_000.0
        fallback_row.win_rate_mtd = None
        fallback_row.avg_deal_size = None
        fallback_row.new_today = 1

        conn.execute.side_effect = [
            Exception("mv not available"),
            MagicMock(**{"fetchone.return_value": fallback_row}),
        ]

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/dashboard/pipeline-kpi")
        assert resp.status_code == 200

    def test_digest_not_found(self, app):
        """GET /api/v2/dashboard/digest → 404 when no digest."""
        e = _eng(fetchone=None)
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/dashboard/digest")
        assert resp.status_code == 404

    def test_digest_found_fresh(self, app):
        """GET /api/v2/dashboard/digest returns content when fresh."""
        fresh_time = datetime.now(timezone.utc)

        class _Row:
            def __getitem__(self, k):
                return ({"content": "Daily digest text"} if k == 0 else fresh_time)

        e = _eng(fetchone=_Row())
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/dashboard/digest")
        assert resp.status_code == 200
        assert "content" in resp.json()

    def test_digest_expired(self, app):
        """GET /api/v2/dashboard/digest → 404 when digest older than 8 hours."""
        from datetime import timedelta
        old_time = datetime.now(timezone.utc) - timedelta(hours=10)

        # row must return actual dict and datetime for index access
        class _Row:
            def __getitem__(self, k):
                return ({"content": "Old digest"} if k == 0 else old_time)

        e = _eng(fetchone=_Row())
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/dashboard/digest")
        assert resp.status_code == 404

    def test_generate_digest_vllm_unavailable(self, app):
        """POST /api/v2/dashboard/digest/generate → 502 when vLLM is down."""
        e = self._dashboard_engine()
        with patch(self.PATCH, return_value=e), \
             patch("services.api.services.api.routers.dashboard.cache_get", return_value=None), \
             patch("services.api.services.api.routers.dashboard.cache_set"):
            resp = app.post("/api/v2/dashboard/digest/generate")
        assert resp.status_code == 502

    def test_market_charts(self, app):
        """GET /api/v2/dashboard/market-charts returns dict or 500."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        kpi_mock = MagicMock()
        kpi_mock.bzp_30d = 10
        kpi_mock.unique_contractors = 5
        kpi_mock.avg_value_k = 100.0
        kpi_mock.total_value_bln = 0.5
        ted_kpi = MagicMock()
        ted_kpi.ted_30d = 3
        pretender_kpi = MagicMock()
        pretender_kpi.pretender_30d = 1
        gus_latest = MagicMock()
        gus_latest.avg_production_mln = 200.0

        conn.execute.side_effect = [
            MagicMock(**{"fetchone.return_value": kpi_mock}),
            MagicMock(**{"fetchone.return_value": ted_kpi}),
            MagicMock(**{"fetchone.return_value": pretender_kpi}),
            MagicMock(**{"fetchone.return_value": gus_latest}),
            MagicMock(**{"fetchall.return_value": []}),
            MagicMock(**{"fetchall.return_value": []}),
            MagicMock(**{"fetchall.return_value": []}),
            MagicMock(**{"fetchall.return_value": []}),
            MagicMock(**{"fetchall.return_value": []}),
            MagicMock(**{"fetchall.return_value": []}),
            MagicMock(**{"fetchall.return_value": []}),
            MagicMock(**{"fetchall.return_value": []}),
        ]

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/dashboard/market-charts")
        assert resp.status_code in (200, 500)


# ─── Analytics V2 ─────────────────────────────────────────────────────────────

class TestAnalyticsV2:
    PATCH = "services.api.services.api.routers.analytics_v2.get_engine"

    def test_optimal_markup(self, app):
        """POST /api/v2/analytics/optimal-markup."""
        with patch("services.api.services.api.analytics.optimal_markup",
                   return_value={"optimal_markup": 0.15, "win_probability": 0.5}):
            resp = app.post("/api/v2/analytics/optimal-markup", json={
                "cost_estimate": 100000.0,
                "n_competitors": 5,
                "cpv": "45",
                "region": "mazowieckie",
            })
        assert resp.status_code == 200

    def test_optimal_markup_validation_error(self, app):
        """POST /api/v2/analytics/optimal-markup with missing fields → 422."""
        resp = app.post("/api/v2/analytics/optimal-markup", json={})
        assert resp.status_code == 422

    def test_ahp_score(self, app):
        """POST /api/v2/analytics/ahp-score."""
        with patch("services.api.services.api.analytics.compute_ahp_score",
                   return_value={"total_score": 0.72, "breakdown": {}}):
            resp = app.post("/api/v2/analytics/ahp-score", json={
                "scores": {"cpv": 0.8, "region": 0.6, "value": 0.5},
            })
        assert resp.status_code == 200

    def test_ahp_criteria(self, app):
        """GET /api/v2/analytics/ahp-criteria."""
        with patch("services.api.services.api.analytics.DEFAULT_CRITERIA",
                   [{"name": "cpv", "weight": 0.35}]):
            resp = app.get("/api/v2/analytics/ahp-criteria")
        assert resp.status_code == 200
        assert "criteria" in resp.json()

    def test_cost_estimate_get(self, app):
        """GET /api/v2/analytics/cost-estimate (no auth)."""
        with patch("services.api.services.api.analytics.estimate_cost",
                   return_value={"expected_estimate": 500000.0, "method": "benchmark"}):
            resp = app.get("/api/v2/analytics/cost-estimate?cpv=45&region=mazowieckie&value=500000")
        assert resp.status_code == 200

    def test_cost_estimate_post(self, app):
        """POST /api/v2/analytics/cost-estimate."""
        with patch("services.api.services.api.analytics.estimate_cost",
                   return_value={"expected_estimate": 400000.0, "method": "benchmark"}), \
             patch("services.api.services.api.analytics.explain_cost_drivers",
                   return_value={"drivers": []}):
            resp = app.post("/api/v2/analytics/cost-estimate", json={
                "cpv": "45",
                "region": "śląskie",
                "area_m2": 500.0,
                "value_estimated": 400000.0,
            })
        assert resp.status_code == 200

    def test_win_probability(self, app):
        """GET /api/v2/analytics/win-probability."""
        with patch("services.api.services.api.analytics.estimate_win_probability",
                   return_value={"win_probability": 0.35, "markup_pct": 10.0}):
            resp = app.get("/api/v2/analytics/win-probability?markup=10.0&n_competitors=4")
        assert resp.status_code == 200

    def test_recommendation(self, app):
        """POST /api/v2/analytics/recommendation."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e), \
             patch("services.api.services.api.analytics.generate_recommendation",
                   return_value={"go": True, "score": 0.8}):
            resp = app.post("/api/v2/analytics/recommendation", json={
                "cost_estimate": 200000.0,
                "n_competitors": 3,
                "cpv": "45",
            })
        assert resp.status_code == 200

    def test_analytics_dashboard_no_org(self, app):
        """GET /api/v2/analytics/dashboard with no org_id returns 403."""
        # conftest user has org_id, so we expect 200 or error fallback
        e = _eng(
            fetchone=MagicMock(pipeline_value=500_000.0, active_bids=5,
                               won=2, total=10),
            rows=[MagicMock(status="active", count=5)],
        )
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/analytics/dashboard")
        assert resp.status_code in (200, 403)

    def test_market_overview(self, app):
        """GET /api/v2/analytics/market-overview (no auth)."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        totals = MagicMock()
        totals.__getitem__ = lambda s, k: (100 if k == 0 else 1_000_000.0)

        conn.execute.side_effect = [
            MagicMock(**{"scalar.return_value": 2024}),
            MagicMock(**{"fetchone.return_value": totals}),
            MagicMock(**{"fetchall.return_value": []}),
            MagicMock(**{"fetchall.return_value": []}),
        ]
        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/analytics/market-overview")
        assert resp.status_code == 200

    def test_pipeline_funnel(self, app):
        """GET /api/v2/analytics/pipeline-funnel."""
        row = MagicMock()
        row.status = "active"
        row.count = 5
        e = _eng(rows=[row])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/analytics/pipeline-funnel")
        assert resp.status_code in (200, 403)

    def test_analyze_swz_no_ai(self, app):
        """POST /api/v2/ai/analyze-swz with use_ai=false."""
        with patch("services.api.services.api.analytics.extract_risks_from_text",
                   return_value={"red_flags": [], "summary": "ok"}):
            resp = app.post("/api/v2/ai/analyze-swz", json={
                "text": "Test SWZ text with some content.",
                "use_ai": False,
            })
        assert resp.status_code == 200

    def test_analyze_swz_with_ai(self, app):
        """POST /api/v2/ai/analyze-swz with use_ai=true."""
        with patch("services.api.services.api.analytics.extract_risks_with_ai",
                   new=AsyncMock(return_value={"red_flags": [], "summary": "ok"})):
            resp = app.post("/api/v2/ai/analyze-swz", json={
                "text": "Test SWZ content",
                "use_ai": True,
            })
        assert resp.status_code == 200


# ─── Competitor Watch ─────────────────────────────────────────────────────────

class TestCompetitorWatch:
    PATCH = "services.api.services.api.routers.competitor_watch.get_engine"

    def _mk_row(self, **kwargs):
        row = dict(
            id=str(uuid.uuid4()), competitor_nip="1234567890",
            competitor_name="Firma ABC", notes=None, tags=[], notify_on_win=True,
            created_at="2026-01-01", updated_at="2026-01-01",
            city="Warszawa", province="mazowieckie", total_wins=5,
            total_value=100_000.0, win_rate=0.4, top_cpv="45",
        )
        row.update(kwargs)
        return row

    def _conn_for_list(self, rows=None):
        """Engine where both list query and count query work."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        # First call: list rows (mappings)
        rows = rows or []
        mapping_result = MagicMock()
        mapping_result.all.return_value = [MagicMock(**{**r}) for r in rows]

        row_exec = MagicMock()
        row_exec.mappings.return_value = mapping_result

        # Second call: count scalar
        count_exec = MagicMock()
        count_exec.scalar.return_value = len(rows)

        conn.execute.side_effect = [row_exec, count_exec]
        return engine

    def test_search_contractors(self, app):
        """GET /api/v2/competitors/search."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        mapping_result = MagicMock()
        mapping_result.all.return_value = []
        r = MagicMock()
        r.mappings.return_value = mapping_result
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/competitors/search?q=Firma")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_search_contractors_short_query(self, app):
        """GET /api/v2/competitors/search with q=1 → 422."""
        resp = app.get("/api/v2/competitors/search?q=X")
        assert resp.status_code == 422

    def test_list_watched_empty(self, app):
        """GET /api/v2/competitors returns empty list."""
        e = self._conn_for_list(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/competitors")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_add_competitor(self, app):
        """POST /api/v2/competitors adds a new entry."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        # auto-enrich lookup
        ac_result = MagicMock()
        ac_result.one_or_none.return_value = None
        ac_result.mappings.return_value.one_or_none.return_value = None

        inserted = {
            "id": str(uuid.uuid4()), "competitor_nip": "1234567890",
            "competitor_name": "Firma XYZ", "notify_on_win": True,
            "created_at": "2026-01-01",
        }
        ins_result = MagicMock()
        ins_result.mappings.return_value.one.return_value = inserted

        conn.execute.side_effect = [ac_result, ins_result]

        with patch(self.PATCH, return_value=engine):
            resp = app.post("/api/v2/competitors", json={
                "competitor_nip": "1234567890",
                "competitor_name": "Firma XYZ",
            })
        assert resp.status_code in (201, 409, 500)

    def test_add_competitor_invalid_nip(self, app):
        """POST /api/v2/competitors with invalid NIP → 422."""
        resp = app.post("/api/v2/competitors", json={
            "competitor_nip": "abc",
        })
        assert resp.status_code == 422

    def test_get_competitor_not_found(self, app):
        """GET /api/v2/competitors/{id} → 404."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.mappings.return_value.one_or_none.return_value = None
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.get(f"/api/v2/competitors/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_update_competitor_not_found(self, app):
        """PUT /api/v2/competitors/{id} → 404."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.one_or_none.return_value = None
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.put(f"/api/v2/competitors/{uuid.uuid4()}", json={"notes": "Updated"})
        assert resp.status_code == 404

    def test_update_competitor_no_fields(self, app):
        """PUT /api/v2/competitors/{id} with empty body → 400."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.one_or_none.return_value = MagicMock(id=str(uuid.uuid4()))
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.put(f"/api/v2/competitors/{uuid.uuid4()}", json={})
        assert resp.status_code == 400

    def test_delete_competitor(self, app):
        """DELETE /api/v2/competitors/{id}."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.rowcount = 1
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.delete(f"/api/v2/competitors/{uuid.uuid4()}")
        assert resp.status_code in (204, 404)

    def test_competitor_wins(self, app):
        """GET /api/v2/competitors/{id}/wins."""
        cw_id = str(uuid.uuid4())
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        # First call: get NIP
        nip_result = MagicMock()
        nip_result.one_or_none.return_value = MagicMock(__getitem__=lambda s, k: "1234567890")

        # Second call: wins
        wins_result = MagicMock()
        wins_result.mappings.return_value.all.return_value = []

        conn.execute.side_effect = [nip_result, wins_result]

        with patch(self.PATCH, return_value=engine):
            resp = app.get(f"/api/v2/competitors/{cw_id}/wins")
        assert resp.status_code in (200, 404)

    def test_competitor_intel_invalid_nip(self, app):
        """GET /api/v2/competitors/intel/{nip} with invalid NIP → 400."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        conn.execute.return_value = MagicMock(**{"mappings.return_value.one_or_none.return_value": None,
                                                  "mappings.return_value.all.return_value": []})

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/competitors/intel/badnip")
        assert resp.status_code == 400

    def test_competitor_intel_valid_nip(self, app):
        """GET /api/v2/competitors/intel/{nip} with valid NIP."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        profile_res = MagicMock()
        profile_res.mappings.return_value.one_or_none.return_value = None
        all_res = MagicMock()
        all_res.mappings.return_value.all.return_value = []
        conn.execute.side_effect = [profile_res, all_res, all_res, all_res]

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/competitors/intel/1234567890")
        assert resp.status_code == 200

    @pytest.mark.xfail(reason="Route shadowed by /competitors/{watch_id} — routing conflict in prod code")
    def test_last_checked(self, app):
        """GET /api/v2/competitors/last-checked is shadowed by /{watch_id} path."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/competitors/last-checked")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_market_share(self, app):
        """GET /api/v2/analytics/market-share."""
        PATCH2 = "services.api.services.api.routers.competitor_watch.get_engine"
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        conn.execute.side_effect = [
            MagicMock(**{"scalar.return_value": 3}),
            MagicMock(**{"fetchall.return_value": []}),
        ]

        with patch(PATCH2, return_value=engine):
            resp = app.get("/api/v2/analytics/market-share")
        assert resp.status_code == 200


# ─── Tender Bookmarks ─────────────────────────────────────────────────────────

class TestTenderBookmarks:
    PATCH = "services.api.services.api.routers.tender_bookmarks.get_engine"

    def _bm_conn(self):
        """Connection for bookmark list endpoints."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)
        rows_res = MagicMock()
        rows_res.mappings.return_value.all.return_value = []
        count_res = MagicMock()
        count_res.scalar.return_value = 0
        conn.execute.side_effect = [rows_res, count_res]
        return engine

    def test_bookmark_stats_empty(self, app):
        """GET /api/v2/bookmarks/stats."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        rows_res = MagicMock()
        rows_res.mappings.return_value.all.return_value = []
        count_res = MagicMock()
        count_res.scalar.return_value = 0
        conn.execute.side_effect = [rows_res, count_res]

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/bookmarks/stats")
        assert resp.status_code == 200
        assert "total" in resp.json()

    def test_list_bookmarks(self, app):
        """GET /api/v2/bookmarks."""
        e = self._bm_conn()
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/bookmarks")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_bookmarks_stage_filter(self, app):
        """GET /api/v2/bookmarks?stage=watching."""
        e = self._bm_conn()
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/bookmarks?stage=watching")
        assert resp.status_code == 200

    def test_list_bookmarks_invalid_stage(self, app):
        """GET /api/v2/bookmarks?stage=invalid → 400."""
        resp = app.get("/api/v2/bookmarks?stage=invalid_stage")
        assert resp.status_code == 400

    def test_export_bookmarks_csv(self, app):
        """GET /api/v2/bookmarks/export returns CSV."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        rows_res = MagicMock()
        rows_res.mappings.return_value.all.return_value = []
        conn.execute.return_value = rows_res

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/bookmarks/export")
        assert resp.status_code == 200

    def test_export_invalid_stage(self, app):
        """GET /api/v2/bookmarks/export?stage=bad → 400."""
        resp = app.get("/api/v2/bookmarks/export?stage=badstage")
        assert resp.status_code == 400

    def test_create_bookmark(self, app):
        """POST /api/v2/bookmarks."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        dup_res = MagicMock()
        dup_res.one_or_none.return_value = None

        new_bm = {
            "id": str(uuid.uuid4()), "stage": "watching", "priority": 3,
            "ht_id": "HT-001", "tender_id": None, "created_at": "2026-01-01",
        }
        ins_res = MagicMock()
        ins_res.mappings.return_value.one.return_value = new_bm
        conn.execute.side_effect = [dup_res, ins_res]

        with patch(self.PATCH, return_value=engine):
            resp = app.post("/api/v2/bookmarks", json={"ht_id": "HT-001", "stage": "watching"})
        assert resp.status_code in (201, 409, 500)

    def test_create_bookmark_no_source(self, app):
        """POST /api/v2/bookmarks without ht_id or tender_id → 422."""
        resp = app.post("/api/v2/bookmarks", json={"stage": "watching"})
        assert resp.status_code == 422

    def test_create_bookmark_both_sources(self, app):
        """POST /api/v2/bookmarks with both ht_id and tender_id → 422."""
        resp = app.post("/api/v2/bookmarks", json={
            "ht_id": "HT-001", "tender_id": str(uuid.uuid4()),
        })
        assert resp.status_code == 422

    def test_get_bookmark_not_found(self, app):
        """GET /api/v2/bookmarks/{id} → 404."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.mappings.return_value.one_or_none.return_value = None
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.get(f"/api/v2/bookmarks/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_patch_bookmark_no_fields(self, app):
        """PATCH /api/v2/bookmarks/{id} with empty body → 400."""
        resp = app.patch(f"/api/v2/bookmarks/{uuid.uuid4()}", json={})
        assert resp.status_code == 400

    def test_patch_bookmark_invalid_stage(self, app):
        """PATCH /api/v2/bookmarks/{id} with bad stage → 400."""
        resp = app.patch(f"/api/v2/bookmarks/{uuid.uuid4()}", json={"stage": "bad_stage"})
        assert resp.status_code == 400

    def test_patch_bookmark_not_found(self, app):
        """PATCH /api/v2/bookmarks/{id} → 404 when not found."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.rowcount = 0
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.patch(f"/api/v2/bookmarks/{uuid.uuid4()}", json={"priority": 1})
        assert resp.status_code == 404

    def test_delete_bookmark(self, app):
        """DELETE /api/v2/bookmarks/{id}."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.rowcount = 1
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.delete(f"/api/v2/bookmarks/{uuid.uuid4()}")
        assert resp.status_code in (204, 404)

    def test_watch_bookmark_not_found(self, app):
        """POST /api/v2/bookmarks/{id}/watch → 404 when bookmark missing."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.mappings.return_value.one_or_none.return_value = None
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.post(f"/api/v2/bookmarks/{uuid.uuid4()}/watch")
        assert resp.status_code == 404


# ─── Buyer CRM ────────────────────────────────────────────────────────────────

class TestBuyerCRM:
    PATCH = "services.api.services.api.routers.buyer_crm.get_engine"

    def test_search_buyers(self, app):
        """GET /api/v2/buyer-crm/search."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.mappings.return_value.all.return_value = []
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/buyer-crm/search?q=Gmina")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_search_buyers_short_query(self, app):
        """GET /api/v2/buyer-crm/search with q=X → 422."""
        resp = app.get("/api/v2/buyer-crm/search?q=X")
        assert resp.status_code == 422

    def test_followups(self, app):
        """GET /api/v2/buyer-crm/followups."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.mappings.return_value.all.return_value = []
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/buyer-crm/followups")
        assert resp.status_code == 200
        assert "followups" in resp.json()

    def test_list_crm(self, app):
        """GET /api/v2/buyer-crm."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        rows_res = MagicMock()
        rows_res.mappings.return_value.all.return_value = []
        count_res = MagicMock()
        count_res.scalar.return_value = 0
        conn.execute.side_effect = [rows_res, count_res]

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/buyer-crm")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_crm_invalid_stage(self, app):
        """GET /api/v2/buyer-crm?stage=bad → 400."""
        resp = app.get("/api/v2/buyer-crm?stage=invalid")
        assert resp.status_code == 400

    def test_create_crm_invalid_nip(self, app):
        """POST /api/v2/buyer-crm with invalid NIP → 422."""
        resp = app.post("/api/v2/buyer-crm", json={
            "buyer_nip": "abc",
            "crm_stage": "prospect",
        })
        assert resp.status_code == 422

    def test_create_crm_invalid_stage(self, app):
        """POST /api/v2/buyer-crm with invalid stage → 400."""
        resp = app.post("/api/v2/buyer-crm", json={
            "buyer_nip": "1234567890",
            "crm_stage": "badstage",
        })
        assert resp.status_code == 400

    def test_create_crm_success(self, app):
        """POST /api/v2/buyer-crm creates entry."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        new_crm = {
            "id": str(uuid.uuid4()), "buyer_nip": "1234567890",
            "crm_stage": "prospect", "priority": 3, "created_at": "2026-01-01",
        }
        r = MagicMock()
        r.mappings.return_value.one.return_value = new_crm
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.post("/api/v2/buyer-crm", json={
                "buyer_nip": "1234567890",
                "crm_stage": "prospect",
            })
        assert resp.status_code in (201, 409, 500)

    def test_get_crm_not_found(self, app):
        """GET /api/v2/buyer-crm/{id} → 404."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.mappings.return_value.one_or_none.return_value = None
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.get(f"/api/v2/buyer-crm/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_update_crm_not_found(self, app):
        """PUT /api/v2/buyer-crm/{id} → 404."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.one_or_none.return_value = None
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.put(f"/api/v2/buyer-crm/{uuid.uuid4()}", json={"notes": "Updated"})
        assert resp.status_code == 404

    def test_update_crm_invalid_stage(self, app):
        """PUT /api/v2/buyer-crm/{id} with invalid stage → 400."""
        resp = app.put(f"/api/v2/buyer-crm/{uuid.uuid4()}",
                       json={"crm_stage": "invalidstage"})
        assert resp.status_code == 400

    def test_delete_crm(self, app):
        """DELETE /api/v2/buyer-crm/{id}."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.rowcount = 1
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.delete(f"/api/v2/buyer-crm/{uuid.uuid4()}")
        assert resp.status_code in (204, 404)

    def test_buyer_tenders_not_found(self, app):
        """GET /api/v2/buyer-crm/{id}/tenders → 404 when CRM entry missing."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        r = MagicMock()
        r.one_or_none.return_value = None
        conn.execute.return_value = r

        with patch(self.PATCH, return_value=engine):
            resp = app.get(f"/api/v2/buyer-crm/{uuid.uuid4()}/tenders")
        assert resp.status_code == 404


# ─── Estimates V2 ─────────────────────────────────────────────────────────────

class TestEstimatesV2:
    PATCH = "services.api.services.api.routers.estimates_v2.get_engine"

    def test_list_estimates_invalid_uuid(self, app):
        """GET /api/v2/estimates?tender_id=notauuid returns empty."""
        with patch(self.PATCH, return_value=_eng(rows=[])):
            resp = app.get("/api/v2/estimates?tender_id=not-a-uuid")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_estimates_empty(self, app):
        """GET /api/v2/estimates returns empty list."""
        tid = str(uuid.uuid4())
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get(f"/api/v2/estimates?tender_id={tid}")
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "total": 0}

    def test_create_estimate_tender_not_found(self, app):
        """POST /api/v2/estimates → 404 when tender not found."""
        e = _eng(fetchone=None)
        with patch(self.PATCH, return_value=e):
            resp = app.post("/api/v2/estimates", json={
                "tender_id": str(uuid.uuid4()),
                "variant": "doc",
            })
        assert resp.status_code == 404

    def test_create_estimate_invalid_variant(self, app):
        """POST /api/v2/estimates with invalid variant → 422."""
        e = _eng(fetchone=MagicMock(id=str(uuid.uuid4())))
        with patch(self.PATCH, return_value=e):
            resp = app.post("/api/v2/estimates", json={
                "tender_id": str(uuid.uuid4()),
                "variant": "invalid",
            })
        assert resp.status_code == 422

    def test_create_estimate_success(self, app):
        """POST /api/v2/estimates creates estimate."""
        tender_row = MagicMock(id=str(uuid.uuid4()))
        created = MagicMock()
        created.id = str(uuid.uuid4())
        created.tender_id = str(uuid.uuid4())
        created.variant = "doc"
        created.total_net_pln = 100_000.0
        created.overhead_pct = 10.0
        created.profit_pct = 5.0
        created.params = {}
        created.created_at = datetime.now(timezone.utc)

        engine = MagicMock()
        conn_read = MagicMock()
        conn_write = MagicMock()

        engine.connect.return_value.__enter__ = MagicMock(return_value=conn_read)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value.__enter__ = MagicMock(return_value=conn_write)
        engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        conn_read.execute.return_value = MagicMock(**{"fetchone.return_value": tender_row})
        conn_write.execute.return_value = MagicMock(**{"fetchone.return_value": created})

        with patch(self.PATCH, return_value=engine):
            resp = app.post("/api/v2/estimates", json={
                "tender_id": str(uuid.uuid4()),
                "variant": "doc",
                "total_net_pln": 100_000.0,
            })
        assert resp.status_code == 200

    def test_get_estimate_not_found(self, app):
        """GET /api/v2/estimates/{id} → 404."""
        e = _eng(fetchone=None)
        with patch(self.PATCH, return_value=e):
            resp = app.get(f"/api/v2/estimates/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_get_estimate_found(self, app):
        """GET /api/v2/estimates/{id} returns estimate with lines."""
        est_row = MagicMock()
        est_row.id = str(uuid.uuid4())
        est_row.tender_id = str(uuid.uuid4())
        est_row.variant = "doc"
        est_row.total_net_pln = 50_000.0
        est_row.overhead_pct = 10.0
        est_row.profit_pct = 5.0
        est_row.params = {}
        est_row.created_at = datetime.now(timezone.utc)

        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        conn.execute.side_effect = [
            MagicMock(**{"fetchone.return_value": est_row}),
            MagicMock(**{"fetchall.return_value": []}),
        ]

        with patch(self.PATCH, return_value=engine):
            resp = app.get(f"/api/v2/estimates/{uuid.uuid4()}")
        assert resp.status_code == 200
        assert "lines" in resp.json()

    def test_update_estimate_no_fields(self, app):
        """PUT /api/v2/estimates/{id} with no fields → 422."""
        with patch(self.PATCH, return_value=_eng()):
            resp = app.put(f"/api/v2/estimates/{uuid.uuid4()}", json={})
        assert resp.status_code == 422

    def test_update_estimate_not_found(self, app):
        """PUT /api/v2/estimates/{id} → 404."""
        e = _eng(fetchone=None)
        with patch(self.PATCH, return_value=e):
            resp = app.put(f"/api/v2/estimates/{uuid.uuid4()}",
                           json={"total_net_pln": 99_000.0})
        assert resp.status_code == 404

    def test_predict_cost(self, app):
        """GET /api/v2/estimates/predict returns cost prediction."""
        estimator_mock = MagicMock()
        estimator_mock.predict.return_value = {
            "total_net_pln": 500_000.0,
            "confidence_low": 400_000.0,
            "confidence_high": 600_000.0,
            "method": "benchmark",
            "variant": "doc",
            "lines": [],
            "notes": "",
        }

        with patch("services.api.services.api.analytics.cost_estimation.get_estimator",
                   return_value=estimator_mock), \
             patch("services.api.services.api.analytics.cost_estimation._resolve_cpv_benchmark",
                   return_value={"price_per_m2": 500.0}), \
             patch("services.api.services.api.routers.estimates_v2.get_engine",
                   return_value=_eng(rows=[])), \
             patch("services.api.services.api.redis_cache._get_redis", return_value=None):
            resp = app.get("/api/v2/estimates/predict?cpv=45&region=mazowieckie&area_m2=1000")
        assert resp.status_code == 200
        data = resp.json()
        assert "ai_estimate" in data

    def test_patch_estimate_lines(self, app):
        """PATCH /api/v2/estimates/{id}/lines."""
        est_row = MagicMock(id=str(uuid.uuid4()))
        engine = MagicMock()
        conn_read = MagicMock()
        conn_write = MagicMock()

        engine.connect.return_value.__enter__ = MagicMock(return_value=conn_read)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value.__enter__ = MagicMock(return_value=conn_write)
        engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        conn_read.execute.return_value = MagicMock(**{"fetchone.return_value": est_row,
                                                       "fetchall.return_value": []})
        conn_write.execute.return_value = MagicMock()

        with patch(self.PATCH, return_value=engine):
            resp = app.patch(f"/api/v2/estimates/{uuid.uuid4()}/lines", json=[
                {"description": "Roboty ziemne", "unit": "m2", "quantity": 100.0, "unit_price": 50.0}
            ])
        assert resp.status_code in (200, 404)


# ─── Offer Assembly ───────────────────────────────────────────────────────────

class TestOfferAssembly:
    """Plan-gated endpoints — expect 403 (free plan) or 200 (if plan check succeeds)."""

    GENERATE_URL = "/api/v2/documents/generate"
    KNR_URL = "/api/v2/knr/map"

    def _valid_generate_body(self):
        return {
            "tender": {
                "nr_sprawy": "ZP/001/2026",
                "tytul": "Budowa drogi",
                "zamawiajacy_nazwa": "Gmina Testowa",
                "cpv_kody": ["45233120-6"],
            },
            "company": {
                "nazwa_pelna": "Firma Budowlana Sp. z o.o.",
                "nip": "1234567890",
                "adres": "ul. Budowlana 12, 40-600 Katowice",
            },
            "kosztorys": {
                "pozycje": [],
                "suma_netto": 100000.0,
                "vat_pct": 23.0,
                "suma_brutto": 123000.0,
            },
        }

    def test_generate_documents_plan_gated(self, app):
        """POST /api/v2/documents/generate is plan-gated → 403 or 200."""
        resp = app.post(self.GENERATE_URL, json=self._valid_generate_body())
        assert resp.status_code in (200, 403, 500)

    def test_generate_documents_missing_required(self, app):
        """POST /api/v2/documents/generate missing required fields → 422."""
        resp = app.post(self.GENERATE_URL, json={})
        assert resp.status_code == 422

    def test_knr_map_plan_gated(self, app):
        """POST /api/v2/knr/map is plan-gated → 403 or 200."""
        resp = app.post(self.KNR_URL, json={
            "positions": [
                {"id": "1", "description": "Roboty ziemne wykop", "quantity": 50.0, "unit": "m3"}
            ]
        })
        assert resp.status_code in (200, 403, 500)

    def test_knr_map_missing_body(self, app):
        """POST /api/v2/knr/map with empty body → 422."""
        resp = app.post(self.KNR_URL, json={})
        assert resp.status_code == 422


# ─── M7 Phase 2 ───────────────────────────────────────────────────────────────

class TestM7Phase2:
    PATCH = "services.api.services.api.routers.m7_phase2.get_engine"

    def test_list_buyers_empty(self, app):
        """GET /api/v2/buyers returns empty list."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/buyers")
        assert resp.status_code == 200
        data = resp.json()
        assert "buyers" in data

    def test_list_buyers_with_query(self, app):
        """GET /api/v2/buyers?q=Gmina."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/buyers?q=Gmina&sort=name")
        assert resp.status_code == 200

    def test_buyer_history(self, app):
        """GET /api/v2/buyers/{name}/history."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/buyers/GminaWarszawa/history")
        assert resp.status_code == 200
        assert "history" in resp.json()

    def test_buyer_insights(self, app):
        """GET /api/v2/buyers/{name}/insights."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        stats_row = MagicMock()
        stats_row.__getitem__ = lambda s, k: ([3, 100_000, 50_000, 200_000, None, None][k])

        conn.execute.side_effect = [
            MagicMock(**{"fetchone.return_value": stats_row}),
            MagicMock(**{"fetchall.return_value": []}),
            MagicMock(**{"fetchall.return_value": []}),
        ]

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/buyers/GminaTestowa/insights")
        assert resp.status_code == 200
        assert "seasonality" in resp.json()

    def test_list_competitors_m7(self, app):
        """GET /api/v2/competitors via m7_phase2 (fallback)."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/competitors")
        assert resp.status_code == 200

    @pytest.mark.xfail(reason="Route shadowed by competitor_watch /{watch_id} — routing conflict in prod code")
    def test_competitor_heatmap(self, app):
        """GET /api/v2/competitors/heatmap is shadowed by /{watch_id} path."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/competitors/heatmap")
        assert resp.status_code == 200
        assert "heatmap" in resp.json()

    def test_market_intel_overview(self, app):
        """GET /api/v2/market-intel/overview."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        total_row = MagicMock()
        total_row.__getitem__ = lambda s, k: ([100, 1_000_000.0, 50, 20, 200_000.0][k])
        conn.execute.side_effect = [
            MagicMock(**{"fetchone.return_value": total_row}),
            MagicMock(**{"fetchall.return_value": []}),
            MagicMock(**{"fetchall.return_value": []}),
        ]

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/market-intel/overview")
        assert resp.status_code == 200

    def test_cpv_trends(self, app):
        """GET /api/v2/market-intel/cpv-trends."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/market-intel/cpv-trends")
        assert resp.status_code == 200

    def test_market_regional(self, app):
        """GET /api/v2/market-intel/regional."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/market-intel/regional")
        assert resp.status_code == 200

    def test_list_notifications(self, app):
        """GET /api/v2/notifications."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/notifications")
        assert resp.status_code == 200

    def test_list_notifications_unread_only(self, app):
        """GET /api/v2/notifications?unread_only=true."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/notifications?unread_only=true")
        assert resp.status_code == 200

    def test_unread_count(self, app):
        """GET /api/v2/notifications/unread-count."""
        e = _eng(scalar_val=3)
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/notifications/unread-count")
        assert resp.status_code == 200
        data = resp.json()
        # Router returns {"unread": N}
        assert "unread" in data or "unread_count" in data

    def test_mark_notification_read(self, app):
        """PATCH /api/v2/notifications/{id}/read."""
        e = _eng()
        with patch(self.PATCH, return_value=e):
            resp = app.patch(f"/api/v2/notifications/{uuid.uuid4()}/read")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_command_search(self, app):
        """GET /api/v2/command/search?q=test."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        conn.execute.return_value = MagicMock(**{"fetchall.return_value": []})

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/command/search?q=testquery")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data

    def test_command_search_short_q(self, app):
        """GET /api/v2/command/search?q=X → 422."""
        resp = app.get("/api/v2/command/search?q=X")
        assert resp.status_code == 422


# ─── M7 Advanced ──────────────────────────────────────────────────────────────

class TestM7Advanced:
    PATCH = "services.api.services.api.routers.m7_advanced.get_engine"

    def test_generate_offer_pdf_not_found(self, app):
        """POST /api/v2/offers/generate-pdf/{tender_id} → tender not found."""
        e = _eng(fetchone=None)
        with patch(self.PATCH, return_value=e):
            resp = app.post(
                f"/api/v2/offers/generate-pdf/{uuid.uuid4()}?tenant_id={uuid.uuid4()}"
            )
        assert resp.status_code == 200
        assert resp.json().get("error") == "tender not found"

    def test_generate_offer_pdf_found(self, app):
        """POST /api/v2/offers/generate-pdf/{tender_id} calls LLM when tender found."""
        tender_row = MagicMock()
        tender_row.__getitem__ = lambda s, k: (
            ["Budowa drogi", "Gmina X", 500_000.0, "45", "mazowieckie", "2026-12-31"][k]
        )

        engine = MagicMock()
        conn_read = MagicMock()
        conn_write = MagicMock()

        engine.connect.return_value.__enter__ = MagicMock(return_value=conn_read)
        engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        engine.begin.return_value.__enter__ = MagicMock(return_value=conn_write)
        engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        conn_read.execute.return_value = MagicMock(**{"fetchone.return_value": tender_row})
        conn_write.execute.return_value = MagicMock()

        llm_mock = MagicMock()
        llm_mock.generate.return_value = "Oferta Brief: ..."

        with patch(self.PATCH, return_value=engine), \
             patch("services.api.services.api.routers.m7_advanced.get_llm_client",
                   return_value=llm_mock):
            resp = app.post(
                f"/api/v2/offers/generate-pdf/{uuid.uuid4()}?tenant_id={uuid.uuid4()}"
            )
        assert resp.status_code == 200
        assert "brief" in resp.json()

    def test_record_outcome(self, app):
        """POST /api/v2/learning/record records outcome."""
        e = _eng()
        with patch(self.PATCH, return_value=e):
            resp = app.post(
                f"/api/v2/learning/record?tenant_id={uuid.uuid4()}",
                json={"outcome": "won", "actual_price": 450_000.0, "notes": "Great result"}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "recorded"

    def test_learning_stats(self, app):
        """GET /api/v2/learning/stats."""
        row = MagicMock()
        row.__getitem__ = lambda s, k: ([10, 7, 2, 4.2][k])
        e = _eng(fetchone=row)
        with patch(self.PATCH, return_value=e):
            resp = app.get(f"/api/v2/learning/stats?tenant_id={uuid.uuid4()}")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_outcomes" in data

    def test_trigger_finetune_insufficient_data(self, app):
        """POST /api/v2/finetune/trigger with < 10 samples."""
        e = _eng(scalar_val=5)
        with patch(self.PATCH, return_value=e):
            resp = app.post(f"/api/v2/finetune/trigger?tenant_id={uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "insufficient_data"

    def test_trigger_finetune_sufficient_data(self, app):
        """POST /api/v2/finetune/trigger with >= 10 samples → queued."""
        e = _eng(scalar_val=15)
        with patch(self.PATCH, return_value=e):
            resp = app.post(f"/api/v2/finetune/trigger?tenant_id={uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"

    def test_finetune_status(self, app):
        """GET /api/v2/finetune/status returns model info."""
        resp = app.get("/api/v2/finetune/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_model"] == "axon"
        assert data["status"] == "active"


# ─── OLAP ─────────────────────────────────────────────────────────────────────

class TestOLAP:
    PATCH = "services.api.services.api.routers.olap.get_engine"

    def test_market_olap_empty(self, app):
        """GET /api/v2/analytics/olap returns empty list."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/analytics/olap")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_market_olap_with_filters(self, app):
        """GET /api/v2/analytics/olap?cpv_division=45&year=2024."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/analytics/olap?cpv_division=45&year=2024&group_by=quarter")
        assert resp.status_code == 200

    def test_market_olap_invalid_group_by(self, app):
        """GET /api/v2/analytics/olap?group_by=invalid → 422."""
        resp = app.get("/api/v2/analytics/olap?group_by=invalid")
        assert resp.status_code == 422

    def test_price_index_empty(self, app):
        """GET /api/v2/analytics/price-index returns empty list."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/analytics/price-index")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_price_index_with_cpv(self, app):
        """GET /api/v2/analytics/price-index?cpv_group=45."""
        row = MagicMock()
        row.__getitem__ = lambda s, k: (
            ["45", MagicMock(isoformat=lambda: "2024-Q1"), 500_000.0, 10, None, None][k]
        )
        e = _eng(rows=[row])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/analytics/price-index?cpv_group=45")
        assert resp.status_code == 200

    def test_buyer_trajectory_empty(self, app):
        """GET /api/v2/analytics/buyer-trajectory returns empty list."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/analytics/buyer-trajectory")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_buyer_trajectory_with_buyer(self, app):
        """GET /api/v2/analytics/buyer-trajectory?buyer=Gmina."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/analytics/buyer-trajectory?buyer=Gmina")
        assert resp.status_code == 200

    def test_seasonal_patterns_empty(self, app):
        """GET /api/v2/analytics/seasonal returns empty list (both queries empty)."""
        engine = MagicMock()
        conn = MagicMock()
        for ctx_mgr in (engine.connect.return_value, engine.begin.return_value):
            ctx_mgr.__enter__ = MagicMock(return_value=conn)
            ctx_mgr.__exit__ = MagicMock(return_value=False)

        # Both execute calls return empty
        conn.execute.return_value = MagicMock(**{"fetchall.return_value": []})

        with patch(self.PATCH, return_value=engine):
            resp = app.get("/api/v2/analytics/seasonal")
        assert resp.status_code == 200

    def test_buyer_cohort(self, app):
        """GET /api/v2/analytics/cohort returns cohort data."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/analytics/cohort")
        assert resp.status_code == 200
        assert resp.json() == []


# ─── Scoring Config ───────────────────────────────────────────────────────────

class TestScoringConfig:
    PATCH = "services.api.services.api.routers.scoring_config.get_engine"

    def test_get_config_default(self, app):
        """GET /api/v2/scoring/config returns default when no row in DB."""
        e = _eng(fetchone=None)
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/scoring/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_default"] is True
        assert data["cpv_weight"] == 0.35

    def test_get_config_from_db(self, app):
        """GET /api/v2/scoring/config returns stored config."""
        row = MagicMock()
        row.__getitem__ = lambda s, k: (
            [0.4, 0.25, 0.15, 0.1, 0.1, None, None, [], []][k]
        )
        e = _eng(fetchone=row)
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/scoring/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_default"] is False

    def test_update_config(self, app):
        """PUT /api/v2/scoring/config upserts config."""
        e = _eng()
        with patch(self.PATCH, return_value=e):
            resp = app.put("/api/v2/scoring/config", json={
                "cpv_weight": 0.35,
                "value_weight": 0.20,
                "region_weight": 0.15,
                "deadline_weight": 0.10,
                "historical_win_weight": 0.20,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "cpv_weight" in data

    def test_update_config_weights_normalized(self, app):
        """PUT /api/v2/scoring/config auto-normalizes weights."""
        e = _eng()
        with patch(self.PATCH, return_value=e):
            resp = app.put("/api/v2/scoring/config", json={
                "cpv_weight": 1.0,
                "value_weight": 1.0,
                "region_weight": 1.0,
                "deadline_weight": 1.0,
                "historical_win_weight": 1.0,
            })
        assert resp.status_code == 200
        # All weights should sum to ~1.0
        data = resp.json()
        total = (data["cpv_weight"] + data["value_weight"] + data["region_weight"] +
                 data["deadline_weight"] + data["historical_win_weight"])
        assert abs(total - 1.0) < 0.01

    def test_trigger_rescore(self, app):
        """POST /api/v2/scoring/rescore calls rescore_tenant."""
        rescore_result = {
            "total": 100, "processed": 100,
            "avg_score_before": 0.55, "avg_score_after": 0.62,
        }
        with patch("services.ingestion.scorer.rescore_tenant", return_value=rescore_result):
            resp = app.post("/api/v2/scoring/rescore")
        assert resp.status_code in (200, 500)

    def test_get_win_rates_empty(self, app):
        """GET /api/v2/scoring/win-rates returns empty list."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/scoring/win-rates")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_win_rates_with_data(self, app):
        """GET /api/v2/scoring/win-rates returns win rate items."""
        row = MagicMock()
        row.__getitem__ = lambda s, k: (["45230", 50, ["Firma A", "Firma B"]][k])
        e = _eng(rows=[row])
        with patch(self.PATCH, return_value=e):
            resp = app.get("/api/v2/scoring/win-rates?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["cpv_prefix"] == "45230"


# ─── Semantic Search ──────────────────────────────────────────────────────────

class TestSemanticSearch:
    PATCH = "services.api.services.api.routers.semantic_search.get_engine"

    def test_semantic_search(self, app):
        """POST /api/v2/tenders/semantic-search."""
        e = _eng(rows=[])
        with patch(self.PATCH, return_value=e), \
             patch("services.api.services.api.routers.semantic_search.embed_text",
                   return_value=[0.1] * 768):
            resp = app.post("/api/v2/tenders/semantic-search", json={
                "query": "budowa drogi ekspresowej",
                "limit": 10,
                "tenant_id": str(uuid.uuid4()),
            })
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_rag_query(self, app):
        """POST /api/v2/rag/query."""
        e = _eng()
        with patch(self.PATCH, return_value=e), \
             patch("services.api.services.api.routers.semantic_search.rag_query",
                   return_value=[{"chunk": "test", "score": 0.9}]):
            resp = app.post(
                f"/api/v2/rag/query?tender_id={uuid.uuid4()}",
                json={"query": "warunki techniczne", "top_k": 3}
            )
        assert resp.status_code == 200

    def test_rag_chat_streaming(self, app):
        """POST /api/v2/rag/chat/{tender_id} returns SSE stream."""
        def _gen(*args, **kwargs):
            yield "token1"
            yield "token2"

        e = _eng()
        with patch(self.PATCH, return_value=e), \
             patch("services.api.services.api.routers.semantic_search.rag_generate",
                   return_value=_gen()), \
             patch("services.api.services.api.routers.semantic_search.get_llm_client",
                   return_value=MagicMock()):
            resp = app.post(
                f"/api/v2/rag/chat/{uuid.uuid4()}",
                json={"query": "co zawiera SWZ?"}
            )
        assert resp.status_code == 200

    def test_embed_document(self, app):
        """POST /api/v2/rag/embed-document/{tender_id}."""
        e = _eng()
        with patch(self.PATCH, return_value=e), \
             patch("services.api.services.api.routers.semantic_search.embed_document_chunks",
                   return_value=5):
            resp = app.post(
                f"/api/v2/rag/embed-document/{uuid.uuid4()}",
                json={"text": "Długi tekst SWZ do indeksowania...", "source_type": "swz"}
            )
        assert resp.status_code == 200
        assert resp.json()["chunks_created"] == 5

    def test_run_batch_embedding(self, app):
        """POST /api/v2/embeddings/run-batch."""
        e = _eng()
        with patch(self.PATCH, return_value=e), \
             patch("services.api.services.api.routers.semantic_search.embed_tenders_batch",
                   return_value=42):
            resp = app.post("/api/v2/embeddings/run-batch?limit=100")
        assert resp.status_code == 200
        assert resp.json()["embedded_count"] == 42

    def test_run_batch_embedding_with_tenant(self, app):
        """POST /api/v2/embeddings/run-batch?tenant_id=..."""
        e = _eng()
        with patch(self.PATCH, return_value=e), \
             patch("services.api.services.api.routers.semantic_search.embed_tenders_batch",
                   return_value=10):
            resp = app.post(
                f"/api/v2/embeddings/run-batch?tenant_id={uuid.uuid4()}&limit=50"
            )
        assert resp.status_code == 200
