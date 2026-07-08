"""M1 — BZP connector: fetches notices from ezamowienia.gov.pl public API."""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)

BZP_BASE = "https://ezamowienia.gov.pl/mo-board/api/v1"
_NOTICE_EP = f"{BZP_BASE}/notice"

# CPV codes — pełne budownictwo (CPV 45)
# Zachowane dla kompatybilności wstecznej
EARTHWORKS_CPV = [
    "45111200-0",  # Przygotowanie terenu + roboty ziemne — PRIMARY
    "45111000-8",  # Roboty ziemne ogólne
    "45112000-5",  # Usuwanie gleby
    "45112700-2",  # Kształtowanie terenu
    "45233120-6",  # Budowa dróg — PRIMARY
    "45233200-1",  # Różne nawierzchnie
    "45233140-2",  # Roboty drogowe
    "45231300-8",  # Wodociągi i rurociągi (+ roboty ziemne)
    "45232410-9",  # Kanalizacja ściekowa
    "45246000-3",  # Regulacja rzek, wały
    "45112500-0",  # Tereny poprzemysłowe
]

# CPV codes — pełne budownictwo (CPV 45)
CONSTRUCTION_CPV_PREFIXES = [
    "45",  # Cała dywizja 45 — Roboty budowlane
]

# CPV prefixes for broader matching (first 5 digits = division)
# Zachowane dla kompatybilności wstecznej
EARTHWORKS_CPV_PREFIXES = {"45111", "45112", "45233", "45231", "45232", "45246"}


def is_construction_scope(cpv_codes: list[str]) -> bool:
    """Return True if any CPV code is in construction scope (division 45)."""
    return any(c.startswith("45") for c in cpv_codes)


class BZPRawNotice:
    """Raw notice from BZP API — just a typed dict wrapper."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._d = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._d.get(key, default)

    @property
    def raw(self) -> dict[str, Any]:
        return self._d


def _cpv_matches(cpv_list: list[str]) -> bool:
    """Return True if any CPV code is in construction scope (backward compat alias)."""
    return is_construction_scope(cpv_list)


class BZPConnector:
    """Fetches notices from the public BZP API.

    Endpoint: GET https://ezamowienia.gov.pl/mo-board/api/v1/notice
    Auth: None (public endpoint)
    Format: JSON

    Reference: https://ezamowienia.gov.pl/pl/integracja/
    Attachment 3: Instrukcja integracji z API BZP
    """

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        page_size: int = 50,
        max_pages: int = 100,
    ) -> None:
        self._timeout = timeout
        self._page_size = page_size
        self._max_pages = max_pages
        self._client: httpx.Client | None = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def fetch_notices(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        cpv_codes: list[str] | None = None,
        voivodeship: str | None = None,
        order_type: str = "RC",  # RC = roboty budowlane
    ) -> list[BZPRawNotice]:
        """Fetch raw notices from BZP API.

        BZP API does NOT support true pagination — pageNumber always returns the same set.
        We work around this by iterating in half-day windows (AM/PM) within the date range.
        pageSize=500 is the effective BZP max. Each half-day window returns up to 500 results.
        Results are deduplicated by bzpNumber.
        """
        from datetime import timedelta

        today = date.today()
        d_from = date_from or (today - timedelta(days=7))
        d_to = date_to or today

        seen: dict[str, BZPRawNotice] = {}  # bzpNumber → notice (dedup)
        page_size = 500  # BZP effective max (1000 breaks, 500 works)

        with self._get_client() as client:
            current = d_from
            while current <= d_to:
                # Split each day into 2 windows (AM: 00-12, PM: 12-24) to stay under 500 limit
                windows = [
                    (f"{current}T00:00:00", f"{current}T11:59:59"),
                    (f"{current}T12:00:00", f"{current}T23:59:59"),
                ]
                for win_from, win_to in windows:
                    params: dict[str, Any] = {
                        "pageSize": page_size,
                        "pageNumber": 0,
                        "NoticeType": "ContractNotice",
                        "PublicationDateFrom": win_from,
                        "PublicationDateTo": win_to,
                    }
                    try:
                        resp = client.get(_NOTICE_EP, params=params, timeout=self._timeout)
                        resp.raise_for_status()
                        data = resp.json()
                    except httpx.HTTPError as exc:
                        logger.warning("BZP API error (%s): %s", win_from, exc)
                        continue

                    notices = data if isinstance(data, list) else data.get("notices", data.get("content", []))
                    win_count = 0
                    for n in notices:
                        raw = BZPRawNotice(n)
                        key = raw.get("bzpNumber") or raw.get("noticeNumber") or raw.get("id")
                        if key and key not in seen:
                            seen[key] = raw
                            win_count += 1
                    if win_count:
                        logger.debug("BZP %s: %d new (total %d)", win_from[:10], win_count, len(seen))

                current += timedelta(days=1)

        results = list(seen.values())
        logger.info("BZP fetch complete: %d unique notices over %d days", len(results), (d_to - d_from).days + 1)
        return results

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_params(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
        cpv_codes: list[str],
        voivodeship: str | None,
        order_type: str,
        page: int,
        size: int,
    ) -> dict[str, Any]:
        # BZP API (ezamowienia.gov.pl) expects these exact parameter names
        params: dict[str, Any] = {
            "pageSize": size,
            "pageNumber": page,
            "NoticeType": "ContractNotice",
        }
        if date_from:
            params["PublicationDateFrom"] = date_from.strftime("%Y-%m-%dT00:00:00")
        if date_to:
            params["PublicationDateTo"] = date_to.strftime("%Y-%m-%dT23:59:59")
        # NOTE: BZP API does NOT support cpvCodes or voivodeship filters in list endpoint.
        # CPV/scope filtering is done in normalize_bzp_notice() after fetching.
        return params

    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "Accept": "application/json",
                "User-Agent": "TerraOS/0.1 (terra-os.qa10.io)",
            },
            follow_redirects=True,
        )
