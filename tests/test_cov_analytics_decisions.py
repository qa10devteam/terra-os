"""Coverage tests for analytics_v2 and decisions_v2 routers.

Targets:
  analytics_v2.py  — lines 145-201, 268-285
  decisions_v2.py  — lines 65-99, 128-138, 149-158, 160-163, 165-168, 170-178
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _user(org_id: str = TENANT_ID):
    u = MagicMock()
    u.org_id = org_id
    return u


def _make_conn(rows_by_key: dict | None = None):
    """Build a mock connection whose execute() looks up rows by SQL substring."""
    rows_by_key = rows_by_key or {}
    conn = MagicMock()

    def _execute(stmt, params=None):
        sql = str(stmt)
        for key, rows in rows_by_key.items():
            if key in sql:
                res = MagicMock()
                res.fetchall.return_value = rows
                res.fetchone.return_value = rows[0] if rows else None
                res.scalar.return_value = rows[0] if rows else None
                return res
        # Default — empty result
        res = MagicMock()
        res.fetchall.return_value = []
        res.fetchone.return_value = None
        res.scalar.return_value = None
        return res

    conn.execute = MagicMock(side_effect=_execute)
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.commit = MagicMock()
    return conn


def _engine(rows_by_key: dict | None = None):
    engine = MagicMock()
    conn = _make_conn(rows_by_key)
    engine.connect.return_value = conn
    engine.begin.return_value = conn
    return engine


# ═══════════════════════════════════════════════════════════════════════════════
# analytics_v2  — calc_win_probability  (lines 146-159)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCalcWinProbability:
    def test_returns_probability(self):
        from services.api.services.api.routers.analytics_v2 import calc_win_probability
        import services.api.services.api.analytics as _analytics_pkg

        mock_fn = MagicMock(return_value={"win_probability": 0.42})
        orig = getattr(_analytics_pkg, "estimate_win_probability", None)
        _analytics_pkg.estimate_win_probability = mock_fn
        try:
            result = calc_win_probability(
                current_user=_user(),
                markup=15.0,
                n_competitors=3,
                cpv="45000000",
            )
            assert "win_probability" in result
        finally:
            if orig is not None:
                _analytics_pkg.estimate_win_probability = orig
            else:
                delattr(_analytics_pkg, "estimate_win_probability")

    def test_calls_with_correct_params(self):
        from services.api.services.api.routers.analytics_v2 import calc_win_probability
        import services.api.services.api.analytics as _ap

        mock_fn = MagicMock(return_value={"win_probability": 0.55})
        orig = getattr(_ap, "estimate_win_probability", None)
        _ap.estimate_win_probability = mock_fn
        try:
            calc_win_probability(
                current_user=_user(),
                markup=20.0,
                n_competitors=5,
                cpv="",
            )
            mock_fn.assert_called_once_with(
                markup_pct=20.0, n_competitors=5, cpv=""
            )
        finally:
            if orig is not None:
                _ap.estimate_win_probability = orig


# ═══════════════════════════════════════════════════════════════════════════════
# analytics_v2  — get_recommendation  (lines 162-193)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetRecommendation:
    def _mock_analytics(self):
        import services.api.services.api.analytics as _ap
        mock_fn = MagicMock(return_value={"action": "GO", "confidence": 0.8})
        orig = getattr(_ap, "generate_recommendation", None)
        _ap.generate_recommendation = mock_fn
        return _ap, mock_fn, orig

    def _restore(self, ap, orig):
        if orig is not None:
            ap.generate_recommendation = orig
        else:
            try:
                delattr(ap, "generate_recommendation")
            except AttributeError:
                pass

    def test_no_tender_id(self):
        from services.api.services.api.routers.analytics_v2 import (
            get_recommendation,
            RecommendationRequest,
        )
        ap, mock_fn, orig = self._mock_analytics()
        try:
            body = RecommendationRequest(
                tender_id=None,
                cost_estimate=500000.0,
                n_competitors=4,
            )
            result = get_recommendation(body=body, current_user=_user())
            assert result["action"] == "GO"
            mock_fn.assert_called_once()
            call_kwargs = mock_fn.call_args.kwargs
            assert call_kwargs["red_flags"] == []
        finally:
            self._restore(ap, orig)

    def test_with_tender_id_db_success(self):
        from services.api.services.api.routers.analytics_v2 import (
            get_recommendation,
            RecommendationRequest,
        )
        ap, mock_fn, orig = self._mock_analytics()
        try:
            risk_row = MagicMock()
            risk_row.message = "High penalty clauses"
            risk_row.severity = "block"

            engine = _engine({"discrepancy": [risk_row]})
            body = RecommendationRequest(
                tender_id="tid-123",
                cost_estimate=1_000_000.0,
                n_competitors=2,
                cpv="45200000",
                region="mazowieckie",
            )
            with patch(
                "services.api.services.api.routers.analytics_v2.get_engine",
                return_value=engine,
            ):
                result = get_recommendation(body=body, current_user=_user())

            assert result["action"] == "GO"
            call_kwargs = mock_fn.call_args.kwargs
            assert len(call_kwargs["red_flags"]) == 1
            assert call_kwargs["red_flags"][0]["message"] == "High penalty clauses"
        finally:
            self._restore(ap, orig)

    def test_with_tender_id_db_error(self):
        """DB exception is swallowed; red_flags defaults to []."""
        from services.api.services.api.routers.analytics_v2 import (
            get_recommendation,
            RecommendationRequest,
        )
        ap, mock_fn, orig = self._mock_analytics()
        try:
            engine = MagicMock()
            engine.connect.side_effect = Exception("DB down")
            body = RecommendationRequest(
                tender_id="tid-bad",
                cost_estimate=200_000.0,
                n_competitors=3,
            )
            with patch(
                "services.api.services.api.routers.analytics_v2.get_engine",
                return_value=engine,
            ):
                result = get_recommendation(body=body, current_user=_user())

            assert "action" in result
            call_kwargs = mock_fn.call_args.kwargs
            assert call_kwargs["red_flags"] == []
        finally:
            self._restore(ap, orig)


# ═══════════════════════════════════════════════════════════════════════════════
# analytics_v2  — get_analytics_dashboard  (lines 196-266)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAnalyticsDashboard:
    def test_no_org_raises_403(self):
        from services.api.services.api.routers.analytics_v2 import get_analytics_dashboard

        with pytest.raises(HTTPException) as exc:
            get_analytics_dashboard(current_user=_user(org_id=None))
        assert exc.value.status_code == 403

    def test_success_path(self):
        from services.api.services.api.routers.analytics_v2 import get_analytics_dashboard

        pipeline_row = MagicMock()
        pipeline_row.active_bids = 5
        pipeline_row.pipeline_value = 1_500_000.0

        decision_row = MagicMock()
        decision_row.won = 3
        decision_row.total = 6

        funnel_row = MagicMock()
        funnel_row.status = "active"
        funnel_row.count = 5

        call_n = [0]
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)

        def _exe(stmt, params=None):
            call_n[0] += 1
            res = MagicMock()
            n = call_n[0]
            if n == 1:
                res.fetchone.return_value = pipeline_row
            elif n == 2:
                res.fetchone.return_value = decision_row
            else:
                res.fetchall.return_value = [funnel_row]
            return res

        conn.execute = MagicMock(side_effect=_exe)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch(
            "services.api.services.api.routers.analytics_v2.get_engine",
            return_value=engine,
        ):
            result = get_analytics_dashboard(current_user=_user())

        assert result["active_bids"] == 5
        assert result["pipeline_value"] == 1_500_000.0
        assert result["win_rate_pct"] == 50.0
        assert result["funnel"][0]["status"] == "active"

    def test_win_rate_zero_when_no_decisions(self):
        from services.api.services.api.routers.analytics_v2 import get_analytics_dashboard

        pipeline_row = MagicMock()
        pipeline_row.active_bids = 0
        pipeline_row.pipeline_value = 0.0

        decision_row = MagicMock()
        decision_row.won = 0
        decision_row.total = 0

        call_n = [0]
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)

        def _exe(stmt, params=None):
            call_n[0] += 1
            res = MagicMock()
            if call_n[0] == 1:
                res.fetchone.return_value = pipeline_row
            elif call_n[0] == 2:
                res.fetchone.return_value = decision_row
            else:
                res.fetchall.return_value = []
            return res

        conn.execute = MagicMock(side_effect=_exe)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch(
            "services.api.services.api.routers.analytics_v2.get_engine",
            return_value=engine,
        ):
            result = get_analytics_dashboard(current_user=_user())

        assert result["win_rate_pct"] == 0.0

    def test_db_exception_returns_error_dict(self):
        from services.api.services.api.routers.analytics_v2 import get_analytics_dashboard

        engine = MagicMock()
        engine.connect.side_effect = Exception("connection refused")

        with patch(
            "services.api.services.api.routers.analytics_v2.get_engine",
            return_value=engine,
        ):
            result = get_analytics_dashboard(current_user=_user())

        assert "error" in result
        assert result["pipeline_value"] == 0.0
        assert result["funnel"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# analytics_v2  — get_market_overview  (lines 268-337)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetMarketOverview:
    def test_success_path(self):
        from services.api.services.api.routers.analytics_v2 import get_market_overview

        totals_row = MagicMock()
        totals_row.__getitem__ = lambda self, i: [42, 8_000_000.0][i]

        cpv_row = MagicMock()
        cpv_row.__getitem__ = lambda self, i: ["45000000", 10][i]

        region_row = MagicMock()
        region_row.__getitem__ = lambda self, i: ["mazowieckie", 15][i]

        call_n = [0]
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)

        def _exe(stmt, params=None):
            call_n[0] += 1
            res = MagicMock()
            n = call_n[0]
            if n == 1:
                # year scalar
                res.scalar.return_value = 2024
            elif n == 2:
                # totals
                res.fetchone.return_value = totals_row
            elif n == 3:
                # top CPV
                res.fetchall.return_value = [cpv_row]
            else:
                # top regions
                res.fetchall.return_value = [region_row]
            return res

        conn.execute = MagicMock(side_effect=_exe)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch(
            "services.api.services.api.routers.analytics_v2.get_engine",
            return_value=engine,
        ):
            result = get_market_overview()

        assert result["total_tenders"] == 42
        assert result["total_value_pln"] == 8_000_000.0
        assert result["period"] == "2024"
        assert len(result["top_cpv"]) == 1
        assert len(result["top_regions"]) == 1

    def test_db_error_returns_fallback(self):
        from services.api.services.api.routers.analytics_v2 import get_market_overview

        engine = MagicMock()
        engine.connect.side_effect = Exception("timeout")

        with patch(
            "services.api.services.api.routers.analytics_v2.get_engine",
            return_value=engine,
        ):
            result = get_market_overview()

        assert "error" in result
        assert result["total_tenders"] == 0
        assert result["top_cpv"] == []

    def test_zero_tenders_avg_is_zero(self):
        from services.api.services.api.routers.analytics_v2 import get_market_overview

        totals_row = MagicMock()
        totals_row.__getitem__ = lambda self, i: [0, 0.0][i]

        call_n = [0]
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)

        def _exe(stmt, params=None):
            call_n[0] += 1
            res = MagicMock()
            n = call_n[0]
            if n == 1:
                res.scalar.return_value = 2023
            elif n == 2:
                res.fetchone.return_value = totals_row
            else:
                res.fetchall.return_value = []
            return res

        conn.execute = MagicMock(side_effect=_exe)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch(
            "services.api.services.api.routers.analytics_v2.get_engine",
            return_value=engine,
        ):
            result = get_market_overview()

        assert result["avg_per_tender"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# decisions_v2  — create_decision  (lines 65-168)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCreateDecision:
    def test_no_org_raises_403(self):
        from services.api.services.api.routers.decisions_v2 import (
            create_decision,
            DecisionCreate,
        )
        body = DecisionCreate(tender_id="t1", decision="GO")
        with pytest.raises(HTTPException) as exc:
            create_decision(body=body, user=_user(org_id=None))
        assert exc.value.status_code == 403

    def test_invalid_decision_raises_422(self):
        from services.api.services.api.routers.decisions_v2 import (
            create_decision,
            DecisionCreate,
        )
        body = DecisionCreate(tender_id="t1", decision="MAYBE")
        engine = _engine()
        with patch(
            "services.api.services.api.routers.decisions_v2.get_engine",
            return_value=engine,
        ):
            with pytest.raises(HTTPException) as exc:
                create_decision(body=body, user=_user())
        assert exc.value.status_code == 422

    def test_tender_not_found_raises_404(self):
        from services.api.services.api.routers.decisions_v2 import (
            create_decision,
            DecisionCreate,
        )
        body = DecisionCreate(tender_id="missing-tender", decision="GO")
        # connect() returns a conn where fetchone() is None
        engine = _engine()  # all queries return None by default
        with patch(
            "services.api.services.api.routers.decisions_v2.get_engine",
            return_value=engine,
        ):
            with pytest.raises(HTTPException) as exc:
                create_decision(body=body, user=_user())
        assert exc.value.status_code == 404

    def _setup_create_engine(self, decision_str: str, value_pln: float | None = None):
        """Return engine, request body and a mock result row for create_decision."""
        tender_row = MagicMock()
        tender_row.id = "tender-abc"
        tender_row.tenant_id = TENANT_ID

        result_row = MagicMock()
        result_row.id = str(uuid.uuid4())
        result_row.status = "approved" if decision_str == "GO" else "rejected"
        result_row.requested_at = datetime(2026, 1, 15, 10, 30)
        result_row.action = "bid_decision"
        result_row.payload = {
            "tender_id": "tender-abc",
            "decision": decision_str,
            "rationale": "",
            "org_id": TENANT_ID,
        }

        call_n = [0]
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.commit = MagicMock()

        def _exe(stmt, params=None):
            call_n[0] += 1
            res = MagicMock()
            n = call_n[0]
            if n == 1:
                # SELECT FROM tender (fetchone)
                res.fetchone.return_value = tender_row
            elif n == 2:
                # INSERT INTO approval_request (RETURNING)
                res.fetchone.return_value = result_row
            else:
                # UPDATE tender or escalation INSERT
                res.fetchone.return_value = None
                res.fetchall.return_value = []
            return res

        conn.execute = MagicMock(side_effect=_exe)
        engine = MagicMock()
        engine.connect.return_value = conn
        engine.begin.return_value = conn

        from services.api.services.api.routers.decisions_v2 import DecisionCreate
        body = DecisionCreate(
            tender_id="tender-abc",
            decision=decision_str,
            rationale="Test rationale",
            value_pln=value_pln,
        )
        return engine, body

    def test_create_go_decision(self):
        from services.api.services.api.routers.decisions_v2 import create_decision

        engine, body = self._setup_create_engine("GO")
        with patch(
            "services.api.services.api.routers.decisions_v2.get_engine",
            return_value=engine,
        ):
            result = create_decision(body=body, user=_user())

        assert result["decision"] == "GO"
        assert "id" in result
        assert "tender_id" in result

    def test_create_nogo_decision(self):
        from services.api.services.api.routers.decisions_v2 import create_decision

        engine, body = self._setup_create_engine("NO-GO")
        with patch(
            "services.api.services.api.routers.decisions_v2.get_engine",
            return_value=engine,
        ):
            result = create_decision(body=body, user=_user())

        assert result["decision"] == "NO-GO"

    def test_create_go_with_escalation(self):
        """GO + value_pln > 1_000_000 → escalation_created = True."""
        from services.api.services.api.routers.decisions_v2 import create_decision

        engine, body = self._setup_create_engine("GO", value_pln=2_000_000.0)
        with patch(
            "services.api.services.api.routers.decisions_v2.get_engine",
            return_value=engine,
        ):
            result = create_decision(body=body, user=_user())

        assert result.get("escalation") == "pending"

    def test_create_go_no_escalation_below_threshold(self):
        """GO + value_pln <= 1_000_000 → no escalation."""
        from services.api.services.api.routers.decisions_v2 import create_decision

        engine, body = self._setup_create_engine("GO", value_pln=500_000.0)
        with patch(
            "services.api.services.api.routers.decisions_v2.get_engine",
            return_value=engine,
        ):
            result = create_decision(body=body, user=_user())

        assert "escalation" not in result

    def test_nogo_variants(self):
        """NOGO and NO_GO are also valid."""
        from services.api.services.api.routers.decisions_v2 import create_decision

        for variant in ("NOGO", "NO_GO"):
            engine, body = self._setup_create_engine(variant)
            body.decision = variant  # override
            with patch(
                "services.api.services.api.routers.decisions_v2.get_engine",
                return_value=engine,
            ):
                result = create_decision(body=body, user=_user())
            assert result["decision"] == variant


# ═══════════════════════════════════════════════════════════════════════════════
# decisions_v2  — get_decision  (lines 170-198)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetDecision:
    def test_not_found_raises_404(self):
        from services.api.services.api.routers.decisions_v2 import get_decision

        engine = _engine()  # fetchone returns None
        with patch(
            "services.api.services.api.routers.decisions_v2.get_engine",
            return_value=engine,
        ):
            with pytest.raises(HTTPException) as exc:
                get_decision(decision_id="no-such-id", user=_user())
        assert exc.value.status_code == 404

    def test_found_returns_dict(self):
        from services.api.services.api.routers.decisions_v2 import get_decision

        row = MagicMock()
        row.id = str(uuid.uuid4())
        row.status = "approved"
        row.requested_at = datetime(2026, 3, 10, 8, 0)
        row.decided_at = None
        row.payload = {
            "tender_id": "t-99",
            "decision": "GO",
            "rationale": "Looks good",
        }

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        res = MagicMock()
        res.fetchone.return_value = row
        conn.execute = MagicMock(return_value=res)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch(
            "services.api.services.api.routers.decisions_v2.get_engine",
            return_value=engine,
        ):
            result = get_decision(decision_id=str(row.id), user=_user())

        assert result["id"] == str(row.id)
        assert result["decision"] == "GO"
        assert result["tender_id"] == "t-99"
        assert result["status"] == "approved"
        assert result["decided_at"] is None

    def test_found_with_decided_at(self):
        from services.api.services.api.routers.decisions_v2 import get_decision

        row = MagicMock()
        row.id = str(uuid.uuid4())
        row.status = "rejected"
        row.requested_at = datetime(2026, 4, 1, 12, 0)
        row.decided_at = datetime(2026, 4, 2, 9, 0)
        row.payload = {"tender_id": "t-42", "decision": "NO-GO", "rationale": ""}

        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        res = MagicMock()
        res.fetchone.return_value = row
        conn.execute = MagicMock(return_value=res)
        engine = MagicMock()
        engine.connect.return_value = conn

        with patch(
            "services.api.services.api.routers.decisions_v2.get_engine",
            return_value=engine,
        ):
            result = get_decision(decision_id=str(row.id), user=_user())

        assert result["decided_at"] == "2026-04-02T09:00:00"
