# Terra.OS — Moduł Zwiad: Plan Roboczy
**Data:** 2026-07-08  
**Zakres:** Tylko moduł Zwiad (ingestion pipeline + UI feed)  
**Podział:** 20 faz Discovery (nowe źródła) · 60 faz Poprawki (jakość, UX, scoring) · 10 faz Audit

---

## Stan wyjściowy (zweryfikowany 2026-07-08)

| Element | Stan |
|---|---|
| BZP live API | ✅ działa, ~21 Works/dzień, paginacja po dniach |
| TED EU API | ⚠️ endpoint działa (`organisation-country-buyer=POL`), brak normalizera |
| `ted_tenders` tabela | ✅ istnieje, 0 rekordów |
| `historical_tenders` | ✅ 1.4M rekordów, source=bzp/inne |
| `source_kind` enum | `bzp`, `ted`, `bk`, `bip`, `manual`, `excel` |
| BIP connector | ❌ brak — source_kind istnieje ale 0 implementacji |
| BK (Biuletyn Kancelarii?) | ❌ brak implementacji |
| Cron/scheduler | ❌ brak — ingest tylko ręczny |
| Deduplicator | ❌ brak — ta sama oferta może mieć kilka numerów BZP |
| Geo enrichment | ⚠️ voivodeship z BZP, ale bez NUTS/TERC/coords |
| ZwiadPage source filter | ❌ brak — UI nie ma filtra po źródle |
| Liczba przetargów w demo | 109 (po naprawie tenant + day-slice pagination) |

---

## BLOK A — DISCOVERY: Nowe źródła przetargów (Fazy 1–20)

### Faza 1 — TED EU: Konektor + Normalizer
**Cel:** Pobierać przetargi budowlane z Polski z TED Europa (duże kontrakty, UE-progowe)  
**Plik:** `services/ingestion/ted_connector.py` (nowy)  
**API:** `POST https://api.ted.europa.eu/v3/notices/search`  
**Auth:** brak (publiczne)  
**Query:**
```json
{
  "query": "organisation-country-buyer=POL",
  "fields": ["publication-number","organisation-name-buyer","organisation-country-buyer","BT-22-Procedure","BT-821-Lot","BT-13(t)-Part"],
  "limit": 100,
  "page": 1
}
```
**Zadanie:**
1. Utwórz `services/ingestion/ted_connector.py` — klasa `TEDConnector` analogiczna do `BZPConnector`
2. Iteruj `page` (1, 2, …) dopóki `notices` niepuste i `totalNoticeCount` nie osiągnięty
3. Mapuj pola TED → `TenderIn` (normalize.py: nowa funkcja `normalize_ted_notice`)
4. Dodaj `source='ted'` do pipeline — pipeline.py: obsłuż oba connektory równolegle
5. `external_id` = `publication-number`
6. **Test:** `pytest tests/ingestion/test_ted_connector.py` — mock HTTP, assert ≥1 `TenderIn`

**Plik normalizer:** dodaj do `normalize.py`:
```python
def normalize_ted_notice(raw: dict) -> TenderIn | None:
    pub_num = raw.get("publication-number", "")
    title = raw.get("BT-13(t)-Part") or raw.get("title-business") or pub_num
    buyer = raw.get("organisation-name-buyer") or "Unknown"
    return TenderIn(
        source="ted",
        external_id=pub_num,
        title=title,
        buyer=buyer,
        cpv=[],  # TED zwraca CPV przez xml — parsuj z BT-26m-Lot
        voivodeship=None,
        value_pln=None,
        deadline_at=None,
        published_at=datetime.utcnow(),
        url=f"https://ted.europa.eu/en/notice/{pub_num}",
        raw=raw,
    )
```

---

### Faza 2 — TED: CPV + wartość z XML notice
**Cel:** Wzbogacić rekordy TED o CPV i wartość kontraktu z XML  
**API:** `GET https://ted.europa.eu/en/notice/{pub_num}/xml` — XML eForms  
**Zadanie:**
1. Przy normalizacji TED pobierz XML (`httpx.get(...)`), parsuj `lxml.etree`
2. Wyciągnij `cbc:CPVCode`, `cbc:EstimatedOverallContractAmount`, `cbc:EndDate`
3. Zaktualizuj `TenderIn` z danymi XML
4. Cache XML w `raw['xml_parsed']` — żeby nie pobierać ponownie przy upsert
5. **Limit:** tylko jeśli `orderType=Works` po wstępnym filtrowaniu JSON

---

### Faza 3 — BZP: Dokumenty SIWZ jako źródło danych
**Cel:** Pobierać listę dokumentów przetargu z BZP (SIWZ, OPZ) i zapisywać linki  
**API:** `GET https://ezamowienia.gov.pl/mo-board/api/v1/notice/{bzpNumber}/documents`  
**Istniejący router:** `bzp_documents.py` — sprawdzić czy działa live  
**Zadanie:**
1. Przy ingestion BZP, po upsert dodaj zadanie background do `bzp_documents_router` — fetch docs
2. Zapisz w tabeli `bzp_documents` (już istnieje w DB): `tender_id, doc_name, doc_url, doc_type`
3. UI: w detalu przetargu (ZwiadPage drawer) dodaj zakładkę "Dokumenty" z listą plików
4. **Test:** sprawdź że dla 3 przetargów z bazy dokumenty są dostępne

---

### Faza 4 — BZP: Ogłoszenia o wynikach (ResultNotice)
**Cel:** Pobierać wyniki postępowań (kto wygrał, za ile) — historyczne dane do analizy  
**API:** `NoticeType=ResultNotice` w BZP  
**Problem:** BZP ResultNotice 2026-07 zwraca 0 — sprawdzić czy endpoint działa dla starszych dat  
**Zadanie:**
1. Dodaj `fetch_result_notices(date_from, date_to)` do `BZPConnector`
2. Mapuj na tabelę `historical_bids` (już istnieje): `winner_name, winner_nip, awarded_value`
3. Powiąż z `tender` przez `external_id` — enrichment istniejących rekordów
4. Wywołaj w pipeline po ContractNotice jako `background_task`

---

### Faza 5 — Historical Tenders: Import do głównej tabeli
**Cel:** Przetargi z `historical_tenders` (1.4M rekordów) dostępne jako źródło searchowe  
**Problem:** `historical_tenders` i `tender` to osobne tabele — brak joinów  
**Zadanie:**
1. Utwórz widok `v_tender_all` łączący `tender` (live) i `historical_tenders` (archiwum)
2. Lub: migracja — skopiuj wybrane historyczne do `tender` (ostatnie 90 dni, Works CPV45)
3. Wybór: **migracja selektywna** (90 dni, ~5k rekordów) — bezpieczniejsza
4. Skrypt: `scripts/migrate_historical_to_tender.py`
   - `SELECT id, title, buyer, cpv_code, date, estimated_value, province, notice_url FROM historical_tenders WHERE order_type='Works' AND date >= NOW()-'90 days'::interval`
   - Mapuj kolumny → `TenderIn`, upsert przez pipeline
5. **Test:** po migracji `SELECT COUNT(*) FROM tender WHERE source='bzp'` rośnie

---

### Faza 6 — Cron: Automatyczny dzienny ingest BZP
**Cel:** Przetargi pobierane automatycznie co noc, bez klikania "Skanuj"  
**Brak:** żaden scheduler w terra-api  
**Opcja A — APScheduler:** dodaj `apscheduler` do `requirements.txt`, uruchom w lifespan FastAPI  
**Opcja B — systemd timer:** `terra-ingest.service` + `terra-ingest.timer`  
**Wybór:** **systemd timer** — prostszy, bez zależności  
**Zadanie:**
1. Utwórz `/etc/systemd/system/terra-ingest.service`:
   ```ini
   [Service]
   User=ubuntu
   ExecStart=/home/ubuntu/terra-os/.venv/bin/python3 /home/ubuntu/terra-os/services/ingestion/run_ingest.py
   Environment=DEFAULT_TENANT_ID=ec3d1e16-2139-48c2-93b5-ffe0defd606d
   ```
2. Utwórz `/etc/systemd/system/terra-ingest.timer` — `OnCalendar=*-*-* 04:00:00`
3. Skrypt `run_ingest.py` wywołuje `run_ingest(days_back=1, offline=False)`
4. Log do `/var/log/terra-ingest.log`
5. **Test:** `systemctl start terra-ingest.service` — sprawdź log

---

### Faza 7 — Cron: Automatyczny tygodniowy ingest TED
**Cel:** TED pobierany raz w tygodniu (ogłoszenia EU ukazują się wolniej)  
**Zadanie:**
1. Dodaj `terra-ted-ingest.timer` — `OnCalendar=Mon *-*-* 05:00:00`
2. `run_ingest_ted.py` — wywołuje `TEDConnector.fetch_notices(days_back=7)`
3. Deduplikacja po `publication-number`

---

### Faza 8 — BIP: Scraper ogłoszeń samorządowych
**Cel:** Przetargi z BIP (Biuletyn Informacji Publicznej) gmin — małe zamówienia poniżej progu BZP  
**API:** Brak centralnego API — każda gmina ma własny BIP  
**Podejście:** Centralny aggregator — `bip.gov.pl` ma listę podmiotów  
**Alternatywa:** `przetargi.pl` (prywatny aggregator, scrapeable)  
**Zadanie:**
1. Utwórz `services/ingestion/bip_connector.py` — scraper RSS z wybranych BIP-ów regionalnych
2. Lista 20 głównych BIP-ów śląskie/dolnośląskie/opolskie z RSS feeds
3. Parser RSS → `TenderIn` z `source='bip'`
4. Filtr: tylko ogłoszenia zawierające "roboty budowlane" lub CPV 45*
5. **Test:** mock HTTP, assert parsuje datę + tytuł

---

### Faza 9 — Excel Import: Źródło przetargów offline
**Cel:** Użytkownik może importować własną bazę przetargów (export z innego systemu)  
**Istniejący router:** `excel_import.py` — sprawdzić czy działa  
**Zadanie:**
1. Weryfikacja `excel_import.py` — czy mapuje na `tender` czy na inną tabelę
2. Jeśli działa: dodaj przycisk "Importuj z Excel" w ZwiadPage header
3. Szablon Excel: `templates/tender_import_template.xlsx` z kolumnami: Tytuł, Zamawiający, CPV, Wartość, Deadline, URL
4. Walidacja: duplikaty po tytule+zamawiający, oznacz `source='excel'`

---

### Faza 10 — Manual Entry: Formularz dodania przetargu
**Cel:** Ręczne dodanie przetargu znalezionego poza systemem  
**Zadanie:**
1. W ZwiadPage: przycisk "Dodaj ręcznie" → modal z formularzem
2. Pola: Tytuł*, Zamawiający*, URL BZP/BIP, Wartość, Deadline, CPV (autocomplete z cpv_taxonomy)
3. `POST /api/v1/tenders` (nowy endpoint) — zapisuje `source='manual'`
4. Wyświetl od razu na liście z badge "Ręczny"

---

### Faza 11 — BZP: Wyszukiwanie pełnotekstowe
**Cel:** Pobierać przetargi przez słowa kluczowe a nie tylko przez datę i typ  
**API BZP search:** `GET /mo-board/api/v1/notice?keyword=roboty+ziemne&NoticeType=ContractNotice`  
**Zadanie:**
1. Sprawdź czy BZP ma parametr `keyword` lub `searchPhrase`
2. Jeśli tak: dodaj `fetch_by_keyword(keywords: list[str], days_back: int)` do `BZPConnector`
3. Odpal dla keywords z `OwnerProfileSnap.keywords`
4. Deduplicate wyniki po `bzpNumber`

---

### Faza 12 — TED: Filtr wartości (duże kontrakty >130k EUR)
**Cel:** TED dotyczy zamówień powyżej progu UE (~5.4M PLN roboty) — odfiltrować mniejsze  
**Zadanie:**
1. W `ted_connector.py` dodaj filtr `value_pln >= 5_000_000` po normalizacji
2. Oznacz w `match_reason` że pochodzi z TED EU
3. Dodaj w ZwiadPage badge "EU" dla source=ted

---

### Faza 13 — GUS BDL: Wskaźniki w kontekście przetargu
**Cel:** Przy wyświetlaniu przetargu pokaż aktualny wskaźnik cen materiałów budowlanych  
**Istniejący:** `gus_bdl.py` router + `gus_indicators` tabela  
**Zadanie:**
1. Sprawdź czy `gus_indicators` ma dane — jeśli nie, trigger sync
2. W ZwiadPage detail panel: dodaj sekcję "Rynek" z GUS wskaźnikami (ceny materiałów, CPI)
3. Cache w `gus_indicators` — refresh raz na tydzień

---

### Faza 14 — Enrichment: NIP Zamawiającego → KRS
**Cel:** Przy ingestion wzbogacić rekordy o NIP zamawiającego, dane z KRS  
**Istniejący:** `krs_verify.py` router  
**Zadanie:**
1. Po upsert przetargu (background task): wyciągnij NIP z `raw.buyerNip`
2. Wywołaj `GET /api/v1/krs/verify?nip={nip}` — pobierz nazwę pełną, formę prawną
3. Zapisz w `buyer_crm` tabeli (link do istniejącego CRM)
4. W ZwiadPage: przy nazwie zamawiającego link do kartoteki CRM

---

### Faza 15 — Enrichment: Geokodowanie miejsca realizacji
**Cel:** Współrzędne geograficzne dla każdego przetargu → mapa  
**Dane BZP:** `placeOfPerformance` — nazwa miejscowości  
**Zadanie:**
1. Po upsert: jeśli `voivodeship` nie null, geokoduj przez Nominatim OSM (bezpłatny)
2. Dodaj kolumny `lat FLOAT, lon FLOAT` do tabeli `tender` (migracja Alembic)
3. Zapisz koordinaty w `tender.raw['lat'], tender.raw['lon']`
4. ZwiadPage: widget mini-mapa (Leaflet.js) z pinami przetargów

---

### Faza 16 — Enrichment: Automatyczny CPV score
**Cel:** Dopasuj CPV przetargu do profilu firmy precyzyjniej (hierarchia CPV)  
**Istniejące:** `cpv_taxonomy` tabela  
**Zadanie:**
1. Pobierz `cpv_taxonomy` do pamięci przy starcie
2. Dla każdego CPV przetargu sprawdź drzewo: dział 45 (budowlane) → klasa → kategoria
3. Podnieś score o +15% jeśli CPV jest w `OwnerProfileSnap.cpv_preferred`
4. Zapisz `match_reason` z listą dopasowanych CPV

---

### Faza 17 — Deduplikacja: Ten sam przetarg z BZP + TED
**Cel:** Przetarg może pojawić się w BZP (polska publikacja) i TED (EU) jednocześnie  
**Zadanie:**
1. Po każdym ingest: szukaj kandydatów do dedup: `buyer ILIKE %X% AND value_pln BETWEEN Y*0.9 AND Y*1.1 AND published_at WITHIN 2 days`
2. Jeśli znaleziono duplikat: zachowaj BZP jako `primary`, TED jako `secondary` — ustaw `raw['duplicate_of']`
3. W UI: nie wyświetlaj secondary duplikatów domyślnie (filtr)

---

### Faza 18 — Webhook: Powiadomienie o nowych przetargach
**Cel:** Push notification w aplikacji gdy pojawi się nowy przetarg ≥ score 0.7  
**Istniejące:** `notifications.py` router + `tender_alerts.py`  
**Zadanie:**
1. Po każdym ingest: sprawdź nowo dodane przetargi z `match_score >= 0.7`
2. Utwórz notification przez `notifications.py` → użytkownik widzi alert w topbarze
3. Opcjonalnie: email notification (MailerLite?) — jeśli włączone w ustawieniach

---

### Faza 19 — API Export: Endpoint do pobierania danych przetargów
**Cel:** Klient może eksportować przetargi do Excel/CSV z API  
**Istniejący:** `export.py` router  
**Zadanie:**
1. Sprawdź `GET /api/v1/export/tenders?format=xlsx` — czy działa
2. Jeśli nie: dodaj endpoint generujący xlsx z openpyxl (już w requirements)
3. Filtruj po `status, score_min, date_from, source`
4. W ZwiadPage: przycisk "Eksportuj" → pobierz Excel

---

### Faza 20 — Monitoring: Status źródeł (health check)
**Cel:** Dashboard statusu: BZP ✅/❌, TED ✅/❌, ostatni ingest kiedy  
**Zadanie:**
1. Utwórz endpoint `GET /api/v1/sources/health` — sprawdza każde źródło (ping API, last_ingest_at z DB)
2. Zapisuj `last_ingest_at, last_ingest_count, last_error` per source w tabeli `job_status` (już istnieje)
3. W ZwiadPage header: kolorowe kropki statusu (zielona/czerwona/szara) per source

---

## BLOK B — POPRAWKI: Jakość, Scoring, UX (Fazy 21–80)

### PACZKA B1 — Skorygowanie pipeline (Fazy 21–30)

#### Faza 21 — Pipeline: Usuń stare seed data z bazy
**Cel:** Seedy 2024/BZP w `tenant c48186e2` zaśmiecają bazę  
**Zadanie:**
1. `scripts/cleanup_seeds.py` — DELETE FROM tender WHERE source='bzp' AND external_id LIKE '2024/%' WITH CASCADE
2. Uruchom `TRUNCATE tenant` dla `c48186e2` (drugi tenant)
3. Zostaw tylko `tenant ec3d1e16` z live BZP data

#### Faza 22 — Pipeline: Zwiększ zakres historyczny do 90 dni
**Cel:** Ingest przy pierwszym uruchomieniu powinien pobrać 90 dni wstecz  
**Plik:** `zwiad.py` router — endpoint `/api/v1/ingest/run`  
**Zadanie:**
1. Zmień domyślny `days_back` z 14 → 90 w ZwiadPage.tsx
2. W pipeline: podziel 90 dni na batche 7-dniowe żeby uniknąć timeout
3. Zwróć progress jako streaming response lub background job ID

#### Faza 23 — Pipeline: Progress bar dla długiego ingestu
**Cel:** UX — przy skanowaniu BZP pokaż "Pobrano X z Y ogłoszeń"  
**Zadanie:**
1. Endpoint `GET /api/v1/ingest/status` — zwraca `{running: bool, progress: {fetched, total}}`
2. W ZwiadPage: podczas skanowania pokaż pasek postępu zamiast spinner
3. Poll co 2s przez `setInterval`

#### Faza 24 — Pipeline: Retry failed requests
**Cel:** BZP czasem zwraca 429/503 — retry z exponential backoff  
**Plik:** `bzp_connector.py`  
**Zadanie:**
1. Obuduj `httpx.get` w `tenacity.retry(stop=stop_after_attempt(3), wait=wait_exponential(2))`
2. Dodaj `tenacity` do requirements
3. Loguj każdy retry z numerem próby

#### Faza 25 — Pipeline: Limit na max stron per dzień
**Cel:** Jeden dzień może mieć >50 rekordów (aktualnie pageSize=50 i tylko 1 strona)  
**Plik:** `bzp_connector.py`  
**Zadanie:**
1. W pętli po dniach: jeśli `len(page_items) == pageSize`, próbuj stronę 1, 2, … aż do pustej
2. Limit bezpieczeństwa: max 5 stron per dzień (250 rekordów/dzień max)
3. **Test:** sprawdź że dla dnia z 80 ogłoszeniami pobiera strony 0+1

#### Faza 26 — Normalize: Wartość z pola szacunkowej wartości
**Cel:** `value_pln` jest NULL dla wielu przetargów — BZP ma `estimatedValueMax`  
**Plik:** `normalize.py`  
**Zadanie:**
1. Sprawdź wszystkie pola BZP z wartością: `estimatedValue`, `estimatedValueMax`, `awardedValue`
2. Priorytet: `awardedValue` > `estimatedValueMax` > `estimatedValue` > `_parse_value_from_html`
3. **Test:** assert `value_pln is not None` dla ≥70% rekordów

#### Faza 27 — Normalize: Deadline z `submittingOffersDeadline`
**Cel:** `deadline_at` jest NULL — BZP ma `submittingOffersDeadline`  
**Plik:** `normalize.py`  
**Zadanie:**
1. Parsuj `submittingOffersDeadline` ISO string → datetime
2. Fallback: `openingOffersDeadline`
3. **Test:** assert `deadline_at is not None` dla ≥80% rekordów

#### Faza 28 — Normalize: Voivodeship z NUTs / `placeOfPerformance`
**Cel:** 30% przetargów ma `voivodeship=None` — BZP ma `placeOfPerformance`  
**Plik:** `normalize.py`  
**Zadanie:**
1. Parsuj `placeOfPerformance` → lista miast/województw
2. Map przez `nuts_region_map` tabela (już w DB) → nazwa województwa PL
3. Fallback: regex na tytule przetargu (heurystyka)

#### Faza 29 — Filters: Konfigurowalny próg wartości
**Cel:** `passes_value_filter` odrzuca >50M — to za mało elastyczne  
**Plik:** `filters.py`  
**Zadanie:**
1. Dodaj `value_min_pln` do `apply_filters` — domyślnie 50k (odrzuć mikroprzetargi)
2. Czytaj min/max z `owner_profile` tabeli per tenant
3. **Test:** przetarg za 30k jest odrzucany, za 150k przechodzi

#### Faza 30 — Pipeline: Ingest result log w tabeli job_status
**Cel:** Zapisuj wynik każdego ingestu do DB — historia skanowań  
**Plik:** `repository.py`, `pipeline.py`  
**Zadanie:**
1. Po ingest: `INSERT INTO job_status (job_name, status, result_json, created_at)` 
2. `GET /api/v1/ingest/history` — ostatnie 10 skanowań z wynikami
3. W ZwiadPage: link "Historia skanowań" pod przyciskiem Skanuj

---

### PACZKA B2 — Scoring i relevance (Fazy 31–42)

#### Faza 31 — Scorer: Wagi konfigurowane przez użytkownika
**Cel:** `OwnerProfileSnap` ma hardcoded wagi — user powinien móc je zmienić  
**Plik:** `scorer.py`, `owner_profile` tabela  
**Zadanie:**
1. Dodaj kolumnę `scoring_weights JSONB` do `owner_profile`
2. `OwnerProfileSnap.from_db(tenant_id)` — ładuje profil z DB
3. UI: w Ustawieniach → Profil firmy → sliders wag (CPV 35%, Geo 25%, Wartość 20%, …)

#### Faza 32 — Scorer: Boost dla przetargów w pipeline (obserwowanych)
**Cel:** Przetargi które firma już obserwuje powinny być wyżej  
**Zadanie:**
1. Sprawdź `tender_bookmark` — jeśli przetarg zaobserwowany: boost `match_score += 0.1`
2. W `score_tender()`: sprawdź bookmark przed wynikiem

#### Faza 33 — Scorer: Penalizacja dla przetargów z blisko deadline
**Cel:** Jeśli zostało <3 dni do deadline: flag "PILNE" + obniż score (za mało czasu)  
**Zadanie:**
1. W scorer: jeśli `days_remaining < 3`: add to `match_reason` "⚠️ Pilne — <3 dni"
2. W API: dodaj pole `is_urgent: bool` do response
3. W UI: czerwony badge PILNE zamiast standardowego

#### Faza 34 — Scorer: NLP keyword extraction z tytułu
**Cel:** Zamiast prostego regex — lepsze dopasowanie słów kluczowych  
**Zadanie:**
1. Dodaj `spacy` lub `sklearn.feature_extraction.text.TfidfVectorizer`
2. Przy starcie: wektory dla keywords z `OwnerProfileSnap.keywords`
3. Cosine similarity tytuł przetargu vs keywords → zastąp `_keyword_score`
4. Alternatywa lżejsza: `fuzzywuzzy` dla fuzzy matching

#### Faza 35 — Scorer: Boost ze słownika CPV → sektor
**Cel:** Przetarg na "Roboty drogowe" (45233120) = sektor drogowy — boost jeśli firma w nim  
**Plik:** `filters.py::get_tender_sector`, `services/engine/l2_stochastic/sector_profiles.py`  
**Zadanie:**
1. Sprawdź `detect_sector()` — czy działa poprawnie
2. Dodaj `sector_key` do `TenderIn` i zapisuj w `tender.raw['sector']`
3. W scorer: boost +10% jeśli `sector_key` w preferowanych przez firmę

#### Faza 36 — Match reason: Czytelny opis dopasowania
**Cel:** Pole `match_reason` to surowe JSON — UI powinien pokazać czytelny opis  
**Zadanie:**
1. Zmień format `match_reason` na humanreadable string: "CPV 45233120 ✓, Woj. Śląskie ✓, Wartość w zakresie"
2. Wyświetl w ZwiadPage detail drawer jako colored badges
3. Pełny rozkład punktów pod spodem (collapsible)

#### Faza 37 — Scorer: Historia wygranych jako input
**Cel:** Jeśli firma wygrała już przetargi zamawiającego X — wyższy score  
**Dane:** `historical_bids` tabela  
**Zadanie:**
1. Przy score_tender: sprawdź `historical_bids` czy `buyer ILIKE tender.buyer`
2. Jeśli tak: boost +8%, `match_reason += "Znany zamawiający (2x wcześniej)"`

#### Faza 38 — Scorer: Penalizacja konsorcjum wymagane
**Cel:** Przetargi wymagające konsorcjum są trudniejsze — obniż score  
**Dane BZP:** `isConsortiumAllowed`, `requiredDeposit`  
**Zadanie:**
1. Parse z `raw` — jeśli `consortiumRequired=true`: `score -= 0.05`
2. Jeśli `deposit > value*0.05`: ostrzeżenie w match_reason

#### Faza 39 — Scorer: Szacowanie konkurencji (offers_count z historii)
**Cel:** Przetargi z mniejszą konkurencją historyczną = lepsze szanse  
**Dane:** `historical_tenders.offers_count`  
**Zadanie:**
1. Query: `SELECT AVG(offers_count) FROM historical_tenders WHERE cpv_code LIKE :cpv_prefix AND province = :voivodeship`
2. Jeśli `avg_offers < 3`: boost +10% ("Niska konkurencja historyczna")
3. Jeśli `avg_offers > 10`: penalizacja -10%

#### Faza 40 — Scorer: Wartość score na karcie (nie tylko %)
**Cel:** Pokaż breakdown: "CPV 35/35 | Geo 20/25 | Wartość 18/20"  
**Zadanie:**
1. `ScoreResult` rozszerz o dict `{factor: {earned, max}}`
2. W ZwiadPage: mini progress bars per czynnik w detalu przetargu

#### Faza 41 — Re-score: Aktualizacja score po zmianie profilu
**Cel:** Gdy użytkownik zmieni profil firmy (CPV, obszar) — rescoruj wszystkie przetargi  
**Zadanie:**
1. Endpoint `POST /api/v1/tenders/rescore` — rescoruj wszystkie `status=new`
2. Background task, progress w `job_status`
3. Trigger automatycznie po save profilu

#### Faza 42 — Score visibility: Historia zmian score
**Cel:** Przetarg może dostać inny score po zmianie profilu — pokaż historię  
**Zadanie:**
1. Dodaj tabelę `score_history (tender_id, score, reason, scored_at)`
2. Przy każdym upsert: jeśli score się zmienił — zapisz poprzedni do historii
3. W UI: tooltip "Score zmieniony z 0.7 → 0.8 po aktualizacji profilu"

---

### PACZKA B3 — UI/UX ZwiadPage (Fazy 43–60)

#### Faza 43 — ZwiadPage: Filtr po źródle
**Cel:** UI ma `source` w danych ale brak filtra  
**Zadanie:**
1. Dodaj dropdown "Źródło: Wszystkie / BZP / TED / BIP / Ręczne" nad listą
2. Przekaż `?source=bzp` do `/api/v1/tenders`
3. Dodaj `source` jako param query w router zwiad.py

#### Faza 44 — ZwiadPage: Filtr po województwie
**Cel:** Brak filtra geograficznego — user nie może ograniczyć do regionu  
**Zadanie:**
1. Dodaj multi-select "Województwo" z listą 16 województw
2. API: `?voivodeships=slaskie,dolnoslaskie`
3. WHERE clause w zwiad.py

#### Faza 45 — ZwiadPage: Filtr po CPV
**Cel:** Filtr CPV istnieje w API ale nie w UI  
**Zadanie:**
1. Autocomplete "CPV kod" — search w `cpv_taxonomy`
2. API: `?cpv=45233120` — już jest, tylko podłączyć UI

#### Faza 46 — ZwiadPage: Filtr po zakresie wartości
**Cel:** Firma chce widzieć tylko przetargi 200k–5M PLN  
**Zadanie:**
1. Range slider "Wartość min-max" (500k–10M)
2. API: `?value_min=500000&value_max=10000000`
3. Dodaj parametry do query w router

#### Faza 47 — ZwiadPage: Filtr po deadline
**Cel:** Pokaż tylko przetargi z deadline w ciągu X dni  
**Zadanie:**
1. Dropdown "Deadline: 3 dni / 7 dni / 14 dni / 30 dni / wszystkie"
2. API: `?deadline_days=14` → WHERE `deadline_at <= NOW() + 14 days`

#### Faza 48 — ZwiadPage: Sortowanie (score/data/wartość)
**Cel:** User może sortować — aktualnie tylko score DESC  
**Zadanie:**
1. Dropdown "Sortuj: Najlepsze / Najnowsze / Największa wartość / Deadline"
2. API: `?sort=published_at_desc|score_desc|value_desc|deadline_asc`
3. Zmień ORDER BY w zwiad.py

#### Faza 49 — ZwiadPage: Tryb tabeli vs karty
**Cel:** Karty są ładne ale tabela lepsza do porównywania wielu przetargów  
**Zadanie:**
1. Toggle "Widok: Karty | Tabela" w toolbarze
2. Komponent `TenderTable` z kolumnami: Tytuł, Zamawiający, Wartość, Score, Deadline, Akcje
3. Zachowaj w localStorage

#### Faza 50 — ZwiadPage: Infinite scroll zamiast paginacji
**Cel:** Aktualnie `limit=25` bez paginacji — user nie widzi pozostałych  
**Zadanie:**
1. Intersection Observer na ostatniej karcie → `fetchFeed()` z `offset+25`
2. API: `?offset=25&limit=25` — dodaj do query params
3. Append items do listy zamiast replace

#### Faza 51 — ZwiadPage: Drawer szczegółów — pełny widok
**Cel:** Drawer przetargu jest pusty/skeleton — brakuje kluczowych danych  
**Zadanie:**
1. Sekcja "Zamawiający" — NIP, forma prawna z KRS (Faza 14)
2. Sekcja "Dokumenty" — lista PDF (Faza 3)
3. Sekcja "Warunki" — wymagana polisa, gwarancja, wadium z BZP raw
4. Sekcja "Konkurencja" — avg offers count z historical (Faza 39)
5. Sekcja "Score breakdown" — (Faza 40)

#### Faza 52 — ZwiadPage: Quick actions na karcie
**Cel:** Szybkie akcje bez otwierania drawera  
**Zadanie:**
1. Hover card: 3 przyciski — "Obserwuj ⭐", "Pipeline →", "Odrzuć ✗"
2. "Obserwuj" → `POST /api/v1/bookmarks` (już istnieje)
3. "Pipeline" → zmień status na `matched` → pojawi się w Pipeline
4. "Odrzuć" → status `rejected` + ukryj z listy

#### Faza 53 — ZwiadPage: Badge etykiet na kartach
**Cel:** Szybka identyfikacja charakterystyk przetargu bez otwierania  
**Zadanie:**
1. Badge "🔥 PILNE" — jeśli deadline <3 dni
2. Badge "🇪🇺 EU" — jeśli source=ted
3. Badge "🏆 Top Match" — jeśli score ≥ 0.85
4. Badge "📄 SIWZ" — jeśli są dokumenty
5. Badge wartości (kolorowy zakres)

#### Faza 54 — ZwiadPage: Search pełnotekstowy
**Cel:** Pole search nad listą — szukaj po tytule/zamawiającym  
**Istniejące:** `idx_tender_title_fts` GIN index  
**Zadanie:**
1. Input search z debounce 300ms
2. API: `?q=roboty+ziemne` → WHERE `to_tsvector('simple', title || buyer) @@ to_tsquery('simple', :q)`
3. Podświetl frazy w wynikach (highlight)

#### Faza 55 — ZwiadPage: Podgląd linku BZP
**Cel:** User chce otworzyć BZP bez opuszczania Terra.OS  
**Zadanie:**
1. Przycisk "Otwórz BZP ↗" → otwiera `https://ezamowienia.gov.pl/mp-client/tenders/{bzpId}` w nowej karcie
2. Mini preview iframe w drawer (iframes BZP mogą być zablokowane — fallback link)

#### Faza 56 — ZwiadPage: Bulk actions
**Cel:** Zaznacz wiele przetargów → masowe akcje  
**Zadanie:**
1. Checkbox na każdej karcie
2. Toolbar: "Zaznaczono X → Dodaj do pipeline / Eksportuj / Odrzuć"
3. API: `PATCH /api/v1/tenders/bulk` z listą IDs i akcją

#### Faza 57 — ZwiadPage: Alerty (saved searches)
**Cel:** User zapisuje filtr i dostaje powiadomienie gdy pojawi się match  
**Istniejący:** `tender_alert.py` router  
**Zadanie:**
1. Przycisk "Zapisz wyszukiwanie 🔔" → zapisuje aktywne filtry jako alert
2. Cron (faza 6): po ingest sprawdza alerty → wysyła notifications
3. Lista alertów w zakładce "Zakładki"

#### Faza 58 — ZwiadPage: Tytuł KPI — live numbers
**Cel:** Header KPI (aktywne, wartość, score) powinien odzwierciedlać aktywne filtry  
**Zadanie:**
1. KPI endpoint `GET /api/v1/tenders/kpi?source=bzp&voivodeship=slaskie` — filtrowane
2. Refresh KPI gdy zmienią się filtry

#### Faza 59 — ZwiadPage: Empty state design
**Cel:** "Brak przetargów" jest suche — powinno zachęcać do akcji  
**Zadanie:**
1. Ilustracja + tekst "Nie znaleziono przetargów spełniających kryteria"
2. Sugestia: "Rozszerz obszar geograficzny" lub "Zwiększ zakres CPV"
3. Przycisk "Skanuj BZP teraz"

#### Faza 60 — ZwiadPage: Responsive mobile
**Cel:** Na mobile (375px) drawer i karty są ucięte  
**Zadanie:**
1. Na mobile: drawer = full-screen bottom sheet
2. Karty: uproszczony widok (tylko tytuł + wartość + score)
3. Toolbar: kolapsuje do ikon

---

## BLOK C — AUDIT i DEBUGGING (Fazy 81–90)

### Faza 81 — Audit: Pełne testy pipeline E2E
**Cel:** Weryfikacja end-to-end: BZP → normalize → filter → score → DB → API → UI  
**Plik:** `tests/ingestion/test_pipeline_e2e.py`  
**Zadanie:**
1. Mock BZP API — zwróć 5 fixture notices (Works, mieszane CPV)
2. Assert: `created >= 3` (2 odfiltrowane)
3. Assert: wszystkie mają `match_score > 0`
4. Assert: `external_id` unikalne
5. Assert: `tenant_id` = env var `DEFAULT_TENANT_ID`

### Faza 82 — Audit: Test normalizera BZP na prawdziwych danych
**Cel:** Sprawdź czy wszystkie pola są poprawnie parsowane  
**Zadanie:**
1. Pobierz 50 realnych BZP Works notices
2. Sprawdź: `value_pln` not null ≥70%, `deadline_at` not null ≥80%, `voivodeship` not null ≥60%
3. Log który przetarg ma jakie null pola — priorytetyzuj Fazy 26–28

### Faza 83 — Audit: Diagnoza duplikatów w bazie
**Cel:** Czy są duplikaty po `(title, buyer, published_at::date)`?  
**Zadanie:**
1. SQL: `SELECT title, buyer, COUNT(*) FROM tender GROUP BY title, buyer HAVING COUNT(*) > 1`
2. Jeśli tak: napisz skrypt dedup — zatrzymaj jeden, usuń pozostałe
3. Dodaj unique partial index: `UNIQUE (tenant_id, LOWER(title), LOWER(buyer), published_at::date)`

### Faza 84 — Audit: Weryfikacja tenant isolation
**Cel:** Upewnij się że tenant `c48186e2` nie przecieka do `ec3d1e16`  
**Zadanie:**
1. SQL: `EXPLAIN ANALYZE SELECT * FROM tender WHERE tenant_id='ec3d1e16...'`
2. Sprawdź czy Row Level Security działa: login jako inny user, sprawdź czy widzi cudze przetargi
3. Jeśli nie: `ALTER TABLE tender FORCE ROW LEVEL SECURITY`

### Faza 85 — Audit: Performance API /tenders dla 10k+ rekordów
**Cel:** Przy 10k przetargów query może być wolne  
**Zadanie:**
1. Zaseeduj 10k przetargów (skrypt bulk insert)
2. `EXPLAIN ANALYZE` na `/api/v1/tenders?limit=25&sort=score`
3. Jeśli >500ms: dodaj composite index `(tenant_id, match_score DESC, published_at DESC)`
4. Dodaj query timeout 5s

### Faza 86 — Audit: Bezpieczeństwo ingest endpoint
**Cel:** `/api/v1/ingest/run` jest POST — czy wymaga auth? Kto może triggerować?  
**Zadanie:**
1. Sprawdź czy endpoint ma `Depends(get_current_user)` — jeśli nie, DODAJ
2. Dodaj rate limit: max 1 ingest / 5 minut per tenant
3. Log kto i kiedy triggerował ingest

### Faza 87 — Audit: Error handling w BZP connector
**Cel:** Jeśli BZP zwróci 500/429 — co się dzieje?  
**Zadanie:**
1. Symuluj 429: `requests.exceptions.HTTPError` → sprawdź czy pipeline crasha
2. Dodaj global exception handler w pipeline: `try/except → log → continue`
3. Zwróć partial result gdy część dni się nie pobrała

### Faza 88 — Audit: Memory/CPU profiling pipeline
**Cel:** Ingest 30 dni pobiera 5000 notices — ile zużywa RAM?  
**Zadanie:**
1. `python3 -m memory_profiler run_ingest.py`
2. Jeśli >500MB: zastąp `list` → `generator` w `fetch_notices`
3. Streaming normalize: przetwarzaj po 50 naraz, nie ładuj wszystkiego do RAM

### Faza 89 — Audit: Schema migration versioning
**Cel:** Fazy 15 (lat/lon) i 42 (score_history) wymagają migracji DB  
**Zadanie:**
1. Sprawdź Alembic — czy migrations istnieją i są aktualne
2. `alembic revision --autogenerate -m "add lat lon to tender"`
3. `alembic upgrade head`
4. Utwórz rollback test: `alembic downgrade -1` → nie crashuje

### Faza 90 — Audit: End-to-end live test na Vercel + EC2
**Cel:** Po wszystkich zmianach — weryfikacja kompletna na produkcji  
**Zadanie:**
1. Login na `terra-os-opal.vercel.app`
2. Kliknij "Skanuj BZP" → sprawdź że pojawią się przetargi datowane dzisiaj
3. Sprawdź Pipeline — nowe karty w kolumnie "Monitoring"
4. Sprawdź TED — po ingest pojawią się przetargi source=ted
5. Sprawdź score breakdown w drawer
6. Eksport Excel — pobierz plik
7. Zapis wyszukiwania — weryfikuj powiadomienie

---

## Priorytety implementacji

| Priorytet | Fazy | Efekt |
|---|---|---|
| 🔴 KRYTYCZNE | 21, 22, 24, 25, 26, 27 | Czysta baza, pełne dane |
| 🟠 WAŻNE | 6, 1, 43–48, 54 | Automatyzacja + filtry UI |
| 🟡 WARTOŚCIOWE | 2, 3, 39, 31, 52, 53 | Jakość danych + UX |
| 🟢 NICE-TO-HAVE | 8, 15, 34, 57, 60 | Nowe źródła + mobile |

**Kolejność wdrożenia:** Blok C (audit) → Paczka B1 (pipeline fixes) → Fazy 1, 6 (TED + cron) → Paczka B3 (UI filtry) → reszta

---

## Pliki do modyfikacji (mapa)

```
services/ingestion/
  bzp_connector.py     — Fazy 24, 25, 11
  normalize.py         — Fazy 26, 27, 28, 1(ted)
  filters.py           — Fazy 29, 35
  scorer.py            — Fazy 31–42
  pipeline.py          — Fazy 22, 23, 30, 1(ted)
  repository.py        — Fazy 30, 42
  ted_connector.py     — Fazy 1, 2, 7 [NOWY]
  bip_connector.py     — Faza 8 [NOWY]

services/api/services/api/routers/
  zwiad.py             — Fazy 43–50, 54–56, 58
  ted_integration.py   — Faza 1 (podłączyć TEDConnector)
  gus_bdl.py           — Faza 13
  export.py            — Faza 19

apps/ui/src/components/pages/
  ZwiadPage.tsx        — Fazy 43–60

scripts/
  cleanup_seeds.py     — Faza 21 [NOWY]
  migrate_historical_to_tender.py — Faza 5 [NOWY]

systemd/
  terra-ingest.service — Faza 6 [NOWY]
  terra-ingest.timer   — Faza 6 [NOWY]
  terra-ted-ingest.timer — Faza 7 [NOWY]
```

---

*Plan wygenerowany na podstawie inspekcji kodu 2026-07-08. Research: BZP API ✅ (21 Works/dzień), TED API ✅ (`organisation-country-buyer=POL` działa), historical_tenders 1.4M rekordów. Gotowy do implementacji — zacznij od Bloku C (audit) lub od konkretnej fazy.*
