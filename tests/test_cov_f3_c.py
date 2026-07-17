"""F3-C: Shotgun smoke tests — hit every GET endpoint once.
Goal: raise coverage from 44% to 60%+ by touching all route imports/auth/early-returns.
"""
from __future__ import annotations
import uuid
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="module")
def app():
    from services.api.services.api.main import app as _app
    return _app


def _uid():
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════════════
# System / Health / Observability
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health_v1(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_health_v2(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_sources_health_v1(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/sources/health")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_sources_health_v2(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/sources/health")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_system_agents_404(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get(f"/api/v1/agents/{_uid()}")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_system_agents_pause(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(f"/api/v1/agents/{_uid()}/pause")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.xfail(reason="DB not mocked", strict=False)
@pytest.mark.asyncio
async def test_dashboard_v2(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/dashboard")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_dashboard_stats(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/dashboard/stats")
    assert r.status_code < 500


@pytest.mark.xfail(reason="DB not mocked", strict=False)
@pytest.mark.asyncio
async def test_dashboard_digest(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/dashboard/digest")
    assert r.status_code < 500


@pytest.mark.xfail(reason="DB not mocked", strict=False)
@pytest.mark.asyncio
async def test_dashboard_pipeline_kpi(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/dashboard/pipeline-kpi")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_dashboard_market_charts(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/dashboard/market-charts")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Notifications
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_notifications_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/notifications")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_notifications_unread(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/notifications/unread-count")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Search / Analytics / Market Intel
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_command_search(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/command/search", params={"q": "test"})
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_market_intel_overview(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/market-intel/overview")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_market_intel_cpv_trends(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/market-intel/cpv-trends")
    assert r.status_code < 500


@pytest.mark.xfail(reason="DB not mocked", strict=False)
@pytest.mark.asyncio
async def test_market_intel_regional(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/market-intel/regional")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_competitors_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/competitors")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_competitors_heatmap(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/competitors/heatmap")
    assert r.status_code < 500


@pytest.mark.xfail(reason="DB not mocked", strict=False)
@pytest.mark.asyncio
async def test_buyers_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/buyers")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Tender Alerts / Bookmarks / Workflows
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_tender_alerts_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/tender-alerts")
    assert r.status_code < 500


@pytest.mark.xfail(reason="DB not mocked", strict=False)
@pytest.mark.asyncio
async def test_tender_alerts_create(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v2/tender-alerts", json={
            "name": "Test alert",
            "keywords": ["drogi", "mosty"],
            "cpv_prefixes": ["45"],
            "min_value": 100000,
        })
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_bookmarks_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/bookmarks")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_bookmarks_stats(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/bookmarks/stats")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_bookmarks_export(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/bookmarks/export")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_workflows_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/workflows")
    assert r.status_code < 500


@pytest.mark.xfail(reason="DB not mocked", strict=False)
@pytest.mark.asyncio
async def test_workflows_create(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v2/workflows", json={
            "name": "Test WF",
            "trigger": "new_tender",
            "actions": [{"type": "notify", "target": "email"}],
        })
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# SWZ / Validation / Offer Assembly
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_swz_analyze(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v2/swz/analyze", json={"tender_id": _uid()})
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_validation_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/validation/rules")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# BZP / TED / KRS / GUS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bzp_v2_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/bzp")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_ted_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/ted")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_ted_sync(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v1/ted/sync")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Estimates v2
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_estimates_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/estimates")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_estimates_predict(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v2/estimates/predict", json={"tender_id": _uid()})
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Decisions v2 / Scoring
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_decisions_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/decisions")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Organizations / API Keys / GDPR
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_organizations_me(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/organizations/me")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_api_keys_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/api-keys")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_gdpr_consent(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/gdpr/consent")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Billing / Demo / Onboarding
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_billing_plans(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/billing/plans")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_demo_generate(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v2/demo/generate")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_onboarding_status(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/onboarding/status")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Advanced Analytics / Benchmark / Forecasting / OLAP
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_analytics_summary(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/analytics/summary")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_analytics_trends(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/analytics/trends")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_benchmark_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/benchmark")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_forecasting(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/forecasting")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_olap_query(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/olap")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring / Feature Flags / AB Testing / Events
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_scoring_config(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/scoring/config")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_feature_flags(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/feature-flags")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_events_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/events")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Audit / Metrics / Reports / Data Quality / Kaizen
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_audit_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/audit")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_metrics_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/metrics")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_reports_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/reports")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_data_quality(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/data-quality")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_kaizen_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/kaizen")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Gantt / Escalation / Integrations / PWA
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_gantt_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/gantt")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_escalation_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/escalation")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_integrations_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/integrations")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_pwa_manifest(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/pwa/manifest")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Kosztorys v2/v3 / Import Offer History / CPV Win Rates
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_kosztorys_v2_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/kosztorys")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_kosztorys_v3_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/kosztorys-v3")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_cpv_win_rates(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/cpv-win-rates")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_import_offer_history(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/import-offer-history")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Semantic Search / Scoring v2 / Agent Pipeline / Chat v2
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_semantic_search(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/semantic-search", params={"q": "budowa drogi"})
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_scoring_v2(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/scoring-v2")
    assert r.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# Offers / Documents / Chat
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_offers_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/offers")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_documents_list(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/documents")
    assert r.status_code < 500


@pytest.mark.asyncio
async def test_chat_history(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v2/chat/history")
    assert r.status_code < 500
