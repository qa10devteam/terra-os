# Terra.OS

> **AI-powered tender intelligence & earthworks management for Polish construction companies** — discover tenders, estimate costs, assess risk, and dispatch crews, all in one local-first platform.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org)
[![License: BSL-1.0](https://img.shields.io/badge/license-BSL--1.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#running-tests)

---

## Why Terra.OS?

**Polish construction firms lose bids not because they lack expertise — but because of broken tools.**

| Pain Point | Terra.OS Solution |
|---|---|
| 😤 Manually browsing BZP/TED for relevant tenders every morning | **Zwiad** auto-ingests & scores tenders daily, surfacing only what matches your CPV profile |
| 📊 Kosztorysy built in Excel that nobody trusts | **Kosztorysant** runs two deterministic variants (doc + owner RMS) — totals reconcile to zero tolerance |
| 🎲 "We feel like we can win this" decisions | **Silnik** computes p10/p50/p90 margin distributions and win probability via Monte Carlo (L2) on top of symbolic rule checks (L1) |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Terra.OS Monorepo                           │
│                                                                     │
│  ┌──────────────┐   REST/JSON    ┌──────────────────────────────┐  │
│  │  apps/ui     │◄──────────────►│  services/api  (FastAPI)     │  │
│  │  (Next.js 15)│                │  127.0.0.1:8765              │  │
│  └──────────────┘                │                              │  │
│                                  │  ┌─────────┐  ┌──────────┐  │  │
│  ┌──────────────┐                │  │ Zwiad   │  │Kosztorys │  │  │
│  │  apps/desktop│                │  │ /zwiad  │  │/estimator│  │  │
│  │  (Tauri)     │                │  └─────────┘  └──────────┘  │  │
│  └──────────────┘                │  ┌─────────┐  ┌──────────┐  │  │
│                                  │  │ Silnik  │  │  Mózg    │  │  │
│  ┌──────────────┐                │  │ /engine │  │  /plans  │  │  │
│  │  apps/mobile │                │  └─────────┘  └──────────┘  │  │
│  │  (Flutter)   │                └──────────────────────────────┘  │
│  └──────────────┘                           │                      │
│                                             ▼                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              packages/db (SQLAlchemy 2.0 + Alembic)         │   │
│  │              PostgreSQL 16 + pgvector  (32 tables)          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  packages/shared: Provenance · Flag · AuditWriter · TerraError      │
└─────────────────────────────────────────────────────────────────────┘

External Sources: BZP · TED · Budzetowanie Kadr
LLM: Ollama (local) · AWS Bedrock (opt-in, gated)
```

---

## Quick Start

Get Terra.OS running in under 15 minutes.

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (or Docker)
- Git

### 1. Clone & configure

```bash
git clone https://github.com/your-org/terra-os.git
cd terra-os
cp .env.example .env
# Edit .env — set DB_PASSWORD and TERRA_SECRET_KEY at minimum
```

### 2. Start the database

```bash
# Option A: Docker (recommended)
docker compose -f docker-compose.dev.yml up -d

# Option B: existing PostgreSQL — ensure DB_URL is set in .env
```

### 3. Install Python dependencies & run migrations

```bash
python3.12 -m pip install -e packages/shared -e packages/db -e services/api
python3.12 -m alembic -c packages/db/alembic.ini upgrade head
python3.12 -m services.api.seed    # creates demo tenant + owner_profile
```

### 4. Start the API

```bash
uvicorn services.api.services.api.main:app --host 127.0.0.1 --port 8765
# API docs → http://127.0.0.1:8765/docs
```

### 5. Start the UI (optional)

```bash
cd apps/ui && npm ci && npm run dev
# UI → http://localhost:3000
```

**Done!** Try `curl http://127.0.0.1:8765/health` — you should see `{"status":"ok","db":"ok"}`.

---

## Modules

### 🔭 Zwiad — Tender Discovery
Automated daily ingestion from **BZP**, **TED**, and **Budzetowanie Kadr**. Filters by your CPV profile and voivodeship, scores each tender 0–1 via a deterministic algorithm (CPV overlap × value band × deadline feasibility × geo distance), then adds a local-LLM relevance pass over title and scope. Every match includes a Polish-language `match_reason`. Results are paginated with cursor-based navigation at `GET /api/v2/tenders`.

### 📐 Kosztorysant — Estimator
Produces two variants simultaneously: **Variant A (doc)** mirrors the buyer's simplified calc (Rozp. MRiT 20.12.2021), and **Variant B (owner)** uses your private rate card (`rate_card`) with RMS efficiency multipliers. Both are computed by deterministic local code — your rates **never leave the machine**. `GET /api/v1/estimates/{id}/compare` returns `delta_pln` and `margin_headroom_pct`.

### ⚙️ Silnik — Decision Engine (L1 + L2)
Two-layer engine that turns an estimate into a go/no-go signal. **L1 (symbolic)** runs clingo + Z3 axioms against the przedmiar, flagging violations with provenance and severity (`warn` / `block`). **L2 (stochastic)** runs a constrained Monte Carlo sampler (2 000 samples, reproducible under seed) to produce `margin_p10/p50/p90`, `win_prob_at_price` curves, and Sobol sensitivity `drivers`. Full run via `POST /api/v1/tenders/{id}/engine/run`.

### 🧠 Mózg — Resource Management *(Tier 3)*
OR-Tools MILP optimizer assigns equipment and crew to contracts by day, respecting availability, competency, and capacity. Builds daily dispatch plans with location pins, drawings, and cautions. All dispatches are **gated** — `POST /plans/{id}/dispatch` returns `approval_id`; actual push to mobile happens only after `POST /approvals/{id}/approve`. Learning loop on contract close updates `calibration_coeff` for future Variant B estimates.

---

## API Reference

Interactive Swagger UI available at **`http://127.0.0.1:8765/docs`** (dev mode only).

Key base paths:

| Prefix | Description |
|---|---|
| `/api/v2/auth` | Registration, login, token refresh |
| `/api/v2/tenders` | Tender list, detail, status patch |
| `/api/v1/tenders/{id}/engine/run` | Full L1+L2 engine run |
| `/api/v1/tenders/{id}/rfq` | RFQ creation (gated) |
| `/api/v1/plans` | Logistics plans |
| `/api/v1/approvals` | Approval gate management |

Full API documentation: [docs/api-reference.md](docs/api-reference.md)

---

## Contributing

1. **Fork** the repository and create a feature branch: `git checkout -b feat/my-feature`
2. **Follow** the code style: `ruff check .` + `black --check .` + `mypy --strict services packages`
3. **Write tests** — every new endpoint needs a contract test; engine changes need a golden fixture
4. **Run the full test suite** before opening a PR:
   ```bash
   python3.12 -m pytest tests/ -q
   cd apps/ui && npm run lint && npm run typecheck && npm test
   ```
5. **Zero-network rule:** all unit tests must pass with no internet access (use fixtures/stubs)
6. **Record assumptions** in `DECISIONS.md`; update `CHANGELOG.md` per [Keep a Changelog](https://keepachangelog.com)
7. **Open a PR** — describe what changes and why; link to the spec section if relevant

> ⚠️ **Security:** never commit real API keys, rate cards, or owner RMS data. The `.env.example` file contains only placeholder values.

---

## Project Status

| Milestone | Status | Description |
|---|---|---|
| M0 — Scaffold | ✅ Done | DB schema (32 tables), `/health`, 14 tests green |
| M1 — Ingestion | ✅ Done | BZP/TED connectors, CPV filter, scoring |
| M2 — Documents | ✅ Done | OCR, przedmiar parsing, RAG analysis |
| M3 — Estimator | ✅ Done | Variant A+B, compare, chat edits |
| M4 — Engine L1 | ✅ Done | Symbolic axiom engine, discrepancies |
| M5 — Engine L2 | ✅ Done | Monte Carlo risk, Sobol drivers |
| M6 — RFQ + Autofill | ✅ Done | Gated sends, IMAP parse, kosztorys sidebar |
| M7 — Mózg core | 🔄 In progress | OR-Tools optimizer, registries |
| M8 — Mobile | 🔄 In progress | Flutter app, offline cache |
| M9 — Orchestration | 🔄 In progress | LangGraph pipeline, packaging |

---

## License

Business Source License 1.0 (BSL-1.0). See [LICENSE](LICENSE) for details.  
Contact: [contact@terra-os.pl](mailto:contact@terra-os.pl)
