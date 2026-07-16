"""Baza Konkurencyjności connector — pobiera ogłoszenia z BK API.

Endpoint: https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl/api/announcements/search
Publiczne REST API, bez klucza (GET z query params w formacie tablicowym).

Parametry filtrowania:
  - status[0]=PUBLISHED
  - publicationDateRange[from]=YYYY-MM-DD
  - publicationDateRange[to]=YYYY-MM-DD
  - page, pageSize (max ~100 per request)
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

logger = logging.getLogger(__name__)

BK_BASE = "https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl"
BK_SEARCH_EP = f"{BK_BASE}/api/announcements/search"
BK_DETAIL_EP = f"{BK_BASE}/api/announcements/{{oid}}"
BK_PUBLIC_URL = f"{BK_BASE}/ogloszenia/{{oid}}"

_PAGE_SIZE = 100          # max items per request
_RATE_SLEEP = 0.5         # sekundy między stronami
_TIMEOUT = 20             # sekund na request
_MAX_RETRIES = 3

# Mapowanie kategorii BK → reprezentatywne kody CPV
# Używane gdy detail fetch jest wyłączony lub nie zwraca CPV
_CATEGORY_TO_CPV: dict[str, str] = {
    "roboty budowlane": "45000000-7",
    "dostawy": "33000000-0",
    "dostawa": "33000000-0",
    "usługi": "73000000-2",
    "usługa": "73000000-2",
    "szkolenia": "80000000-4",
    "szkolenie": "80000000-4",
    "it": "72000000-5",
    "informatyczne": "72000000-5",
}


def _get_json(url: str, params: list[tuple], attempt: int = 0) -> dict | None:
    """GET z prostym retry."""
    try:
        r = requests.get(
            url,
            params=params,
            timeout=_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        if attempt < _MAX_RETRIES - 1:
            wait = 2 ** attempt
            logger.warning("source=bk url=%s error=%s retry_in=%ds", url, exc, wait)
            time.sleep(wait)
            return _get_json(url, params, attempt + 1)
        logger.error("source=bk url=%s FAILED after %d attempts: %s", url, _MAX_RETRIES, exc)
        return None


def fetch_bk_notices(
    *,
    date_from: date,
    date_to: date,
    status: str = "PUBLISHED",
    page_size: int = _PAGE_SIZE,
    fetch_details: bool = False,
) -> list[dict[str, Any]]:
    """Pobierz wszystkie ogłoszenia BK z podanego zakresu dat.

    Zwraca listę surowych dict-ów (pola z search endpoint + derived url/id).
    Używa paginacji — automatycznie pobiera wszystkie strony.

    Args:
        fetch_details: jeśli True, pobiera szczegóły każdego ogłoszenia
                       (zawierają CPV). Wolniejsze (1 req/ogłoszenie).
    """
    results: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    page = 1

    logger.info(
        "source=bk fetching date_from=%s date_to=%s status=%s",
        date_from, date_to, status,
    )

    while True:
        params: list[tuple] = [
            (f"status[0]", status),
            ("publicationDateRange[from]", date_from.isoformat()),
            ("publicationDateRange[to]", date_to.isoformat()),
            ("page", str(page)),
            ("pageSize", str(page_size)),
        ]

        data = _get_json(BK_SEARCH_EP, params)
        if not data or data.get("status") != "OK":
            logger.warning("source=bk page=%d bad response: %s", page, data)
            break

        inner = data.get("data", {})
        advertisements = inner.get("advertisements", [])
        meta = inner.get("meta", {})
        total = meta.get("total", 0)

        if not advertisements:
            break

        for ad in advertisements:
            oid = ad.get("id")
            if oid and oid not in seen_ids:
                seen_ids.add(oid)
                # Dodaj URL do rekordu
                ad["_bk_url"] = BK_PUBLIC_URL.format(oid=oid)
                results.append(ad)

        logger.info(
            "source=bk page=%d got=%d total_so_far=%d / %d",
            page, len(advertisements), len(results), total,
        )

        if len(results) >= total or len(advertisements) < page_size:
            break

        page += 1
        time.sleep(_RATE_SLEEP)

    logger.info("source=bk fetch complete: %d notices", len(results))

    # Opcjonalnie pobierz szczegóły (wolne, ale daje CPV)
    if fetch_details and results:
        logger.info("source=bk fetching details for %d notices...", len(results))
        _enrich_with_details(results)

    return results


def _enrich_with_details(notices: list[dict[str, Any]]) -> None:
    """Wzbogać rekordy o dane z detail endpoint (CPV, wartość, places).

    Modyfikuje dicts in-place. Wolne przy dużej ilości — używaj selektywnie.
    """
    for i, notice in enumerate(notices):
        oid = notice.get("id")
        if not oid:
            continue
        try:
            data = _get_json(BK_DETAIL_EP.format(oid=oid), [])
            if data and data.get("status") == "OK":
                detail = data.get("data", {}).get("advertisement", {})
                # Merge detail fields into notice
                notice["orders"] = detail.get("orders", [])
                notice["planned_sign_date"] = detail.get("planned_sign_date")
            if i % 50 == 0:
                logger.debug("source=bk details %d/%d", i, len(notices))
            time.sleep(0.2)  # delikatny rate limit
        except Exception as exc:
            logger.debug("source=bk detail skip id=%s: %s", oid, exc)


def _parse_bk_date(raw: str | None) -> datetime | None:
    """Parsuj daty BK: 'YYYY-MM-DD' lub 'YYYY-MM-DD HH:MM:SS'."""
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _extract_cpv_from_notice(notice: dict) -> list[str]:
    """Wyciągnij kody CPV z ogłoszenia BK (search endpoint nie ma CPV, mamy je w raw)."""
    cpv_codes: list[str] = []
    orders = notice.get("orders", [])
    for order in orders:
        for item in order.get("order_items", []):
            for cpv_item in item.get("cpv_items", []):
                code = cpv_item.get("code", "")
                if code:
                    cpv_codes.append(code)
    return list(dict.fromkeys(cpv_codes))  # deduplikacja z zachowaniem kolejności


def _extract_value(notice: dict) -> Decimal | None:
    """Wyciągnij wartość zamówienia z ogłoszenia."""
    orders = notice.get("orders", [])
    for order in orders:
        raw_val = order.get("estimated_value")
        if raw_val is not None:
            try:
                return Decimal(str(raw_val))
            except InvalidOperation:
                pass
    return None


def _extract_voivodeship(notice: dict) -> str | None:
    """Wyciągnij województwo z places fulfillment."""
    orders = notice.get("orders", [])
    for order in orders:
        for item in order.get("order_items", []):
            for place in item.get("fulfillment_places", []):
                voi = place.get("voivodeship")
                if voi:
                    return voi.lower()
    # fallback — pole fulfillment_place z search np. "Gliwice, śląskie"
    fp = notice.get("fulfillment_place", "")
    if fp and "," in fp:
        return fp.split(",")[-1].strip().lower()
    return None


def normalize_bk_notice(notice: dict[str, Any]) -> Any:
    """Normalize raw BK notice dict → TenderIn.

    Import TenderIn lokalnie żeby uniknąć circular import.
    Zwraca TenderIn | None.
    """
    from .normalize import TenderIn, normalize_voivodeship

    oid = notice.get("id")
    if not oid:
        return None

    title = (notice.get("title") or "").strip()
    if not title:
        return None

    external_id = str(oid)
    buyer = (notice.get("advertiser_name") or "").strip() or None
    published_at = _parse_bk_date(notice.get("publication_date"))
    deadline_at = _parse_bk_date(notice.get("submission_deadline"))
    url = notice.get("_bk_url") or BK_PUBLIC_URL.format(oid=oid)

    # CPV — z search endpoint nie ma CPV, mogą być w szczegółach (orders)
    cpv = _extract_cpv_from_notice(notice)

    # Fallback CPV: szukaj w tytule/treści nazw kategorii
    if not cpv:
        cpv = _infer_cpv_from_text(title, notice.get("content", "") or "")

    value_pln = _extract_value(notice)
    voivodeship = normalize_voivodeship(_extract_voivodeship(notice))

    return TenderIn(
        source="bk",
        external_id=external_id,
        title=title,
        buyer=buyer,
        cpv=cpv,
        voivodeship=voivodeship,
        nuts_code=None,
        value_pln=value_pln,
        deadline_at=deadline_at,
        published_at=published_at,
        url=url,
        raw=notice,
    )


def _infer_cpv_from_text(title: str, content: str) -> list[str]:
    """Wydedukuj kod CPV na podstawie słów kluczowych w tytule/treści.

    Zwraca listę z jednym kodem lub pustą listę.
    """
    text = (title + " " + content).lower()
    for keyword, cpv_code in _CATEGORY_TO_CPV.items():
        if keyword in text:
            return [cpv_code]
    # BK to głównie projekty UE — domyślnie "usługi różne"
    return ["98000000-3"]  # Inne usługi publiczne (marker dla filtru)
