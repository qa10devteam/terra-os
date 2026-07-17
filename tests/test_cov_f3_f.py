"""F3-F: Unit tests for offers.py, kosztorys_v2.py, resources.py, m7_backend.py, advanced_analytics.py"""
from __future__ import annotations
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

MOD_OFF = "services.api.services.api.routers.offers"
MOD_KOZ = "services.api.services.api.routers.kosztorys_v2"
MOD_RES = "services.api.services.api.routers.resources"
MOD_M7 = "services.api.services.api.routers.m7_backend"
MOD_AA = "services.api.services.api.routers.advanced_analytics"


@pytest.fixture(scope="module")
def app():
    from starlette.testclient import TestClient
    from services.api.services.api.main import app as _app
    with TestClient(_app) as client:
        yield client


def _eng(fetchone=None, rows=None):
    """Quick mock engine factory — supports connect() and begin()."""
    e = MagicMock()
    c = MagicMock()
    # Support both context manager forms
    for ctx in (e.connect.return_value, e.begin.return_value):
        ctx.__enter__ = lambda s: c
        ctx.__exit__ = MagicMock(return_value=False)
    r = MagicMock()
    r.fetchone.return_value = fetchone
    r.fetchall.return_value = rows if rows is not None else ([] if fetchone is None else [fetchone])
    r.rowcount = 1
    # Support both r[0] and r.field access for tuples/named
    if fetchone is not None and isinstance(fetchone, tuple):
        r.__getitem__ = lambda self, k: fetchone[k]
    c.execute.return_value = r
    return e


def _user(tenant_id=None, org_id=None, role="owner"):
    u = MagicMock()
    u.user_id = str(uuid.uuid4())
    u.tenant_id = tenant_id or str(uuid.uuid4())
    u.org_id = org_id or str(uuid.uuid4())
    u.role = role
    u.email = "test@qa10.io"
    return u


# ═══════════════════════════════════════════════════════════════════════════════
# offers.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_offers_list_empty():
    """list_offers → empty page (user with org_id)."""
    from services.api.services.api.routers.offers import list_offers
    e = _eng(rows=[])
    u = _user()
    u.org_id = str(uuid.uuid4())  # ensure not None
    with patch(f"{MOD_OFF}.get_engine", return_value=e):
        result = list_offers(user=u, limit=10, cursor=None, status=None, tender_id=None, source=None)
    assert result is not None


def test_offers_list_with_rows():
    """list_offers → rows returned."""
    from services.api.services.api.routers.offers import list_offers
    from datetime import datetime, timezone
    row = MagicMock()
    row.id = str(uuid.uuid4())
    row.tender_id = str(uuid.uuid4())
    row.title = "Test Offer"
    row.status = "draft"
    row.total_net = 100000.0
    row.created_at = datetime(2025, 7, 1, tzinfo=timezone.utc)
    e = _eng(rows=[row])
    u = _user()
    u.org_id = str(uuid.uuid4())
    with patch(f"{MOD_OFF}.get_engine", return_value=e):
        result = list_offers(user=u, limit=10, cursor=None, status=None, tender_id=None, source=None)
    assert result is not None


def test_offers_create():
    """create_offer → new offer dict."""
    from services.api.services.api.routers.offers import create_offer, OfferCreate
    new_row = MagicMock()
    new_row.id = str(uuid.uuid4())
    new_row.created_at = None
    e = _eng(fetchone=new_row)
    u = _user()
    u.org_id = str(uuid.uuid4())
    body = OfferCreate(tender_id=str(uuid.uuid4()), title="New Offer")
    with patch(f"{MOD_OFF}.get_engine", return_value=e):
        result = create_offer(body=body, user=u)
    assert result is not None


def test_offers_get():
    """get_offer → returns offer or 404."""
    from services.api.services.api.routers.offers import get_offer
    oid = str(uuid.uuid4())
    row = MagicMock()
    row.id = oid
    row.title = "Test"
    row.status = "draft"
    e = _eng(fetchone=row)
    with patch(f"{MOD_OFF}.get_engine", return_value=e):
        result = get_offer(offer_id=oid, user=_user())
    assert result is not None


def test_offers_get_not_found():
    """get_offer → 404 when row is None."""
    from services.api.services.api.routers.offers import get_offer
    from fastapi import HTTPException
    e = _eng(fetchone=None)
    with patch(f"{MOD_OFF}.get_engine", return_value=e):
        with pytest.raises(HTTPException) as exc:
            get_offer(offer_id=str(uuid.uuid4()), user=_user())
    assert exc.value.status_code == 404


def test_offers_delete():
    """delete_offer → 204 None."""
    from services.api.services.api.routers.offers import delete_offer
    oid = str(uuid.uuid4())
    e = _eng(fetchone=(oid,))
    with patch(f"{MOD_OFF}.get_engine", return_value=e):
        result = delete_offer(offer_id=oid, user=_user())
    assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# kosztorys_v2.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_koz_create():
    """create_kosztorys → returns new kosztorys."""
    from services.api.services.api.routers.kosztorys_v2 import create_kosztorys, KosztorysCreate
    e = _eng()
    body = KosztorysCreate(nazwa="Test kosztorys", tender_id=str(uuid.uuid4()))
    with patch(f"{MOD_KOZ}.get_engine", return_value=e):
        result = create_kosztorys(body=body, user=_user())
    assert result is not None


def test_koz_list():
    """list_kosztorysy → dict with items."""
    from services.api.services.api.routers.kosztorys_v2 import list_kosztorysy
    rows = [MagicMock(id=str(uuid.uuid4()), name="K1", tender_id=str(uuid.uuid4()),
                      status="draft", created_at=None)]
    e = _eng(rows=rows)
    with patch(f"{MOD_KOZ}.get_engine", return_value=e):
        result = list_kosztorysy(user=_user(), limit=10, offset=0)
    assert result is not None


def test_koz_get():
    """get_kosztorys → single item."""
    from services.api.services.api.routers.kosztorys_v2 import get_kosztorys
    kid = str(uuid.uuid4())
    row = MagicMock(id=kid, name="K1", tender_id=str(uuid.uuid4()),
                    status="draft", margin_pct=0.1, overhead_pct=0.15,
                    risk_pct=0.05, vat_pct=0.23, created_at=None, updated_at=None)
    e = _eng(fetchone=row)
    with patch(f"{MOD_KOZ}.get_engine", return_value=e):
        result = get_kosztorys(kid=kid, user=_user())
    assert result is not None


def test_koz_get_not_found():
    """get_kosztorys → 404."""
    from services.api.services.api.routers.kosztorys_v2 import get_kosztorys
    from fastapi import HTTPException
    e = _eng(fetchone=None)
    with patch(f"{MOD_KOZ}.get_engine", return_value=e):
        with pytest.raises(HTTPException) as exc:
            get_kosztorys(kid=str(uuid.uuid4()), user=_user())
    assert exc.value.status_code == 404


def test_koz_delete():
    """delete_kosztorys → 204."""
    from services.api.services.api.routers.kosztorys_v2 import delete_kosztorys
    kid = str(uuid.uuid4())
    row = MagicMock(id=kid)
    e = _eng(fetchone=row)
    with patch(f"{MOD_KOZ}.get_engine", return_value=e):
        result = delete_kosztorys(kid=kid, user=_user())
    assert result is None


def test_koz_win_probability():
    """get_win_probability → returns probability dict."""
    from services.api.services.api.routers.kosztorys_v2 import get_win_probability
    kid = str(uuid.uuid4())
    hdr = MagicMock()
    hdr.suma_netto = 150000.0
    hdr.win_probability = 0.65
    hdr.tenant_id = str(uuid.uuid4())
    e = _eng(fetchone=hdr)
    u = _user()
    u.tenant_id = str(hdr.tenant_id)
    with patch(f"{MOD_KOZ}.get_engine", return_value=e):
        result = get_win_probability(kid=kid, user=u)
    assert result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# resources.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_resources_list_subcontractors():
    """list_subcontractors → list."""
    from services.api.services.api.routers.resources import list_subcontractors
    rows = [MagicMock(id=str(uuid.uuid4()), name="Sub1", nip="1234567890",
                      specialization="electrical", rating=4.5, created_at=None)]
    e = _eng(rows=rows)
    with patch(f"{MOD_RES}.get_engine", return_value=e):
        result = list_subcontractors(user=_user(), limit=10, offset=0)
    assert result is not None


def test_resources_create_subcontractor():
    """create_subcontractor → new sub."""
    from services.api.services.api.routers.resources import create_subcontractor, SubcontractorCreate
    e = _eng()
    body = SubcontractorCreate(name="New Sub", nip="1234567890", specialization=["plumbing"])
    with patch(f"{MOD_RES}.get_engine", return_value=e):
        result = create_subcontractor(sub=body, user=_user())
    assert result is not None


def test_resources_delete_subcontractor():
    """delete_subcontractor → ok dict."""
    from services.api.services.api.routers.resources import delete_subcontractor
    sid = str(uuid.uuid4())
    e = _eng(fetchone=(sid,))
    with patch(f"{MOD_RES}.get_engine", return_value=e):
        result = delete_subcontractor(sub_id=sid, user=_user())
    assert result is not None


def test_resources_list_equipment():
    """list_equipment → list."""
    from services.api.services.api.routers.resources import list_equipment
    rows = [MagicMock(id=str(uuid.uuid4()), name="Excavator", type="heavy",
                      status="available", daily_rate=500.0)]
    e = _eng(rows=rows)
    with patch(f"{MOD_RES}.get_engine", return_value=e):
        result = list_equipment(user=_user(), limit=10, offset=0)
    assert result is not None


def test_resources_create_equipment():
    """create_equipment → new eq."""
    from services.api.services.api.routers.resources import create_equipment, EquipmentCreate
    e = _eng()
    body = EquipmentCreate(name="Crane", category="heavy", daily_cost=1000.0)
    with patch(f"{MOD_RES}.get_engine", return_value=e):
        result = create_equipment(eq=body, user=_user())
    assert result is not None


def test_resources_get_gantt():
    """get_gantt → gantt data with datetime fields."""
    from services.api.services.api.routers.resources import get_gantt
    from datetime import date
    rows = [MagicMock(id=str(uuid.uuid4()), parent_id=None, name="Task1",
                      start_date=date(2025, 7, 1), end_date=date(2025, 7, 15),
                      progress=0.5, color="#blue", position=1)]
    e = _eng(rows=rows)
    with patch(f"{MOD_RES}.get_engine", return_value=e):
        result = get_gantt(tender_id=str(uuid.uuid4()), user=_user())
    assert result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# m7_backend.py
# ═══════════════════════════════════════════════════════════════════════════════

def test_m7_get_usage():
    """get_usage → usage dict."""
    from services.api.services.api.routers.m7_backend import get_usage
    row = (100, 50, 25, 1500.0)
    e = _eng(fetchone=row)
    with patch(f"{MOD_M7}.get_engine", return_value=e):
        result = get_usage(tenant_id=str(uuid.uuid4()))
    assert result is not None


def test_m7_monthly_report():
    """monthly_report → report dict (single row with 5 fields)."""
    from services.api.services.api.routers.m7_backend import monthly_report
    row = (10, 4, 2, 800000.0, 400000.0)
    e = _eng(fetchone=row)
    with patch(f"{MOD_M7}.get_engine", return_value=e):
        result = monthly_report(tenant_id=str(uuid.uuid4()))
    assert result is not None


def test_m7_report_templates():
    """report_templates → list."""
    from services.api.services.api.routers.m7_backend import report_templates
    result = report_templates()
    assert isinstance(result, list)


def test_m7_market_kpi():
    """market_kpi_bar → kpi dict (single row with 3 fields)."""
    from services.api.services.api.routers.m7_backend import market_kpi_bar
    row = (25, 1500000.0, 500)
    e = _eng(fetchone=row)
    with patch(f"{MOD_M7}.get_engine", return_value=e):
        result = market_kpi_bar()
    assert result is not None


def test_m7_get_bookmarks():
    """get_bookmarks → list."""
    from services.api.services.api.routers.m7_backend import get_bookmarks
    rows = [MagicMock(id=str(uuid.uuid4()), tender_id=str(uuid.uuid4()),
                      note="Important", created_at=None)]
    e = _eng(rows=rows)
    with patch(f"{MOD_M7}.get_engine", return_value=e):
        result = get_bookmarks(tenant_id=str(uuid.uuid4()))
    assert result is not None


def test_m7_add_bookmark():
    """add_bookmark → created dict."""
    from services.api.services.api.routers.m7_backend import add_bookmark, BookmarkRequest
    e = _eng()
    body = BookmarkRequest(notes="key tender", priority=1)
    with patch(f"{MOD_M7}.get_engine", return_value=e):
        result = add_bookmark(tender_id=str(uuid.uuid4()),
                              tenant_id=str(uuid.uuid4()), body=body)
    assert result is not None


def test_m7_remove_bookmark():
    """remove_bookmark → ok."""
    from services.api.services.api.routers.m7_backend import remove_bookmark
    e = _eng(fetchone=(1,))
    with patch(f"{MOD_M7}.get_engine", return_value=e):
        result = remove_bookmark(tender_id=str(uuid.uuid4()), tenant_id=str(uuid.uuid4()))
    assert result is not None


def test_m7_get_alerts():
    """get_alerts → list."""
    from services.api.services.api.routers.m7_backend import get_alerts
    rows = [MagicMock(id=str(uuid.uuid4()), keyword="CPV45", threshold=5,
                      channel="email", active=True, created_at=None)]
    e = _eng(rows=rows)
    with patch(f"{MOD_M7}.get_engine", return_value=e):
        result = get_alerts(tenant_id=str(uuid.uuid4()))
    assert result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# advanced_analytics.py — uses Depends(), test via HTTP client
# ═══════════════════════════════════════════════════════════════════════════════

def test_aa_analyze_swz(app):
    """analyze_swz → non-500 response."""
    r = app.post("/api/v2/ai/analyze-swz",
                 json={"tender_id": str(uuid.uuid4())})
    assert r.status_code < 500


def test_aa_score_decision(app):
    """score_decision → non-500 response."""
    r = app.post("/api/v2/decisions/score",
                 json={"tender_id": str(uuid.uuid4())})
    assert r.status_code < 500


def test_aa_cost_trends(app):
    """cost_trends → non-500 response."""
    r = app.get("/api/v2/analytics/cost-trends")
    assert r.status_code < 500


def test_aa_get_report(app):
    """get_report → non-500 response."""
    r = app.get(f"/api/v2/reports/{str(uuid.uuid4())}")
    assert r.status_code < 500
