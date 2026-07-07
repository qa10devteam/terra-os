# Terra.OS — Batch 3: Technical Writer Output

**Agent:** 📚 Technical Writer  
**Date:** 2024  
**Status:** ✅ Complete

---

## Table of Contents

1. [Developer Guide — Getting Started](#1-developer-guide--getting-started)
2. [API Documentation](#2-api-documentation)
3. [User Guide (Polish) — Kierownicy Przetargów](#3-user-guide--kierownicy-przetargów)
4. [Changelog Template](#4-changelog)

---

# 1. Developer Guide — Getting Started

## Overview

Terra.OS is a FastAPI + Next.js monorepo for Polish construction companies. This guide walks you from zero to a running local dev environment with your first successful API call.

**Estimated time:** 10–15 minutes  
**Target audience:** Backend, frontend, and fullstack developers

---

## Prerequisites

| Tool | Required Version | Check |
|---|---|---|
| Python | 3.12+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| npm | 10+ | `npm --version` |
| PostgreSQL | 15 or 16 | `psql --version` |
| Git | any | `git --version` |
| Docker *(optional)* | 24+ | `docker --version` |

> **Note:** Redis is not required for the core API. It is used by optional Celery workers (`services/api/services/api/celery_app.py`) for background tasks. For local dev, you can skip it unless working on async task features.

---

## Clone + Setup

### Step 1: Clone the repository

```bash
git clone https://github.com/your-org/terra-os.git
cd terra-os
```

### Step 2: Create and activate a Python virtual environment

```bash
# Using venv (standard)
python3.12 -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows

# Or using uv (faster)
uv venv --python 3.12
source .venv/bin/activate
```

### Step 3: Install Python packages in editable mode

The monorepo has three installable Python packages. Install all three:

```bash
pip install -e packages/shared -e packages/db -e services/api
```

This gives you:
- `terra_shared` — Provenance, Flag, AuditWriter, TerraError
- `terra_db` — SQLAlchemy 2.0 models, Alembic config, `get_engine()`, `get_session()`
- `services.api` — FastAPI application with all routers

### Step 4: Install UI dependencies

```bash
cd apps/ui
npm ci
cd ../..
```

---

## Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

### `.env.example` — annotated

```dotenv
# ─── Database ──────────────────────────────────────────────────────────────
# Full PostgreSQL connection URL
# Format: postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME
DB_URL=postgresql+psycopg2://terra:CHANGE_ME@localhost:5432/terra_os

# Password only (used by docker-compose.dev.yml to create the DB)
DB_PASSWORD=CHANGE_ME

# ─── Security ──────────────────────────────────────────────────────────────
# Secret key for JWT signing. MUST be set. Generate with:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
TERRA_SECRET_KEY=CHANGE_ME_generate_a_long_random_string

# JWT token lifetime in minutes (default: 60)
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Refresh token lifetime in days (default: 30)
REFRESH_TOKEN_EXPIRE_DAYS=30

# ─── Environment ───────────────────────────────────────────────────────────
# "dev" enables Swagger UI at /docs; any other value disables it
ENVIRONMENT=dev

# ─── LLM (optional for local dev) ─────────────────────────────────────────
# LLM backend: "stub" (no LLM, returns fixtures), "ollama", or "bedrock"
LLM_BACKEND=stub

# Ollama endpoint (only used when LLM_BACKEND=ollama)
OLLAMA_URL=http://localhost:11434

# AWS region for Bedrock (only used when LLM_BACKEND=bedrock)
AWS_DEFAULT_REGION=eu-central-1

# ─── Email (optional — gated RFQ sends) ────────────────────────────────────
# If not set, email sends are simulated in dev mode
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
IMAP_HOST=
IMAP_USER=
IMAP_PASSWORD=

# ─── Tier feature flags ─────────────────────────────────────────────────────
# "1" = Tier 1 only, "2" = Tier 1+2, "3" = all tiers
TIER=2

# ─── Celery / Redis (optional — async tasks only) ───────────────────────────
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## Database Setup

### Option A: Docker (recommended for local dev)

```bash
docker compose -f docker-compose.dev.yml up -d
# Starts: PostgreSQL 16 + pgvector on port 5432
# Health check: docker compose ps
```

### Option B: Existing PostgreSQL instance

```bash
# Create the database manually
psql -U postgres -c "CREATE USER terra WITH PASSWORD 'CHANGE_ME';"
psql -U postgres -c "CREATE DATABASE terra_os OWNER terra;"
psql -U terra terra_os -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -U terra terra_os -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
```

### Run Alembic Migrations

```bash
# Upgrade to latest schema (32 tables)
python3.12 -m alembic -c packages/db/alembic.ini upgrade head

# Verify: should show no pending migrations
python3.12 -m alembic -c packages/db/alembic.ini current
```

### Seed Demo Data

```bash
# Creates: demo tenant, owner_profile, sample rate_card, test user
python3.12 -m services.api.seed
```

After seeding you'll have:
- **User:** `demo@terra-os.pl` / `demo1234`
- **Tenant:** `tenant_demo`
- **Owner profile:** CPV `45110000`, `45112000`, voivodeship: `mazowieckie`

### Rollback (if needed)

```bash
# Roll back one migration
python3.12 -m alembic -c packages/db/alembic.ini downgrade -1

# Roll back everything
python3.12 -m alembic -c packages/db/alembic.ini downgrade base
```

---

## Running Tests

Terra.OS uses `pytest` with a **zero-network** policy — all tests pass without internet access.

### Full test suite

```bash
python3.12 -m pytest tests/ -v
```

### With coverage report

```bash
python3.12 -m pytest tests/ --cov=services --cov=packages --cov-report=term-missing -q
```

### Run specific test categories

```bash
# Engine golden tests only
python3.12 -m pytest tests/ -k "engine" -v

# Contract / API tests
python3.12 -m pytest tests/ -k "api or contract" -v

# Sum reconciliation tests
python3.12 -m pytest tests/ -k "reconcil" -v

# Skip slow tests
python3.12 -m pytest tests/ -m "not slow" -q
```

### Lint + type checks (required before PR)

```bash
ruff check .
black --check .
mypy --strict services packages
```

### UI tests

```bash
cd apps/ui
npm run lint
npm run typecheck
npm test
```

---

## Starting the Development Server

```bash
# Make sure .env is loaded (or export DB_URL manually)
uvicorn services.api.services.api.main:app \
  --host 127.0.0.1 \
  --port 8765 \
  --reload

# API available at: http://127.0.0.1:8765
# Swagger UI:       http://127.0.0.1:8765/docs  (ENVIRONMENT=dev only)
# Health check:     http://127.0.0.1:8765/health
```

Start the UI in a separate terminal:

```bash
cd apps/ui
npm run dev
# UI available at: http://localhost:3000
```

---

## Making Your First API Call

### 1. Get an auth token

```bash
curl -s -X POST http://127.0.0.1:8765/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@terra-os.pl","password":"demo1234"}' \
  | python3 -m json.tool
```

Copy the `access_token` from the response.

### 2. List tenders

```bash
TOKEN="your_access_token_here"

curl -s http://127.0.0.1:8765/api/v2/tenders \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

### 3. Run the engine on a tender

```bash
TENDER_ID="uuid-of-a-tender"

curl -s -X POST \
  "http://127.0.0.1:8765/api/v1/tenders/$TENDER_ID/engine/run?seed=42&n_samples=500" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

---

## Common Errors & Fixes

### `ModuleNotFoundError: No module named 'terra_db'`

**Cause:** packages not installed in editable mode.  
**Fix:**
```bash
pip install -e packages/shared -e packages/db -e services/api
```

### `sqlalchemy.exc.OperationalError: could not connect to server`

**Cause:** PostgreSQL not running, or `DB_URL` not set.  
**Fix:**
```bash
# Check Docker containers
docker compose ps

# Or export manually
export DB_URL=postgresql+psycopg2://terra:CHANGE_ME@localhost:5432/terra_os
```

### `alembic.util.exc.CommandError: Can't locate revision identified by '...'`

**Cause:** Migration history is out of sync (e.g., after a hard reset).  
**Fix:**
```bash
python3.12 -m alembic -c packages/db/alembic.ini stamp head
python3.12 -m alembic -c packages/db/alembic.ini upgrade head
```

### `HTTP 403 — no_org`

**Cause:** Authenticated user has no `org_id` (not assigned to an organization).  
**Fix:** Make sure you used the seeded demo user, or run:
```bash
python3.12 -m services.api.seed
```

### `HTTP 401 — Nieprawidłowy email lub hasło`

**Cause:** Wrong credentials, or user doesn't exist yet.  
**Fix:** Register first via `POST /api/v2/auth/register`, or use seeded demo credentials.

### `HTTP 422 — invalid_status`

**Cause:** Sent an unrecognized tender status value.  
**Valid values:** `new`, `matched`, `watching`, `analyzing`, `estimated`, `decided_go`, `decided_nogo`, `archived`

### Tests fail with `network access denied`

**Cause:** A test is making real HTTP calls. Terra.OS tests must be zero-network.  
**Fix:** Add a `requests_mock` or `responses` fixture, or use the existing `conftest.py` stubs.

### `TERRA_SECRET_KEY` missing on startup

**Cause:** The JWT secret is not set.  
**Fix:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# Add the output to .env as TERRA_SECRET_KEY=<value>
```

---

---

# 2. API Documentation

**Base URL:** `http://127.0.0.1:8765`  
**Auth:** Bearer JWT in `Authorization` header  
**Content-Type:** `application/json`

All error responses follow:
```json
{
  "error": {
    "code": "error_code",
    "message": "Human-readable message",
    "details": {}
  }
}
```

---

## Endpoint 1: POST /api/v2/auth/login

### Description

Authenticates a user with email + password. Returns a short-lived JWT access token and a long-lived refresh token. The access token must be included in `Authorization: Bearer <token>` for all protected endpoints.

### Request Body

```json
{
  "email": "jan.kowalski@firma.pl",
  "password": "MySecurePassword1"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `email` | string | ✅ | User email address (case-insensitive) |
| `password` | string | ✅ | User password (min. 8 characters) |

### Response `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "dGVzdC10b2tlbi1yZWZyZXNodA==",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "jan.kowalski@firma.pl",
    "name": "Jan Kowalski",
    "org_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "role": "owner"
  }
}
```

| Field | Type | Description |
|---|---|---|
| `access_token` | string | JWT, valid for `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 min) |
| `refresh_token` | string | Opaque token, valid for `REFRESH_TOKEN_EXPIRE_DAYS` (default: 30 days) |
| `token_type` | string | Always `"bearer"` |
| `user.role` | string | `"owner"` \| `"manager"` \| `"viewer"` |

### Error Codes

| HTTP | Code | Message |
|---|---|---|
| `401` | — | `Nieprawidłowy email lub hasło` |
| `403` | — | `Konto dezaktywowane` |
| `422` | — | Validation error (malformed JSON) |

### cURL Example

```bash
curl -X POST http://127.0.0.1:8765/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@terra-os.pl",
    "password": "demo1234"
  }'
```

---

## Endpoint 2: GET /api/v2/tenders

### Description

Returns a paginated list of tenders for the authenticated user's organization. Supports cursor-based pagination and multiple filter parameters. Excludes `archived` tenders by default (unless `status=archived` is explicitly requested).

### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `cursor` | string | — | Opaque pagination cursor from previous response's `next_cursor` |
| `limit` | integer | `50` | Results per page (1–200) |
| `status` | string | — | Filter by status: `new`, `matched`, `watching`, `analyzing`, `estimated`, `decided_go`, `decided_nogo`, `archived` |
| `cpv` | string | — | CPV prefix filter, e.g. `45110` matches all `4511x` codes |
| `voivodeship` | string | — | Partial match on voivodeship name, e.g. `mazow` |
| `value_min` | float | — | Minimum `value_pln` (PLN) |
| `value_max` | float | — | Maximum `value_pln` (PLN) |
| `deadline_before` | string | — | ISO 8601 date, e.g. `2024-12-31` |

### Response `200 OK`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "Budowa drogi gminnej w miejscowości Przykładowo",
      "buyer": "Gmina Przykładowo",
      "cpv": ["45110000", "45233120"],
      "voivodeship": "mazowieckie",
      "value_pln": 2350000.00,
      "deadline_at": "2024-11-15T23:59:00",
      "published_at": "2024-10-01T08:00:00",
      "url": "https://ezamowienia.gov.pl/mp-client/search/list/ocds-148610-...",
      "status": "matched",
      "match_score": 0.87,
      "created_at": "2024-10-01T09:15:32"
    }
  ],
  "total": 142,
  "next_cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNC0xMC0wMVQwOToxNTozMiIsImlkIjoiNTUwZTg0MDAifQ=="
}
```

| Field | Type | Description |
|---|---|---|
| `items` | array | Array of tender objects |
| `total` | integer | Total matching records (before cursor offset) |
| `next_cursor` | string \| null | Pass to next request as `cursor`; `null` means last page |
| `match_score` | float \| null | 0–1 relevance score; `null` if not yet scored |

### Error Codes

| HTTP | Code | Description |
|---|---|---|
| `400` | `invalid_cursor` | Cursor is malformed or expired |
| `401` | — | Missing or invalid access token |
| `403` | `no_org` | Authenticated user has no organization |
| `422` | `invalid_status` | Unknown status value |

### cURL Example

```bash
TOKEN="your_access_token_here"

# Basic list
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8765/api/v2/tenders"

# Filtered: mazowieckie, value 1M–5M PLN, CPV 45110
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8765/api/v2/tenders?voivodeship=mazow&value_min=1000000&value_max=5000000&cpv=45110"

# Second page
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8765/api/v2/tenders?cursor=eyJjcmVhdGVkX2F0IjoiMjAyNC0xMC0wMVQwOToxNTozMiIsImlkIjoiNTUwZTg0MDAifQ=="
```

---

## Endpoint 3: POST /api/v1/tenders/{id}/engine/run

### Description

Runs the full two-layer decision engine for a tender:

- **L1 (Symbolic):** Checks przedmiar items and estimate against earthworks axiom corpus (clingo + Z3). Produces `violations[]` with provenance and severity. Results stored in `discrepancy` table (previous violations replaced).
- **L2 (Stochastic):** If an estimate exists, runs constrained Monte Carlo sampling to produce margin distribution (p10/p50/p90) and win probability curves. Results stored in `risk_run` table.

Requires the tender to have at least one `analysis` record (run `POST /tenders/{id}/analyze` first).

### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `tender_id` | UUID string | Tender ID |

### Query Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `seed` | integer | `42` | Random seed for L2 reproducibility |
| `n_samples` | integer | `2000` | Monte Carlo sample count (higher = more accurate, slower) |

### Request Body

*None required.*

### Response `200 OK`

```json
{
  "feasible": true,
  "violations": [
    {
      "axiom_code": "A004",
      "axiom_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "severity": "warn",
      "message": "Cena oferty (1 850 000 PLN) jest o 21% niższa od szacunku zamawiającego. Ryzyko odrzucenia jako rażąco niska.",
      "provenance": {
        "page": 12,
        "section": "Rozdział III pkt 4",
        "source": "SWZ_v2.pdf"
      }
    }
  ],
  "risk": {
    "margin_p10": -0.032,
    "margin_p50": 0.081,
    "margin_p90": 0.194,
    "win_prob_at_price": [
      {"price_pln": 1700000.0, "win_prob": 0.85, "margin_p50": 0.12},
      {"price_pln": 1850000.0, "win_prob": 0.62, "margin_p50": 0.08},
      {"price_pln": 2000000.0, "win_prob": 0.38, "margin_p50": 0.05}
    ],
    "drivers": [
      {"factor": "cost_overrun", "S1": 0.41, "ST": 0.48},
      {"factor": "volume_deviation", "S1": 0.28, "ST": 0.33},
      {"factor": "market_price_uncertainty", "S1": 0.18, "ST": 0.22}
    ],
    "n_samples_used": 1987,
    "n_rejected": 13
  },
  "explanation_md": "## Analiza przetargu\n\nSilnik L1 wykrył 1 ostrzeżenie (brak blokad). Analiza ryzyka L2 wskazuje pozytywną marżę p50 = 8.1%..."
}
```

| Field | Type | Description |
|---|---|---|
| `feasible` | boolean | `true` if no `block`-severity violations |
| `violations[].severity` | string | `"warn"` (informational) or `"block"` (hard stop) |
| `risk.margin_p10/p50/p90` | float | Margin as fraction (e.g. `0.081` = 8.1%). Negative = projected loss |
| `risk.win_prob_at_price` | array | Price sensitivity curve: given price → win probability |
| `risk.drivers` | array | Sobol sensitivity indices: `S1` = first-order, `ST` = total-order |
| `explanation_md` | string | LLM-generated markdown summary (the **only** LLM-authored field) |

### Error Codes

| HTTP | Description |
|---|---|
| `404` | Tender not found |
| `422` | No estimate found — run `POST /estimate` (Variant A) first |

### cURL Example

```bash
TOKEN="your_access_token_here"
TENDER_ID="550e8400-e29b-41d4-a716-446655440001"

curl -X POST \
  "http://127.0.0.1:8765/api/v1/tenders/$TENDER_ID/engine/run?seed=42&n_samples=2000" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Endpoint 4: POST /api/v1/tenders/{id}/rfq

### Description

Creates a Request for Quotation (RFQ) draft for out-of-scope subcontracting items and enters the **approval gate**. Returns `202 Accepted` with an `approval_id` — **no emails are sent at this point**. The actual send is triggered only by `POST /approvals/{approval_id}/approve`.

This design ensures all external communications are human-reviewed before dispatch.

### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `tender_id` | UUID string | Parent tender ID |

### Request Body

```json
{
  "scope_desc": "Dostawa i montaż elementów placu zabaw zgodnie z pkt 4.3 SWZ",
  "counterparties": [
    "firma-ogrodnicza@example.pl",
    "playground-supplier@example.com"
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `scope_desc` | string | ✅ | Description of the work/items to quote. Used as email subject prefix |
| `counterparties` | array of strings | — | Recipient email addresses. Can be empty (add later) |

### Response `202 Accepted`

```json
{
  "approval_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

Use `GET /api/v1/approvals?status=pending` to list pending approvals, then:
- **Send:** `POST /api/v1/approvals/{approval_id}/approve`
- **Cancel:** `POST /api/v1/approvals/{approval_id}/reject`

### Approval Execute Response (`POST /approvals/{id}/approve`)

```json
{
  "executed": true,
  "result": {
    "rfq_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "sent_to": ["firma-ogrodnicza@example.pl", "playground-supplier@example.com"]
  }
}
```

### Error Codes

| HTTP | Description |
|---|---|
| `404` | Tender not found |
| `409` | Approval already processed (on `/approvals/{id}/approve`) |

### cURL Example

```bash
TOKEN="your_access_token_here"
TENDER_ID="550e8400-e29b-41d4-a716-446655440001"

# Step 1: Create RFQ (gated)
APPROVAL_ID=$(curl -s -X POST \
  "http://127.0.0.1:8765/api/v1/tenders/$TENDER_ID/rfq" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scope_desc": "Dostawa elementów placu zabaw wg SWZ pkt 4.3",
    "counterparties": ["supplier@example.pl"]
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['approval_id'])")

echo "Approval ID: $APPROVAL_ID"

# Step 2: Approve the send
curl -s -X POST \
  "http://127.0.0.1:8765/api/v1/approvals/$APPROVAL_ID/approve" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Endpoint 5: GET /api/v1/plans/{id}

### Description

Returns a fully assembled daily logistics plan for a crew dispatch. Plans include location data (lat/lng Google Maps pin), technical cautions derived from tender documents, assigned equipment and employees, and the boss note. Plans are created by `POST /api/v1/plans` (Tier 3 / Module 3 only) and dispatched via the approval gate.

### Path Parameters

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID string | Plan ID |

### Response `200 OK`

```json
{
  "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "contract_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "date": "2024-11-20",
  "status": "dispatched",
  "location": {
    "lat": 52.2297,
    "lng": 21.0122,
    "address": "ul. Przykładowa 15, 00-001 Warszawa",
    "maps_url": "https://maps.google.com/?q=52.2297,21.0122"
  },
  "assignments": [
    {
      "employee_id": "e5f6a7b8-c9d0-1234-efab-345678901234",
      "employee_name": "Tomasz Nowak",
      "role": "operator_koparki",
      "equipment_id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
      "equipment_name": "Koparka Komatsu PC210",
      "start_time": "07:00",
      "end_time": "15:00"
    }
  ],
  "cautions_md": "## Uwagi techniczne\n\n- Głębokość wykopu: 2.5m — wymagane szalowanie\n- Poziom wód gruntowych: 1.8m — pompy odwadniające obowiązkowe\n- Strefa ochronna kabli elektrycznych w odległości 1m od osi wykopu",
  "boss_note": "Priorytet: dokończyć odcinek A–B. Inspektor nadzoru na placu o 10:00.",
  "documents": [
    {
      "kind": "drawing",
      "filename": "przekroj_A-B.pdf",
      "url": "/api/v1/documents/abc123/download"
    }
  ],
  "dispatch": {
    "dispatched_at": "2024-11-19T18:00:00",
    "dispatched_by": "Jan Kowalski",
    "recipients": ["tomasz.nowak@firma.pl"]
  },
  "created_at": "2024-11-19T15:30:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | `draft` \| `approved` \| `dispatched` \| `completed` |
| `assignments` | array | Employee + equipment assignments for this day |
| `cautions_md` | string | AI-extracted technical cautions from tender docs (markdown) |
| `dispatch` | object \| null | Present when status is `dispatched` or `completed` |

### Error Codes

| HTTP | Description |
|---|---|
| `401` | Missing or invalid access token |
| `404` | Plan not found |

### cURL Example

```bash
TOKEN="your_access_token_here"
PLAN_ID="c3d4e5f6-a7b8-9012-cdef-123456789012"

curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8765/api/v1/plans/$PLAN_ID" \
  | python3 -m json.tool
```

---

---

# 3. User Guide — Kierownicy Przetargów

## Przewodnik użytkownika Terra.OS
### Dla: Kierowników Przetargów i Decydentów

---

## Wprowadzenie

Terra.OS to platforma wspierająca polskie firmy budowlane w procesie przetargowym — od odkrycia ogłoszenia, przez wycenę, po decyzję GO/NO-GO. Nie zastępuje Twojej wiedzy — pomaga Ci działać szybciej i z większą pewnością.

**Główny przepływ pracy:**

```
Przetarg w BZP/TED
      ↓
   [ZWIAD] Odkrycie i ocena trafności
      ↓
   [KOSZTORYS] Wycena robót (Wariant A + B)
      ↓
   [SILNIK] Analiza ryzyka (L1 + L2)
      ↓
   [DECYZJA] Dashboard GO / NO-GO
      ↓
   [MÓZG] Plan logistyczny i dyspozycja (Tier 3)
```

---

## Onboarding: Pierwsze Kroki — 5 kroków do GO/NO-GO

Poniższe 5 kroków przeprowadza Cię przez cały proces od pierwszego logowania do podjęcia decyzji przetargowej.

---

### Krok 1: Zaloguj się i sprawdź profil firmy

[SCREENSHOT: Ekran logowania Terra.OS]

1. Otwórz przeglądarkę i przejdź na adres: `http://localhost:3000` (lub adres podany przez administratora)
2. Wpisz swój adres e-mail i hasło, kliknij **Zaloguj się**
3. Po zalogowaniu przejdź do **Ustawienia → Profil firmy**
4. Sprawdź, czy uzupełnione są:
   - **Preferowane kody CPV** (np. `45110000` — rozbiórka, `45112000` — roboty ziemne)
   - **Województwa działalności**
   - **Maksymalna wartość kontraktu** (Twoja zdolność wykonawcza)

> 💡 **Wskazówka:** Im dokładniej wypełniony profil firmy, tym trafniejsze dopasowania Zwiad będzie pokazywał każdego dnia.

---

### Krok 2: Odkryj przetargi w Zwiadzie

[SCREENSHOT: Dashboard Zwiad — lista przetargów z match_score]

1. Kliknij **Zwiad** w menu głównym
2. Zobaczysz listę przetargów posortowanych według **Match Score** (0–100%) — to miara trafności dla Twojej firmy
3. Użyj filtrów po lewej stronie:
   - **Status:** `Nowe`, `Obserwowane`, `Analizowane`
   - **Województwo:** np. `mazowieckie`
   - **Wartość:** przedział kwotowy
   - **Termin składania:** data graniczna
4. Kliknij na tytuł przetargu, żeby zobaczyć szczegóły i uzasadnienie dopasowania (`match_reason`)
5. Przetarg, który Cię interesuje — kliknij **Zacznij analizę** (zmienia status na `analyzing`)

> 💡 **Kiedy Match Score jest wysoki (>80%):** CPV, wartość i lokalizacja dobrze pasują do Twojego profilu. Warto przeanalizować.
> 
> ⚠️ **Kiedy Match Score jest niski (<40%):** System widzi słabe dopasowanie — możesz pominąć lub zbadać ręcznie.

---

### Krok 3: Wycień przetarg w Kosztorysancie

[SCREENSHOT: Widok Kosztorysant — dwie kolumny: Wariant A i Wariant B]

Po uruchomieniu analizy dokumentów (automatyczne lub ręczne), przejdź do zakładki **Kosztorys**.

#### Wariant A — Dokumentacyjny (jak zamawiający)
- Wycena oparta na cenach rynkowych i katalogach KNR
- **Używaj do:** porównania z szacunkiem zamawiającego

#### Wariant B — Własny (Twoje stawki)
- Wycena oparta na Twojej karcie stawek (RMS)
- **Używaj do:** sprawdzenia rzeczywistej marży

#### Jak korzystać z paska zmiennych:

[SCREENSHOT: Sidebar z suwakami — narzut, zysk, efektywność]

1. Po prawej stronie znajdziesz **panel parametrów**:
   - **Narzut ogólny (%)** — koszty pośrednie firmy
   - **Zysk (%)** — planowana marża
   - **Współczynnik efektywności** — korekta tempa robót
2. Zmień wartości suwakami — kosztorys przelicza się **natychmiast**
3. Każda zmiana jest zapisywana w historii (zakładka **Historia zmian**)

#### Tabela porównawcza:

| | Wariant A (Rynek) | Wariant B (Twój) |
|---|---|---|
| Suma netto | 2 350 000 PLN | 2 180 000 PLN |
| Różnica | — | -170 000 PLN |
| Headroom marży | — | **7,2%** |

> ✅ **Headroom > 5%:** dobry bufor bezpieczeństwa
> ⚠️ **Headroom 0–5%:** ryzykowne — mały margines błędu
> ❌ **Headroom < 0%:** nie składaj oferty bez weryfikacji stawek

---

### Krok 4: Uruchom Silnik i interpretuj wyniki

[SCREENSHOT: Panel Silnik — wynik GO z wykresem p10/p50/p90]

Kliknij **Uruchom Silnik** (przycisk w górnym pasku). Analiza trwa 10–30 sekund.

#### Wyniki L1 — Kontrola zasad (Symboliczna)

[SCREENSHOT: Lista naruszeń z kolorami — zielony/żółty/czerwony]

Silnik sprawdza przetarg i kosztorys pod kątem **reguł prawa i dobrych praktyk**:

| Ikona | Znaczenie | Co robić? |
|---|---|---|
| 🟢 **Feasible: TAK** | Brak blokad — przetarg technicznie wykonalny | Przejdź do oceny ryzyka |
| 🟡 **Ostrzeżenie (warn)** | Potencjalny problem — wymaga uwagi | Czytaj uzasadnienie, oceń ryzyko |
| 🔴 **Blokada (block)** | Twarda przeszkoda — oferta może zostać odrzucona | NIE składaj bez rozwiązania problemu |

**Przykłady naruszeń:**
- `A002` — *„Brak pozycji odwodnienia wykopów przy poziomie WG 1.8m"* → 🔴 BLOCK
- `A004` — *„Twoja cena jest 21% poniżej szacunku zamawiającego — ryzyko rażąco niskiej ceny"* → 🟡 WARN
- `A005` — *„Termin realizacji 45 dni jest nierealistyczny dla wolumenu 8 500 m³"* → 🔴 BLOCK

#### Wyniki L2 — Rozkład Marży (Monte Carlo)

[SCREENSHOT: Wykres rozkładu marży — trzy słupki p10/p50/p90]

Silnik uruchamia 2 000 symulacji i pokazuje trzy scenariusze:

| Miara | Co oznacza | Interpretacja |
|---|---|---|
| **p10** | Pesymistyczny (10% szans na GORSZY wynik) | Sprawdź: czy nadal opłacalne? |
| **p50** | Bazowy (mediana) | Twój najbardziej prawdopodobny wynik |
| **p90** | Optymistyczny (10% szans na LEPSZY wynik) | Górny potencjał |

**Przykład:**
- p10 = **-3,2%** (możliwa strata 3,2%)
- p50 = **+8,1%** (spodziewana marża 8,1%)
- p90 = **+19,4%** (optymistyczny scenariusz)

#### Krzywa prawdopodobieństwa wygranej

[SCREENSHOT: Wykres cena vs win_prob]

Pokazuje, jak zmiana ceny oferty wpływa na szansę wygranej:

| Cena oferty | Szansa wygranej |
|---|---|
| 1 700 000 PLN (nisko) | 85% |
| 1 850 000 PLN (bazowo) | 62% |
| 2 000 000 PLN (wysoko) | 38% |

> 💡 **Użyj tej tabeli do negocjacji:** jeśli konkurencja jest silna, rozważ obniżenie ceny do punktu, gdzie win_prob > 60%.

#### Główne czynniki ryzyka (Drivers)

[SCREENSHOT: Wykres słupkowy drivers]

Sobol Sensitivity — co ma największy wpływ na marżę:
- `cost_overrun` (S1=0.41) — przekroczenie kosztów własnych — **najważniejszy czynnik**
- `volume_deviation` (S1=0.28) — zmiana wolumenu robót
- `market_price_uncertainty` (S1=0.18) — wahania rynkowe

---

### Krok 5: Podejmij decyzję GO / NO-GO

[SCREENSHOT: Dashboard decyzji — duże przyciski GO i NO-GO]

Po przejrzeniu wszystkich analiz przejdź do zakładki **Decyzja**.

#### Panel GO / NO-GO

Platforma wyświetla podsumowanie:

```
┌─────────────────────────────────────────────────────────┐
│  PRZETARG: Budowa drogi gminnej — Gmina Przykładowo     │
│  Wartość: 2 350 000 PLN | Termin: 15 listopada 2024     │
├─────────────────────────────────────────────────────────┤
│  Match Score:    87%  ✅                                 │
│  Feasible (L1):  TAK  ✅  (1 ostrzeżenie, 0 blokad)     │
│  Marża p50:      8,1% ✅                                 │
│  Win Prob:       62%  ✅  (przy cenie 1 850 000 PLN)     │
├─────────────────────────────────────────────────────────┤
│  Rekomendacja systemu:  ✅ GO (warunkowo)                │
│                                                         │
│  Powód: Dobra marża, brak blokad. Uwaga: ryzyko         │
│  rażąco niskiej ceny — rozważ korektę do 1 920 000 PLN  │
├─────────────────────────────────────────────────────────┤
│  [   ✅ IDZIE  —  GO   ]    [  ❌ ODPUSZCZAMY  —  NO-GO ]│
└─────────────────────────────────────────────────────────┘
```

#### Jak podjąć decyzję:

1. **Przeczytaj rekomendację systemu** — to sugestia, nie nakaz
2. **Sprawdź ostrzeżenia L1** — czy masz plan na każde z nich?
3. **Oceń marżę p50** — czy to spełnia Twoje minimum rentowności?
4. **Zaznacz notatkę decyzyjną** (pole tekstowe) — zapisz uzasadnienie
5. Kliknij **GO** lub **NO-GO**

> ⚠️ **Pamiętaj:** Terra.OS dostarcza analizę — decyzja i odpowiedzialność są zawsze po Twojej stronie.

#### Co się dzieje po kliknięciu GO:

- Status przetargu zmienia się na `decided_go`
- System (Tier 3) może wygenerować plan logistyczny
- Możesz uruchomić RFQ do podwykonawców (Mózg)
- Decyzja jest zapisana w logu audytu

---

## Słownik pojęć

| Termin | Definicja |
|---|---|
| **Match Score** | Ocena 0–100% trafności przetargu dla Twojej firmy (CPV + lokalizacja + wartość + termin) |
| **Wariant A** | Kosztorys metodą dokumentacyjną (jak zamawiający, ceny rynkowe) |
| **Wariant B** | Kosztorys własny (Twoje stawki RMS, prywatny) |
| **Headroom marży** | (Wariant A − Wariant B) / Wariant A — ile przestrzeni na zysk lub błąd |
| **Feasible** | Przetarg jest technicznie i prawnie wykonalny (brak naruszeń L1 block) |
| **p10/p50/p90** | Kwantyle rozkładu marży: 10%, 50%, 90% percentyl wyników symulacji |
| **Win Probability** | Szacowane prawdopodobieństwo wygrania przy danej cenie oferty |
| **Drivers** | Czynniki mające największy wpływ na zmienność wyniku (analiza Sobola) |
| **RFQ** | Request for Quotation — zapytanie ofertowe do podwykonawcy |
| **Approval Gate** | Mechanizm zatwierdzania — żadne pismo nie wychodzi bez potwierdzenia człowieka |
| **CPV** | Common Procurement Vocabulary — europejski słownik zamówień publicznych |
| **BZP** | Biuletyn Zamówień Publicznych — polska platforma przetargów |
| **TED** | Tenders Electronic Daily — europejska platforma przetargów |

---

## Często zadawane pytania (FAQ)

**P: Dlaczego mój przetarg ma Match Score tylko 45%, choć wygląda dobrze?**  
O: Sprawdź, czy Twój profil firmy ma uzupełnione CPV i województwa. System nie może dopasować tego, o czym nie wie.

**P: Co oznacza „Feasible: NIE"?**  
O: Silnik L1 znalazł co najmniej jedno naruszenie kategorii `block`. Kliknij na naruszenie, żeby zobaczyć szczegóły i odniesienie do dokumentu. Przed złożeniem oferty musisz rozwiązać każdą blokadę.

**P: Dlaczego marża p10 jest ujemna?**  
O: W 10% pesymistycznych scenariuszy symulacja przewiduje stratę. To normalne przy zmiennych projektach. Kluczowe pytanie: czy p50 jest akceptowalne i czy firma przeżyje scenariusz p10?

**P: Mogę zmienić stawki w Wariancie B?**  
O: Tak, ale tylko przez zakładkę **Ustawienia → Karta stawek**. Zmiany stawek mają efekt na wszystkie przyszłe kosztorysy. Dla jednorazowej korekty użyj paska parametrów w Kosztorysancie.

**P: Czy moje stawki (rate card) są wysyłane do chmury?**  
O: Nie. Wariant B i Twoja karta stawek są obliczane wyłącznie lokalnie i nigdy nie opuszczają Twojego komputera. To gwarancja systemu.

**P: Jak sprawdzić, czy RFQ zostało wysłane?**  
O: Wejdź w **Przetarg → RFQ** i sprawdź status. Statusy: `draft` (niegotowe), `pending approval` (czeka na zatwierdzenie), `sent` (wysłane po zatwierdzeniu), `received` (otrzymano odpowiedź).

---

---

# 4. Changelog

*→ Pełna treść w osobnym pliku [CHANGELOG.md](CHANGELOG.md)*

Szablon wpisów zgodny z [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

### Sekcje każdego wpisu:
- `Added` — nowe funkcjonalności
- `Changed` — zmiany w istniejących funkcjonalnościach
- `Deprecated` — funkcje do usunięcia w przyszłości
- `Removed` — usunięte funkcje
- `Fixed` — naprawione błędy
- `Security` — poprawki bezpieczeństwa

### Konwencja wersjonowania:
- **MAJOR** (1.x.x) — zmiany łamiące kompatybilność API
- **MINOR** (x.1.x) — nowe funkcje, kompatybilne wstecz
- **PATCH** (x.x.1) — poprawki błędów

---

*Dokument wygenerowany przez: Technical Writer Agent (📚)*  
*Projekt: Terra.OS | Batch 3*
