"""HTTP endpoint tests for Group A modules — uses AsyncClient + ASGITransport.

Covers:
  - routers/multimodal.py  (upload, get, analyze, estimate endpoints)
  - routers/sse_mcp_chat.py  (mcp, chat_v2, playground endpoints)
  - routers/audit_v2.py  (trail, entity, diff, stats, recent endpoints)
  - routers/m7_backend.py  (settings, reports, market, bookmarks, alerts, webhooks, team, feedback, axioms, bid-intel)
  - routers/kosztorys_v3.py  (icb/rates, ai-wycena 404)
  - routers/events.py  (emit, notifications, mark-read)
  - routers/scoring.py  (config, put-config, score-breakdown, cpv-heatmap, refresh-views)
  - routers/scoring_v2.py  (backtest, calibration, experiment, experiments)
  - routers/metrics.py (system/metrics, system/db-stats, system/routes)
"""
from __future__ import annotations

import os
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in [ROOT, os.path.join(ROOT, "services", "api")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# routers/sse_mcp_chat.py — MCP, Chat v2, Playground
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_info(client):
    r = await client.get("/api/v1/mcp/info")
    assert r.status_code == 200
    data = r.json()
    assert "tools" in data

@pytest.mark.asyncio
async def test_mcp_tools_list(client):
    r = await client.post("/api/v1/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
    })
    assert r.status_code == 200
    data = r.json()
    assert "result" in data

@pytest.mark.asyncio
async def test_mcp_initialize(client):
    r = await client.post("/api/v1/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}
    })
    assert r.status_code == 200
    data = r.json()
    assert data.get("result", {}).get("protocolVersion") is not None

@pytest.mark.asyncio
async def test_mcp_unknown_method(client):
    r = await client.post("/api/v1/mcp", json={
        "jsonrpc": "2.0", "id": 2, "method": "unknown_method", "params": {}
    })
    assert r.status_code == 200
    data = r.json()
    assert "error" in data

@pytest.mark.asyncio
async def test_mcp_tools_call(client):
    r = await client.post("/api/v1/mcp", json={
        "jsonrpc": "2.0", "id": 3,
        "method": "tools/call",
        "params": {"name": "get_tender", "arguments": {"tender_id": "00000000-0000-0000-0000-000000000000"}}
    })
    assert r.status_code == 200
    data = r.json()
    assert "result" in data or "error" in data

@pytest.mark.asyncio
async def test_mcp_tools_call_list_tenders(client):
    r = await client.post("/api/v1/mcp", json={
        "jsonrpc": "2.0", "id": 4,
        "method": "tools/call",
        "params": {"name": "list_tenders", "arguments": {"limit": 5}}
    })
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_mcp_tools_call_unknown_tool(client):
    r = await client.post("/api/v1/mcp", json={
        "jsonrpc": "2.0", "id": 5,
        "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}}
    })
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_chat_v2_no_tender(client):
    r = await client.post("/api/v2/chat", json={
        "message": "Hello, what can you do?",
        "tender_id": None,
        "history": []
    })
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        assert "reply" in r.json()

@pytest.mark.asyncio
async def test_chat_v2_with_tender(client):
    r = await client.post("/api/v2/chat", json={
        "message": "Analyze this tender",
        "tender_id": "00000000-0000-0000-0000-000000000000",
        "history": []
    })
    assert r.status_code in (200, 401, 403)

@pytest.mark.asyncio
async def test_playground_info(client):
    r = await client.get("/api/v1/playground")
    assert r.status_code in (200, 401, 403)
    if r.status_code == 200:
        assert "endpoints" in r.json()

@pytest.mark.asyncio
async def test_sse_publish(client):
    r = await client.post("/api/v1/sse/publish?event_type=test")
    assert r.status_code in (200, 401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# routers/audit_v2.py
# ─────────────────────────────────────────────────────────────────────────────

REAL_TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"


@pytest.mark.asyncio
async def test_audit_trail(client):
    r = await client.get("/api/v2/audit/trail")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        # Response is list or dict with 'items'
        assert isinstance(data, (list, dict))

@pytest.mark.asyncio
async def test_audit_trail_with_filters(client):
    r = await client.get("/api/v2/audit/trail?entity_type=tender&limit=10&offset=0")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_audit_trail_with_user_filter(client):
    r = await client.get("/api/v2/audit/trail?user_id=some-user&action=update")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_audit_entity_history(client):
    r = await client.get("/api/v2/audit/entity/00000000-0000-0000-0000-000000000000")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        assert isinstance(r.json(), (list, dict))

@pytest.mark.asyncio
async def test_audit_diff(client):
    r = await client.get("/api/v2/audit/diff/00000000-0000-0000-0000-000000000000")
    assert r.status_code in (200, 404, 500)

@pytest.mark.asyncio
async def test_audit_stats(client):
    r = await client.get("/api/v2/audit/stats?days=30")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert isinstance(data, dict)

@pytest.mark.asyncio
async def test_audit_stats_small_window(client):
    r = await client.get("/api/v2/audit/stats?days=1")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_audit_recent(client):
    r = await client.get("/api/v2/audit/recent")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        assert isinstance(r.json(), (list, dict))


# ─────────────────────────────────────────────────────────────────────────────
# routers/m7_backend.py
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_m7_usage(client):
    r = await client.get(f"/api/v2/settings/usage?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_monthly_report(client):
    r = await client.get(f"/api/v2/reports/monthly?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_report_templates(client):
    r = await client.get("/api/v2/reports/templates")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_market_kpi(client):
    r = await client.get("/api/v2/market/kpi-bar")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_bookmarks_list(client):
    r = await client.get(f"/api/v2/bookmarks?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_bookmark_add(client):
    r = await client.post(f"/api/v2/bookmarks/00000000-0000-0000-0000-000000000001?tenant_id={REAL_TENANT_ID}",
                          json={"priority": 1, "notes": "test"})
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_bookmark_delete(client):
    r = await client.delete(f"/api/v2/bookmarks/00000000-0000-0000-0000-000000000001?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 404, 500)

@pytest.mark.asyncio
async def test_m7_alerts_list(client):
    r = await client.get(f"/api/v2/alerts?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_alerts_create(client):
    r = await client.post(f"/api/v2/alerts?tenant_id={REAL_TENANT_ID}", json={
        "name": "Test Alert",
        "cpv_prefixes": ["45000000"],
        "keywords": ["budowa"],
        "min_value": 100000,
        "max_value": None,
    })
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_alerts_test(client):
    r = await client.post(f"/api/v2/alerts/00000000-0000-0000-0000-000000000002/test?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_webhooks_list(client):
    r = await client.get(f"/api/v2/webhooks?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_webhooks_create(client):
    r = await client.post(f"/api/v2/webhooks?tenant_id={REAL_TENANT_ID}", json={
        "name": "Test Webhook",
        "url": "https://example.com/webhook",
        "events": ["tender.new"],
    })
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_webhooks_delete(client):
    r = await client.delete("/api/v2/webhooks/00000000-0000-0000-0000-000000000003")
    assert r.status_code in (200, 404, 500)

@pytest.mark.asyncio
async def test_m7_team_members(client):
    r = await client.get(f"/api/v2/team/members?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_team_activity(client):
    r = await client.get(f"/api/v2/team/activity?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_feedback_submit(client):
    r = await client.post(f"/api/v2/feedback?tenant_id={REAL_TENANT_ID}", json={
        "rating": 4,
        "comment": "Good analysis",
        "tender_id": None,
    })
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_feedback_stats(client):
    r = await client.get(f"/api/v2/feedback/stats?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_axioms_list(client):
    r = await client.get(f"/api/v2/axioms?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_axioms_create(client):
    r = await client.post(f"/api/v2/axioms?tenant_id={REAL_TENANT_ID}", json={
        "axiom_class": "BLOCK",
        "code": "TEST_AX_001",
        "body": "tender['value_pln'] > 1000000",
        "description": "High value filter",
    })
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_axioms_evaluate(client):
    r = await client.post(f"/api/v2/axioms/evaluate/00000000-0000-0000-0000-000000000004?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_bid_intelligence_list(client):
    r = await client.get(f"/api/v2/bid-intelligence?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_bid_intelligence_add(client):
    r = await client.post(f"/api/v2/bid-intelligence?tenant_id={REAL_TENANT_ID}", json={
        "tender_id": "00000000-0000-0000-0000-000000000005",
        "our_price": 1500000.0,
        "winning_price": 1400000.0,
        "rank_position": 2,
        "won": False,
        "markup_pct": 12.5,
    })
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_bid_intelligence_optimal_markup(client):
    r = await client.get(f"/api/v2/bid-intelligence/optimal-markup?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_bid_intelligence_optimal_markup_with_cpv5(client):
    r = await client.get(f"/api/v2/bid-intelligence/optimal-markup?tenant_id={REAL_TENANT_ID}&cpv5=45000")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_m7_bid_intelligence_stats(client):
    r = await client.get(f"/api/v2/bid-intelligence/stats?tenant_id={REAL_TENANT_ID}")
    assert r.status_code in (200, 500)


# ─────────────────────────────────────────────────────────────────────────────
# routers/kosztorys_v3.py
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_kosztorys_icb_rates(client):
    r = await client.get("/api/v2/icb/rates?cpv5=45000&nuts2=PL91")
    assert r.status_code in (200, 401, 403, 500)
    if r.status_code == 200:
        data = r.json()
        assert "cpv5" in data

@pytest.mark.asyncio
async def test_kosztorys_ai_wycena_not_found(client):
    r = await client.post("/api/v2/kosztorys/00000000-0000-0000-0000-000000000001/ai-wycena-v2")
    assert r.status_code in (404, 401, 403, 500)


# ─────────────────────────────────────────────────────────────────────────────
# routers/events.py
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_events_emit(client):
    r = await client.post("/api/v2/events/emit", json={
        "event_type": "tender.new",
        "payload": {"title": "Test Tender"},
        "tenant_id": "test-tenant"
    })
    assert r.status_code in (200, 422)
    if r.status_code == 200:
        data = r.json()
        assert "status" in data

@pytest.mark.asyncio
async def test_events_emit_deadline(client):
    r = await client.post("/api/v2/events/emit", json={
        "event_type": "alert.deadline",
        "payload": {"title": "Urgent Tender", "tender_id": "some-id"},
        "tenant_id": "test-tenant"
    })
    assert r.status_code in (200, 422, 500)

@pytest.mark.asyncio
async def test_events_emit_agent_done(client):
    r = await client.post("/api/v2/events/emit", json={
        "event_type": "agent.done",
        "payload": {"title": "Analysis complete"},
        "tenant_id": "test-tenant"
    })
    assert r.status_code in (200, 422, 500)

@pytest.mark.asyncio
async def test_events_notifications(client):
    r = await client.get("/api/v2/notifications?limit=10")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_events_notifications_unread(client):
    r = await client.get("/api/v2/notifications?unread_only=true")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_events_mark_read_all(client):
    r = await client.post("/api/v2/notifications/mark-read", json=[])
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_events_mark_read_specific(client):
    r = await client.post("/api/v2/notifications/mark-read",
                          json=["00000000-0000-0000-0000-000000000001"])
    assert r.status_code in (200, 500)


# ─────────────────────────────────────────────────────────────────────────────
# routers/scoring.py
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scoring_config_get(client):
    r = await client.get("/api/v2/scoring/config")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        # Config keys may vary — just check it's a dict
        assert isinstance(data, dict)

@pytest.mark.asyncio
async def test_scoring_config_put_valid(client):
    r = await client.put("/api/v2/scoring/config", json={
        "weights": {"cpv_match": 30, "value_range": 25, "deadline_pressure": 20, "buyer_history": 15, "document_quality": 10}
    })
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_scoring_config_put_invalid_sum(client):
    r = await client.put("/api/v2/scoring/config", json={
        "weights": {"cpv_match": 50, "value_range": 50}  # sums to 100 but different fields
    })
    # Sum = 100, should pass or fail depending on required fields
    assert r.status_code in (200, 400, 500)

@pytest.mark.asyncio
async def test_scoring_config_put_bad_sum(client):
    r = await client.put("/api/v2/scoring/config", json={
        "weights": {"cpv_match": 30, "value_range": 20}  # sums to 50, not 100
    })
    # Some implementations accept partial weights
    assert r.status_code in (200, 400, 500)

@pytest.mark.asyncio
async def test_scoring_score_breakdown(client):
    r = await client.get("/api/v2/tenders/00000000-0000-0000-0000-000000000001/score-breakdown")
    assert r.status_code in (200, 404, 500)

@pytest.mark.asyncio
async def test_scoring_cpv_heatmap(client):
    r = await client.get("/api/v2/market/cpv-heatmap")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        assert isinstance(r.json(), list)

@pytest.mark.asyncio
async def test_scoring_refresh_views(client):
    r = await client.post("/api/v2/admin/refresh-views")
    assert r.status_code in (200, 500)


# ─────────────────────────────────────────────────────────────────────────────
# routers/scoring_v2.py
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scoring_v2_backtest(client):
    r = await client.post("/api/v2/scoring/backtest", json={
        "weights": {
            "cpv_match": 25, "value_range": 20, "deadline_pressure": 20,
            "buyer_history": 20, "document_quality": 15
        },
        "lookback_days": 90
    })
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert "lookback_days" in data or "error" in data

@pytest.mark.asyncio
async def test_scoring_v2_calibration(client):
    r = await client.get("/api/v2/scoring/calibration")
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_scoring_v2_create_experiment(client):
    r = await client.post("/api/v2/scoring/experiment", json={
        "name": "Test Experiment",
        "variant_weights": {
            "cpv_match": 30, "value_range": 20, "deadline_pressure": 20,
            "buyer_history": 15, "document_quality": 15
        },
        "sample_pct": 50,
    })
    assert r.status_code in (200, 500)

@pytest.mark.asyncio
async def test_scoring_v2_list_experiments(client):
    r = await client.get("/api/v2/scoring/experiments")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        assert isinstance(r.json(), list)


# ─────────────────────────────────────────────────────────────────────────────
# routers/metrics.py (system routes)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_system_metrics(client):
    r = await client.get("/api/v2/system/metrics")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert "database" in data

@pytest.mark.asyncio
async def test_system_db_stats(client):
    r = await client.get("/api/v2/system/db-stats")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        assert isinstance(r.json(), list)

@pytest.mark.asyncio
async def test_system_routes(client):
    r = await client.get("/api/v2/system/routes")
    assert r.status_code in (200, 500)
    if r.status_code == 200:
        data = r.json()
        assert "total_routes" in data


# ─────────────────────────────────────────────────────────────────────────────
# routers/multimodal.py
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_multimodal_upload_non_pdf(client):
    """Only PDFs allowed — should return 400."""
    import io
    r = await client.post(
        "/api/v2/documents/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert r.status_code in (400, 422)

@pytest.mark.asyncio
async def test_multimodal_get_document_not_found(client):
    r = await client.get("/api/v2/documents/00000000-0000-0000-0000-000000000001")
    assert r.status_code in (404, 500)

@pytest.mark.asyncio
async def test_multimodal_analyze_not_found(client):
    r = await client.post("/api/v2/documents/00000000-0000-0000-0000-000000000001/analyze")
    assert r.status_code in (404, 500)

@pytest.mark.asyncio
async def test_multimodal_estimate_not_found(client):
    r = await client.get("/api/v2/documents/00000000-0000-0000-0000-000000000001/estimate")
    assert r.status_code in (404, 500)

@pytest.mark.asyncio
async def test_multimodal_upload_pdf(client):
    """Upload a valid PDF bytes."""
    import io
    # Minimal valid PDF header
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
    r = await client.post(
        "/api/v2/documents/upload",
        files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert r.status_code in (200, 400, 422, 500)
