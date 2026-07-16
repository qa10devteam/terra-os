"""Asystent SWZ — analiza dokumentacji przetargowej przy użyciu Claude AI.

POST /api/v2/swz/analyze
  - Przyjmuje tender_id (UUID) + opcjonalnie raw_text
  - Pobiera dokumenty SWZ z DB (tabele: tender, tender_document, document_chunk)
  - Wysyła do Claude Sonnet prompt analizujący SWZ
  - Zwraca: summary, requirements, red_flags, checklist, go_nogo_score, go_nogo_reason
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/swz", tags=["swz"])


# ─── Schematy ─────────────────────────────────────────────────────────────────

class SWZAnalyzeRequest(BaseModel):
    tender_id: str = Field(..., description="UUID przetargu")
    raw_text: str | None = Field(None, description="Opcjonalny tekst SWZ (nadpisuje pobieranie z DB)")


class SWZAnalyzeResponse(BaseModel):
    tender_id: str
    summary: str
    requirements: list[str]
    red_flags: list[str]
    checklist: list[str]
    go_nogo_score: int = Field(..., ge=0, le=100)
    go_nogo_reason: str
    source: str = Field("ai", description="Źródło analizy: 'ai' lub 'fallback'")


# ─── DB helper ────────────────────────────────────────────────────────────────

def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


def _fetch_swz_text(db: Any, tenant_id: str, tender_id: str) -> tuple[str, str]:
    """Pobiera tekst SWZ z DB.

    Kolejność priorytetu:
    1. DocumentChunk (sparsowane fragmenty dokumentów)
    2. Tender.raw (surowe dane przetargu jako fallback)

    Zwraca: (tekst, źródło)
    """
    # 1. Pobierz chunki dokumentów SWZ
    rows = db.execute(
        text(
            "SELECT dc.content "
            "FROM document_chunk dc "
            "JOIN tender_document td ON td.id = dc.document_id "
            "WHERE td.tenant_id = :tid AND td.tender_id = :tender_id "
            "ORDER BY dc.ordinal "
            "LIMIT 50"
        ),
        {"tid": tenant_id, "tender_id": tender_id},
    ).fetchall()

    if rows:
        chunks = "\n\n".join(r.content for r in rows)
        return chunks[:12000], "document_chunks"

    # 2. Fallback: dane z tabeli tender
    row = db.execute(
        text(
            "SELECT title, buyer, raw FROM tender "
            "WHERE id = :tender_id AND tenant_id = :tid"
        ),
        {"tender_id": tender_id, "tid": tenant_id},
    ).fetchone()

    if row:
        raw_data = row.raw if isinstance(row.raw, dict) else {}
        description = raw_data.get("description", "") or raw_data.get("content", "")
        text_parts = [
            f"Tytuł przetargu: {row.title}",
            f"Zamawiający: {row.buyer or 'nieznany'}",
        ]
        if description:
            text_parts.append(f"Opis: {description}")
        return "\n\n".join(text_parts)[:12000], "tender_raw"

    return "", "none"


# ─── AI helper ────────────────────────────────────────────────────────────────

SWZ_PROMPT_TEMPLATE = """Jesteś ekspertem ds. zamówień publicznych w Polsce. Analizujesz Specyfikację Warunków Zamówienia (SWZ).

TREŚĆ SWZ:
{swz_text}

Wykonaj analizę i zwróć WYŁĄCZNIE JSON (bez komentarzy, bez markdown) z następującymi polami:
{{
  "summary": "5-punktowe streszczenie SWZ (punkty oddzielone znakiem |)",
  "requirements": ["wymaganie 1", "wymaganie 2", ...],
  "red_flags": ["ryzyko 1", "niekorzystny zapis 1", ...],
  "checklist": ["dokument do przygotowania 1", "dokument 2", ...],
  "go_nogo_score": 75,
  "go_nogo_reason": "Uzasadnienie oceny Go/No-Go"
}}

Zasady:
- summary: 5 kluczowych punktów oddzielonych znakiem | (pionowy pasek)
- requirements: lista wymagań formalnych (min. 3-8 pozycji)
- red_flags: klauzule niekorzystne dla wykonawcy, kary umowne, ryzyka (0-10 pozycji)
- checklist: dokumenty i oświadczenia wymagane od wykonawcy (min. 3-8 pozycji)
- go_nogo_score: 0-100 (szansa na spełnienie wymagań i wygranie przetargu)
- go_nogo_reason: 2-3 zdania uzasadnienia oceny

Odpowiedz TYLKO poprawnym JSON."""

FALLBACK_RESPONSE = {
    "summary": "Brak treści SWZ do analizy | Nie można pobrać dokumentów przetargu | Sprawdź czy przetarg istnieje w systemie | Uzupełnij dokumentację SWZ | Spróbuj ponownie po dodaniu dokumentów",
    "requirements": [
        "Brak danych do analizy wymagań",
        "Dodaj dokumenty SWZ do przetargu",
    ],
    "red_flags": ["Brak dokumentów SWZ — analiza niemożliwa"],
    "checklist": [
        "Uzupełnij dokumenty SWZ w systemie",
        "Sprawdź czy przetarg istnieje",
    ],
    "go_nogo_score": 0,
    "go_nogo_reason": "Brak dokumentów SWZ uniemożliwia ocenę. Dodaj treść SWZ do przetargu.",
}


def _analyze_with_ai(swz_text: str) -> dict:
    """Wysyła SWZ do Claude i zwraca sparsowany JSON."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — using regex fallback")
        return _analyze_with_regex(swz_text)

    try:
        from anthropic import Anthropic  # type: ignore

        client = Anthropic(api_key=api_key)
        prompt = SWZ_PROMPT_TEMPLATE.format(swz_text=swz_text[:10000])

        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text

        # Wyciągnij JSON z odpowiedzi
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result["source"] = "ai"
            return result
        else:
            logger.warning("Claude returned non-JSON response, using regex fallback")
            return _analyze_with_regex(swz_text)

    except Exception as exc:
        logger.error("Bedrock/Claude error: %s", exc)
        return _analyze_with_regex(swz_text)


def _analyze_with_regex(swz_text: str) -> dict:
    """Fallback — analiza regułami regex gdy AI niedostępne."""
    from ..analytics.risk_extractor import RED_FLAG_RULES

    red_flags = []
    for rule in RED_FLAG_RULES:
        if re.search(rule["pattern"], swz_text, re.IGNORECASE):
            red_flags.append(f"{rule['msg']} (waga: {rule['severity']})")

    # Proste heurystyki
    requirements = []
    if re.search(r"doświadczen|referencj|należyt.*wykonan", swz_text, re.IGNORECASE):
        requirements.append("Wymagane doświadczenie/referencje")
    if re.search(r"ubezpieczen|OC", swz_text, re.IGNORECASE):
        requirements.append("Wymagane ubezpieczenie OC")
    if re.search(r"wadium", swz_text, re.IGNORECASE):
        requirements.append("Wymagane wadium")
    if re.search(r"KRS|CEIDG|NIP|REGON", swz_text, re.IGNORECASE):
        requirements.append("Wymagane dokumenty rejestracyjne (KRS/CEIDG/NIP)")
    if re.search(r"zaświadczen.*ZUS|zaświadczen.*US", swz_text, re.IGNORECASE):
        requirements.append("Wymagane zaświadczenia ZUS/US o niezaleganiu")
    if not requirements:
        requirements = ["Wymagania formalne — brak danych do analizy (dodaj dokumenty SWZ)"]

    checklist = [
        "Formularz ofertowy",
        "Oświadczenie o spełnieniu warunków udziału",
        "Oświadczenie o braku podstaw wykluczenia",
    ]
    if "Wymagane wadium" in requirements:
        checklist.append("Dokument potwierdzający wniesienie wadium")
    if "Wymagane doświadczenie/referencje" in requirements:
        checklist.append("Wykaz wykonanych robót/usług z referencjami")

    score = max(30, 70 - len(red_flags) * 10)
    reason = f"Analiza regułami (AI niedostępne). Wykryto {len(red_flags)} red flag(s). Uzupełnij dokumenty SWZ dla pełnej analizy."

    return {
        "summary": (
            "Analiza wstępna na podstawie reguł (bez AI) | "
            f"Wykryto {len(red_flags)} potencjalnych ryzyk | "
            f"Zidentyfikowano {len(requirements)} wymagań | "
            "Zalecana weryfikacja przez specjalistę ds. zamówień | "
            "Dodaj klucz ANTHROPIC_API_KEY dla pełnej analizy AI"
        ),
        "requirements": requirements,
        "red_flags": red_flags if red_flags else ["Brak wyraźnych red flags (analiza regex)"],
        "checklist": checklist,
        "go_nogo_score": score,
        "go_nogo_reason": reason,
        "source": "fallback",
    }


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=SWZAnalyzeResponse,
    summary="Analizuj SWZ przetargu przy użyciu Claude AI",
    description=(
        "Pobiera dokumenty SWZ z DB lub akceptuje raw_text, "
        "wysyła do Claude Sonnet i zwraca ustrukturyzowaną analizę."
    ),
)
def analyze_swz(
    body: SWZAnalyzeRequest,
    user: AuthUser,
    db: DB,
) -> SWZAnalyzeResponse:
    """POST /api/v2/swz/analyze — analizuj SWZ przetargu."""
    tenant_id = str(user.org_id)
    tender_id = body.tender_id

    # Walidacja UUID
    try:
        import uuid as _uuid
        _uuid.UUID(tender_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tender_id musi być poprawnym UUID",
        )

    # Pobierz lub użyj podanego tekstu SWZ
    if body.raw_text and body.raw_text.strip():
        swz_text = body.raw_text.strip()
        source_label = "raw_text"
    else:
        swz_text, source_label = _fetch_swz_text(db, tenant_id, tender_id)

    # Graceful fallback gdy brak dokumentów
    if not swz_text:
        logger.info("No SWZ content for tender_id=%s — returning fallback response", tender_id)
        fb = FALLBACK_RESPONSE.copy()
        return SWZAnalyzeResponse(
            tender_id=tender_id,
            source="fallback_no_content",
            **{k: v for k, v in fb.items()},
        )

    logger.info(
        "Analyzing SWZ for tender_id=%s (source=%s, text_len=%d)",
        tender_id, source_label, len(swz_text),
    )

    # Analiza AI lub regex fallback
    result = _analyze_with_ai(swz_text)

    # Parsuj summary do listy jeśli oddzielone "|"
    summary_raw = result.get("summary", "")

    # Walidacja i normalizacja pól
    go_nogo_score = result.get("go_nogo_score", 50)
    if not isinstance(go_nogo_score, int):
        try:
            go_nogo_score = int(go_nogo_score)
        except (ValueError, TypeError):
            go_nogo_score = 50
    go_nogo_score = max(0, min(100, go_nogo_score))

    return SWZAnalyzeResponse(
        tender_id=tender_id,
        summary=summary_raw,
        requirements=result.get("requirements", []),
        red_flags=result.get("red_flags", []),
        checklist=result.get("checklist", []),
        go_nogo_score=go_nogo_score,
        go_nogo_reason=result.get("go_nogo_reason", ""),
        source=result.get("source", "ai"),
    )
