"""Faza 44 — KRS/CEIDG Verification: weryfikacja podmiotów gospodarczych."""
from __future__ import annotations


import uuid

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v1/verify", tags=["krs-verify"])

KRS_API_BASE = "https://api-krs.ms.gov.pl/api/krs"
CEIDG_API_BASE = "https://dane.biznes.gov.pl/api/ceidg/v2"
REGON_API_BASE = "https://wyszukiwarkaregon.stat.gov.pl/appBIR/index.aspx"
VIES_API_BASE = "https://ec.europa.eu/taxation_customs/vies/services/checkVatService"


class VerifyRequest(BaseModel):
    nip: str
    source: str = "krs"  # krs | ceidg | auto


def _verify_krs(nip: str) -> dict:
    """Verify entity via KRS API."""
    try:
        with httpx.Client(timeout=20) as client:
            # KRS search by NIP
            resp = client.get(
                f"{KRS_API_BASE}/OdpisAktualny/podmiot/nip/{nip}",
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                odpis = data.get("odpis", {})
                dane = odpis.get("dane", {})
                podmiot = dane.get("dzialy", {}).get("dzial1", {}).get("danePodmiotu", {})
                return {
                    "nip": nip,
                    "krs": data.get("numerKRS", ""),
                    "name": podmiot.get("nazwa", ""),
                    "status": "active",
                    "address": "",
                    "source": "krs",
                    "raw": data,
                }
    except Exception as exc:
        pass
    return {"nip": nip, "source": "krs", "status": "lookup_failed", "error": "KRS API niedostępne"}


def _verify_ceidg(nip: str) -> dict:
    """Verify entity via CEIDG API."""
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(
                f"{CEIDG_API_BASE}/firmy",
                params={"nip": nip},
                headers={"Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                firms = data.get("firma", [])
                if firms:
                    firm = firms[0]
                    return {
                        "nip": nip,
                        "regon": firm.get("regon", ""),
                        "name": firm.get("nazwa", ""),
                        "status": firm.get("status", "unknown"),
                        "address": f"{firm.get('ulica','')}, {firm.get('kodPocztowy','')} {firm.get('miejscowosc','')}",
                        "source": "ceidg",
                        "raw": firm,
                    }
    except Exception as exc:
        pass
    return {"nip": nip, "source": "ceidg", "status": "lookup_failed", "error": "CEIDG API niedostępne"}


@router.post("")
def verify_entity(req: VerifyRequest, user: AuthUser) -> dict:
    """Weryfikuj podmiot (NIP) w KRS lub CEIDG."""
    engine = get_engine()

    # Check cache first (< 7 days)
    with engine.connect() as conn:
        cached = conn.execute(
            sa.text("""
                SELECT id, nip, regon, krs, name, status, address, source, verified_at
                FROM entity_verifications
                WHERE nip = :nip AND verified_at > NOW() - INTERVAL '7 days'
                ORDER BY verified_at DESC LIMIT 1
            """),
            {"nip": req.nip},
        ).fetchone()
    if cached:
        return {
            "id": str(cached.id),
            "nip": cached.nip,
            "regon": cached.regon,
            "krs": cached.krs,
            "name": cached.name,
            "status": cached.status,
            "address": cached.address,
            "source": cached.source,
            "verified_at": cached.verified_at.isoformat() if cached.verified_at else None,
            "cached": True,
        }

    # Perform fresh lookup
    if req.source == "ceidg":
        result = _verify_ceidg(req.nip)
    elif req.source == "krs":
        result = _verify_krs(req.nip)
    else:
        # auto: try KRS first, then CEIDG
        result = _verify_krs(req.nip)
        if result.get("status") == "lookup_failed":
            result = _verify_ceidg(req.nip)

    # Store in cache
    import json
    rec_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO entity_verifications
                    (id, nip, regon, krs, name, status, address, source, raw_json, verified_at)
                VALUES (:id, :nip, :regon, :krs, :name, :status, :address, :source, :raw::jsonb, now())
            """),
            {
                "id": rec_id,
                "nip": req.nip,
                "regon": result.get("regon", ""),
                "krs": result.get("krs", ""),
                "name": result.get("name", ""),
                "status": result.get("status", "unknown"),
                "address": result.get("address", ""),
                "source": result.get("source", req.source),
                "raw": json.dumps(result.get("raw", {})),
            },
        )
        conn.commit()

    result["id"] = rec_id
    result["cached"] = False
    result.pop("raw", None)
    return result


@router.get("/search")
def search_verifications(
    user: AuthUser,
    nip: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Historia weryfikacji podmiotów."""
    engine = get_engine()
    params: dict = {"limit": limit}
    where = "WHERE nip = :nip" if nip else ""
    if nip:
        params["nip"] = nip
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(f"""
                SELECT id, nip, regon, krs, name, status, address, source, verified_at
                FROM entity_verifications {where}
                ORDER BY verified_at DESC
                LIMIT :limit
            """),
            params,
        ).fetchall()
    return {
        "items": [
            {
                "id": str(r.id),
                "nip": r.nip,
                "regon": r.regon,
                "krs": r.krs,
                "name": r.name,
                "status": r.status,
                "address": r.address,
                "source": r.source,
                "verified_at": r.verified_at.isoformat() if r.verified_at else None,
            }
            for r in rows
        ]
    }
