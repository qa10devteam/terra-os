"""Faza 6 — File Upload router."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import sqlalchemy as sa
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/documents", tags=["documents-v2"])

UPLOAD_BASE = Path("/var/terra/uploads")
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".zip"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload")
async def upload_document(
    user: AuthUser,
    file: UploadFile = File(...),
    tender_id: str = Form(...),
) -> dict:
    """Upload dokumentu przetargowego."""
    engine = get_engine()
    tenant_id = user.org_id or user.user_id  # fallback gdy brak org

    # Walidacja rozszerzenia
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail={
                "error": "unsupported_file_type",
                "message": f"Obsługiwane typy: PDF, DOCX, XLSX, ZIP. Otrzymano: {ext}",
            },
        )

    # Sprawdź czy przetarg istnieje i należy do tenanta
    with engine.connect() as conn:
        tender = conn.execute(
            sa.text("SELECT id FROM tender WHERE id = :id AND tenant_id = :tid"),
            {"id": tender_id, "tid": tenant_id},
        ).fetchone()

    if not tender:
        raise HTTPException(
            status_code=404,
            detail={"error": "tender_not_found", "message": "Przetarg nie znaleziony"},
        )

    # Czytaj zawartość
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail={"error": "file_too_large", "message": f"Maksymalny rozmiar pliku: {MAX_FILE_SIZE // 1024 // 1024}MB"},
        )

    # Zapisz plik
    org_dir = UPLOAD_BASE / tenant_id / tender_id
    org_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
    file_path = org_dir / safe_filename

    with open(file_path, "wb") as f:
        f.write(content)

    # Zapisz rekord w DB
    doc_id = str(uuid.uuid4())
    content_type = file.content_type or "application/octet-stream"

    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """INSERT INTO tender_document
                       (id, tenant_id, tender_id, kind, filename, local_path, mime, created_at)
                   VALUES (:id, :tid, :tender_id, :kind, :filename, :path, :mime, NOW())"""
            ),
            {
                "id": doc_id,
                "tid": tenant_id,
                "tender_id": tender_id,
                "kind": ext.lstrip("."),
                "filename": filename,
                "path": str(file_path),
                "mime": content_type,
            },
        )

    return {
        "id": doc_id,
        "filename": filename,
        "size": len(content),
        "content_type": content_type,
        "path": str(file_path),
    }
