"""Faza 6 — File Upload router.

Endpoints:
  GET  /api/v2/documents         — lista dokumentów tenanta
  POST /api/v2/documents/upload  — upload pliku (tender_id opcjonalny)
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import sqlalchemy as sa
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/documents", tags=["documents-v2"])

UPLOAD_BASE = Path("/tmp/terra-docs")
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".zip"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ─── GET /api/v2/documents ────────────────────────────────────────────────────

@router.get("")
@router.get("/")
def list_documents(
    user: AuthUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    tender_id: Optional[str] = Query(default=None),
) -> dict:
    """Lista dokumentów przetargowych tenanta (tabela tender_documents)."""
    engine = get_engine()
    tenant_id = str(user.org_id or user.user_id)

    with engine.connect() as conn:
        try:
            # tender_documents nie ma kolumny tenant_id — filtrujemy przez JOIN z tender
            base_where = "WHERE t.tenant_id = :tid"
            params: dict = {"tid": tenant_id, "lim": limit, "off": offset}

            if tender_id:
                base_where += " AND td.tender_id = :tender_id"
                params["tender_id"] = tender_id

            rows = conn.execute(
                sa.text(
                    f"""SELECT td.id, td.tender_id, td.filename, td.file_size,
                               td.status, td.uploaded_at
                        FROM tender_documents td
                        JOIN tender t ON t.id = td.tender_id
                        {base_where}
                        ORDER BY td.uploaded_at DESC
                        LIMIT :lim OFFSET :off"""
                ),
                params,
            ).mappings().fetchall()

            count_params = {k: v for k, v in params.items() if k not in ("lim", "off")}
            total = conn.execute(
                sa.text(
                    f"""SELECT COUNT(*) FROM tender_documents td
                        JOIN tender t ON t.id = td.tender_id
                        {base_where}"""
                ),
                count_params,
            ).scalar() or 0

        except Exception:
            # Fallback: tabela może nie istnieć w środowisku CI
            rows = []
            total = 0

    return {
        "items": [
            {
                "id": str(r["id"]),
                "tender_id": str(r["tender_id"]) if r["tender_id"] else None,
                "filename": r["filename"],
                "file_size": r["file_size"],
                "status": r["status"],
                "uploaded_at": str(r["uploaded_at"]) if r["uploaded_at"] else None,
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ─── POST /api/v2/documents/upload ───────────────────────────────────────────

@router.post("/upload")
async def upload_document(
    user: AuthUser,
    file: UploadFile = File(...),
    tender_id: Optional[str] = Form(default=None),
) -> dict:
    """Upload dokumentu przetargowego.

    tender_id jest opcjonalny — dokument może być wgrany bez powiązania z przetargiem
    (np. z DocumentsPage bez kontekstu przetargu).
    Jeśli podany, weryfikujemy czy przetarg należy do tenanta.
    """
    engine = get_engine()
    tenant_id = str(user.org_id or user.user_id)

    # Walidacja rozszerzenia
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail={
                "error": "unsupported_file_type",
                "message": f"Obsługiwane typy: PDF, DOCX, XLSX, ZIP. Otrzymano: '{ext}'.",
            },
        )

    # Jeśli tender_id podany — zweryfikuj że należy do tenanta
    if tender_id:
        with engine.connect() as conn:
            tender = conn.execute(
                sa.text("SELECT id FROM tender WHERE id = :id AND tenant_id = :tid"),
                {"id": tender_id, "tid": tenant_id},
            ).fetchone()
        if not tender:
            raise HTTPException(
                status_code=404,
                detail={"error": "tender_not_found", "message": "Przetarg nie znaleziony lub brak dostępu."},
            )

    # Czytaj zawartość
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={"error": "file_too_large", "message": f"Maksymalny rozmiar: {MAX_FILE_SIZE // 1024 // 1024} MB."},
        )

    # Zapisz plik (używamy tego samego katalogu co multimodal.py)
    UPLOAD_BASE.mkdir(parents=True, exist_ok=True)
    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}{ext}"
    file_path = UPLOAD_BASE / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    content_type = file.content_type or "application/octet-stream"

    # Zapisz w tender_documents (tabela używana przez multimodal.py)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """INSERT INTO tender_documents
                       (id, tender_id, filename, file_path, file_size, status, uploaded_at)
                   VALUES (:id, :tid, :filename, :path, :size, 'uploaded', NOW())"""
            ),
            {
                "id": doc_id,
                "tid": tender_id,
                "filename": filename,
                "path": str(file_path),
                "size": len(content),
            },
        )

    return {
        "document_id": doc_id,
        "id": doc_id,  # alias dla kompatybilności
        "filename": filename,
        "size_bytes": len(content),
        "status": "uploaded",
        "next_step": f"POST /api/v2/documents/{doc_id}/analyze",
    }
