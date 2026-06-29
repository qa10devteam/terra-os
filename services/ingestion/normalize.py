"""M1 — Normalize: converts raw BZP/TED/BK notices to canonical TenderIn model."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .bzp_connector import BZPRawNotice, _cpv_matches

logger = logging.getLogger(__name__)

# Mapping of Polish voivodeship names/codes to canonical lowercase strings
_VOIVODESHIP_ALIASES: dict[str, str] = {
    "dolnośląskie": "dolnośląskie",
    "dolnoslaskie": "dolnośląskie",
    "lower silesian": "dolnośląskie",
    "kujawsko-pomorskie": "kujawsko-pomorskie",
    "lubelskie": "lubelskie",
    "lubuskie": "lubuskie",
    "łódzkie": "łódzkie",
    "lodzkie": "łódzkie",
    "małopolskie": "małopolskie",
    "malopolskie": "małopolskie",
    "mazowieckie": "mazowieckie",
    "opolskie": "opolskie",
    "podkarpackie": "podkarpackie",
    "podlaskie": "podlaskie",
    "pomorskie": "pomorskie",
    "śląskie": "śląskie",
    "slaskie": "śląskie",
    "świętokrzyskie": "świętokrzyskie",
    "swietokrzyskie": "świętokrzyskie",
    "warmińsko-mazurskie": "warmińsko-mazurskie",
    "warminsko-mazurskie": "warmińsko-mazurskie",
    "wielkopolskie": "wielkopolskie",
    "zachodniopomorskie": "zachodniopomorskie",
}


def normalize_voivodeship(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = raw.strip().lower()
    return _VOIVODESHIP_ALIASES.get(cleaned, cleaned)


def normalize_cpv(raw_cpv: Any) -> list[str]:
    """Normalize CPV codes from various formats to list of strings."""
    if not raw_cpv:
        return []
    if isinstance(raw_cpv, str):
        # comma-separated or single
        codes = [c.strip() for c in raw_cpv.split(",")]
    elif isinstance(raw_cpv, list):
        codes = [str(c).strip() for c in raw_cpv]
    else:
        return []
    # Normalize format: "45233120-6" or "45233120" → "45233120-6"
    result = []
    for code in codes:
        code = code.strip().replace(" ", "")
        if re.match(r"^\d{8}-\d$", code):
            result.append(code)
        elif re.match(r"^\d{8}$", code):
            # Missing check digit — keep as-is with unknown suffix
            result.append(code)
        elif code:
            result.append(code)
    return result


def parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(raw[:len(fmt)].replace("Z", ""), fmt.replace("%z", ""))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    logger.debug("Cannot parse datetime: %r", raw)
    return None


def parse_value(raw: Any) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(str(raw)).quantize(Decimal("0.01"))
    except Exception:
        return None


class TenderIn:
    """Canonical representation of a tender before DB upsert.

    This is NOT a SQLAlchemy model — it's a pure data transfer object.
    """

    __slots__ = (
        "source",
        "external_id",
        "title",
        "buyer",
        "cpv",
        "voivodeship",
        "value_pln",
        "deadline_at",
        "published_at",
        "url",
        "raw",
    )

    def __init__(
        self,
        *,
        source: str,
        external_id: str,
        title: str,
        buyer: str | None,
        cpv: list[str],
        voivodeship: str | None,
        value_pln: Decimal | None,
        deadline_at: datetime | None,
        published_at: datetime | None,
        url: str | None,
        raw: dict,
    ) -> None:
        self.source = source
        self.external_id = external_id
        self.title = title
        self.buyer = buyer
        self.cpv = cpv
        self.voivodeship = voivodeship
        self.value_pln = value_pln
        self.deadline_at = deadline_at
        self.published_at = published_at
        self.url = url
        self.raw = raw


def normalize_bzp_notice(notice: BZPRawNotice) -> TenderIn | None:
    """Convert raw BZP notice to TenderIn. Returns None if notice should be skipped."""
    # Must be construction works
    contract_type = notice.get("contractType", "")
    if contract_type not in ("RC", "RB", ""):  # RC = roboty, empty = unknown
        if contract_type in ("D", "U"):  # Dostawa / Usługa — skip
            return None

    cpv = normalize_cpv(notice.get("cpvCodes", []))
    if not cpv and not _cpv_matches([]):
        return None

    # External ID: use noticeNumber as canonical ID
    external_id = notice.get("noticeNumber", "")
    if not external_id:
        return None

    title = (notice.get("procurementObject") or notice.get("title") or "").strip()
    if not title:
        return None

    buyer = (notice.get("orderingPartyName") or notice.get("buyer") or "").strip() or None

    voivodeship = normalize_voivodeship(
        notice.get("executionPlace") or notice.get("voivodeship")
    )

    # Value: prefer estimatedValue, fallback to range
    value_pln = parse_value(notice.get("estimatedValue")) or parse_value(
        notice.get("estimatedValueFrom")
    )

    deadline_at = parse_datetime(
        notice.get("submissionDeadlineDate") or notice.get("deadline")
    )
    published_at = parse_datetime(
        notice.get("noticePublicationDate") or notice.get("publishedAt")
    )

    # Build URL
    notice_number = notice.get("noticeNumber", "")
    url = (
        f"https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/id/{notice_number}"
        if notice_number
        else None
    )

    return TenderIn(
        source="bzp",
        external_id=external_id,
        title=title,
        buyer=buyer,
        cpv=cpv,
        voivodeship=voivodeship,
        value_pln=value_pln,
        deadline_at=deadline_at,
        published_at=published_at,
        url=url,
        raw=notice.raw,
    )
