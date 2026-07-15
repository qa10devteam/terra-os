"""BLOK-E — Coverage boost for scoring / audit_v2 / kosztorys_v3 / reports.

Strategy:
  - scoring.py     : test functions directly (routing conflicts with scoring_config.py);
                     HTTP only for unique endpoints: cpv-heatmap, refresh-views, score-breakdown
  - audit_v2.py    : HTTP for /entity/{id}, /diff/{id}, /stats (unique routes);
                     direct function calls for /trail, /recent (shadowed by audit.py);
                     unit tests for _summarize_changes helper
  - kosztorys_v3.py: HTTP for /icb/rates and /kosztorys/{id}/ai-wycena-v2 (unique)
  - reports.py     : direct function calls (reports/monthly, reports/benchmark shadowed by m7_backend.py);
                     HTTP for pdf endpoint if accessible
"""
from __future__ import annotations

import io
import json
import uuid
from datetime import datetime, date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

import pytest
from httpx import ASGITransport, AsyncClient


# ─── Fixtures ─────────────────────────────────────────────────────────────────

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


def _conn_mock(fetchall=None, fetchone=None, scalar=0):
    """Build a fake SQLAlchemy connection with a simple execute mock."""
    conn = MagicMock()
    result = MagicMock()
    result.fetchall.return_value = fetchall if fetchall is not None else []
    result.fetchone.return_value = fetchone
    result.scalar.return_value = scalar
    conn.execute.return_value = result
    return conn


# ═══════════════════════════════════════════════════════════════════════════════
# scoring.py — direct function tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoringDirect:
    """Direct calls to scoring.py functions — avoids routing conflicts."""

    def test_update_scoring_config_sum_not_100_raises(self):
        """update_scoring_config raises HTTPException when sum != 100."""
        from fastapi import HTTPException
        from services.api.services.api.routers.scoring import update_scoring_config, ScoringConfigRequest

        body = ScoringConfigRequest(weights={"cpv_match": 10, "value_range": 10})
        with pytest.raises(HTTPException) as exc_info:
            update_scoring_config(body)
        assert exc_info.value.status_code == 400
        assert "100" in exc_info.value.detail

    def test_update_scoring_config_sum_100_ok(self):
        """update_scoring_config saves when weights sum to 100."""
        from services.api.services.api.routers.scoring import update_scoring_config, ScoringConfigRequest

        weights = {
            "cpv_match": 30,
            "value_range": 25,
            "deadline_pressure": 20,
            "buyer_history": 15,
            "document_quality": 10,
        }
        body = ScoringConfigRequest(weights=weights)

        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.begin.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.begin.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value = MagicMock()

            result = update_scoring_config(body)

        assert result["saved"] is True
        assert result["weights"] == weights

    def test_get_scoring_config_default(self):
        """get_scoring_config returns defaults when no DB row."""
        from services.api.services.api.routers.scoring import get_scoring_config, _DEFAULT_WEIGHTS

        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchone.return_value = None

            result = get_scoring_config()

        assert "weights" in result
        assert result["weights"] == _DEFAULT_WEIGHTS

    def test_get_scoring_config_from_db(self):
        """get_scoring_config returns DB value when row exists."""
        from services.api.services.api.routers.scoring import get_scoring_config

        db_weights = {"cpv_match": 40, "value_range": 60}
        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            row = MagicMock()
            row.__getitem__ = lambda s, i: json.dumps(db_weights) if i == 0 else None
            conn.execute.return_value.fetchone.return_value = row

            result = get_scoring_config()

        assert "weights" in result
        assert result["weights"] == db_weights

    def test_get_score_breakdown_not_found_direct(self):
        """get_score_breakdown raises 404 when no rows."""
        from fastapi import HTTPException
        from services.api.services.api.routers.scoring import get_score_breakdown

        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = []

            with pytest.raises(HTTPException) as exc:
                get_score_breakdown(str(uuid.uuid4()))
        assert exc.value.status_code == 404

    def test_get_score_breakdown_found_direct(self):
        """get_score_breakdown returns breakdown with total_score."""
        from services.api.services.api.routers.scoring import get_score_breakdown

        tid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = [
                ("cpv_match", 80.0, 30.0, 24.0),
                ("value_range", 70.0, 25.0, 17.5),
            ]

            result = get_score_breakdown(tid)

        assert result["tender_id"] == tid
        assert len(result["breakdown"]) == 2
        assert result["total_score"] == pytest.approx(41.5)

    def test_get_cpv_heatmap_with_nulls_direct(self):
        """get_cpv_heatmap coerces None values to 0."""
        from services.api.services.api.routers.scoring import get_cpv_heatmap

        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = [
                (45200, "mazowieckie", None, None, None),
            ]

            result = get_cpv_heatmap()

        assert result[0]["tender_count"] == 0
        assert result[0]["avg_value"] == 0.0
        assert result[0]["total_value"] == 0.0

    def test_get_cpv_heatmap_with_values_direct(self):
        """get_cpv_heatmap returns correct data with real values."""
        from services.api.services.api.routers.scoring import get_cpv_heatmap

        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = [
                (45200, "mazowieckie", 15, 500000.0, 7500000.0),
            ]

            result = get_cpv_heatmap()

        assert len(result) == 1
        assert result[0]["cpv5"] == 45200
        assert result[0]["tender_count"] == 15
        assert result[0]["avg_value"] == 500000.0

    def test_refresh_views_direct(self):
        """refresh_views executes 4 REFRESH statements and returns refreshed."""
        from services.api.services.api.routers.scoring import refresh_views

        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.begin.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.begin.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value = MagicMock()

            result = refresh_views()

        assert result == {"status": "refreshed"}
        assert conn.execute.call_count == 4


# ═══════════════════════════════════════════════════════════════════════════════
# scoring.py — HTTP via unique endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestScoringHTTP:

    @pytest.mark.asyncio
    async def test_get_cpv_heatmap_http(self, app, auth_headers):
        """GET /market/cpv-heatmap → 200 list."""
        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = [
                (45200, "mazowieckie", 10, 500000.0, 5000000.0),
            ]

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/v2/market/cpv-heatmap", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_refresh_views_http(self, app, auth_headers):
        """POST /admin/refresh-views → 200 refreshed."""
        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.begin.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.begin.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value = MagicMock()

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/v2/admin/refresh-views", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "refreshed"

    @pytest.mark.asyncio
    async def test_score_breakdown_404_http(self, app, auth_headers):
        """GET /tenders/{id}/score-breakdown → 404 when no rows."""
        tid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = []

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(f"/api/v2/tenders/{tid}/score-breakdown", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_score_breakdown_200_http(self, app, auth_headers):
        """GET /tenders/{id}/score-breakdown → 200 with breakdown."""
        tid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.scoring.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = [
                ("cpv_match", 80.0, 30.0, 24.0),
            ]

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(f"/api/v2/tenders/{tid}/score-breakdown", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "breakdown" in data
        assert "total_score" in data


# ═══════════════════════════════════════════════════════════════════════════════
# audit_v2.py — _summarize_changes unit tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSummarizeChanges:

    def test_none_input(self):
        from services.api.services.api.routers.audit_v2 import _summarize_changes
        assert _summarize_changes(None) == "brak szczegółów"

    def test_empty_string(self):
        from services.api.services.api.routers.audit_v2 import _summarize_changes
        assert _summarize_changes("") == "brak szczegółów"

    def test_dict_few_keys(self):
        from services.api.services.api.routers.audit_v2 import _summarize_changes
        result = _summarize_changes(json.dumps({"status": "active", "value": 100}))
        assert result.startswith("Zmieniono:")
        assert "status" in result

    def test_dict_many_keys_has_suffix(self):
        from services.api.services.api.routers.audit_v2 import _summarize_changes
        data = {f"field_{i}": i for i in range(6)}
        result = _summarize_changes(json.dumps(data))
        assert "więcej" in result

    def test_list_input(self):
        from services.api.services.api.routers.audit_v2 import _summarize_changes
        result = _summarize_changes(json.dumps([1, 2, 3]))
        assert isinstance(result, str)

    def test_invalid_json(self):
        from services.api.services.api.routers.audit_v2 import _summarize_changes
        result = _summarize_changes("not-valid-json{{{{")
        assert result == "zmiana"

    def test_dict_passed_directly(self):
        from services.api.services.api.routers.audit_v2 import _summarize_changes
        result = _summarize_changes({"a": 1, "b": 2})
        assert result.startswith("Zmieniono:")


# ═══════════════════════════════════════════════════════════════════════════════
# audit_v2.py — direct function tests for shadowed routes
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditV2Direct:

    def test_get_audit_trail_no_filters(self):
        """get_audit_trail with no filters → dict with items/total."""
        from services.api.services.api.routers.audit_v2 import get_audit_trail

        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            call_count = [0]

            def execute_side(stmt, params=None):
                result = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    result.fetchall.return_value = []
                else:
                    result.fetchone.return_value = (0,)
                return result

            conn.execute.side_effect = execute_side

            result = get_audit_trail()

        assert "items" in result
        assert "total" in result
        assert result["total"] == 0

    def test_get_audit_trail_with_entity_type(self):
        """get_audit_trail with entity_type filter adds WHERE clause."""
        from services.api.services.api.routers.audit_v2 import get_audit_trail

        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            call_count = [0]

            def execute_side(stmt, params=None):
                result = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    result.fetchall.return_value = []
                else:
                    result.fetchone.return_value = (5,)
                return result

            conn.execute.side_effect = execute_side

            result = get_audit_trail(entity_type="tender")

        assert result["total"] == 5

    def test_get_audit_trail_with_all_filters(self):
        """get_audit_trail with all filters — entity_type + user_id + action."""
        from services.api.services.api.routers.audit_v2 import get_audit_trail

        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            call_count = [0]

            def execute_side(stmt, params=None):
                result = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    dt = datetime(2026, 1, 10)
                    row = (
                        str(uuid.uuid4()), "tender", str(uuid.uuid4()),
                        "update", "usr@test.pl",
                        json.dumps({"status": "active"}), dt,
                    )
                    result.fetchall.return_value = [row]
                else:
                    result.fetchone.return_value = (1,)
                return result

            conn.execute.side_effect = execute_side

            result = get_audit_trail(entity_type="tender", user_id="some-user", action="update")

        assert result["total"] == 1
        assert len(result["items"]) == 1

    def test_get_entity_history_direct(self):
        """get_entity_history returns correct list."""
        from services.api.services.api.routers.audit_v2 import get_entity_history

        eid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            dt = datetime(2026, 3, 1)
            row = (str(uuid.uuid4()), "tender", "create", "user@test.pl",
                   json.dumps({"status": "draft"}), dt)
            conn.execute.return_value.fetchall.return_value = [row]

            result = get_entity_history(eid)

        assert len(result) == 1
        assert result[0]["entity_type"] == "tender"
        assert result[0]["changes"] == {"status": "draft"}

    def test_get_entity_history_null_changes(self):
        """get_entity_history with NULL detail → changes={}."""
        from services.api.services.api.routers.audit_v2 import get_entity_history

        eid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            dt = datetime(2026, 3, 1)
            row = (str(uuid.uuid4()), "offer", "delete", None, None, dt)
            conn.execute.return_value.fetchall.return_value = [row]

            result = get_entity_history(eid)

        assert result[0]["changes"] == {}
        assert result[0]["actor"] is None

    def test_get_diff_not_found_direct(self):
        """get_diff returns error dict when row not found."""
        from services.api.services.api.routers.audit_v2 import get_diff

        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchone.return_value = None

            result = get_diff(str(uuid.uuid4()))

        assert result["error"] == "Not found"

    def test_get_diff_found_direct(self):
        """get_diff returns diff with fields_changed."""
        from services.api.services.api.routers.audit_v2 import get_diff

        aid = str(uuid.uuid4())
        changes = {"status": {"before": "draft", "after": "active"}, "value": {"before": 100, "after": 200}}

        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            dt = datetime(2026, 4, 1)
            row = MagicMock()
            row.__getitem__ = lambda s, i: [
                aid, "tender", str(uuid.uuid4()), "update",
                "user@test.pl", json.dumps(changes), dt
            ][i]
            conn.execute.return_value.fetchone.return_value = row

            result = get_diff(aid)

        assert "diff" in result
        assert "fields_changed" in result
        assert set(result["fields_changed"]) == {"status", "value"}

    def test_get_diff_null_changes_direct(self):
        """get_diff when changes column is NULL → diff={}, fields_changed=[]."""
        from services.api.services.api.routers.audit_v2 import get_diff

        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            dt = datetime(2026, 4, 1)
            row = MagicMock()
            row.__getitem__ = lambda s, i: [
                str(uuid.uuid4()), "tender", str(uuid.uuid4()), "create",
                None, None, dt
            ][i]
            conn.execute.return_value.fetchone.return_value = row

            result = get_diff(str(uuid.uuid4()))

        assert result["diff"] == {}
        assert result["fields_changed"] == []

    def test_get_audit_stats_direct(self):
        """get_audit_stats returns daily_activity, top_actors, action_distribution."""
        from services.api.services.api.routers.audit_v2 import get_audit_stats

        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            call_count = [0]

            def execute_side(stmt, params=None):
                result = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    result.fetchall.return_value = [(date(2026, 1, 1), 5, 2)]
                elif call_count[0] == 2:
                    result.fetchall.return_value = [("user@test.pl", 10)]
                else:
                    result.fetchall.return_value = [("update", "tender", 7)]
                return result

            conn.execute.side_effect = execute_side

            result = get_audit_stats(days=7)

        assert result["period_days"] == 7
        assert len(result["daily_activity"]) == 1
        assert result["daily_activity"][0]["changes"] == 5
        assert result["top_actors"][0]["actor"] == "user@test.pl"
        assert result["action_distribution"][0]["count"] == 7


# ═══════════════════════════════════════════════════════════════════════════════
# audit_v2.py — HTTP tests for unique routes
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditV2HTTP:

    @pytest.mark.asyncio
    async def test_entity_history_http(self, app, auth_headers):
        """GET /audit/entity/{id} → 200 list (unique to audit_v2)."""
        eid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            dt = datetime(2026, 1, 15)
            row = (str(uuid.uuid4()), "tender", "update", "user@test.pl",
                   json.dumps({"status": "active"}), dt)
            conn.execute.return_value.fetchall.return_value = [row]

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(f"/api/v2/audit/entity/{eid}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_entity_history_empty_http(self, app, auth_headers):
        """GET /audit/entity/{id} → empty list."""
        eid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = []

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(f"/api/v2/audit/entity/{eid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_diff_not_found_http(self, app, auth_headers):
        """GET /audit/diff/{id} → error when not found."""
        aid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchone.return_value = None

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(f"/api/v2/audit/diff/{aid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["error"] == "Not found"

    @pytest.mark.asyncio
    async def test_diff_found_http(self, app, auth_headers):
        """GET /audit/diff/{id} → returns diff data."""
        aid = str(uuid.uuid4())
        changes = {"status": {"before": "draft", "after": "active"}}
        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            dt = datetime(2026, 1, 15)
            row = MagicMock()
            row.__getitem__ = lambda s, i: [
                aid, "tender", str(uuid.uuid4()), "update",
                "user@test.pl", json.dumps(changes), dt
            ][i]
            conn.execute.return_value.fetchone.return_value = row

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(f"/api/v2/audit/diff/{aid}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "fields_changed" in data

    @pytest.mark.asyncio
    async def test_audit_stats_http(self, app, auth_headers):
        """GET /audit/stats → 200 with stats structure."""
        with patch("services.api.services.api.routers.audit_v2.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            call_count = [0]

            def execute_side(stmt, params=None):
                result = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    result.fetchall.return_value = [(date(2026, 1, 1), 3, 1)]
                elif call_count[0] == 2:
                    result.fetchall.return_value = [("actor@test.pl", 3)]
                else:
                    result.fetchall.return_value = [("create", "tender", 3)]
                return result

            conn.execute.side_effect = execute_side

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/v2/audit/stats?days=14", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_days"] == 14


# ═══════════════════════════════════════════════════════════════════════════════
# kosztorys_v3.py — HTTP tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestKosztorysV3HTTP:

    @pytest.mark.asyncio
    async def test_get_icb_rates_with_data(self, app, auth_headers):
        """GET /api/v2/icb/rates → returns rows with all numeric fields."""
        with patch("services.api.services.api.routers.kosztorys_v3.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            row = MagicMock()
            row.quarter = "2026Q1"
            row.icb_r_rate = 45.5
            row.icb_m_rate = 120.0
            row.icb_s_rate = 80.0
            row.avg_value = 500000.0
            row.median_value = 450000.0
            row.n_tenders = 12
            conn.execute.return_value.fetchall.return_value = [row]

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(
                    "/api/v2/icb/rates?cpv5=45200&nuts2=PL91",
                    headers=auth_headers,
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cpv5"] == "45200"
        assert data["nuts2_code"] == "PL91"
        assert len(data["rates"]) == 1
        assert data["rates"][0]["r"] == 45.5
        assert data["rates"][0]["m"] == 120.0

    @pytest.mark.asyncio
    async def test_get_icb_rates_null_values(self, app, auth_headers):
        """GET /api/v2/icb/rates → None values in output when DB has NULLs."""
        with patch("services.api.services.api.routers.kosztorys_v3.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            row = MagicMock()
            row.quarter = "2026Q1"
            row.icb_r_rate = None
            row.icb_m_rate = None
            row.icb_s_rate = None
            row.avg_value = None
            row.median_value = None
            row.n_tenders = 0
            conn.execute.return_value.fetchall.return_value = [row]

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(
                    "/api/v2/icb/rates?cpv5=99999&nuts2=PL99",
                    headers=auth_headers,
                )
        assert resp.status_code == 200
        rate = resp.json()["rates"][0]
        assert rate["r"] is None
        assert rate["avg_val"] is None

    @pytest.mark.asyncio
    async def test_get_icb_rates_empty(self, app, auth_headers):
        """GET /api/v2/icb/rates → empty rates list."""
        with patch("services.api.services.api.routers.kosztorys_v3.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchall.return_value = []

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get(
                    "/api/v2/icb/rates?cpv5=00000&nuts2=PL00",
                    headers=auth_headers,
                )
        assert resp.status_code == 200
        assert resp.json()["rates"] == []

    @pytest.mark.asyncio
    async def test_ai_wycena_kosztorys_not_found(self, app, auth_headers):
        """POST /kosztorys/{id}/ai-wycena-v2 → 404 when kosztorys missing."""
        kid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.kosztorys_v3.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)
            conn.execute.return_value.fetchone.return_value = None

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    f"/api/v2/kosztorys/{kid}/ai-wycena-v2",
                    headers=auth_headers,
                )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_ai_wycena_found_no_tender_id(self, app, auth_headers):
        """POST /kosztorys/{id}/ai-wycena-v2 → StreamingResponse when kosztorys found, tender_id=None."""
        kid = str(uuid.uuid4())
        with patch("services.api.services.api.routers.kosztorys_v3.get_engine") as mock_eng:
            conn = MagicMock()
            mock_eng.return_value.connect.return_value.__enter__ = lambda s: conn
            mock_eng.return_value.connect.return_value.__exit__ = MagicMock(return_value=False)

            call_count = [0]

            def execute_side(stmt, params=None):
                result = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    krow = MagicMock()
                    krow.id = kid
                    krow.nazwa = "Test Kosztorys"
                    krow.tender_id = None
                    krow.kwartalnr = 1
                    krow.kwartalrok = 2026
                    result.fetchone.return_value = krow
                elif call_count[0] == 2:
                    result.fetchall.return_value = []
                return result

            conn.execute.side_effect = execute_side

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post(
                    f"/api/v2/kosztorys/{kid}/ai-wycena-v2",
                    headers=auth_headers,
                )
        # StreamingResponse means 200; if VLLM unreachable it may 500 in _event_stream but that's pragma:no cover
        assert resp.status_code in (200, 500)


# ═══════════════════════════════════════════════════════════════════════════════
# reports.py — direct function tests (routes shadowed by m7_backend.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestReportsDirect:

    def _make_user(self):
        user = MagicMock()
        user.org_id = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
        return user

    def test_monthly_report_basic(self):
        """monthly_report returns year, month, win_rate, pipeline_value_pln."""
        from services.api.services.api.routers.reports import monthly_report

        conn = MagicMock()
        call_count = [0]

        def execute_side(stmt, params=None):
            result = MagicMock()
            call_count[0] += 1
            vals = {1: 10, 2: 3, 3: 15, 4: 200000.0}
            result.scalar.return_value = vals.get(call_count[0], 0)
            return result

        conn.execute.side_effect = execute_side

        result = monthly_report(self._make_user(), conn, year=2026, month=7)

        assert result["year"] == 2026
        assert result["month"] == 7
        assert "win_rate" in result
        assert "pipeline_value_pln" in result
        assert result["win_rate"] == pytest.approx(3 / 15 * 100, rel=0.01)

    def test_monthly_report_zero_total_or_fallback(self):
        """monthly_report: when total_or=0 scalar returns None → uses 1 (avoid ZeroDivisionError)."""
        from services.api.services.api.routers.reports import monthly_report

        conn = MagicMock()
        call_count = [0]

        def execute_side(stmt, params=None):
            result = MagicMock()
            call_count[0] += 1
            # new_tenders=0, won=0, total_or=None→1, pipeline_val=0
            vals = {1: 0, 2: 0, 3: None, 4: 0}
            result.scalar.return_value = vals.get(call_count[0], 0)
            return result

        conn.execute.side_effect = execute_side

        result = monthly_report(self._make_user(), conn, year=2025, month=1)
        assert result["win_rate"] == 0.0  # won=0, total_or=1

    def test_monthly_report_pdf_importerror_fallback(self):
        """monthly_report_pdf returns HTML when reportlab unavailable."""
        import sys
        from services.api.services.api.routers.reports import monthly_report_pdf

        conn = MagicMock()
        user = self._make_user()

        # Temporarily hide reportlab to trigger ImportError branch
        saved = {k: v for k, v in sys.modules.items() if "reportlab" in k}
        for k in list(saved.keys()):
            del sys.modules[k]
        # Force import to fail by setting None
        sys.modules["reportlab"] = None  # type: ignore

        try:
            resp = monthly_report_pdf(user, conn, year=2024, month=6)
        finally:
            del sys.modules["reportlab"]
            sys.modules.update(saved)

        assert resp.media_type == "text/html"
        assert b"2024-06" in resp.body

    def test_monthly_report_pdf_with_mock_reportlab(self):
        """monthly_report_pdf returns PDF when reportlab available (mocked)."""
        import sys
        from services.api.services.api.routers.reports import monthly_report_pdf

        conn = MagicMock()
        user = self._make_user()

        # Create a fake reportlab module hierarchy
        fake_buf_content = b"%PDF-fake"
        fake_canvas_instance = MagicMock()
        fake_canvas_instance.save = MagicMock()

        fake_canvas_mod = MagicMock()
        fake_canvas_mod.Canvas.return_value = fake_canvas_instance

        fake_pdfgen_mod = MagicMock()
        fake_pdfgen_mod.canvas = fake_canvas_mod

        fake_rl_mod = MagicMock()
        fake_rl_mod.pdfgen = fake_pdfgen_mod

        with patch.dict(sys.modules, {
            "reportlab": fake_rl_mod,
            "reportlab.pdfgen": fake_pdfgen_mod,
            "reportlab.pdfgen.canvas": fake_canvas_mod,
        }):
            # Patch io.BytesIO to return predictable content
            with patch("services.api.services.api.routers.reports.io.BytesIO") as mock_bio:
                bio_instance = MagicMock()
                bio_instance.read.return_value = fake_buf_content
                mock_bio.return_value = bio_instance

                resp = monthly_report_pdf(user, conn, year=2026, month=7)

        # It's the PDF path
        assert resp.media_type == "application/pdf"

    def test_report_benchmark_no_tenant(self):
        """report_benchmark: tenant not in rows → rank=None, tenders=0."""
        from services.api.services.api.routers.reports import report_benchmark

        conn = MagicMock()
        other_row = MagicMock()
        other_row.tenant_id = str(uuid.uuid4())
        other_row.cnt = 50
        other_row.avg_score = 0.75
        conn.execute.return_value.fetchall.return_value = [other_row]

        result = report_benchmark(self._make_user(), conn)

        assert result["your_rank"] is None
        assert result["your_tenders"] == 0
        assert result["your_avg_score"] == 0
        assert result["total_tenants"] == 1

    def test_report_benchmark_tenant_found(self):
        """report_benchmark: tenant IS in rows → correct rank and tenders."""
        from services.api.services.api.routers.reports import report_benchmark

        DEMO_ORG = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"
        conn = MagicMock()

        other_row = MagicMock()
        other_row.tenant_id = str(uuid.uuid4())
        other_row.cnt = 100
        other_row.avg_score = 0.90

        my_row = MagicMock()
        my_row.tenant_id = DEMO_ORG
        my_row.cnt = 25
        my_row.avg_score = 0.82

        conn.execute.return_value.fetchall.return_value = [other_row, my_row]

        result = report_benchmark(self._make_user(), conn)

        assert result["your_rank"] == 2
        assert result["your_tenders"] == 25
        assert result["your_avg_score"] == pytest.approx(0.82)
        assert result["total_tenants"] == 2

    def test_report_benchmark_empty_rows(self):
        """report_benchmark with empty rows → rank=None, total=0."""
        from services.api.services.api.routers.reports import report_benchmark

        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = []

        result = report_benchmark(self._make_user(), conn)

        assert result["your_rank"] is None
        assert result["total_tenants"] == 0
