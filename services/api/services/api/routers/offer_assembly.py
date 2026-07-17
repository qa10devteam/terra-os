"""
YU-NA Intelligence — Offer Assembly Router
POST /api/v2/documents/generate  → ZIP package (Formularz+Zał.1-4+Kosztorys)
POST /api/v2/knr/map             → KNR mapping for OPZ positions
"""
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2", tags=["offer-assembly"])


# ─── Document Generator Schemas ─────────────────────────────────────────────

class TenderIn(BaseModel):
    nr_sprawy: str
    tytul: str
    zamawiajacy_nazwa: str
    cpv_kody: list[str] = []
    wartosc_brutto: Optional[float] = None
    warunek_zdolnosc_techniczna: Optional[str] = None
    warunek_sytuacja_finansowa: Optional[str] = None
    warunek_uprawnienia: Optional[str] = None
    wykluczenie_art109: Optional[str] = None
    termin_skladania: Optional[str] = None


class CompanyIn(BaseModel):
    nazwa_pelna: str
    nip: str
    adres: Optional[str] = None          # "ul. X 1, 40-000 Miasto"
    adres_ulica: Optional[str] = None
    adres_nr_budynku: Optional[str] = None
    adres_kod_pocztowy: Optional[str] = None
    adres_miasto: Optional[str] = None
    nr_krs: Optional[str] = None
    regon: Optional[str] = None
    reprezentant: Optional[str] = None
    stanowisko: Optional[str] = None
    referencje: list[dict] = []
    osoby_kluczowe: list[dict] = []


class KosztorysIn(BaseModel):
    pozycje: list[dict] = []
    suma_netto: float = 0.0
    vat_pct: float = 23.0
    suma_brutto: float = 0.0
    cennik_okres: str = "Q2/2026"
    cennik_region: str = "śląskie"


class BidStrategyIn(BaseModel):
    termin_realizacji_dni: int = 90
    gwarancja_miesiecy: int = 60
    wadium_forma: Optional[str] = None
    wadium_kwota: Optional[float] = None
    podwykonawcy: Optional[str] = None
    termin_zwiazania_dni: int = 30


class GenerateDocsRequest(BaseModel):
    tender: TenderIn
    company: CompanyIn
    kosztorys: KosztorysIn
    bid_strategy: BidStrategyIn = Field(default_factory=BidStrategyIn)
    offer_id: Optional[str] = None


# ─── KNR Mapper Schemas ──────────────────────────────────────────────────────

class OPZPositionIn(BaseModel):
    id: str
    description: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    section: Optional[str] = None


class KNRMapRequest(BaseModel):
    positions: list[OPZPositionIn]


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/documents/generate", response_class=Response,
             responses={200: {"content": {"application/zip": {}}}})
async def generate_documents(req: GenerateDocsRequest):
    """
    Generuj komplet dokumentów ofertowych jako ZIP.
    Dokumenty: Formularz Oferty + Załączniki 1-4 + Kosztorys PDF.
    """
    try:
        from ..intelligence.document_generator import (
            generate_oferta_package,
            TenderContext, CompanyContext, KosztorysContext, BidStrategy,
        )
        from datetime import datetime

        t = req.tender
        c = req.company
        k = req.kosztorys

        # Rozwiąż adres company
        if c.adres and not c.adres_ulica:
            # "ul. Budowlana 12, 40-600 Katowice" → split
            parts = c.adres.split(",")
            street_part = parts[0].strip() if parts else c.adres
            city_part = parts[1].strip() if len(parts) > 1 else ""
            # Split street into ulica + nr
            tokens = street_part.rsplit(" ", 1)
            ulica = tokens[0] if len(tokens) == 2 else street_part
            nr_bud = tokens[1] if len(tokens) == 2 else "1"
            # Split city into kod + miasto
            city_tokens = city_part.split(" ", 1)
            kod = city_tokens[0] if len(city_tokens) == 2 else ""
            miasto = city_tokens[1] if len(city_tokens) == 2 else city_part
        else:
            ulica = c.adres_ulica or "ul. Nieznana"
            nr_bud = c.adres_nr_budynku or "1"
            kod = c.adres_kod_pocztowy or "00-000"
            miasto = c.adres_miasto or "Katowice"

        termin = None
        if t.termin_skladania:
            try:
                termin = datetime.fromisoformat(t.termin_skladania.replace("Z", ""))
            except Exception:
                pass

        tender_ctx = TenderContext(
            nr_sprawy=t.nr_sprawy,
            tytul=t.tytul,
            zamawiajacy_nazwa=t.zamawiajacy_nazwa,
            cpv_kody=t.cpv_kody,
            wartosc_brutto=Decimal(str(t.wartosc_brutto)) if t.wartosc_brutto else None,
            warunek_zdolnosc_techniczna=t.warunek_zdolnosc_techniczna,
            warunek_sytuacja_finansowa=t.warunek_sytuacja_finansowa,
            warunek_uprawnienia=t.warunek_uprawnienia,
            wykluczenie_art109=t.wykluczenie_art109,
            termin_skladania=termin,
        )

        company_ctx = CompanyContext(
            nazwa_pelna=c.nazwa_pelna,
            nip=c.nip,
            adres_ulica=ulica,
            adres_nr_budynku=nr_bud,
            adres_kod_pocztowy=kod,
            adres_miasto=miasto,
            regon=c.regon,
            krs=c.nr_krs,
            referencje=c.referencje,
            osoby_kluczowe=c.osoby_kluczowe,
        )

        vat_pct = Decimal(str(k.vat_pct))
        suma_netto = Decimal(str(k.suma_netto))
        suma_brutto = Decimal(str(k.suma_brutto))
        vat_kwota = suma_brutto - suma_netto

        koszt_ctx = KosztorysContext(
            total_netto=suma_netto,
            total_brutto=suma_brutto,
            vat_stawka=vat_pct,
            vat_kwota=vat_kwota,
            pozycje=k.pozycje,
            cennik_okres=k.cennik_okres,
            cennik_region=k.cennik_region,
        )

        bs = req.bid_strategy
        bid_ctx = BidStrategy(
            termin_realizacji_dni=bs.termin_realizacji_dni,
            gwarancja_miesiecy=bs.gwarancja_miesiecy,
            wadium_forma=bs.wadium_forma,
            wadium_kwota=Decimal(str(bs.wadium_kwota)) if bs.wadium_kwota else None,
            podwykonawcy=bs.podwykonawcy,
            termin_zwiazania_dni=bs.termin_zwiazania_dni,
        )

        package = await asyncio.get_event_loop().run_in_executor(
            None, generate_oferta_package, tender_ctx, company_ctx, koszt_ctx, bid_ctx
        )

        zip_name = f"oferta_{t.nr_sprawy.replace('/', '_')}.zip"
        return Response(
            content=package.zip_content,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_name}"',
                     "X-Checksum-SHA256": package.zip_checksum,
                     "X-Documents-Count": str(len(package.documents))},
        )

    except Exception as exc:
        logger.exception("Błąd generowania dokumentów: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/knr/map")
async def map_knr_positions(req: KNRMapRequest):
    """
    Mapuj pozycje OPZ na pozycje katalogu KNR.
    4 strategie: direct → vector → keyword rules → LLM fallback.
    """
    try:
        from ..intelligence.knr_mapper import KNRMapper, OPZPosition

        mapper = KNRMapper()
        opz_positions = [
            OPZPosition(
                id=p.id,
                description=p.description,
                quantity=p.quantity,
                unit=p.unit,
                section=p.section,
            )
            for p in req.positions
        ]

        results = await mapper.map_opz_positions(opz_positions)

        return [
            {
                "id": opz.id,
                "knr_code": res.knr_code,
                "description": res.description,
                "naklady_r": res.naklady_r,
                "naklady_m": res.naklady_m,
                "naklady_s": res.naklady_s,
                "unit": res.unit,
                "confidence": res.confidence,
                "strategy_used": res.strategy_used,
                "alternatives_count": len(res.alternatives),
            }
            for opz, res in zip(opz_positions, results)
        ]
    except Exception as exc:
        logger.exception("Błąd KNR mapper: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
