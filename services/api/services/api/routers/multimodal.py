"""Multimodal document processing — PDF drawings → cost estimates.

Faza 8.35: pipeline przetwarzania dokumentów przetargowych:
1. Upload PDF (SIWZ, rysunki techniczne, przedmiary)
2. Ekstrakcja tekstu + OCR rysunków  
3. Rozpoznanie elementów (budowlane, instalacyjne)
4. Automatyczny kosztorys z ICB

Endpoints:
  POST /api/v2/documents/upload          — upload PDF
  GET  /api/v2/documents/{doc_id}        — get processed document
  POST /api/v2/documents/{doc_id}/analyze — run AI analysis
  GET  /api/v2/documents/{doc_id}/estimate — get cost estimate
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Query
import sqlalchemy as sa

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/documents", tags=["multimodal"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.environ.get("DOCUMENT_UPLOAD_DIR", "/tmp/terra-docs"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_document(
    user: AuthUser,
    file: UploadFile = File(...),
    tender_id: Optional[str] = None,
    tender_id_form: Optional[str] = None,
) -> dict[str, Any]:
    """Upload a PDF document for processing. tender_id is optional."""
    # Accept PDF, DOCX, XLSX, ZIP
    fname = (file.filename or "upload").lower()
    allowed_exts = (".pdf", ".docx", ".xlsx", ".zip")
    if not any(fname.endswith(e) for e in allowed_exts):
        raise HTTPException(400, f"Only PDF/DOCX/XLSX/ZIP files are supported")

    doc_id = str(uuid.uuid4())
    # Zachowaj oryginalne rozszerzenie (nie zawsze .pdf)
    from pathlib import Path as _Path
    _ext = _Path(file.filename or "upload").suffix.lower() or ".pdf"
    file_path = UPLOAD_DIR / f"{doc_id}{_ext}"

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(413, "File too large (max 50MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO tender_documents (id, tender_id, filename, file_path, file_size, 
                                         status, uploaded_at)
            VALUES (:id, :tid, :fname, :path, :size, 'uploaded', NOW())
        """), {
            "id": doc_id,
            "tid": tender_id,
            "fname": file.filename,
            "path": str(file_path),
            "size": len(content),
        })

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "size_bytes": len(content),
        "status": "uploaded",
        "next_step": f"POST /api/v2/documents/{doc_id}/analyze",
    }


@router.get("/{doc_id}")
def get_document(doc_id: str, user: AuthUser) -> dict[str, Any]:
    """Get document metadata and processing status."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT id, tender_id, filename, file_size, status, 
                   extracted_text, analysis_result, cost_estimate, uploaded_at
            FROM tender_documents WHERE id = :id
        """), {"id": doc_id}).fetchone()

    if not row:
        raise HTTPException(404, "Document not found")

    return {
        "document_id": str(row[0]),
        "tender_id": str(row[1]) if row[1] else None,
        "filename": row[2],
        "size_bytes": row[3],
        "status": row[4],
        "has_text": bool(row[5]),
        "has_analysis": bool(row[6]),
        "has_estimate": bool(row[7]),
        "uploaded_at": row[8].isoformat() if row[8] else None,
    }


@router.post("/{doc_id}/analyze")
async def analyze_document(doc_id: str, user: AuthUser) -> dict[str, Any]:
    """Run AI analysis on uploaded document — extract text, identify elements."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT file_path, status FROM tender_documents WHERE id = :id
        """), {"id": doc_id}).fetchone()

    if not row:
        raise HTTPException(404, "Document not found")

    file_path = Path(row[0])
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk")

    # Extract text using PyMuPDF (fitz)
    extracted_text = ""
    page_count = 0
    elements_found = []

    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(file_path))
        page_count = len(doc)
        pages_text = []
        
        for page in doc:
            text = page.get_text()
            pages_text.append(text)
            
            # Detect construction elements in text
            elements_found.extend(_detect_elements(text, page.number + 1))
        
        extracted_text = "\n\n---PAGE BREAK---\n\n".join(pages_text)
        doc.close()
    except ImportError:
        # Fallback: basic text extraction hint
        extracted_text = "[PyMuPDF not available — install with: pip install pymupdf]"
        page_count = 0
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        extracted_text = f"[Extraction error: {e}]"

    # Store results
    analysis = {
        "page_count": page_count,
        "text_length": len(extracted_text),
        "elements_found": len(elements_found),
        "elements": elements_found[:50],  # Top 50
        "categories_detected": list(set(e["category"] for e in elements_found)),
        "analyzed_at": datetime.utcnow().isoformat(),
    }

    with engine.begin() as conn:
        conn.execute(sa.text("""
            UPDATE tender_documents 
            SET extracted_text = :text, analysis_result = :analysis, status = 'analyzed'
            WHERE id = :id
        """), {"id": doc_id, "text": extracted_text[:100000], "analysis": json.dumps(analysis)})

    return {
        "document_id": doc_id,
        "status": "analyzed",
        "has_text": bool(extracted_text),
        "has_analysis": True,
        "has_estimate": False,
        "pages": page_count,
        "text_chars": len(extracted_text),
        "elements": elements_found[:20],
        "categories": analysis["categories_detected"],
        "next_step": f"GET /api/v2/documents/{doc_id}/estimate",
    }


def _detect_elements(text: str, page_num: int) -> list[dict]:
    """Detect construction elements from text using keyword patterns."""
    import re
    
    elements = []
    patterns = {
        "roboty_ziemne": [r"wykop[yów]*", r"nasyp[yów]*", r"korytowanie", r"odwodnienie"],
        "fundamenty": [r"fundament[yów]*", r"ław[ay]*", r"stop[ay]*", r"pale"],
        "konstrukcja": [r"beton\s+C\d+", r"zbrojenie", r"stal\s+\w+", r"żelbet"],
        "murowe": [r"mur(?:ow|ów)", r"cegł[ay]*", r"bloczk[ió]", r"pustak"],
        "dachowe": [r"dach", r"więźba", r"pokrycie", r"papa", r"blachodachówka"],
        "instalacje_san": [r"kanalizac", r"wodociąg", r"rur[ay]*\s*\w*\s*\d+", r"instalac.*san"],
        "instalacje_el": [r"instalac.*elektr", r"kabel\s*\d+", r"rozdzielni", r"oświetleni"],
        "wykonczenie": [r"tynk", r"malowanie", r"glazur", r"posadzk", r"podłog"],
        "drogi": [r"nawierzchni[ay]", r"asfalt", r"kostk[ay]", r"krawężnik", r"chodnik"],
    }

    text_lower = text.lower()
    for category, regexes in patterns.items():
        for pattern in regexes:
            matches = re.finditer(pattern, text_lower)
            for m in matches:
                # Get context (30 chars before and after)
                start = max(0, m.start() - 30)
                end = min(len(text_lower), m.end() + 50)
                context = text[start:end].strip().replace("\n", " ")
                
                elements.append({
                    "category": category,
                    "keyword": m.group(),
                    "context": context,
                    "page": page_num,
                })
                if len(elements) > 200:
                    return elements
    return elements


@router.get("/{doc_id}/estimate")
def get_cost_estimate(doc_id: str, user: AuthUser) -> dict[str, Any]:
    """Generate cost estimate from document analysis using ICB data."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT analysis_result, cost_estimate, extracted_text
            FROM tender_documents WHERE id = :id
        """), {"id": doc_id}).fetchone()

    if not row:
        raise HTTPException(404, "Document not found")
    if not row[0]:
        raise HTTPException(400, "Document not analyzed yet — POST /analyze first")

    # If estimate already cached, return it
    if row[1]:
        cached = row[1] if isinstance(row[1], dict) else json.loads(row[1])
        return cached

    # analysis_result może być dict (jsonb z SQLAlchemy) lub str (legacy)
    analysis = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    categories = analysis.get("categories_detected", [])

    # Map detected categories to ICB categories and fetch prices
    category_mapping = {
        "roboty_ziemne": "Roboty ziemne",
        "fundamenty": "Fundamenty",
        "konstrukcja": "Konstrukcje betonowe",
        "murowe": "Roboty murowe",
        "dachowe": "Roboty dachowe",
        "instalacje_san": "Instalacje sanitarne",
        "instalacje_el": "Instalacje elektryczne",
        "wykonczenie": "Roboty wykończeniowe",
        "drogi": "Roboty drogowe",
    }

    estimate_items = []
    total_min = 0
    total_max = 0

    for cat in categories:
        icb_name = category_mapping.get(cat, cat)

        # Query ICB — tabela icb_ceny_srednie (cena_netto, cena_narzut)
        with engine.connect() as conn2:
            icb_row = conn2.execute(sa.text("""
                SELECT MIN(cena_netto) as min_price, MAX(cena_netto) as max_price,
                       AVG(cena_netto) as avg_price, COUNT(*) as sample_count
                FROM icb_ceny_srednie
                WHERE nazwa ILIKE '%' || :cat || '%'
                   OR category ILIKE '%' || :cat || '%'
            """), {"cat": icb_name}).fetchone()

        if icb_row and icb_row[3] and icb_row[3] > 0:
            item_min = float(icb_row[0])
            item_max = float(icb_row[1])
            item_avg = float(icb_row[2])
        else:
            # Fallback estimates per category (PLN)
            fallbacks = {
                "roboty_ziemne": (50_000, 200_000),
                "fundamenty": (80_000, 400_000),
                "konstrukcja": (200_000, 1_500_000),
                "murowe": (100_000, 500_000),
                "dachowe": (80_000, 350_000),
                "instalacje_san": (60_000, 300_000),
                "instalacje_el": (50_000, 250_000),
                "wykonczenie": (100_000, 600_000),
                "drogi": (150_000, 800_000),
            }
            item_min, item_max = fallbacks.get(cat, (50_000, 300_000))
            item_avg = (item_min + item_max) / 2

        estimate_items.append({
            "category": icb_name,
            "category_code": cat,
            "min_pln": item_min,
            "max_pln": item_max,
            "avg_pln": item_avg,
            "icb_backed": bool(icb_row and icb_row[3] and icb_row[3] > 0),
            "elements_on_pages": [e["page"] for e in analysis.get("elements", []) if e.get("category") == cat][:5],
        })
        total_min += item_min
        total_max += item_max

    estimate = {
        "document_id": doc_id,
        "status": "estimated",
        "categories_count": len(estimate_items),
        "items": estimate_items,
        "total": {
            "min_pln": total_min,
            "max_pln": total_max,
            "mid_pln": (total_min + total_max) / 2,
            "confidence": "low" if not any(i["icb_backed"] for i in estimate_items) else "medium",
        },
        "disclaimer": "Szacunek wstępny na podstawie ICB i analizy dokumentu. Wymaga weryfikacji kosztorysanta.",
        "generated_at": datetime.utcnow().isoformat(),
    }

    # Cache
    with engine.begin() as conn:
        conn.execute(sa.text("""
            UPDATE tender_documents SET cost_estimate = :est, status = 'estimated'
            WHERE id = :id
        """), {"id": doc_id, "est": json.dumps(estimate)})

    return estimate
