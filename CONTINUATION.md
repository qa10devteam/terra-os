# Terra.OS — kontynuacja projektu (Tier 2, M4+)

## Repo
https://github.com/qa10devteam/terra-os.git
branch: main, last commit: 147554f

## Stack
- Python 3.12 system-wide (`/usr/bin/python3.12`)
- FastAPI monorepo: `services/api/`, `services/ingestion/`, `services/documents/`, `services/ai/`, `services/estimator/`
- Next.js 16 UI: `apps/ui/`
- PostgreSQL 16 lokalnie: host=127.0.0.1, port=5432, db=terraos, user=terraos
- pgvector + pgcrypto aktywne
- Wszystkie pakiety zainstalowane edytowalnie (`pip install -e`)

## DB password
`terraosdev2026` — przekazuj przez env `DB_PASSWORD`, nie przez terminal (Hermes redaktuje `***`)

## Uruchamianie testów
```bash
TERRA_OFFLINE=1 DB_PASSWORD=terraosdev2026 DB_HOST=127.0.0.1 DB_PORT=5432 DB_NAME=terraos DB_USER=terraos \
  python3.12 -m pytest tests/ -q
```
Wynik: **85/85 ✅** (M0+M1+M2+M3)

## Ukończone Milestones

### M0 — Scaffold (commit 84baa30)
- FastAPI app, lifespan, CORS
- `GET /api/v1/health` → `{status: ok, db: ok}`
- Alembic migrations (raw DDL approach — `create_type=False` na 9 enumach)
- `packages/shared/` (provenance, flag, audit, errors)
- `packages/db/` (SQLAlchemy 2.0 models, session)
- 14 testów ✅

### M1 — Zwiad BZP (commit 1094517)
- `services/ingestion/` — bzp_connector, normalize, CPV/geo filter, scorer, repository, fixtures, pipeline
- `POST /api/v1/ingest/run` — pobiera ogłoszenia BZP (offline: 5 fixtures → 3 po filtrze)
- `GET /api/v1/tenders` — lista posortowana match_score DESC
- `GET /api/v1/tenders/{id}` — szczegół + raw
- CPV whitelist: prefixes 45112, 45111, 45231, 45233, 45262 (roboty ziemne)
- Geo filter: podkarpackie, małopolskie, śląskie, lubelskie, świętokrzyskie
- 29 testów ✅

### M2 — Documents/OCR/RAG (commit 73dd0f5)
- `services/ai/` — LLM router, StubClient (call_count tracking, JSON mode)
- `services/documents/` — fetch, classify (SWZ/STWiOR/przedmiar/umowa/other), ocr, parse_przedmiar, chunk+embed (384-dim), analysis
- Red-flags: kary_umowne, brak_waloryzacji, znwu_wysokie, krotki_termin, kara_odstapienie (regex + LLM)
- `POST /api/v1/tenders/{id}/analyze` → items + flags + chunks
- `GET /api/v1/tenders/{id}/analysis` → summary_md + red_flags[]
- DB table: `analysis` (UNIQUE on tender_id)
- 21 testów ✅

### M3 — Estimator MVP (commit 147554f)
- `services/estimator/` — Variant A (Wk=Σ(Lj×Cj), SEKOCENBUD BRZ), Variant B (Cj=Σ(n×c)+Kp+Z, RMS rate_card)
- `compare_estimates()` → delta_pln + margin_headroom_pct
- Sum reconciliation: `Σ(line_total) == total_net_pln` (Decimal, zero tolerance)
- No-egress-of-rates: StubClient._call_count nie wzrasta podczas Variant B
- `POST /api/v1/tenders/{id}/estimate` → obie wariacje
- `GET /api/v1/estimates/{id}` → szczegół + sum_reconciled
- `PATCH /api/v1/estimates/{id}/params` → recompute z nowymi KP/Z/robocizna
- `GET /api/v1/tenders/{id}/estimate/compare`
- DB: `estimate` tabela z enum `estimate_variant` (wartości: `doc`, `owner`)
- DB: `owner_profile` ma kolumnę `rate_card JSONB` (dodana przez ALTER TABLE)
- Acceptance A1: ingest → /tenders → analyze → estimate → compare (offline) ✅
- 21 testów ✅

## Następny krok: M4 — Decision Engine L1

### Co budować (spec/09):
**Build:** `engine/l1_symbolic` (clingo + Z3), facts builder, axiom tables + loader, discrepancy emission z provenance + `axiom_id`; `/engine/run`, `/rules/check`. Earthworks class-C corpus.

**DoD:** golden fixtures → expected discrepancies; each axiom has passing test; missing fact → flag.

**Acceptance T-M4:**
- broken-przedmiar fixture (missing dewatering, mass-balance off, sum mismatch) → exact flags z correct provenance
- clean fixture → feasible, no false positives

### Axiomy L1 (wstępne z badań):
- A001: masa_bilans — masa wykopu ≈ masa nasypu ± 15% (sprawdź tolerancję)
- A002: odwodnienie — jeśli wykop > 1.5m AND teren mokry → musi być pozycja odwodnienia
- A003: cena_rynkowa — Cj ≤ 1.5× stawki SEKOCENBUD (cena nienormalnie niska/wysoka)
- A004: pzp_abnormal_low — oferta ≤ 70% wartości zamawiającego → red flag
- A005: suma_zgodnosc — Σ(pozycje) == wartość z tytułu (1% tolerancja)
- A006: cpv_zgodnosc — CPV ogłoszenia ⊆ CPV zakresu robót w STWiOR

### Kluczowe decyzje architektoniczne:
- Alembic migration = raw DDL (`op.execute(DDL)`) — bez `op.create_table` z SA Enum
- `_clean_tenders()` w testach musi kasować: `estimate → analysis → tender` (FK kaskada)
- `estimate.variant` = enum `doc`/`owner` (nie `A`/`B`)
- Python 3.12 przez `subprocess` z `env` dict dla DB_PASSWORD
- httpx 0.28 → `ASGITransport(app=app)` (nie `app=app` bezpośrednio)
- `sum(..., Decimal("0"))` nie `sum(...)` dla Decimal (Pyright + Python)

## Pliki spec
```
/tmp/terra_os_spec/spec/   ← może nie istnieć po restarcie
/home/ubuntu/terra-os/spec/ ← zawsze dostępne
```
Spec files: 01_overview.md, 02_api_contracts.md, 03_modules.md, 04_data_model.md,
05_ai_and_ingestion.md, 06_security.md, 07_tech_stack.md, 08_deployment.md, 09_milestones_acceptance.md

## Vercel (apps/ui)
- Root Directory: `apps/ui` (musi być ustawione w Vercel dashboard!)
- `apps/ui/vercel.json` istnieje z `{"rewrites": [...]}`
- Next.js 16.2.9
- Build error: "Couldn't find any pages or app directory" = Vercel buduje z repo root
- FIX: w Vercel dashboard → Settings → General → Root Directory → `apps/ui`
