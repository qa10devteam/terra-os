"""
BudOS Estimates v2 — pełny silnik kosztorysowy.

Trzy warianty:
  doc    — kosztorys wg dokumentacji projektowej (ręczne pozycje R/M/S)
  icb    — auto-generowany z InterCenBud (ICB) stawek per CPV
  custom — własne stawki firmy z rate_card

Endpointy:
  GET    /api/v2/estimates                     — lista dla przetargu / org
  POST   /api/v2/estimates                     — utwórz (+ auto-generuj ICB)
  GET    /api/v2/estimates/{id}                — szczegóły + linie + narzuty
  PUT    /api/v2/estimates/{id}                — update narzutów/nazwy
  DELETE /api/v2/estimates/{id}                — usuń
  POST   /api/v2/estimates/{id}/lines          — dodaj pozycję (R/M/S pełny model)
  PUT    /api/v2/estimates/{id}/lines/{lid}    — edytuj pozycję
  DELETE /api/v2/estimates/{id}/lines/{lid}    — usuń pozycję
  POST   /api/v2/estimates/{id}/recalc         — przelicz summy R/M/S + narzuty
  POST   /api/v2/estimates/{id}/icb-autofill   — uzupełnij stawki ICB dla pozycji
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from terra_db.session import get_engine
from ..auth.deps import AuthUser, get_tenant_id, TenantDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/estimates", tags=["estimates-v2"])


# ─── Request / Response models ────────────────────────────────────────────────

class NarzutyIn(BaseModel):
    ko_r_pct: float = 65.0   # KO od robocizny %
    ko_s_pct: float = 30.0   # KO od sprzętu %
    z_pct:    float = 10.0   # zysk %
    kz_pct:   float = 2.0    # koszty zakupu materiałów %
    vat_pct:  float = 23.0   # VAT %

    class Config:
        validate_default = True


class EstimateCreate(BaseModel):
    tender_id: str
    variant: str = "doc"    # doc | icb | custom
    nazwa: str | None = None
    narzuty: NarzutyIn = NarzutyIn()
    # ICB auto-fill params
    cpv_prefix: str | None = None   # np. "45" — jeśli variant=icb i brak
    area_m2:    float | None = None  # pow. do auto-estymacji ICB


class EstimateUpdate(BaseModel):
    nazwa: str | None = None
    narzuty: NarzutyIn | None = None


class LineIn(BaseModel):
    kst_code:  str   = ""
    opis:      str
    jednostka: str   = "m2"
    ilosc:     float = 1.0
    r_jcena:   float = 0.0   # cena jedn. robocizny [PLN]
    m_jcena:   float = 0.0   # cena jedn. materiału [PLN]
    s_jcena:   float = 0.0   # cena jedn. sprzętu [PLN]
    icb_r_id:  int | None = None
    icb_m_id:  int | None = None
    icb_s_id:  int | None = None


class LineUpdate(BaseModel):
    kst_code:  str   | None = None
    opis:      str   | None = None
    jednostka: str   | None = None
    ilosc:     float | None = None
    r_jcena:   float | None = None
    m_jcena:   float | None = None
    s_jcena:   float | None = None
    icb_r_id:  int   | None = None
    icb_m_id:  int   | None = None
    icb_s_id:  int   | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _narzuty_from_row(row) -> dict:
    return {
        "ko_r_pct": float(row.ko_r_pct or 65),
        "ko_s_pct": float(row.ko_s_pct or 30),
        "z_pct":    float(row.z_pct or 10),
        "kz_pct":   float(row.kz_pct or 2),
        "vat_pct":  float(row.vat_pct or 23),
    }


def _calc_line(r: float, m: float, s: float, narzuty: dict, ilosc: float) -> dict:
    """Oblicz narzuty i wartości dla pozycji kosztorysu."""
    ko = r * narzuty["ko_r_pct"] / 100 + s * narzuty["ko_s_pct"] / 100
    kz = m * narzuty["kz_pct"] / 100
    z  = (r + m + s + ko + kz) * narzuty["z_pct"] / 100
    cj = r + m + s + ko + kz + z
    return {
        "jcena_netto":   round(cj, 4),
        "wartosc_netto": round(cj * ilosc, 2),
        "r_total":  round(r * ilosc, 4),
        "m_total":  round(m * ilosc, 4),
        "s_total":  round(s * ilosc, 4),
        "ko_total": round(ko * ilosc, 2),
        "z_total":  round(z * ilosc, 2),
        "kz_total": round(kz * ilosc, 2),
    }


def _calc_sums(lines: list[dict], narzuty: dict) -> dict:
    """Oblicz sumy kosztorysu z listy pozycji."""
    r = sum(ln.get("r_total") or 0 for ln in lines)
    m = sum(ln.get("m_total") or 0 for ln in lines)
    s = sum(ln.get("s_total") or 0 for ln in lines)
    ko = sum(ln.get("ko_total") or 0 for ln in lines)
    z  = sum(ln.get("z_total") or 0 for ln in lines)
    kz = sum(ln.get("kz_total") or 0 for ln in lines)
    net = sum(ln.get("wartosc_netto") or 0 for ln in lines)
    brut = round(net * (1 + narzuty["vat_pct"] / 100), 2)
    return {
        "suma_r": round(r, 2), "suma_m": round(m, 2), "suma_s": round(s, 2),
        "suma_ko": round(ko, 2), "suma_z": round(z, 2), "suma_kz": round(kz, 2),
        "suma_netto": round(net, 2), "suma_brutto": brut,
    }


def _fetch_lines(conn, estimate_id: str, tenant_id: str, narzuty: dict) -> list[dict]:
    """Pobierz pozycje kosztorysu z DB i oblicz wartości."""
    rows = conn.execute(sa.text("""
        SELECT id, lp, kst_code, opis, jednostka, ilosc,
               r_jcena, m_jcena, s_jcena, jcena_netto, wartosc_netto,
               ko_total, z_total, kz_total, is_anomaly,
               icb_r_id, icb_m_id, icb_s_id,
               -- legacy compat fields
               description, unit, quantity, unit_price,
               labor_pln, material_pln, equipment_pln
        FROM estimate_line
        WHERE estimate_id = :eid AND tenant_id = :tid
        ORDER BY COALESCE(lp, 0), created_at
    """), {"eid": estimate_id, "tid": tenant_id}).fetchall()

    result = []
    for i, row in enumerate(rows, 1):
        # Resolve opis/ilosc/r_jcena from new or legacy fields
        opis      = row.opis or row.description or ""
        jednostka = row.jednostka or row.unit or "szt"
        ilosc     = float(row.ilosc or row.quantity or 1)
        r         = float(row.r_jcena or row.labor_pln or 0)
        m         = float(row.m_jcena or row.material_pln or 0)
        s         = float(row.s_jcena or row.equipment_pln or 0)

        # Recalc (in case narzuty changed)
        calc = _calc_line(r, m, s, narzuty, ilosc)

        result.append({
            "id":           str(row.id),
            "lp":           row.lp or i,
            "kst_code":     row.kst_code or "",
            "opis":         opis,
            "jednostka":    jednostka,
            "ilosc":        ilosc,
            "r_jcena":      r,
            "m_jcena":      m,
            "s_jcena":      s,
            "jcena_netto":  calc["jcena_netto"],
            "wartosc_netto":calc["wartosc_netto"],
            "r_total":      calc["r_total"],
            "m_total":      calc["m_total"],
            "s_total":      calc["s_total"],
            "ko_total":     calc["ko_total"],
            "z_total":      calc["z_total"],
            "kz_total":     calc["kz_total"],
            "is_anomaly":   bool(row.is_anomaly),
            "icb_r_id":     row.icb_r_id,
            "icb_m_id":     row.icb_m_id,
            "icb_s_id":     row.icb_s_id,
        })
    return result


def _row_to_estimate(row, lines: list[dict], narzuty: dict) -> dict:
    sums = _calc_sums(lines, narzuty)
    return {
        "id":          str(row.id),
        "tender_id":   str(row.tender_id),
        "variant":     row.variant,
        "nazwa":       row.nazwa or "",
        "narzuty":     narzuty,
        **sums,
        "params":      row.params if isinstance(row.params, dict) else {},
        "created_at":  row.created_at.isoformat() if row.created_at else None,
        "lines":       lines,
        "line_count":  len(lines),
    }


def _get_tenant(user: AuthUser) -> str:
    """Resolve org_id → real tenant_id via organizations table."""
    org_id = user.org_id
    if not org_id:
        raise HTTPException(403, {"error": "no_org", "message": "Brak org_id w tokenie"})
    engine = get_engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text("SELECT tenant_id FROM organizations WHERE id = :oid LIMIT 1"),
                {"oid": org_id},
            ).fetchone()
        if row and row.tenant_id:
            return str(row.tenant_id)
    except Exception:
        pass
    return str(org_id)


def _icb_autofill_lines(conn, cpv_prefix: str, area_m2: float | None) -> list[dict]:
    """Generuj linie kosztorysu z ICB stawek (icb_ceny_srednie)."""
    try:
        rows = conn.execute(sa.text("""
            SELECT symbol, nazwa, jednostka,
                   MAX(CASE WHEN typ_rms='R' THEN cena_netto END) AS r_cena,
                   MAX(CASE WHEN typ_rms='M' THEN cena_netto END) AS m_cena,
                   MAX(CASE WHEN typ_rms='S' THEN cena_netto END) AS s_cena
            FROM icb_ceny_srednie
            WHERE kwartalrok = (SELECT MAX(kwartalrok) FROM icb_ceny_srednie)
              AND COALESCE(cena_netto, 0) > 0
            GROUP BY symbol, nazwa_pozycji, jednostka
            HAVING MAX(CASE WHEN typ_rms='R' THEN cena_netto END) > 0
            ORDER BY symbol
            LIMIT 15
        """)).fetchall()

        if rows:
            result = []
            for i, r in enumerate(rows, 1):
                result.append({
                    "kst_code":  r.symbol or f"ICB-{i:03d}",
                    "opis":      r.nazwa or r.symbol or "Pozycja ICB",
                    "jednostka": r.jednostka or "m2",
                    "ilosc":     float(area_m2 or 1.0),
                    "r_jcena":   float(r.r_cena or 0),
                    "m_jcena":   float(r.m_cena or 0),
                    "s_jcena":   float(r.s_cena or 0),
                })
            return result
    except Exception:
        pass

    # Fallback: typowe roboty budowlane gdy brak danych ICB
    return _default_icb_lines(area_m2)


def _default_icb_lines(area_m2: float | None) -> list[dict]:
    """Domyślne linie gdy brak danych ICB."""
    area = area_m2 or 1.0
    return [
        {"kst_code": "KNR 2-01/0101", "opis": "Roboty ziemne — wykopy",            "jednostka": "m3",  "ilosc": area * 0.3, "r_jcena": 45.0,  "m_jcena": 0,     "s_jcena": 12.0},
        {"kst_code": "KNR 2-02/0101", "opis": "Fundamenty — ławy betonowe",        "jednostka": "m3",  "ilosc": area * 0.1, "r_jcena": 180.0, "m_jcena": 350.0, "s_jcena": 30.0},
        {"kst_code": "KNR 2-02/1201", "opis": "Ściany murowane z bloczków",        "jednostka": "m2",  "ilosc": area * 2.5, "r_jcena": 85.0,  "m_jcena": 120.0, "s_jcena": 8.0},
        {"kst_code": "KNR 2-02/2101", "opis": "Strop żelbetowy",                   "jednostka": "m2",  "ilosc": area,       "r_jcena": 95.0,  "m_jcena": 180.0, "s_jcena": 22.0},
        {"kst_code": "KNR 2-02/3101", "opis": "Dach — więźba dachowa",             "jednostka": "m2",  "ilosc": area * 1.2, "r_jcena": 120.0, "m_jcena": 90.0,  "s_jcena": 0},
        {"kst_code": "KNR 2-18/0301", "opis": "Tynki wewnętrzne gipsowe",          "jednostka": "m2",  "ilosc": area * 3.5, "r_jcena": 28.0,  "m_jcena": 12.0,  "s_jcena": 0},
        {"kst_code": "KNR 2-18/0501", "opis": "Posadzki — wylewka betonowa",       "jednostka": "m2",  "ilosc": area,       "r_jcena": 35.0,  "m_jcena": 25.0,  "s_jcena": 5.0},
        {"kst_code": "KNR 4-01/0101", "opis": "Instalacja elektryczna",            "jednostka": "m2",  "ilosc": area,       "r_jcena": 55.0,  "m_jcena": 45.0,  "s_jcena": 0},
        {"kst_code": "KNR 4-02/0101", "opis": "Instalacja wod.-kan.",              "jednostka": "kpl", "ilosc": 1,          "r_jcena": 8500,  "m_jcena": 6000,  "s_jcena": 0},
        {"kst_code": "KNR 4-03/0101", "opis": "Instalacja CO — grzejniki",        "jednostka": "kpl", "ilosc": 1,          "r_jcena": 6000,  "m_jcena": 8000,  "s_jcena": 0},
    ]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
def list_estimates(user: AuthUser, tender_id: str | None = None) -> dict:
    """Lista kosztorysów dla przetargu lub całej org."""
    tenant_id = _get_tenant(user)
    engine = get_engine()
    with engine.connect() as conn:
        if tender_id:
            # Validate UUID
            try: uuid.UUID(tender_id)
            except (ValueError, AttributeError):
                return {"items": [], "total": 0}
            rows = conn.execute(sa.text("""
                SELECT id, tender_id, variant, nazwa,
                       ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct,
                       suma_netto, suma_brutto, created_at
                FROM estimate
                WHERE tenant_id = :tid AND tender_id = CAST(:eid AS UUID)
                ORDER BY variant, created_at
            """), {"tid": tenant_id, "eid": tender_id}).fetchall()
        else:
            rows = conn.execute(sa.text("""
                SELECT id, tender_id, variant, nazwa,
                       ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct,
                       suma_netto, suma_brutto, created_at
                FROM estimate
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
                LIMIT 50
            """), {"tid": tenant_id}).fetchall()

    items = []
    for r in rows:
        narzuty = {
            "ko_r_pct": float(r.ko_r_pct or 65),
            "ko_s_pct": float(r.ko_s_pct or 30),
            "z_pct":    float(r.z_pct or 10),
            "kz_pct":   float(r.kz_pct or 2),
            "vat_pct":  float(r.vat_pct or 23),
        }
        items.append({
            "id":          str(r.id),
            "tender_id":   str(r.tender_id),
            "variant":     r.variant,
            "nazwa":       r.nazwa or "",
            "narzuty":     narzuty,
            "suma_netto":  float(r.suma_netto or 0),
            "suma_brutto": float(r.suma_brutto or 0),
            "created_at":  r.created_at.isoformat() if r.created_at else None,
        })
    return {"items": items, "total": len(items)}


@router.post("", status_code=201)
def create_estimate(body: EstimateCreate, user: AuthUser) -> dict:
    """Utwórz kosztorys (doc / icb / custom)."""
    tenant_id = _get_tenant(user)
    variant = body.variant

    if variant not in ("doc", "icb", "custom"):
        raise HTTPException(422, {"error": "invalid_variant", "message": "variant: doc | icb | custom"})

    engine = get_engine()

    # Verify tender belongs to tenant
    with engine.connect() as conn:
        tender = conn.execute(
            sa.text("SELECT id, title, cpv FROM tender WHERE id = CAST(:id AS UUID) AND tenant_id = :tid"),
            {"id": body.tender_id, "tid": tenant_id},
        ).fetchone()

    if not tender:
        raise HTTPException(404, {"error": "tender_not_found", "message": "Przetarg nie znaleziony"})

    # ICB variant: generate lines BEFORE opening write transaction
    auto_lines: list[dict] = []
    if variant == "icb":
        cpv_prefix = body.cpv_prefix or ""
        if not cpv_prefix and tender.cpv:
            cpv_list = tender.cpv if isinstance(tender.cpv, list) else []
            cpv_prefix = cpv_list[0][:2] if cpv_list else "45"
        with engine.connect() as read_conn:
            auto_lines = _icb_autofill_lines(read_conn, cpv_prefix, body.area_m2)

    narzuty = body.narzuty.model_dump()
    nazwa = body.nazwa or (f"{tender.title[:80]} [{variant.upper()}]" if tender.title else f"Kosztorys {variant.upper()}")

    new_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO estimate
                (id, tenant_id, tender_id, variant, nazwa,
                 ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct,
                 params, created_at)
            VALUES
                (:id, :tid, CAST(:tender_id AS UUID), :variant, :nazwa,
                 :ko_r, :ko_s, :z, :kz, :vat,
                 CAST(:params AS jsonb), NOW())
        """), {
            "id": new_id, "tid": tenant_id, "tender_id": body.tender_id,
            "variant": variant, "nazwa": nazwa,
            "ko_r": narzuty["ko_r_pct"], "ko_s": narzuty["ko_s_pct"],
            "z": narzuty["z_pct"], "kz": narzuty["kz_pct"], "vat": narzuty["vat_pct"],
            "params": json.dumps({}),
        })

        # ICB variant: insert auto-generated lines
        if variant == "icb" and auto_lines:
            for i, ln in enumerate(auto_lines, 1):
                calc = _calc_line(ln["r_jcena"], ln["m_jcena"], ln["s_jcena"], narzuty, ln["ilosc"])
                conn.execute(sa.text("""
                    INSERT INTO estimate_line
                        (id, estimate_id, tenant_id, lp, kst_code, opis, jednostka, ilosc,
                         r_jcena, m_jcena, s_jcena, jcena_netto, wartosc_netto,
                         ko_total, z_total, kz_total, description, unit, quantity,
                         unit_price, labor_pln, material_pln, equipment_pln, created_at)
                    VALUES
                        (:id, :eid, :tid, :lp, :kst, :opis, :jm, :ilosc,
                         :r, :m, :s, :jcena, :wart,
                         :ko, :z, :kz, :opis, :jm, :ilosc,
                         :jcena, :r, :m, :s, NOW())
                """), {
                    "id": str(uuid.uuid4()), "eid": new_id, "tid": tenant_id,
                    "lp": i, "kst": ln["kst_code"], "opis": ln["opis"],
                    "jm": ln["jednostka"], "ilosc": ln["ilosc"],
                    "r": ln["r_jcena"], "m": ln["m_jcena"], "s": ln["s_jcena"],
                    "jcena": calc["jcena_netto"], "wart": calc["wartosc_netto"],
                    "ko": calc["ko_total"], "z": calc["z_total"], "kz": calc["kz_total"],
                })

    # Recalc sums
    with engine.begin() as conn:
        lines = _fetch_lines(conn, new_id, tenant_id, narzuty)
        sums = _calc_sums(lines, narzuty)
        conn.execute(sa.text("""
            UPDATE estimate SET
                suma_r=:sr, suma_m=:sm, suma_s=:ss,
                suma_ko=:sko, suma_z=:sz, suma_kz=:skz,
                suma_netto=:sn, suma_brutto=:sb
            WHERE id=:id
        """), {**sums, "id": new_id, "sr": sums["suma_r"], "sm": sums["suma_m"],
               "ss": sums["suma_s"], "sko": sums["suma_ko"], "sz": sums["suma_z"],
               "skz": sums["suma_kz"], "sn": sums["suma_netto"], "sb": sums["suma_brutto"]})

    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT * FROM estimate WHERE id=:id"), {"id": new_id}).fetchone()
        lines = _fetch_lines(conn, new_id, tenant_id, narzuty)

    return _row_to_estimate(row, lines, narzuty)


@router.get("/{estimate_id}")
def get_estimate(estimate_id: str, user: AuthUser) -> dict:
    """Szczegóły kosztorysu z pozycjami."""
    tenant_id = _get_tenant(user)
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT id, tender_id, variant, nazwa,
                   ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct,
                   suma_netto, suma_brutto, params, created_at
            FROM estimate WHERE id=:id AND tenant_id=:tid
        """), {"id": estimate_id, "tid": tenant_id}).fetchone()

        if not row:
            raise HTTPException(404, {"error": "not_found", "message": "Kosztorys nie znaleziony"})

        narzuty = _narzuty_from_row(row)
        lines = _fetch_lines(conn, estimate_id, tenant_id, narzuty)

    return _row_to_estimate(row, lines, narzuty)


@router.put("/{estimate_id}")
def update_estimate(estimate_id: str, body: EstimateUpdate, user: AuthUser) -> dict:
    """Aktualizuj narzuty / nazwę kosztorysu."""
    tenant_id = _get_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT id FROM estimate WHERE id=:id AND tenant_id=:tid"),
            {"id": estimate_id, "tid": tenant_id}).fetchone()
    if not row:
        raise HTTPException(404, {"error": "not_found"})

    sets = []
    params: dict = {"id": estimate_id}
    if body.nazwa is not None:
        sets.append("nazwa=:nazwa"); params["nazwa"] = body.nazwa
    if body.narzuty is not None:
        nd = body.narzuty.model_dump()
        sets += ["ko_r_pct=:ko_r","ko_s_pct=:ko_s","z_pct=:z","kz_pct=:kz","vat_pct=:vat"]
        params.update(ko_r=nd["ko_r_pct"], ko_s=nd["ko_s_pct"],
                      z=nd["z_pct"], kz=nd["kz_pct"], vat=nd["vat_pct"])

    if sets:
        with engine.begin() as conn:
            conn.execute(sa.text(f"UPDATE estimate SET {','.join(sets)} WHERE id=:id"), params)

    return get_estimate(estimate_id, user)


@router.delete("/{estimate_id}", status_code=204)
def delete_estimate(estimate_id: str, user: AuthUser) -> None:
    """Usuń kosztorys."""
    tenant_id = _get_tenant(user)
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(sa.text(
            "DELETE FROM estimate WHERE id=:id AND tenant_id=:tid"),
            {"id": estimate_id, "tid": tenant_id})


@router.post("/{estimate_id}/lines", status_code=201)
def add_line(estimate_id: str, body: LineIn, user: AuthUser) -> dict:
    """Dodaj pozycję do kosztorysu (pełny model R/M/S)."""
    tenant_id = _get_tenant(user)
    engine = get_engine()

    # Verify estimate
    with engine.connect() as conn:
        est = conn.execute(sa.text("""
            SELECT id, ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct
            FROM estimate WHERE id=:id AND tenant_id=:tid
        """), {"id": estimate_id, "tid": tenant_id}).fetchone()

    if not est:
        raise HTTPException(404, {"error": "not_found", "message": "Kosztorys nie znaleziony"})

    narzuty = _narzuty_from_row(est)
    calc = _calc_line(body.r_jcena, body.m_jcena, body.s_jcena, narzuty, body.ilosc)

    # Get next lp
    with engine.connect() as conn:
        max_lp = conn.execute(sa.text(
            "SELECT COALESCE(MAX(lp),0) FROM estimate_line WHERE estimate_id=:eid AND tenant_id=:tid"),
            {"eid": estimate_id, "tid": tenant_id}).scalar() or 0

    new_id = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO estimate_line
                (id, estimate_id, tenant_id, lp, kst_code, opis, jednostka, ilosc,
                 r_jcena, m_jcena, s_jcena, jcena_netto, wartosc_netto,
                 ko_total, z_total, kz_total,
                 icb_r_id, icb_m_id, icb_s_id,
                 description, unit, quantity, unit_price, labor_pln, material_pln, equipment_pln,
                 created_at)
            VALUES
                (:id, :eid, :tid, :lp, :kst, :opis, :jm, :ilosc,
                 :r, :m, :s, :jcena, :wart,
                 :ko, :z, :kz,
                 :icb_r, :icb_m, :icb_s,
                 :opis, :jm, :ilosc, :jcena, :r, :m, :s,
                 NOW())
        """), {
            "id": new_id, "eid": estimate_id, "tid": tenant_id,
            "lp": max_lp + 1,
            "kst": body.kst_code, "opis": body.opis,
            "jm": body.jednostka, "ilosc": body.ilosc,
            "r": body.r_jcena, "m": body.m_jcena, "s": body.s_jcena,
            "jcena": calc["jcena_netto"], "wart": calc["wartosc_netto"],
            "ko": calc["ko_total"], "z": calc["z_total"], "kz": calc["kz_total"],
            "icb_r": body.icb_r_id, "icb_m": body.icb_m_id, "icb_s": body.icb_s_id,
        })

    _recalc_sums(estimate_id, tenant_id, engine, narzuty)
    return get_estimate(estimate_id, user)


@router.put("/{estimate_id}/lines/{line_id}")
def update_line(estimate_id: str, line_id: str, body: LineUpdate, user: AuthUser) -> dict:
    """Edytuj pozycję kosztorysu."""
    tenant_id = _get_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        est = conn.execute(sa.text("""
            SELECT e.id, e.ko_r_pct, e.ko_s_pct, e.z_pct, e.kz_pct, e.vat_pct
            FROM estimate e
            JOIN estimate_line l ON l.estimate_id=e.id
            WHERE e.id=:eid AND e.tenant_id=:tid AND l.id=:lid
        """), {"eid": estimate_id, "tid": tenant_id, "lid": line_id}).fetchone()

    if not est:
        raise HTTPException(404, {"error": "not_found"})

    narzuty = _narzuty_from_row(est)

    # Get current values
    with engine.connect() as conn:
        cur = conn.execute(sa.text(
            "SELECT r_jcena, m_jcena, s_jcena, ilosc FROM estimate_line WHERE id=:id"),
            {"id": line_id}).fetchone()

    r = float(body.r_jcena if body.r_jcena is not None else (cur.r_jcena or 0))
    m = float(body.m_jcena if body.m_jcena is not None else (cur.m_jcena or 0))
    s = float(body.s_jcena if body.s_jcena is not None else (cur.s_jcena or 0))
    ilosc = float(body.ilosc if body.ilosc is not None else (cur.ilosc or 1))
    calc = _calc_line(r, m, s, narzuty, ilosc)

    sets = ["r_jcena=:r", "m_jcena=:m", "s_jcena=:s", "ilosc=:ilosc",
            "jcena_netto=:jcena", "wartosc_netto=:wart",
            "ko_total=:ko", "z_total=:z", "kz_total=:kz",
            "labor_pln=:r", "material_pln=:m", "equipment_pln=:s",
            "quantity=:ilosc", "unit_price=:jcena"]
    params: dict = {"id": line_id, "r": r, "m": m, "s": s, "ilosc": ilosc,
                    "jcena": calc["jcena_netto"], "wart": calc["wartosc_netto"],
                    "ko": calc["ko_total"], "z": calc["z_total"], "kz": calc["kz_total"]}

    if body.kst_code is not None:
        sets.append("kst_code=:kst"); params["kst"] = body.kst_code
    if body.opis is not None:
        sets.append("opis=:opis"); sets.append("description=:opis"); params["opis"] = body.opis
    if body.jednostka is not None:
        sets.append("jednostka=:jm"); sets.append("unit=:jm"); params["jm"] = body.jednostka
    if body.icb_r_id is not None:
        sets.append("icb_r_id=:icb_r"); params["icb_r"] = body.icb_r_id
    if body.icb_m_id is not None:
        sets.append("icb_m_id=:icb_m"); params["icb_m"] = body.icb_m_id
    if body.icb_s_id is not None:
        sets.append("icb_s_id=:icb_s"); params["icb_s"] = body.icb_s_id

    with engine.begin() as conn:
        conn.execute(sa.text(f"UPDATE estimate_line SET {','.join(sets)} WHERE id=:id"), params)

    _recalc_sums(estimate_id, tenant_id, engine, narzuty)
    return get_estimate(estimate_id, user)


@router.delete("/{estimate_id}/lines/{line_id}", status_code=204)
def delete_line(estimate_id: str, line_id: str, user: AuthUser) -> None:
    """Usuń pozycję z kosztorysu."""
    tenant_id = _get_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        est = conn.execute(sa.text("""
            SELECT e.id, e.ko_r_pct, e.ko_s_pct, e.z_pct, e.kz_pct, e.vat_pct
            FROM estimate e WHERE e.id=:eid AND e.tenant_id=:tid
        """), {"eid": estimate_id, "tid": tenant_id}).fetchone()

    if not est:
        raise HTTPException(404)

    narzuty = _narzuty_from_row(est)

    with engine.begin() as conn:
        conn.execute(sa.text(
            "DELETE FROM estimate_line WHERE id=:id AND estimate_id=:eid AND tenant_id=:tid"),
            {"id": line_id, "eid": estimate_id, "tid": tenant_id})

    # Renumber lp
    with engine.begin() as conn:
        rows = conn.execute(sa.text("""
            SELECT id FROM estimate_line WHERE estimate_id=:eid AND tenant_id=:tid
            ORDER BY COALESCE(lp,0), created_at
        """), {"eid": estimate_id, "tid": tenant_id}).fetchall()
        for i, r in enumerate(rows, 1):
            conn.execute(sa.text("UPDATE estimate_line SET lp=:lp WHERE id=:id"),
                        {"lp": i, "id": str(r.id)})

    _recalc_sums(estimate_id, tenant_id, engine, narzuty)


@router.post("/{estimate_id}/recalc")
def recalc_estimate(estimate_id: str, user: AuthUser) -> dict:
    """Przelicz summy R/M/S i narzuty dla wszystkich pozycji."""
    tenant_id = _get_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        est = conn.execute(sa.text("""
            SELECT id, ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct
            FROM estimate WHERE id=:id AND tenant_id=:tid
        """), {"id": estimate_id, "tid": tenant_id}).fetchone()

    if not est:
        raise HTTPException(404)

    narzuty = _narzuty_from_row(est)
    _recalc_sums(estimate_id, tenant_id, engine, narzuty)
    return get_estimate(estimate_id, user)


# ─── Legacy PATCH /lines (backward compat) ───────────────────────────────────

@router.patch("/{estimate_id}/lines")
def patch_estimate_lines_legacy(estimate_id: str, lines: list[dict], user: AuthUser) -> dict:
    """Legacy bulk-patch. Każdy obiekt bez 'id' = insert, z '_delete'=true = delete."""
    tenant_id = _get_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        est = conn.execute(sa.text("""
            SELECT id, ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct
            FROM estimate WHERE id=:id AND tenant_id=:tid
        """), {"id": estimate_id, "tid": tenant_id}).fetchone()

    if not est:
        raise HTTPException(404, {"error": "not_found"})

    narzuty = _narzuty_from_row(est)

    with engine.begin() as conn:
        for ln in lines:
            line_id = ln.get("id")
            if ln.get("_delete") and line_id:
                conn.execute(sa.text(
                    "DELETE FROM estimate_line WHERE id=:id AND estimate_id=:eid AND tenant_id=:tid"),
                    {"id": line_id, "eid": estimate_id, "tid": tenant_id})
                continue

            # Map legacy field names → new
            r = float(ln.get("labor_pln") or ln.get("r_jcena") or 0)
            m = float(ln.get("material_pln") or ln.get("m_jcena") or 0)
            s = float(ln.get("equipment_pln") or ln.get("s_jcena") or 0)
            ilosc = float(ln.get("quantity") or ln.get("ilosc") or 1)
            opis = ln.get("description") or ln.get("opis") or ""
            jm = ln.get("unit") or ln.get("jednostka") or "szt"
            calc = _calc_line(r, m, s, narzuty, ilosc)

            if not line_id:
                # Insert
                max_lp = conn.execute(sa.text(
                    "SELECT COALESCE(MAX(lp),0) FROM estimate_line WHERE estimate_id=:eid AND tenant_id=:tid"),
                    {"eid": estimate_id, "tid": tenant_id}).scalar() or 0
                conn.execute(sa.text("""
                    INSERT INTO estimate_line
                        (id, estimate_id, tenant_id, lp, opis, jednostka, ilosc,
                         r_jcena, m_jcena, s_jcena, jcena_netto, wartosc_netto,
                         ko_total, z_total, kz_total,
                         description, unit, quantity, unit_price, labor_pln, material_pln, equipment_pln,
                         created_at)
                    VALUES
                        (:id, :eid, :tid, :lp, :opis, :jm, :ilosc,
                         :r, :m, :s, :jcena, :wart, :ko, :z, :kz,
                         :opis, :jm, :ilosc, :jcena, :r, :m, :s, NOW())
                """), {
                    "id": str(uuid.uuid4()), "eid": estimate_id, "tid": tenant_id,
                    "lp": max_lp + 1, "opis": opis, "jm": jm, "ilosc": ilosc,
                    "r": r, "m": m, "s": s,
                    "jcena": calc["jcena_netto"], "wart": calc["wartosc_netto"],
                    "ko": calc["ko_total"], "z": calc["z_total"], "kz": calc["kz_total"],
                })
            else:
                # Update
                conn.execute(sa.text("""
                    UPDATE estimate_line SET
                        opis=:opis, jednostka=:jm, ilosc=:ilosc,
                        r_jcena=:r, m_jcena=:m, s_jcena=:s,
                        jcena_netto=:jcena, wartosc_netto=:wart,
                        ko_total=:ko, z_total=:z, kz_total=:kz,
                        description=:opis, unit=:jm, quantity=:ilosc,
                        unit_price=:jcena, labor_pln=:r, material_pln=:m, equipment_pln=:s
                    WHERE id=:id AND estimate_id=:eid AND tenant_id=:tid
                """), {
                    "id": line_id, "eid": estimate_id, "tid": tenant_id,
                    "opis": opis, "jm": jm, "ilosc": ilosc,
                    "r": r, "m": m, "s": s,
                    "jcena": calc["jcena_netto"], "wart": calc["wartosc_netto"],
                    "ko": calc["ko_total"], "z": calc["z_total"], "kz": calc["kz_total"],
                })

    _recalc_sums(estimate_id, tenant_id, engine, narzuty)
    return get_estimate(estimate_id, user)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _recalc_sums(estimate_id: str, tenant_id: str, engine, narzuty: dict) -> None:
    """Przelicz i zapisz summy kosztorysu."""
    with engine.begin() as conn:
        lines = _fetch_lines(conn, estimate_id, tenant_id, narzuty)
        sums = _calc_sums(lines, narzuty)
        conn.execute(sa.text("""
            UPDATE estimate SET
                suma_r=:sr, suma_m=:sm, suma_s=:ss,
                suma_ko=:sko, suma_z=:sz, suma_kz=:skz,
                suma_netto=:sn, suma_brutto=:sb,
                total_net_pln=:sn
            WHERE id=:id
        """), {
            "id": estimate_id,
            "sr": sums["suma_r"], "sm": sums["suma_m"], "ss": sums["suma_s"],
            "sko": sums["suma_ko"], "sz": sums["suma_z"], "skz": sums["suma_kz"],
            "sn": sums["suma_netto"], "sb": sums["suma_brutto"],
        })
