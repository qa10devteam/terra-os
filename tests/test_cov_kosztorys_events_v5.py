"""
Coverage tests for:
1. routers/kosztorys_v2.py  lines 1224-1253 (material-risk endpoint)
2. routers/kosztorys_v3.py  lines 109-129   (AI wycena ICB branch)
3. routers/icb_advanced.py  lines 655-660   (robocizna_map region grouping)
4. routers/events.py        lines 120-133   (get_notifications)
5. intelligence/buyer_score.py lines 114-137 (get_buyer_score endpoint)
6. routers/validation.py    lines 117-119   (validate_bid_summary exception path)
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Any
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

# ── Auth helpers ──────────────────────────────────────────────────────────────
from services.api.services.api.auth.deps import CurrentUser

def _user(org_id="org-1") -> CurrentUser:
    return CurrentUser(user_id="u1", email="t@t.pl", org_id=org_id, role="owner")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. kosztorys_v2 — get_kosztorys_material_risk  (lines 1224-1253)
# ═══════════════════════════════════════════════════════════════════════════════

from services.api.services.api.routers.kosztorys_v2 import get_kosztorys_material_risk


def _make_engine_v2(rows):
    """Return a mocked engine whose conn.execute returns the supplied rows."""
    kosztorys_row = MagicMock()  # returned by _get_kosztorys_or_404
    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)

    # First execute → _get_kosztorys_or_404; second → materials query
    mock_conn.execute.side_effect = [
        MagicMock(fetchone=lambda: kosztorys_row),   # _get_kosztorys_or_404
        MagicMock(fetchall=lambda: rows),            # material rows
    ]
    engine = MagicMock()
    engine.connect.return_value = mock_conn
    return engine


def _material_row(symbol="SYM", nazwa="Material A", m_jcena=100.0):
    r = MagicMock()
    r.symbol = symbol
    r.nazwa = nazwa
    r.m_jcena = m_jcena
    return r


def test_material_risk_gus_success_low_risk():
    """GUS API returns 200 with ratio=1.0 → risk_level = 'low'."""
    row = _material_row(m_jcena=100.0)
    engine = _make_engine_v2([row])

    gus_response = MagicMock()
    gus_response.status_code = 200
    gus_response.json.return_value = {
        "results": [{"values": [{"val": "100.0"}]}]
    }

    with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine), \
         patch("httpx.get", return_value=gus_response):
        result = get_kosztorys_material_risk("kid-1", _user())

    assert result["kosztorys_id"] == "kid-1"
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["gus_index"] == 100.0
    assert item["risk_level"] == "low"


def test_material_risk_gus_high_risk_low_ratio():
    """ratio = 0.5 < 0.7 → risk_level = 'high'."""
    row = _material_row(m_jcena=50.0)
    engine = _make_engine_v2([row])

    gus_response = MagicMock()
    gus_response.status_code = 200
    gus_response.json.return_value = {
        "results": [{"values": [{"val": "100.0"}]}]
    }

    with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine), \
         patch("httpx.get", return_value=gus_response):
        result = get_kosztorys_material_risk("kid-2", _user())

    assert result["items"][0]["risk_level"] == "high"


def test_material_risk_gus_high_risk_high_ratio():
    """ratio = 2.0 > 1.5 → risk_level = 'high'."""
    row = _material_row(m_jcena=200.0)
    engine = _make_engine_v2([row])

    gus_response = MagicMock()
    gus_response.status_code = 200
    gus_response.json.return_value = {
        "results": [{"values": [{"val": "100.0"}]}]
    }

    with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine), \
         patch("httpx.get", return_value=gus_response):
        result = get_kosztorys_material_risk("kid-3", _user())

    assert result["items"][0]["risk_level"] == "high"


def test_material_risk_gus_medium_risk():
    """ratio = 0.8 → 0.7 ≤ r < 0.85 → risk_level = 'medium'."""
    row = _material_row(m_jcena=80.0)
    engine = _make_engine_v2([row])

    gus_response = MagicMock()
    gus_response.status_code = 200
    gus_response.json.return_value = {
        "results": [{"values": [{"val": "100.0"}]}]
    }

    with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine), \
         patch("httpx.get", return_value=gus_response):
        result = get_kosztorys_material_risk("kid-4", _user())

    assert result["items"][0]["risk_level"] == "medium"


def test_material_risk_gus_404_no_index():
    """GUS returns non-200 → gus_value = None → risk = 'low'."""
    row = _material_row(m_jcena=100.0)
    engine = _make_engine_v2([row])

    gus_response = MagicMock()
    gus_response.status_code = 404

    with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine), \
         patch("httpx.get", return_value=gus_response):
        result = get_kosztorys_material_risk("kid-5", _user())

    item = result["items"][0]
    assert item["gus_index"] is None
    assert item["risk_level"] == "low"


def test_material_risk_gus_exception_swallowed():
    """httpx raises → exception swallowed, risk = 'low'."""
    row = _material_row(m_jcena=100.0)
    engine = _make_engine_v2([row])

    with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine), \
         patch("httpx.get", side_effect=Exception("network error")):
        result = get_kosztorys_material_risk("kid-6", _user())

    item = result["items"][0]
    assert item["gus_index"] is None
    assert item["risk_level"] == "low"


def test_material_risk_no_rows():
    """No material rows → empty items list."""
    engine = _make_engine_v2([])

    with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine), \
         patch("httpx.get", side_effect=Exception("not called")):
        result = get_kosztorys_material_risk("kid-7", _user())

    assert result["items"] == []


def test_material_risk_gus_empty_results_list():
    """GUS 200 but empty results → gus_value = None."""
    row = _material_row(m_jcena=100.0)
    engine = _make_engine_v2([row])

    gus_response = MagicMock()
    gus_response.status_code = 200
    gus_response.json.return_value = {"results": []}

    with patch("services.api.services.api.routers.kosztorys_v2.get_engine", return_value=engine), \
         patch("httpx.get", return_value=gus_response):
        result = get_kosztorys_material_risk("kid-8", _user())

    assert result["items"][0]["gus_index"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# 2. kosztorys_v3 — ai_wycena_v2 ICB rates branch  (lines 109-129)
# ═══════════════════════════════════════════════════════════════════════════════

from services.api.services.api.routers.kosztorys_v3 import ai_wycena_v2


def _make_v3_conn(krow_attrs: dict, pozycje_rows, tender_row=None, icb_rows=None):
    """Build a mock connection returning appropriate rows for kosztorys_v3."""
    krow = MagicMock()
    for k, v in krow_attrs.items():
        setattr(krow, k, v)

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)

    # execute calls in order: 1) kosztorys row, 2) pozycje, 3) tender (opt), 4) icb_rows (opt)
    side_effects = [
        MagicMock(fetchone=lambda: krow),
        MagicMock(fetchall=lambda: pozycje_rows),
    ]
    if tender_row is not None:
        _tr = tender_row
        side_effects.append(MagicMock(fetchone=lambda: _tr))
    if icb_rows is not None:
        _ir = icb_rows
        side_effects.append(MagicMock(fetchall=lambda: _ir))

    mock_conn.execute.side_effect = side_effects
    return mock_conn


def _pozycja_row(lp=1, opis="Roboty ziemne", jednostka="m3",
                 ilosc=10.0, r_jcena=50.0, m_jcena=30.0, s_jcena=20.0):
    r = MagicMock()
    r.lp = lp
    r.opis = opis
    r.jednostka = jednostka
    r.ilosc = ilosc
    r.r_jcena = r_jcena
    r.m_jcena = m_jcena
    r.s_jcena = s_jcena
    return r


def _make_v3_engine(conn):
    engine = MagicMock()
    engine.connect.return_value = conn
    return engine


def _fake_httpx_stream():
    fake = MagicMock()
    fake.__enter__ = lambda s: fake
    fake.__exit__ = MagicMock(return_value=False)
    fake.iter_lines = MagicMock(return_value=iter([
        'data: {"choices": [{"delta": {"content": "ok"}}]}',
        "data: [DONE]",
    ]))
    return fake


@pytest.mark.asyncio
async def test_v3_icb_rates_branch_with_tender_and_icb():
    """Lines 109-133: tender_id present + cpv + nuts2 → ICB rates fetched."""
    tender_row = MagicMock()
    tender_row.cpv = ["45212000"]
    tender_row.nuts_code = "PL91"

    icb_row = MagicMock()
    icb_row.quarter = "2024-1"
    icb_row.icb_r_rate = 55.0
    icb_row.icb_m_rate = 30.0
    icb_row.icb_s_rate = 10.0

    krow_attrs = {"tender_id": "tender-uuid-1", "nazwa": "Kosztorys testowy"}
    conn = _make_v3_conn(
        krow_attrs, [_pozycja_row()],
        tender_row=tender_row, icb_rows=[icb_row],
    )
    engine = _make_v3_engine(conn)

    with patch("services.api.services.api.routers.kosztorys_v3.get_engine", return_value=engine), \
         patch("httpx.stream", return_value=_fake_httpx_stream()):
        from fastapi.responses import StreamingResponse
        result = await ai_wycena_v2(
            kosztorys_id="kid-1",
            user=_user(),
            _gate=None,
        )
        assert isinstance(result, StreamingResponse)


@pytest.mark.asyncio
async def test_v3_no_tender_id():
    """Lines 108-133: tender_id is None → skip ICB lookup."""
    krow_attrs = {"tender_id": None, "nazwa": "Kosztorys bez tender"}
    conn = _make_v3_conn(krow_attrs, [_pozycja_row()])
    engine = _make_v3_engine(conn)

    with patch("services.api.services.api.routers.kosztorys_v3.get_engine", return_value=engine), \
         patch("httpx.stream", return_value=_fake_httpx_stream()):
        from fastapi.responses import StreamingResponse
        result = await ai_wycena_v2(kosztorys_id="kid-2", user=_user(), _gate=None)
        assert isinstance(result, StreamingResponse)


@pytest.mark.asyncio
async def test_v3_tender_cpv_none():
    """Lines 113: tender found but cpv is None → skip icb_rows."""
    tender_row = MagicMock()
    tender_row.cpv = None
    tender_row.nuts_code = "PL91"

    krow_attrs = {"tender_id": "tender-uuid-2", "nazwa": "Test no cpv"}
    conn = _make_v3_conn(krow_attrs, [_pozycja_row()], tender_row=tender_row)
    engine = _make_v3_engine(conn)

    with patch("services.api.services.api.routers.kosztorys_v3.get_engine", return_value=engine), \
         patch("httpx.stream", return_value=_fake_httpx_stream()):
        from fastapi.responses import StreamingResponse
        result = await ai_wycena_v2(kosztorys_id="kid-3", user=_user(), _gate=None)
        assert isinstance(result, StreamingResponse)


@pytest.mark.asyncio
async def test_v3_tender_icb_rows_empty():
    """Lines 127: icb_rows found but empty → icb_rates_txt stays ''."""
    tender_row = MagicMock()
    tender_row.cpv = ["45100000"]
    tender_row.nuts_code = "PL21"

    krow_attrs = {"tender_id": "t-3", "nazwa": "Empty ICB"}
    conn = _make_v3_conn(krow_attrs, [_pozycja_row()], tender_row=tender_row, icb_rows=[])
    engine = _make_v3_engine(conn)

    with patch("services.api.services.api.routers.kosztorys_v3.get_engine", return_value=engine), \
         patch("httpx.stream", return_value=_fake_httpx_stream()):
        from fastapi.responses import StreamingResponse
        result = await ai_wycena_v2(kosztorys_id="kid-4", user=_user(), _gate=None)
        assert isinstance(result, StreamingResponse)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. icb_advanced — robocizna_map region grouping  (lines 655-660)
# ═══════════════════════════════════════════════════════════════════════════════

from services.api.services.api.routers.icb_advanced import robocizna_map


def _region_row(voivodeship, rate_type, coefficient):
    r = MagicMock()
    # Support r[0], r[1], r[2] indexing
    r.__getitem__ = lambda self, i: (voivodeship, rate_type, coefficient)[i]
    return r


def _make_icb_engine(national_row, region_rows):
    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.side_effect = [
        MagicMock(fetchone=lambda: national_row),
        MagicMock(fetchall=lambda: region_rows),
    ]
    engine = MagicMock()
    engine.connect.return_value = mock_conn
    return engine


def test_robocizna_map_region_grouping():
    """Lines 654-660: group regions, set stawka_r for 'Ogolne' rate_type."""
    nat = MagicMock()
    nat.__getitem__ = lambda self, i: (52.0, 40.0, 65.0)[i]
    nat.__bool__ = lambda self: True

    regions = [
        _region_row("Mazowieckie", "Ogolne", 1.1),
        _region_row("Mazowieckie", "Specjalne", 0.9),
        _region_row("Śląskie", "Ogolne", 0.95),
    ]

    engine = _make_icb_engine(nat, regions)

    with patch("services.api.services.api.routers.icb_advanced.get_engine", return_value=engine), \
         patch("services.api.services.api.intelligence.icb_service.get_latest_quarter",
               return_value=(2024, 1), create=True), \
         patch("services.api.services.api.routers.icb_advanced.get_latest_quarter",
               return_value=(2024, 1), create=True):
        # patch inside the function's local import
        import services.api.services.api.intelligence.icb_service as icb_svc_mod
        with patch.object(icb_svc_mod, "get_latest_quarter", return_value=(2024, 1)):
            result = robocizna_map(_user())

    assert "regions" in result
    region_names = {r["voivodeship"] for r in result["regions"]}
    assert "Mazowieckie" in region_names
    assert "Śląskie" in region_names

    maz = next(r for r in result["regions"] if r["voivodeship"] == "Mazowieckie")
    assert "Ogolne" in maz["coefficients"]
    assert "Specjalne" in maz["coefficients"]
    assert "stawka_r" in maz
    assert abs(maz["stawka_r"] - round(52.0 * 1.1, 2)) < 0.01


def test_robocizna_map_no_ogolne_rate():
    """Lines 659: if rate_type != 'Ogolne', stawka_r not set for that region."""
    nat = MagicMock()
    nat.__getitem__ = lambda self, i: (52.0, 40.0, 65.0)[i]
    nat.__bool__ = lambda self: True

    regions = [
        _region_row("Małopolskie", "Specjalne", 0.8),
    ]

    engine = _make_icb_engine(nat, regions)

    import services.api.services.api.intelligence.icb_service as icb_svc_mod
    with patch("services.api.services.api.routers.icb_advanced.get_engine", return_value=engine), \
         patch.object(icb_svc_mod, "get_latest_quarter", return_value=(2024, 1)):
        result = robocizna_map(_user())

    mal = next(r for r in result["regions"] if r["voivodeship"] == "Małopolskie")
    assert "stawka_r" not in mal


def test_robocizna_map_empty_regions():
    """Lines 654-660: no region rows → empty region_map."""
    nat = MagicMock()
    nat.__getitem__ = lambda self, i: (52.0, 40.0, 65.0)[i]
    nat.__bool__ = lambda self: True

    engine = _make_icb_engine(nat, [])

    import services.api.services.api.intelligence.icb_service as icb_svc_mod
    with patch("services.api.services.api.routers.icb_advanced.get_engine", return_value=engine), \
         patch.object(icb_svc_mod, "get_latest_quarter", return_value=(2024, 1)):
        result = robocizna_map(_user())

    assert result["regions"] == []


def test_robocizna_map_national_none():
    """Lines 650: national is None → base_rate defaults to 52.0."""
    engine = _make_icb_engine(None, [])

    import services.api.services.api.intelligence.icb_service as icb_svc_mod
    with patch("services.api.services.api.routers.icb_advanced.get_engine", return_value=engine), \
         patch.object(icb_svc_mod, "get_latest_quarter", return_value=(2024, 1)):
        result = robocizna_map(_user())

    assert result["national_avg_r"] == 52.0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. events.py — get_notifications  (lines 120-133)
# ═══════════════════════════════════════════════════════════════════════════════

from services.api.services.api.routers.events import get_notifications


def _notif_row(id_=None, type_="alert.deadline", title="Title", body="Body",
               link="http://x", read=False, created_at=None):
    from datetime import datetime
    _id = id_ or uuid.uuid4()
    _ca = created_at or datetime(2024, 1, 1, 12, 0, 0)
    r = MagicMock()
    r.__getitem__ = lambda self, i: (_id, type_, title, body, link, read, _ca)[i]
    return r


def _make_events_engine(rows):
    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value = MagicMock(fetchall=lambda: rows)
    engine = MagicMock()
    engine.connect.return_value = mock_conn
    return engine


def test_get_notifications_basic():
    """Lines 120-141: get all notifications (unread_only=False)."""
    nid = uuid.uuid4()
    rows = [_notif_row(id_=nid)]
    engine = _make_events_engine(rows)

    with patch("services.api.services.api.routers.events.get_engine", return_value=engine):
        result = get_notifications(user=_user(), limit=20, unread_only=False)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["event_type"] == "alert.deadline"
    assert result[0]["read"] is False
    assert result[0]["created_at"] is not None


def test_get_notifications_unread_only():
    """Lines 122: where_clause includes 'WHERE read = false'."""
    rows = [_notif_row(read=False)]
    engine = _make_events_engine(rows)

    with patch("services.api.services.api.routers.events.get_engine", return_value=engine):
        result = get_notifications(user=_user(), limit=10, unread_only=True)

    assert len(result) == 1
    # Verify that the SQL generated included read=false clause
    call_args = engine.connect.return_value.execute.call_args
    sql_text = str(call_args[0][0])
    assert "read = false" in sql_text


def test_get_notifications_empty():
    """Lines 120-141: no rows → empty list."""
    engine = _make_events_engine([])

    with patch("services.api.services.api.routers.events.get_engine", return_value=engine):
        result = get_notifications(user=_user(), limit=20, unread_only=False)

    assert result == []


def test_get_notifications_created_at_none():
    """Lines 140: created_at is None → isoformat skipped → result is None."""
    nid = uuid.uuid4()
    r = MagicMock()
    r.__getitem__ = lambda self, i: (nid, "type", "t", "b", "l", False, None)[i]
    engine = _make_events_engine([r])

    with patch("services.api.services.api.routers.events.get_engine", return_value=engine):
        result = get_notifications(user=_user(), limit=20, unread_only=False)

    assert result[0]["created_at"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# 5. intelligence/buyer_score.py — get_buyer_score  (lines 114-137)
# ═══════════════════════════════════════════════════════════════════════════════

from services.api.services.api.intelligence.buyer_score import get_buyer_score


def _make_buyer_engine_stub():
    """Engine whose connect().execute() succeeds (for notification insert path)."""
    engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: mock_conn
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.commit = MagicMock()
    mock_conn.execute = MagicMock(return_value=MagicMock())
    engine.connect.return_value = mock_conn
    return engine


def test_get_buyer_score_high_score():
    """Lines 114-142: score >= 0.6 → risk_level = 'low', no notification."""
    engine = _make_buyer_engine_stub()

    with patch("services.api.services.api.intelligence.buyer_score.get_engine", return_value=engine), \
         patch("services.api.services.api.intelligence.buyer_score.calculate_buyer_score", return_value=0.8):
        result = get_buyer_score(nip="1234567890", user=_user(), tenant_id="t1")

    assert result["nip"] == "1234567890"
    assert result["risk_level"] == "low"
    assert result["alert_created"] is False
    assert abs(result["score"] - 0.8) < 0.001


def test_get_buyer_score_medium_score():
    """Lines 114-142: 0.3 <= score < 0.6 → risk_level = 'medium'."""
    engine = _make_buyer_engine_stub()

    with patch("services.api.services.api.intelligence.buyer_score.get_engine", return_value=engine), \
         patch("services.api.services.api.intelligence.buyer_score.calculate_buyer_score", return_value=0.5):
        result = get_buyer_score(nip="9876543210", user=_user(), tenant_id="t1")

    assert result["risk_level"] == "medium"
    assert result["alert_created"] is False


def test_get_buyer_score_low_score_creates_notification():
    """Lines 119-135: score < 0.3 → INSERT notification, alert_created = True."""
    engine = _make_buyer_engine_stub()

    with patch("services.api.services.api.intelligence.buyer_score.get_engine", return_value=engine), \
         patch("services.api.services.api.intelligence.buyer_score.calculate_buyer_score", return_value=0.2):
        result = get_buyer_score(nip="1111111111", user=_user("org-notif"), tenant_id="t-notif")

    assert result["risk_level"] == "high"
    assert result["alert_created"] is True
    engine.connect.return_value.execute.assert_called()


def test_get_buyer_score_low_score_notification_exception():
    """Lines 134-135: notification INSERT fails → exception swallowed."""
    engine = _make_buyer_engine_stub()
    engine.connect.return_value.execute.side_effect = Exception("insert failed")

    with patch("services.api.services.api.intelligence.buyer_score.get_engine", return_value=engine), \
         patch("services.api.services.api.intelligence.buyer_score.calculate_buyer_score", return_value=0.1):
        result = get_buyer_score(nip="2222222222", user=_user(), tenant_id="t2")

    assert result["alert_created"] is True
    assert result["risk_level"] == "high"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. routers/validation.py — validate_bid_summary exception path (lines 117-119)
# ═══════════════════════════════════════════════════════════════════════════════

from fastapi import HTTPException
from services.api.services.api.routers.validation import validate_bid_summary


@pytest.mark.asyncio
async def test_validate_bid_summary_exception_path():
    """Lines 117-119: validate_bid raises → HTTPException 500."""
    bid_id = uuid.uuid4()

    mock_module = MagicMock()
    mock_module.validate_bid = MagicMock(side_effect=RuntimeError("engine down"))

    orig = sys.modules.get("services.api.services.api.intelligence.validation_engine")
    sys.modules["services.api.services.api.intelligence.validation_engine"] = mock_module
    try:
        with pytest.raises(HTTPException) as exc_info:
            await validate_bid_summary(bid_id=bid_id, strict_mode=False)
    finally:
        if orig is None:
            sys.modules.pop("services.api.services.api.intelligence.validation_engine", None)
        else:
            sys.modules["services.api.services.api.intelligence.validation_engine"] = orig

    assert exc_info.value.status_code == 500
    assert "Validation error" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_bid_summary_success_strips_points():
    """Lines 112-115: success path — 'points' key is removed from response."""
    from datetime import datetime
    bid_id = uuid.uuid4()

    fake_result = MagicMock()
    fake_result.bid_id = bid_id
    fake_result.status = "pass"
    fake_result.passed = 47
    fake_result.failed = 0
    fake_result.warnings = 0
    fake_result.not_applicable = 0
    fake_result.critical_issues = []
    fake_result.recommendations = []
    fake_result.validated_at = datetime(2024, 1, 1)
    fake_result.points = []

    mock_module = MagicMock()
    mock_module.validate_bid = MagicMock(return_value=fake_result)

    orig = sys.modules.get("services.api.services.api.intelligence.validation_engine")
    sys.modules["services.api.services.api.intelligence.validation_engine"] = mock_module
    try:
        from fastapi.responses import JSONResponse
        import json
        response = await validate_bid_summary(bid_id=bid_id, strict_mode=False)
        assert isinstance(response, JSONResponse)
        body = json.loads(response.body)
        assert "points" not in body
        assert body["status"] == "pass"
    finally:
        if orig is None:
            sys.modules.pop("services.api.services.api.intelligence.validation_engine", None)
        else:
            sys.modules["services.api.services.api.intelligence.validation_engine"] = orig
