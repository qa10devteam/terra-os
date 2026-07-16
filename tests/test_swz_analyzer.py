"""Testy dla modułu Asystent SWZ — /api/v2/swz/analyze.

Scenariusze:
1. Brak dokumentów SWZ → graceful fallback (go_nogo_score=0)
2. raw_text podany → analiza regex (bez AI)
3. Poprawna struktura odpowiedzi JSON
4. Niepoprawny tender_id (non-UUID) → 422
5. Mock AI → pełna odpowiedź AI
"""
from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api.services.api.auth.deps import CurrentUser, get_current_user
from services.api.services.api.routers.swz import router


# ─── Fixtures ─────────────────────────────────────────────────────────────────

DEMO_USER = CurrentUser(
    user_id="40a71ef6-d6eb-48a3-b62e-7da3df5f0a17",
    email="demo@terra-os.pl",
    org_id="ec3d1e16-2139-48c2-93b5-ffe0defd606d",
    role="owner",
)

SAMPLE_TENDER_ID = str(uuid.uuid4())

SAMPLE_SWZ_TEXT = """
Specyfikacja Warunków Zamówienia — Budowa drogi gminnej nr 12/2026

1. Zamawiający: Gmina Testowa
2. Przedmiot zamówienia: Budowa drogi asfaltowej 2km
3. Wymagania dla wykonawcy:
   - Doświadczenie min. 3 lata w branży budowlanej
   - Referencje za podobne roboty o wartości min. 500 000 PLN
   - Ubezpieczenie OC na min. 1 000 000 PLN
   - Wadium: 10 000 PLN
4. Kary umowne: 0.5% wartości kontraktu za każdy dzień opóźnienia
5. Dokumenty wymagane:
   - KRS lub CEIDG
   - Zaświadczenie ZUS o niezaleganiu
   - Zaświadczenie US o niezaleganiu
   - Wykaz wykonanych robót (referencje)
6. Termin realizacji: 6 miesięcy od podpisania umowy
7. Termin składania ofert: 30 dni
"""

AI_MOCK_RESPONSE = {
    "summary": "Budowa drogi gminnej 2km | Wymagane doświadczenie 3 lata | Wadium 10 000 PLN | Kara 0.5%/dzień opóźnienia | Termin realizacji 6 miesięcy",
    "requirements": [
        "Doświadczenie min. 3 lata w branży budowlanej",
        "Referencje za podobne roboty ≥ 500 000 PLN",
        "Ubezpieczenie OC min. 1 000 000 PLN",
        "Wadium 10 000 PLN",
    ],
    "red_flags": [
        "Kara umowna 0.5%/dzień — wysoka",
        "Brak waloryzacji cen materiałów",
    ],
    "checklist": [
        "Formularz ofertowy",
        "KRS lub CEIDG",
        "Zaświadczenie ZUS o niezaleganiu",
        "Zaświadczenie US o niezaleganiu",
        "Wykaz wykonanych robót z referencjami",
        "Dowód wniesienia wadium",
        "Polisa OC",
    ],
    "go_nogo_score": 72,
    "go_nogo_reason": "Projekt w zasięgu możliwości firmy budowlanej ze średnim doświadczeniem. Główne ryzyko to wysoka kara umowna dzienna.",
}


def _make_empty_db():
    """Zwraca mock DB — brak dokumentów i brak przetargu."""
    conn = MagicMock()
    result = MagicMock()
    result.fetchall.return_value = []
    result.fetchone.return_value = None
    conn.execute.return_value = result
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = conn
    return engine


def _make_app(db_engine=None) -> FastAPI:
    """Tworzy testową instancję FastAPI z routerem SWZ."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: DEMO_USER
    if db_engine is not None:
        from services.api.services.api.routers.swz import get_db

        def override_db():
            with db_engine.connect() as conn:
                yield conn

        app.dependency_overrides[get_db] = override_db
    return app


# ─── Test 1: Brak dokumentów → fallback ──────────────────────────────────────

def test_analyze_no_swz_documents_returns_fallback():
    """Gdy tender nie ma dokumentów SWZ → graceful fallback z go_nogo_score=0."""
    engine = _make_empty_db()
    app = _make_app(engine)
    client = TestClient(app)

    resp = client.post(
        "/api/v2/swz/analyze",
        json={"tender_id": SAMPLE_TENDER_ID},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["tender_id"] == SAMPLE_TENDER_ID
    assert "summary" in data
    assert isinstance(data["requirements"], list)
    assert isinstance(data["red_flags"], list)
    assert isinstance(data["checklist"], list)
    assert data["go_nogo_score"] == 0
    assert isinstance(data["go_nogo_reason"], str)
    assert data["source"] == "fallback_no_content"


# ─── Test 2: raw_text → analiza regex ────────────────────────────────────────

def test_analyze_with_raw_text_uses_regex_fallback():
    """raw_text podany + brak ANTHROPIC_API_KEY → analiza regułami regex."""
    engine = _make_empty_db()
    app = _make_app(engine)
    client = TestClient(app)

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
        resp = client.post(
            "/api/v2/swz/analyze",
            json={"tender_id": SAMPLE_TENDER_ID, "raw_text": SAMPLE_SWZ_TEXT},
        )

    assert resp.status_code == 200
    data = resp.json()

    assert data["tender_id"] == SAMPLE_TENDER_ID
    assert isinstance(data["summary"], str)
    assert len(data["requirements"]) >= 1
    assert len(data["checklist"]) >= 1
    assert 0 <= data["go_nogo_score"] <= 100
    assert data["source"] == "fallback"

    # Regex powinien wykryć czerwoną flagę "0.5%/dzień"
    red_flags_text = " ".join(data["red_flags"]).lower()
    assert "kara" in red_flags_text or "flag" in red_flags_text or len(data["red_flags"]) >= 1


# ─── Test 3: Poprawna struktura JSON ─────────────────────────────────────────

def test_analyze_response_has_correct_schema():
    """Odpowiedź zawiera wszystkie wymagane pola z poprawnymi typami."""
    engine = _make_empty_db()
    app = _make_app(engine)
    client = TestClient(app)

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
        resp = client.post(
            "/api/v2/swz/analyze",
            json={"tender_id": SAMPLE_TENDER_ID, "raw_text": SAMPLE_SWZ_TEXT},
        )

    assert resp.status_code == 200
    data = resp.json()

    # Wymagane pola
    required_fields = [
        "tender_id", "summary", "requirements", "red_flags",
        "checklist", "go_nogo_score", "go_nogo_reason", "source",
    ]
    for field in required_fields:
        assert field in data, f"Brakuje pola: {field}"

    # Typy
    assert isinstance(data["tender_id"], str)
    assert isinstance(data["summary"], str)
    assert isinstance(data["requirements"], list)
    assert isinstance(data["red_flags"], list)
    assert isinstance(data["checklist"], list)
    assert isinstance(data["go_nogo_score"], int)
    assert 0 <= data["go_nogo_score"] <= 100
    assert isinstance(data["go_nogo_reason"], str)
    assert isinstance(data["source"], str)


# ─── Test 4: Niepoprawny UUID → 422 ──────────────────────────────────────────

def test_analyze_invalid_tender_id_returns_422():
    """Niepoprawny tender_id (nie UUID) → HTTP 422."""
    engine = _make_empty_db()
    app = _make_app(engine)
    client = TestClient(app)

    resp = client.post(
        "/api/v2/swz/analyze",
        json={"tender_id": "not-a-valid-uuid"},
    )
    assert resp.status_code == 422


# ─── Test 5: Mock AI → pełna odpowiedź ───────────────────────────────────────

def test_analyze_with_mocked_ai_returns_full_response():
    """Mock Claude AI → endpoint zwraca pełną analizę AI."""
    engine = _make_empty_db()
    app = _make_app(engine)
    client = TestClient(app)

    mock_ai_result = {**AI_MOCK_RESPONSE, "source": "ai"}

    with patch(
        "services.api.services.api.routers.swz._analyze_with_ai",
        return_value=mock_ai_result,
    ):
        resp = client.post(
            "/api/v2/swz/analyze",
            json={"tender_id": SAMPLE_TENDER_ID, "raw_text": SAMPLE_SWZ_TEXT},
        )

    assert resp.status_code == 200
    data = resp.json()

    assert data["go_nogo_score"] == 72
    assert "0.5%/dzień" in " ".join(data["red_flags"]) or len(data["red_flags"]) >= 1
    assert len(data["requirements"]) == 4
    assert len(data["checklist"]) == 7
    assert data["source"] == "ai"
    assert "drogi" in data["summary"].lower() or "budowa" in data["summary"].lower()


# ─── Test 6: Dokument z DB (chunks) ──────────────────────────────────────────

def test_analyze_fetches_chunks_from_db():
    """Gdy DB ma document_chunk → tekst jest pobrany i użyty do analizy."""
    # Utwórz mock DB z danymi chunków
    conn = MagicMock()

    def _execute(stmt, params=None):
        sql = str(stmt)
        result = MagicMock()
        if "document_chunk" in sql:
            chunk = MagicMock()
            chunk.content = SAMPLE_SWZ_TEXT
            result.fetchall.return_value = [chunk]
            result.fetchone.return_value = None
        else:
            result.fetchall.return_value = []
            result.fetchone.return_value = None
        return result

    conn.execute = MagicMock(side_effect=_execute)
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = conn

    app = _make_app(engine)
    client = TestClient(app)

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
        resp = client.post(
            "/api/v2/swz/analyze",
            json={"tender_id": SAMPLE_TENDER_ID},
        )

    assert resp.status_code == 200
    data = resp.json()
    # Nie powinien zwrócić fallback_no_content — miał dane z DB
    assert data["source"] != "fallback_no_content"
    assert data["go_nogo_score"] > 0
