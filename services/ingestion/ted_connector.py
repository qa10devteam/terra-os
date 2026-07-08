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
_PAGE_SIZE = 100


class TEDConnector:
    """Fetches construction notices from TED EU v3 API for Poland."""

    def __init__(self, timeout: int = 30) -> None:
        self._client = httpx.Client(timeout=timeout)

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
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.error("TED API error (page %d): %s", page, exc)
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
