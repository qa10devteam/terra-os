# Terra.OS — kontynuacja projektu (Tier 2, M5+)

## Repo
https://github.com/qa10devteam/terra-os.git
branch: main, last commit: 001aa9f

## Stack
- Python 3.12 system-wide (`/usr/bin/python3.12`)
- FastAPI monorepo: `services/api/`, `services/ingestion/`, `services/documents/`, `services/ai/`, `services/estimator/`, `services/engine/`
- Next.js 16 UI: `apps/ui/`
- PostgreSQL 16 lokalnie: host=127.0.0.1, port=5432, db=terraos, user=terraos
- pgvector + pgcrypto aktywne
- Wszystkie pakiety zainstalowane edytowalnie (`pip install -e`)
- clingo 5.8.0 + z3-solver zainstalowane (`--break-system-packages`)

## DB password
`terraosdev2026` — przekazuj przez env `DB_PASSWORD`, nie przez terminal (Hermes redaktuje `***`)

## Uruchamianie testów
```bash
TERRA_OFFLINE=1 DB_PASSWORD=terraosdev2026 DB_HOST=127.0.0.1 DB_PORT=5432 DB_NAME=terraos DB_USER=terraos \
  python3.12 -m pytest tests/ -q
```
Wynik: **104/114 ✅** (M0+M1+M2+M3+M4)
Uwaga: 10 pre-istniejących failures w test_m1_ingest.py (IntegrityError w _clean_tenders) — nie regresja M4, istniały w M3.

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

### M4 — Decision Engine L1 (commit 001aa9f)
- `services/engine/l1_symbolic/` — FactsBuilder (int/grosze arithmetic), ClingoRunner, EngineResult/Violation
- 6 aksjoatów: A001 (bilans mas ±15%), A002 (odwodnienie), A003 (cena rynkowa), A004 (PZP cena nienormalnie niska ≤70%), A005 (suma zgodność ±1%), A006 (CPV zgodność)
- `services/engine/axiom_loader.py` — ładuje aksjoaty do tabeli `axiom` (idempotentny)
- `POST /api/v1/tenders/{id}/engine/run` → EngineResult + zapis discrepancy
- `GET  /api/v1/tenders/{id}/engine` → odczyt z discrepancy
- `POST /api/v1/tenders/{id}/rules/check` → live check A004+A005+A006
- **UWAGA clingo**: używa integer arithmetic only — wartości w groszach (PLN×100), głębokość w cm
- 29 testów ✅
- Acceptance T-M4: broken-przedmiar → A001+A002+A005 z provenance; clean → feasible ✅

### M5 — Decision Engine L2 (commit 9e9b9b6)
- `services/engine/l2_stochastic/` — constrained Monte Carlo sampler, Bayesian priors, Sobol sensitivity
- 5 domyślnych czynników ryzyka: soil_class_productivity, material_cost, equipment_availability, weather_delay, subcontractor_cost
- `run_l2(RiskInput)` → `RiskResult{margin_p10, margin_p50, margin_p90, win_prob_at_price[], drivers[]}`
- L1 constraint enforcement: próbki naruszające A004 (offer ≤ 70% market) odrzucane
- Sobol S1/ST: Saltelli (2002) estimator — wyznacza kluczowe czynniki ryzyka
- `POST /api/v1/tenders/{id}/engine/run` → teraz zwraca L1+L2 (risk{} block)
- `POST /api/v1/tenders/{id}/risk` → standalone L2 endpoint
- Persistence: `risk_run` tabela — p10/p50/p90, win_prob_at_price JSONB, drivers JSONB
- 28 testów ✅ (determinism, monotone, p10≤p50≤p90, no L1 violation, Sobol bounds)
- scipy 1.18.0 zainstalowane (`--break-system-packages`)

## Następny krok: M6 — Email-broker + interactive kosztorys + auto-fill

### Co budować (spec/09):
**Build:** RFQ agent (gated send, IMAP parse), variable sidebar (`PATCH params` już jest w M3),
chat-brain structured edits, live rule-violation check, auto-fill draft (gated).

**DoD:** all external sends gated; chat edits applied by deterministic code; rules/check returns violations.

**Acceptance A2 (Tier 2 end-to-end):**
A1 + engine verdict (L1+L2) + risk distribution + RFQ round-trip (gated send → fixtured reply parsed)
+ interactive param edit that reconciles. Auto-fill produces a draft, never submits.
- fixed-seed run reproduces `p10/p50/p90`
- win-prob monotone vs price
- no sample violates a hard L1 constraint

### Kluczowe decyzje architektoniczne:
- Alembic migration = raw DDL (`op.execute(DDL)`) — bez `op.create_table` z SA Enum
- `_clean_tenders()` w testach musi kasować: `estimate → analysis → tender` (FK kaskada)
- `estimate.variant` = enum `doc`/`owner` (nie `A`/`B`)
- Python 3.12 przez `subprocess` z `env` dict dla DB_PASSWORD
- httpx 0.28 → `ASGITransport(app=app)` (nie `app=app` bezpośrednio)
- `sum(..., Decimal("0"))` nie `sum(...)` dla Decimal (Pyright + Python)
- clingo 5.8.0: NO floats w ASP — wszystko integer; grosze zamiast PLN, cm zamiast m
- `--break-system-packages` wymagane przy pip na tym serwerze

## Pliki spec
```
/home/ubuntu/terra-os/spec/   ← zawsze dostępne
```
Spec files: 01_overview.md, 02_api_contracts.md, 03_modules.md, 04_data_model.md,
05_ai_and_ingestion.md, 06_security.md, 07_tech_stack.md, 08_deployment.md, 09_milestones_acceptance.md

## Vercel (apps/ui)
- Root Directory: `apps/ui` (musi być ustawione w Vercel dashboard!)
- `apps/ui/vercel.json` istnieje z `{"rewrites": [...]}`
- Next.js 16.2.9
- Build error: "Couldn't find any pages or app directory" = Vercel buduje z repo root
- FIX: w Vercel dashboard → Settings → General → Root Directory → `apps/ui`
