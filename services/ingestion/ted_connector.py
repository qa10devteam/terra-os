"""TED EU v3 connector — fetches Polish construction notices via CELLAR search API."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"

# Fields validated against TED v3 API (2026-07-08) — only accepted field names
TED_FIELDS = [
    "publication-number",
    "publication-date",
    "dispatch-date",
    # Title — eForms BT-21 (lot/part level), fallback description BT-24
    "BT-21-Lot",            # title at lot level — most common
    "BT-21-Part",           # title at procedure part level
    "BT-24-Lot",            # lot description
    "BT-300-Lot",           # additional description
    "title-part",           # older format fallback
    "description-part",
    # Buyer
    "organisation-name-buyer",   # dict: {"pol": ["Nazwa"]}
    "organisation-city-buyer",   # list: ["Miasto"]
    # CPV
    "classification-cpv",        # list of 8-digit CPV codes (no dash)
    # Value
    "estimated-value-lot",       # list of decimal strings
    "estimated-value-cur-lot",   # list: ["PLN"]
    "estimated-value-glo",       # global value fallback
    "estimated-value-cur-glo",
    # Deadline
    "deadline-receipt-tender-date-lot",  # list: ["2026-12-01+01:00"]
    # Place — for voivodeship enrichment
    "place-performance-streetline1-part",
    "place-of-performance-post-code-part",
    "contract-nature",
]

# TED page size max = 100
import random

_PAGE_SIZE = 100
_MAX_RETRIES = 4
_RETRY_BASE_DELAY = 2.0  # seconds (exponential: 2, 4, 8, 16)


class TEDConnector:
    """Fetches construction notices from TED EU v3 API for Poland."""

    def __init__(self, timeout: int = 30) -> None:
        self._client = httpx.Client(timeout=timeout)

    def _fetch_page(self, query: str, page: int) -> dict | None:
        """Fetch single page with exponential backoff + jitter on 429/5xx."""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = self._client.post(
                    TED_SEARCH_URL,
                    json={
                        "query": query,
                        "fields": TED_FIELDS,
                        "limit": _PAGE_SIZE,
                        "page": page,
                    },
                )
                if resp.status_code == 429:
                    # Honour Retry-After header if present
                    retry_after = float(resp.headers.get("Retry-After", 0))
                    wait = max(retry_after, _RETRY_BASE_DELAY * (2 ** (attempt - 1)))
                    wait += random.uniform(0, wait * 0.2)  # jitter ±20%
                    logger.warning(
                        "TED 429 (page %d, attempt %d/%d) — sleep %.1fs",
                        page, attempt, _MAX_RETRIES, wait,
                    )
                    if attempt < _MAX_RETRIES:
                        import time as _t; _t.sleep(wait)
                        continue
                    logger.error("TED 429: exceeded max retries on page %d", page)
                    return None
                if resp.status_code >= 500:
                    wait = _RETRY_BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    logger.warning(
                        "TED %d (page %d, attempt %d/%d) — sleep %.1fs",
                        resp.status_code, page, attempt, _MAX_RETRIES, wait,
                    )
                    if attempt < _MAX_RETRIES:
                        import time as _t; _t.sleep(wait)
                        continue
                    return None
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException as exc:
                wait = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning("TED timeout (page %d, attempt %d): %s — retry in %.1fs", page, attempt, exc, wait)
                if attempt < _MAX_RETRIES:
                    import time as _t; _t.sleep(wait)
                    continue
                logger.error("TED timeout: exceeded max retries on page %d", page)
                return None
            except Exception as exc:
                logger.error("TED API error (page %d): %s", page, exc)
                return None
        return None

    def fetch_notices(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all PL works notices published in [date_from, date_to].

        Returns list of raw notice dicts (TED v3 JSON format).
        Max 100 per page — paginates via page param (TED supports up to ~1000 total).
        """
        if date_from is None:
            date_from = date.today() - timedelta(days=7)
        if date_to is None:
            date_to = date.today()

        date_from_s = date_from.strftime("%Y%m%d")
        date_to_s = date_to.strftime("%Y%m%d")

        query = (
            f"organisation-country-buyer=POL "
            f"AND contract-nature=works "
            f"AND publication-date>={date_from_s} "
            f"AND publication-date<={date_to_s}"
        )

        all_notices: dict[str, dict] = {}
        page = 1

        while True:
            data = self._fetch_page(query, page)
            if data is None:
                break

            notices = data.get("notices", [])
            if not notices:
                break

            for n in notices:
                pub_num = n.get("publication-number")
                if pub_num and pub_num not in all_notices:
                    all_notices[pub_num] = n

            total = data.get("totalNoticeCount", 0)
            fetched_so_far = page * _PAGE_SIZE
            logger.debug(
                "TED page %d: +%d notices (total declared: %d)", page, len(notices), total
            )

            if fetched_so_far >= total or len(notices) < _PAGE_SIZE:
                break

            page += 1

        logger.info(
            "TED fetch complete: %d unique notices (%s to %s)",
            len(all_notices),
            date_from_s,
            date_to_s,
        )
        return list(all_notices.values())

    def close(self) -> None:
        self._client.close()
