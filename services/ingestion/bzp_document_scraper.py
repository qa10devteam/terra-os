"""Terra-OS BZP Document Scraper.

Fetches SWZ documents from ezamowienia.gov.pl public API.

=== VERIFIED API ENDPOINTS (no auth required) ===

1. Notice PDF — główny dokument ogłoszenia (zawiera pełny opis SWZ):
   GET /mo-board/api/v1/Board/GetNoticePdf?noticeNumber=YEAR%2FBZP%20XXXXXX%2F01
   → status 200, application/pdf, ~100–400KB
   ✅ Działa bez autoryzacji dla 2026/BZP xxxxxxxx/01

2. Raw notice (htmlBody) — pełna treść ogłoszenia w HTML:
   GET /mo-board/api/v1/notice?NoticeType=ContractNotice&PublicationDateFrom=...&PublicationDateTo=...
   → JSON list, każdy element ma "htmlBody" (HTML) + "bzpNumber" + "tenderId"
   ✅ Działa bez autoryzacji. Zawiera link do zewnętrznej platformy w sekcji 3.1

3. Zewnętrzne platformy SWZ (wyciągane z htmlBody sekcja 3.1):
   - platformazakupowa.pl — popularna platforma z publicznymi plikami
   - ezamowienia.gov.pl/mp-client — własna platforma BZP (tu też bywają pliki)
   - josephine.pl, logintrade.pl, przetargi.pl, etc.
   ✅ URL można wyciągnąć z htmlBody i podać użytkownikowi

=== NIE DZIAŁA (wymaga OAuth2) ===
  /mp-readmodels/api/Search/GetTenderDocuments  → 400/empty list anonimowo
  /mp-readmodels/api/Tender/DownloadDocument    → 401 anonimowo
  authIssuer: https://ezamowienia.gov.pl/oauth2/token (clientId: epzp_MP_FE)

=== ARCHITEKTURA DOKUMENTÓW ===
  1. notice_pdf:  oficjalne ogłoszenie BZP w PDF (zawsze dostępne)
  2. swz_link:    link do zewnętrznej platformy postępowania (np. platformazakupowa.pl)
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────

BZP_BASE = "https://ezamowienia.gov.pl"
NOTICE_PDF_API = f"{BZP_BASE}/mo-board/api/v1/Board/GetNoticePdf"
NOTICE_LIST_API = f"{BZP_BASE}/mo-board/api/v1/notice"

# Legacy constants kept for import compatibility
DOWNLOAD_API = f"{BZP_BASE}/mp-readmodels/api/Tender/DownloadDocument"

STORAGE_DIR = Path(os.environ.get("TERRA_DOCUMENTS_DIR", "/var/lib/terra-os/documents"))
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
TIMEOUT = 30  # seconds

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Regex to extract external platform URL from htmlBody section 3.1
_PLATFORM_URL_RE = re.compile(
    r'(?:3\.1\.[^<]*?Adres[^<]*?post[^<]*?powania|'
    r'Adres strony internetowej prowadzonego post[^<]*?powania)'
    r'[^<]*?</h3>\s*(?:<[^>]+>)?\s*(https?://[^\s<"\']+)',
    re.IGNORECASE | re.DOTALL,
)

# ────────────────────────────────────────────────────────────────────
# Data structures
# ────────────────────────────────────────────────────────────────────

@dataclass
class TenderDocument:
    """Represents a single document from BZP."""
    object_id: str
    name: str
    filename: str
    url: str
    published_date: str | None = None
    state: str = "Published"
    file_size: int | None = None
    content_type: str | None = None
    local_path: str | None = None
    doc_type: str = "OTHER"


@dataclass
class FetchResult:
    """Result of fetching documents for a tender."""
    tender_id: str
    bzp_number: str | None = None
    documents: list[TenderDocument] = field(default_factory=list)
    downloaded: int = 0
    errors: list[str] = field(default_factory=list)
    notice_pdf_path: str | None = None
    swz_platform_url: str | None = None


# ────────────────────────────────────────────────────────────────────
# Core Scraper
# ────────────────────────────────────────────────────────────────────

class BZPDocumentScraper:
    """Scrapes SWZ documents from ezamowienia.gov.pl public API."""

    def __init__(self, storage_dir: Path | None = None, db_engine=None):
        self.storage_dir = storage_dir or STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._engine = db_engine
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=TIMEOUT,
                follow_redirects=True,
                headers={
                    "User-Agent": _BROWSER_UA,
                    "Accept": "application/json, application/pdf, */*",
                    "Accept-Language": "pl-PL,pl;q=0.9",
                    "Referer": "https://ezamowienia.gov.pl/",
                },
            )
        return self._client

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ─── Public API ──────────────────────────────────────────────────

    def list_documents(self, tender_id: str) -> list[TenderDocument]:
        """List available documents for a tender.

        Dla każdego przetargu BZP generujemy:
        1. Notice PDF (pobierany przez GetNoticePdf — zawsze publiczny)
        2. SWZ Link — jeśli htmlBody zawiera URL zewnętrznej platformy

        Args:
            tender_id: OCDS tender ID (ocds-148610-xxx) lub numer BZP (2026/BZP...)

        Returns:
            Lista TenderDocument (min. 1 dla notice_pdf)
        """
        # Resolve BZP number
        if re.match(r"\d{4}/BZP[\s\u00a0]", tender_id):
            bzp_number = tender_id
        else:
            bzp_number = self._resolve_bzp_number(tender_id)

        if not bzp_number:
            logger.warning("Cannot resolve BZP number for %s", tender_id)
            return []

        docs: list[TenderDocument] = []
        safe_bzp = re.sub(r"[^0-9A-Za-z]", "_", bzp_number)

        # 1. Notice PDF
        pdf_url = self._notice_pdf_url(bzp_number)
        notice_pdf = TenderDocument(
            object_id=f"notice_pdf_{safe_bzp}",
            name=f"Ogłoszenie o zamówieniu {bzp_number}",
            filename=f"ogloszenie_{safe_bzp}.pdf",
            url=pdf_url,
            state="Published",
            doc_type="NOTICE",
        )
        docs.append(notice_pdf)

        # 2. SWZ external platform link (from htmlBody)
        swz_url = self._get_swz_platform_url(bzp_number)
        if swz_url:
            docs.append(TenderDocument(
                object_id=f"swz_link_{safe_bzp}",
                name=f"Platforma SWZ — {swz_url}",
                filename=f"swz_link_{safe_bzp}.url",
                url=swz_url,
                state="Published",
                doc_type="SWZ",
            ))

        logger.info("Listed %d documents for %s (bzp=%s)", len(docs), tender_id, bzp_number)
        return docs

    def download_document(self, tender_id: str, doc: TenderDocument) -> Path | None:
        """Download a single document file.

        - Notice PDFs (object_id starts 'notice_pdf_'): GET doc.url → PDF
        - SWZ Links (object_id starts 'swz_link_'): save URL as .url file (no download)
        """
        client = self._get_client()

        # SWZ link — save URL text file, don't attempt binary download
        if doc.object_id.startswith("swz_link_"):
            safe_dir = re.sub(r"[^\w\-]", "_", tender_id)
            doc_dir = self.storage_dir / safe_dir
            doc_dir.mkdir(parents=True, exist_ok=True)
            dest = doc_dir / doc.filename
            dest.write_text(f"[InternetShortcut]\nURL={doc.url}\n")
            doc.local_path = str(dest)
            doc.file_size = len(dest.read_bytes())
            logger.info("Saved SWZ link shortcut: %s → %s", doc.url, dest)
            return dest

        # Regular file download
        download_url = doc.url
        if not download_url.startswith("http"):
            logger.error("Invalid URL for document %s: %r", doc.filename, download_url)
            return None

        safe_dir = re.sub(r"[^\w\-]", "_", tender_id)
        doc_dir = self.storage_dir / safe_dir
        doc_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = re.sub(r'[/\\<>:"|?*]', "_", doc.filename) or f"doc_{doc.object_id[-8:]}"
        dest = doc_dir / safe_filename

        try:
            with client.stream("GET", download_url) as resp:
                resp.raise_for_status()
                ct = resp.headers.get("content-type", "application/octet-stream")
                # Detect PDF magic bytes if served as octet-stream
                doc.content_type = ct

                cl = resp.headers.get("content-length")
                if cl and int(cl) > MAX_FILE_SIZE:
                    logger.warning("File too large %s: %s bytes", doc.filename, cl)
                    return None

                total = 0
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        total += len(chunk)
                        if total > MAX_FILE_SIZE:
                            logger.warning("File exceeded max size: %s", doc.filename)
                            f.close()
                            dest.unlink(missing_ok=True)
                            return None
                        f.write(chunk)

                doc.file_size = total
                doc.local_path = str(dest)
                logger.info("Downloaded %s (%dKB) → %s", doc.filename, total // 1024, dest)
                return dest

        except httpx.HTTPStatusError as exc:
            logger.error("HTTP %s downloading %s: %s", exc.response.status_code, doc.filename, exc)
            dest.unlink(missing_ok=True)
            return None
        except httpx.HTTPError as exc:
            logger.error("Failed to download %s: %s", doc.filename, exc)
            dest.unlink(missing_ok=True)
            return None

    def fetch_all(
        self,
        tender_id: str,
        bzp_number: str | None = None,
        *,
        download_files: bool = True,
        include_notice_pdf: bool = True,
    ) -> FetchResult:
        """Fetch all documents for a tender.

        Główny entry point. Listuje + pobiera dokumenty + zapisuje do DB.

        Args:
            tender_id:          OCDS tender ID lub DB UUID
            bzp_number:         Numer BZP (np. "2026/BZP 00306437") — opcjonalny
            download_files:     Czy pobierać pliki na dysk
            include_notice_pdf: Nieużywany — zachowany dla kompatybilności
        """
        result = FetchResult(tender_id=tender_id, bzp_number=bzp_number)

        # If bzp_number provided, use it as tender_id for list_documents
        doc_id = bzp_number if (bzp_number and re.match(r"\d{4}/BZP", bzp_number)) else tender_id
        documents = self.list_documents(doc_id)
        result.documents = documents

        if not documents:
            result.errors.append(f"No documents found for tender {tender_id}")
            logger.warning("No documents found for tender %s (bzp=%s)", tender_id, bzp_number)

        # Extract SWZ platform URL from results
        for d in documents:
            if d.doc_type == "SWZ" and d.url.startswith("http"):
                result.swz_platform_url = d.url
                break

        # Download files
        if download_files:
            for doc in documents:
                path = self.download_document(tender_id, doc)
                if path:
                    result.downloaded += 1
                    if doc.doc_type == "NOTICE":
                        result.notice_pdf_path = str(path)
                else:
                    result.errors.append(f"Failed to download: {doc.filename}")

        # Store in DB
        if self._engine:
            self._store_results(result)

        logger.info(
            "Fetch complete for %s: %d docs, %d downloaded, %d errors",
            tender_id, len(documents), result.downloaded, len(result.errors),
        )
        return result

    # ─── Private helpers ─────────────────────────────────────────────

    def _notice_pdf_url(self, bzp_number: str) -> str:
        """Build GetNoticePdf URL. Appends /01 if no version suffix present."""
        if not re.search(r"/\d+$", bzp_number):
            bzp_number = f"{bzp_number}/01"
        encoded = quote(bzp_number, safe="")
        return f"{NOTICE_PDF_API}?noticeNumber={encoded}"

    def _get_swz_platform_url(self, bzp_number: str) -> str | None:
        """Extract external SWZ platform URL from notice htmlBody (sekcja 3.1).

        API filtruje ogłoszenia po dacie publikacji (nie po numerze BZP).
        Strategia: pobieramy datę z DB (publication_date), szukamy po dacie ±1 dzień,
        matchujemy po numerze BZP w wynikach.
        """
        client = self._get_client()

        # Resolve publication date from DB
        pub_date: str | None = None
        if self._engine:
            try:
                with self._engine.connect() as conn:
                    row = conn.execute(
                        sa.text(
                            "SELECT publication_date FROM tender "
                            "WHERE external_id = :bzp OR external_id LIKE :bzp_like LIMIT 1"
                        ),
                        {"bzp": bzp_number, "bzp_like": f"%{bzp_number.split('/BZP')[1].strip()}%"},
                    ).fetchone()
                    if row and row[0]:
                        pub_date = str(row[0])[:10]  # YYYY-MM-DD
            except Exception:
                pass

        # Fall back to current year scan if no date
        year_m = re.match(r"(\d{4})/BZP", bzp_number)
        year = year_m.group(1) if year_m else "2026"
        if not pub_date:
            # Try scanning last 30 days
            from datetime import datetime, timedelta
            today = datetime.utcnow().date()
            pub_date = str(today - timedelta(days=1))

        date_from = f"{pub_date}T00:00:00"
        date_to = f"{pub_date}T23:59:59"

        # Scan up to 3 pages (pageSize=50 each) on that date
        bzp_short = re.sub(r"/\d+$", "", bzp_number)  # strip /01

        for notice_type in ("ContractNotice", "ContractAwardNotice", "PriorInformationNotice"):
            for page in range(4):
                try:
                    resp = client.get(
                        NOTICE_LIST_API,
                        params={
                            "NoticeType": notice_type,
                            "PublicationDateFrom": date_from,
                            "PublicationDateTo": date_to,
                            "pageSize": 50,
                            "pageNumber": page,
                        },
                        timeout=15,
                    )
                    if resp.status_code != 200:
                        break
                    items = resp.json() if isinstance(resp.json(), list) else []
                    if not items:
                        break

                    for notice in items:
                        n_bzp = notice.get("bzpNumber", "") or ""
                        if bzp_short in n_bzp:
                            html_body = notice.get("htmlBody", "")
                            if html_body:
                                url = _extract_platform_url(html_body)
                                if url:
                                    logger.info("Found SWZ platform URL for %s: %s", bzp_number, url)
                                    return url
                            return None  # Found notice but no platform URL

                except Exception as exc:
                    logger.debug("htmlBody lookup failed page=%d: %s", page, exc)
                    break

        return None

    def _resolve_bzp_number(self, tender_id: str) -> str | None:
        """Resolve BZP number from OCDS tender_id via DB or mo-board notice API."""
        # Try DB first
        if self._engine:
            try:
                with self._engine.connect() as conn:
                    row = conn.execute(
                        sa.text(
                            "SELECT external_id FROM tender "
                            "WHERE url LIKE :p OR id::text = :tid "
                            "LIMIT 1"
                        ),
                        {"p": f"%{tender_id}%", "tid": str(tender_id)},
                    ).fetchone()
                    if row and row[0]:
                        return row[0]
            except Exception as exc:
                logger.warning("DB lookup failed for %s: %s", tender_id, exc)

        # Fall back to mo-board search by tenderId
        client = self._get_client()
        # tenderId resolving requires full date scan — not supported by public API
        # Return None and let caller handle
        return None

    # ─── DB Storage ──────────────────────────────────────────────────

    def _store_results(self, result: FetchResult):
        """Store fetch results in bzp_documents table."""
        try:
            with self._engine.connect() as conn:
                # Resolve internal tender UUID
                internal_id: str | None = None
                for pattern in [result.tender_id, result.bzp_number or ""]:
                    if not pattern:
                        continue
                    row = conn.execute(
                        sa.text(
                            "SELECT id FROM tender "
                            "WHERE id::text = :tid OR url LIKE :p OR external_id = :ext "
                            "LIMIT 1"
                        ),
                        {
                            "tid": str(pattern),
                            "p": f"%{pattern}%",
                            "ext": pattern,
                        },
                    ).fetchone()
                    if row:
                        internal_id = str(row[0])
                        break

                if not internal_id:
                    logger.warning("No internal tender found for %s / bzp=%s", result.tender_id, result.bzp_number)
                    return

                stored = 0
                for doc in result.documents:
                    conn.execute(
                        sa.text("""
                            INSERT INTO bzp_documents
                                (id, tender_id, bzp_notice_id, doc_type, filename, content, url, fetched_at)
                            VALUES (:id, :tid, :notice_id, :doc_type, :filename, :content, :url, now())
                            ON CONFLICT (tender_id, filename) DO UPDATE SET
                                url      = EXCLUDED.url,
                                content  = EXCLUDED.content,
                                doc_type = EXCLUDED.doc_type,
                                fetched_at = now()
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "tid": internal_id,
                            "notice_id": result.bzp_number or "",
                            "doc_type": doc.doc_type or _classify_document(doc.filename),
                            "filename": doc.filename,
                            "content": (
                                f"[file:{doc.local_path}]" if doc.local_path
                                else f"[url:{doc.url}]"
                            ),
                            "url": doc.url,
                        },
                    )
                    stored += 1
                conn.commit()
                logger.info("Stored %d document records for tender %s", stored, internal_id)

        except Exception as exc:
            logger.error("Failed to store results in DB: %s", exc)


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _extract_platform_url(html_body: str) -> str | None:
    """Extract the SWZ proceeding URL from section 3.1 of the notice HTML."""
    # Pattern 1: regex on section 3.1 header
    m = _PLATFORM_URL_RE.search(html_body)
    if m:
        url = m.group(1).rstrip(".,;)")
        if _is_valid_platform_url(url):
            return url

    # Pattern 2: look for known procurement platform URLs near section markers
    # Extract all URLs from htmlBody then filter by known platforms
    all_urls = re.findall(r'https?://[^\s<"\'\\]+', html_body)
    for url in all_urls:
        url = url.rstrip(".,;)")
        if _is_valid_platform_url(url) and "ezamowienia.gov.pl" not in url:
            return url

    return None


_KNOWN_PLATFORMS = (
    "platformazakupowa.pl",
    "przetargi.pl",
    "josephine.pl",
    "logintrade.pl",
    "openplatform.pl",
    "biznes-polska.pl",
    "miniportal.uzp.gov.pl",
    "e-zp.com",
    "zp.pzp.pl",
    "epropublico.pl",
    "orion.pl",
    "proebiz.com",
    "soldea.pl",
    "comarq.pl",
    "eb2b.com.pl",
    "auctions.coig.pl",
    "smartpzp.pl",
    "ezamawiajacy.pl",
    "e-propublico.pl",
)


def _is_valid_platform_url(url: str) -> bool:
    """Check if URL belongs to a known procurement platform."""
    return any(p in url for p in _KNOWN_PLATFORMS)


def _classify_document(filename: str) -> str:
    """Classify document type based on filename."""
    lower = filename.lower()
    if lower.endswith(".pdf") and "ogloszenie" in lower:
        return "NOTICE"
    if "swz" in lower or "siwz" in lower or "specyfikacja" in lower:
        return "SWZ"
    if "formularz" in lower or "ofert" in lower:
        return "FORM"
    if "umow" in lower or "postanowieni" in lower:
        return "CONTRACT"
    if "oświadczen" in lower or "oswiadczen" in lower:
        return "DECLARATION"
    if "wykaz" in lower:
        return "LIST"
    if "dokumentacj" in lower or "projekt" in lower or "rysun" in lower:
        return "TECHNICAL"
    if "zmian" in lower or "modyfikacj" in lower:
        return "AMENDMENT"
    if lower.endswith(".url"):
        return "SWZ"
    return "OTHER"


def extract_tender_id_from_url(url: str) -> str | None:
    """Extract OCDS tender ID from ezamowienia.gov.pl URL."""
    m = re.search(r"(ocds-\d+-[a-f0-9\-]+)", url or "")
    return m.group(1) if m else None


# ────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Terra-OS BZP Document Scraper")
    parser.add_argument("tender_id", help="OCDS tender ID or BZP number (e.g. '2026/BZP 00331648')")
    parser.add_argument("--bzp-number", help="BZP notice number (if tender_id is OCDS)")
    parser.add_argument("--list-only", action="store_true", help="List documents without downloading")
    parser.add_argument("--output-dir", default="/tmp/terra-docs", help="Download directory")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    scraper = BZPDocumentScraper(storage_dir=Path(args.output_dir))

    with scraper:
        if args.list_only:
            docs = scraper.list_documents(args.tender_id)
            if args.as_json:
                print(json.dumps(
                    [{"name": d.name, "filename": d.filename, "id": d.object_id, "url": d.url, "type": d.doc_type}
                     for d in docs],
                    indent=2, ensure_ascii=False,
                ))
            else:
                print(f"\nDokumenty dla: {args.tender_id}")
                for i, d in enumerate(docs, 1):
                    print(f"  {i}. [{d.doc_type:8}] {d.filename}")
                    print(f"       {d.url[:80]}")
                print(f"\nŁącznie: {len(docs)} dokumentów")
        else:
            result = scraper.fetch_all(
                args.tender_id,
                bzp_number=args.bzp_number,
                download_files=True,
            )
            if args.as_json:
                print(json.dumps({
                    "tender_id": result.tender_id,
                    "bzp_number": result.bzp_number,
                    "documents": len(result.documents),
                    "downloaded": result.downloaded,
                    "errors": result.errors,
                    "notice_pdf": result.notice_pdf_path,
                    "swz_platform_url": result.swz_platform_url,
                    "files": [
                        {
                            "name": d.filename,
                            "type": d.doc_type,
                            "size_kb": (d.file_size or 0) // 1024,
                            "path": d.local_path,
                            "url": d.url,
                        }
                        for d in result.documents
                    ],
                }, indent=2, ensure_ascii=False))
            else:
                print(f"\nPrzetarg:  {result.tender_id}")
                print(f"BZP:       {result.bzp_number or '—'}")
                print(f"Dokumenty: {len(result.documents)}")
                print(f"Pobrano:   {result.downloaded}")
                if result.swz_platform_url:
                    print(f"SWZ URL:   {result.swz_platform_url}")
                if result.errors:
                    print(f"\nBłędy ({len(result.errors)}):")
                    for e in result.errors:
                        print(f"  ! {e}")
                print("\nPliki:")
                for d in result.documents:
                    status = "✓" if d.local_path else "✗"
                    size = f"({d.file_size // 1024}KB)" if d.file_size else ""
                    print(f"  {status} [{d.doc_type:8}] {d.filename} {size}")
                    if not d.local_path:
                        print(f"       → {d.url[:80]}")
