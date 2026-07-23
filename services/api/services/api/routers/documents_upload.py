"""Faza 6 — File Upload router."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import sqlalchemy as sa
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

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


@router.get("")
@router.get("/")
def list_documents(
    user: AuthUser,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    tender_id: str | None = Query(default=None),
) -> dict:
    """Lista dokumentów przetargowych tenanta."""
    engine = get_engine()
    tenant_id = user.org_id or user.user_id
    filters = "WHERE tenant_id = :tid"
    params: dict = {"tid": tenant_id, "limit": limit, "offset": offset}
    if tender_id:
        filters += " AND tender_id = :tender_id"
        params["tender_id"] = tender_id
    with engine.connect() as conn:
        rows = conn.execute(sa.text(f"""
            SELECT id, tender_id, filename, pages, parsed_ok, created_at, kind
            FROM tender_document {filters}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """), params).fetchall()
        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        total = conn.execute(sa.text(
            f"SELECT COUNT(*) FROM tender_document {filters}"
        ), count_params).scalar() or 0
    return {
        "items": [
            {
                "id": str(r[0]), "tender_id": str(r[1]),
                "filename": r[2], "pages": r[3],
                "parsed_ok": r[4], "created_at": str(r[5]),
                "kind": r[6],
            }
            for r in rows
        ],
        "total": total, "limit": limit, "offset": offset,
    }


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


# ─── Missing stub: GET /api/v2/documents (list) ───────────────────────────────

@router.get("")
def list_documents(
    user: AuthUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    """List documents for the current tenant. Frontend uses ?limit=5."""
    from terra_db.session import get_engine
    import sqlalchemy as sa

    engine = get_engine()
    tenant_id = str(user.org_id)

    with engine.connect() as conn:
        try:
            # tender_documents joined with tender to filter by tenant
            rows = conn.execute(
                sa.text(
                    """SELECT td.id, td.tender_id, td.filename, td.file_size, td.status, td.uploaded_at
                       FROM tender_documents td
                       JOIN tender t ON t.id = td.tender_id
                       WHERE t.tenant_id=:tid
                       ORDER BY td.uploaded_at DESC
                       LIMIT :lim OFFSET :off"""
                ),
                {"tid": tenant_id, "lim": limit, "off": offset}
            ).mappings().fetchall()
            total = conn.execute(
                sa.text(
                    """SELECT count(*) FROM tender_documents td
                       JOIN tender t ON t.id = td.tender_id
                       WHERE t.tenant_id=:tid"""
                ),
                {"tid": tenant_id}
            ).scalar() or 0
        except Exception:
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
