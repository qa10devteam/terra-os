# TERRA.OS — KONTYNUACJA PRAC
## Data: 07.07.2026 | Wątek: Discovery Sprint — Blok B Silnik Analityczny

---

## STAN PROJEKTU

### Testy
**312/312 passed ✅** (commit `7138946`)

Wszystkie naprawy z poprzedniego wątku:
- conftest: `DB_PASSWORD=terra_dev_2026`, `DEFAULT_TENANT_ID=ec3d1e16-2139-48c2-93b5-ffe0defd606d`, `lru_cache` bust, JWT auth fixture
- `_get_tenant_id()` w `module3.py` + `get_or_create_default_tenant()` w `ingestion/repository.py` — respektują `DEFAULT_TENANT_ID` env
- `bzp.py` `DEFAULT_TENANT_ID` zaktualizowany na demo org
- `test_phases_61_100.py` — `_app_paths()` helper dla FastAPI >= 0.111

### Serwisy (uruchomione)
- **API:** `http://localhost:8000` — FastAPI, db ok, redis ok
- **UI:** `http://localhost:3000` — Next.js
- **DB:** PostgreSQL 16, user `terraos`, hasło `terra_dev_2026`, baza `terraos`
- Demo user: `demo@terra-os.pl` / `demo2026!`

### Repo
- `/home/ubuntu/terra-os/` — branch `main`, commit `7138946`
- `.venv` aktywny (`num2words` zainstalowany)
- `pytest.ini` — `pythonpath = . services/api`

---

## CO DALEJ — ZADANIE NA TEN WĄTEK

### Discovery Sprint: Blok B — Silnik Analityczny

**Problem:** Fazy 26-40 w SPEC.md to plany na podstawie desk research. Żadne dane nie zostały faktycznie pobrane ani zweryfikowane.

**Cel:** Sprawdź każde źródło danych, pobierz próbki, udokumentuj co faktycznie jest dostępne — zanim zaczniesz implementację.

---

### ZADANIA DO WYKONANIA (w kolejności)

#### 1. Atlas Przetargów (FREE, CC BY 4.0)
- Źródło: https://atlasprzetargow.pl / https://github.com/atlasprzetargow
- Pobierz Parquet/CSV z 1.4M rekordów BZP
- Sprawdź schemę: jakie pola, zakres dat, kompletność `value_contract`, `n_bidders`, `cpv`, `region`
- Załaduj do PostgreSQL (tabela `historical_tenders`) lub DuckDB
- Zapisz do `/home/ubuntu/terra-os/data/atlas/`
- **Output:** raport: które pola są użyteczne dla benchmarków i competitor analysis

#### 2. GUS BDL API (FREE, REST)
- Endpoint: https://bdl.stat.gov.pl/api/v1/
- Znajdź wskaźniki cen budowlanych: `ceny robót budowlano-montażowych`, `wskaźniki cen`
- Sprawdź granulację: per region (NUTS3/powiat)? per kwartał? per rodzaj robót?
- Pobierz próbkę dla CPV 45xxx (roboty budowlane) za ostatnie 4 lata
- **Output:** lista ID wskaźników + przykładowe dane + ocena przydatności

#### 3. DDC CWICR PL_WARSAW (FREE CC BY, Qdrant)
- Repozytorium: https://github.com/dariusz-wozniak/ddc-cwicr-pl-warsaw
- Sprawdź czy jest dostępny endpoint Qdrant lub plik do pobrania
- Test query: czy ma polskie KNR pozycje, ile ich jest, jaka jakość opisów
- **Output:** czy warto używać jako WARSTWA 2 (AI semantic search KNR)?

#### 4. BZP API e-Zamówienia (już używamy, ale schema niekompletna)
- Endpoint: `https://ezamowienia.gov.pl/mo-board/api/v1/notice`
- Sprawdź: czy API zwraca `n_bidders` (liczba ofert)? `value_contract` (cena wybranej oferty)?
- To kluczowe dla competitor analysis i bidding optimizer
- **Output:** lista pól dostępnych w API vs. to co mamy w modelu `tender`

#### 5. INTERCENBUD / SEKOCENBUD (płatne — rekonesans)
- Athenasoft: https://athenasoft.pl (INTERCENBUD + Norma PRO)
- Sprawdź czy jest formularz trial/demo, cena licencji, format danych
- SEKOCENBUD: https://sekocenbud.pl — formularz kontaktowy
- **Output:** czy warto negocjować licencję? co daje że Atlas/DDC nie daje?

---

### PLIKI REFERENCYJNE
- `/home/ubuntu/terra-os/SPEC.md` — fazy 26-40 (Blok B) — cel docelowy
- `/home/ubuntu/terra-os/RESEARCH.md` — desk research (punkt wyjścia, nie zweryfikowany)
- `/home/ubuntu/terra-os/services/api/services/api/routers/bzp.py` — aktualny BZP connector
- `/home/ubuntu/terra-os/services/ingestion/repository.py` — ingestion pipeline

---

### OUTPUT DISCOVERY SPRINT

Po zakończeniu utwórz plik `/home/ubuntu/terra-os/DATA_SOURCES.md`:
```
# Terra.OS — Zweryfikowane Źródła Danych

## Atlas Przetargów
- Status: ✅/❌ pobrane
- Rekordów: N
- Pola użyteczne: [lista]
- Jakość: X/10
- Rekomendacja: użyć/pominąć
- Lokalizacja: /home/ubuntu/terra-os/data/atlas/

## GUS BDL
...

## DDC CWICR
...

## BZP API (uzupełnienie)
...

## INTERCENBUD/SEKOCENBUD
...

## Rekomendacja architektury (po weryfikacji)
...
```

---

## KOMENDY TECHNICZNE

```bash
# Aktywacja środowiska
cd /home/ubuntu/terra-os
source .venv/bin/activate

# Testy (powinny być 312/312)
python3 -m pytest tests/ -q --no-header

# Status serwisów
sudo systemctl status terra-api terra-ui

# Restart API po zmianach
sudo systemctl restart terra-api

# DB (hasło: terra_dev_2026)
PGPASSFILE=/tmp/.pgpass psql -h 127.0.0.1 -U terraos -d terraos

# Logi API
journalctl -u terra-api -f
```

---

## ZASADY TECHNICZNE (KRYTYCZNE)

1. **Tailwind v4** — nowa składnia (`@import "tailwindcss"`, nie `@tailwind base`)
2. **motion/react** — NIE framer-motion
3. **AnimatePresence** — zawsze ternary `? : null` (NIE `&&`)
4. **API paths:** relative `/api/v1/...` (Caddy proxy)
5. **Odpowiedzi list:** `{items: [], total: N}`
6. **PLN format:** `1 200 000 zł`
7. **Daty:** `DD.MM.YYYY`
8. **Język UI:** polski
9. **Dark theme:** zinc/slate palette, earth-* accents
10. **NIE em-dash** (używaj –  lub -)
