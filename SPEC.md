# TERRA.OS — SPECYFIKACJA IMPLEMENTACJI
## ~100 faz | Funkcjonalność first, akademia later
## Data: 30.06.2026

---

## FILOZOFIA

**Każda faza musi dawać REALNĄ wartość firmie budowlanej.**
Nie implementujemy czegoś bo "jest state-of-the-art" — tylko dlatego że firma budowlana powie "to mi oszczędza czas/pieniądze".

### 5 pytań które platforma musi odpowiedzieć:
1. **"Czy startować?"** → AHP score + win probability (5 sek zamiast 2h dyskusji)
2. **"Ile to kosztuje?"** → KNR + ceny historyczne + AI prediction z przedziałem ufności
3. **"Jaki narzut dać?"** → Game Theory: optymalny markup vs N konkurentów
4. **"Jakie ryzyko?"** → NLP: auto-wyciąganie kar, terminów, wymagań z SWZ
5. **"Kto startuje?"** → Atlas Przetargów: historia konkurentów w danym CPV/regionie

---

## TECH STACK

```
FRONTEND:     Next.js 15 (App Router) + TypeScript
UI:           Tailwind v4 + shadcn/ui + Radix (dark theme)
STATE:        Zustand + TanStack Query v5
KANBAN:       @dnd-kit/core + @dnd-kit/sortable  
CHARTS:       Recharts
PDF:          react-pdf (viewer)
TABLE:        TanStack Table v8 (virtualized)
CMD:          cmdk (command palette)
MOTION:       motion/react

BACKEND:      FastAPI + Python 3.12 + Pydantic v2
DATABASE:     PostgreSQL 16 + pgvector
QUEUE:        Celery + Redis (background jobs)
CACHE:        Redis
AUTH:         JWT + bcrypt (custom, SSO later)

AI/LLM:       Claude Sonnet (main) + Haiku (fast tasks)
EMBEDDINGS:   text-embedding-3-small → pgvector
EXTRACTION:   Claude structured output (Pydantic schemas)

ANALYTICS:
  Bidding:    Friedman/Gates model (custom Python)
  Decision:   AHP/TOPSIS (custom + scipy)
  Prediction: NGBoost + SHAP (cost estimation)
  Calibration: MAPIE (conformal prediction intervals)
  Risk NLP:   Claude + spaCy (extraction z SWZ)

INFRA:
  Deploy:     Vercel (frontend) + VPS (API) — current setup
  CI/CD:      GitHub Actions
  Monitoring: Sentry + basic dashboards
  CDN:        Cloudflare
```

---

## BLOK A — FUNDAMENT (Fazy 1-25)
### Cel: solidna baza architektoniczna, auth, multi-tenant, design system

---

### Faza 1 — Auth System
- JWT tokens (access + refresh)
- Login/register endpoints: `POST /api/v2/auth/login`, `/register`, `/refresh`
- Password hashing: bcrypt
- User model: `{id, email, name, org_id, role, created_at}`
- Middleware: extract user from JWT, inject into request
- Roles: `owner | admin | estimator | viewer`

### Faza 2 — Organization (Multi-Tenant)
- Org model: `{id, name, nip, plan, settings_json, created_at}`
- Każda tabela ma `org_id` — filtrowanie na DB level
- API middleware: user → org_id → inject into all queries
- Invite system: owner zaprasza członków emailem
- Settings: default CPV codes, regiony, pipeline stages

### Faza 3 — Database Schema v2
- Migracje: Alembic
- Tabele core:
  ```sql
  organizations (id, name, nip, plan, settings, created_at)
  users (id, email, name, password_hash, org_id, role, created_at)
  tenders (id, org_id, bzp_number, title, buyer, cpv, region, value_estimated, value_contract, deadline, status, metadata_json, created_at, updated_at)
  tender_documents (id, tender_id, filename, file_path, doc_type, extracted_text, embedding vector(1536), created_at)
  cost_items (id, tender_id, org_id, description, unit, quantity, unit_price, total, source, confidence, created_at)
  bid_decisions (id, tender_id, org_id, decision, markup_pct, final_price, reasoning, decided_by, created_at)
  competitors (id, org_id, name, nip, cpv_codes[], regions[], win_count, avg_value, created_at)
  historical_bids (id, org_id, tender_id, our_price, winning_price, n_competitors, won, actual_cost, margin_pct, created_at)
  ```

### Faza 4 — API v2 Structure
- Router groups per domain:
  ```
  /api/v2/auth/...
  /api/v2/tenders/...
  /api/v2/estimates/...
  /api/v2/decisions/...
  /api/v2/competitors/...
  /api/v2/analytics/...
  /api/v2/documents/...
  /api/v2/ai/...
  ```
- Pagination: cursor-based `?cursor=X&limit=50`
- Response format: `{items: [], total: N, next_cursor: "..."}`
- Error format: `{error: "code", message: "human readable", details: {}}`

### Faza 5 — Background Jobs (Celery + Redis)
- Setup: Celery worker + Redis broker
- Job types:
  - `sync_bzp` — co 15 min
  - `process_document` — OCR + embedding + AI extract
  - `run_analysis` — cost estimation + risk
  - `notify` — email/in-app notifications
- Priority queues: `critical` (deadline <3d), `normal`, `batch`
- Status tracking: `job_status` table → polling z frontend

### Faza 6 — File Upload & Storage
- MinIO (S3-compatible, self-hosted) lub local filesystem na start
- Upload endpoint: `POST /api/v2/documents/upload` (multipart)
- Supported: PDF, DOCX, XLSX, ZIP
- Path: `/{org_id}/{tender_id}/{filename}`
- Background processing po upload:
  1. Unzip jeśli archiwum
  2. Extract text (pdf-parse, python-docx)
  3. OCR jeśli skan (Tesseract)
  4. Embedding → pgvector
  5. AI classification (SWZ, przedmiar, umowa, projekt)

### Faza 7 — Design System Foundation
- shadcn/ui setup z dark theme jako default
- Custom tokens CSS:
  ```css
  --background: 240 10% 3.9%;      /* zinc-950 */
  --foreground: 0 0% 98%;           /* zinc-50 */
  --card: 240 10% 5.9%;             /* zinc-900 */
  --primary: 142 76% 36%;           /* earth-green */
  --accent: 38 92% 50%;             /* earth-amber */
  --destructive: 0 84% 60%;         /* red */
  ```
- Komponenty base:
  - `GlassCard` — backdrop-blur, subtle border
  - `StatusBadge` — kolorowy pill per status
  - `MetricCard` — KPI z trendem
  - `DataTable` — TanStack Table wrapper
  - `CommandMenu` — cmdk wrapper

### Faza 8 — Navigation Shell
- Sidebar (collapsible):
  - Dashboard (Home)
  - Zwiad (BZP monitoring)
  - Pipeline (Kanban)
  - Kosztorysy
  - Analityka
  - Ustawienia
- Header: org name, user avatar, notifications bell
- Command palette: Cmd+K
- Keyboard shortcuts: G+D (dashboard), G+Z (zwiad), G+P (pipeline)

### Faza 9 — Dashboard v2
- KPIs: Pipeline Value | Win Rate | Active Bids | Avg Margin
- Trend sparklines (last 6 months)
- "Wymagają uwagi" — przetargi z deadline <3 dni
- "Ostatnia aktywność" — timeline
- Quick actions: "Nowy przetarg", "Importuj z BZP"

### Faza 10 — Tender List (Zwiad) v2
- TanStack Table: sortable columns, filters
- Columns: Status | Tytuł | Zamawiający | CPV | Region | Wartość | Deadline | Score
- Filters: status, CPV (tree), region (map), value range, deadline range
- Saved searches: "Moje filtry" per user
- Bulk actions: select multiple → change status, assign

### Faza 11 — Tender Detail v2
- Tabs: Przegląd | Dokumenty | Kosztorys | Ryzyko | Decyzja | Historia
- Przegląd: metadata + AI summary + key dates
- Activity timeline (kto co zrobił)
- Comments: @mentions, timestamps
- File attachments inline

### Faza 12 — Pipeline Kanban (dnd-kit)
- Stages (configurable):
  `MONITORING → ANALIZA → GO/NO-GO → KOSZTORYS → WERYFIKACJA → ZŁOŻENIE → WYNIK`
- Drag & drop between stages
- Card: title, value (PLN), deadline countdown, risk badge (🟢🟡🔴)
- Swimlanes toggle: by assignee | by CPV | by deadline urgency
- Quick filters: "Moje" | "Pilne" | "Wszystkie"

### Faza 13 — BZP Sync v2
- Scheduler: co 15 min poll e-Zamówienia API
- Incremental: only new/modified since last_sync
- Auto-match: CPV ∈ org.cpv_codes AND region ∈ org.regions
- Deduplication: by bzp_number
- Change detection: "Zmieniono termin!" → alert
- Endpoint: `POST /api/v2/bzp/sync` (manual trigger)

### Faza 14 — Notifications System
- In-app: bell icon, unread count, dropdown
- Types: deadline_approaching | new_match | status_change | mention | bzp_change
- Preferences per user: which types, email yes/no
- Model: `notifications(id, user_id, type, title, body, read, link, created_at)`
- SSE endpoint: `GET /api/v2/notifications/stream` (real-time)

### Faza 15 — Search (Full-Text + Semantic)
- PostgreSQL tsvector: Polish stemmer (`to_tsvector('polish', ...)`)
- pgvector: semantic search on embeddings
- Hybrid: FTS for exact terms, vector for "similar to..."
- Endpoint: `GET /api/v2/search?q=...&type=tenders|documents|costs`
- Autocomplete: top 5 suggestions as-you-type

### Faza 16 — Audit Log
- Every state change logged:
  ```sql
  audit_log(id, org_id, user_id, action, resource_type, resource_id, 
            old_value jsonb, new_value jsonb, ip, created_at)
  ```
- View: Historia tab na tender detail
- Filter: by user, by date, by action type
- Immutable: append-only, no deletes

### Faza 17 — Settings & Org Management
- Org profile: name, NIP, logo, default CPV, default regions
- Team management: invite, remove, change role
- Pipeline config: stage names, colors, order
- Notification preferences
- API keys (for future integrations)

### Faza 18 — Data Import: Historical Projects
- CSV/Excel upload wizard
- Fields: project_name, cpv, value, actual_cost, region, date, won (true/false), n_competitors, our_price, winning_price
- Validation + preview before import
- This data feeds: bidding optimizer, win probability, competitor analysis
- **CRITICAL:** bez tego danych historycznych silnik analityczny jest bezwartościowy

### Faza 19 — Error Handling & UX Polish
- Error boundaries per module
- Empty states: helpful CTA ("Dodaj pierwszy przetarg")
- Loading: skeleton screens (nie spinners)
- Toast notifications (sonner)
- Form validation: Zod + real-time feedback
- 404/500 branded pages

### Faza 20 — Testing & CI
- pytest + httpx (API tests)
- Playwright (E2E: login → create tender → view)
- GitHub Actions: lint → test → build → deploy
- Coverage: 70%+ backend
- Preview deploys per PR (Vercel)

### Faza 21 — Performance Baseline
- API: <200ms P95 response time
- Frontend: <3s first load, <1s navigation
- DB: proper indexes (org_id, status, deadline, cpv)
- Caching: Redis for hot queries (dashboard KPIs)
- Pagination: cursor-based, max 100 items

### Faza 22 — Mobile Responsive (Read-Only)
- Desktop: full experience
- Tablet: simplified layout
- Mobile: dashboard + pipeline view + notifications (read-only)
- PWA manifest: installable on phone

### Faza 23 — Onboarding Flow
- First login → wizard:
  1. Profil firmy (NIP, nazwa, branża)
  2. Obszar zainteresowań (CPV codes, regiony)
  3. Import danych historycznych (opcjonalny)
  4. Pierwszy przetarg (demo lub BZP)
- Skip option: "Skonfiguruj później"
- Target: <5 min do pierwszego "aha"

### Faza 24 — Document Viewer (PDF.js)
- In-browser PDF rendering
- Text selection → "Analizuj ten fragment"
- Search within document
- Side-by-side: PDF + AI extraction
- No download needed — oszczędza czas

### Faza 25 — API Documentation
- OpenAPI 3.1 auto-generated (FastAPI native)
- Swagger UI na `/docs`
- API key auth for external access
- Rate limiting: 100 req/min per org

---

## BLOK B — SILNIK ANALITYCZNY (Fazy 26-40)
### Cel: realna wartość decyzyjna, nie akademia

---

### Faza 26 — Atlas Przetargów Integration
- Import 1.4M rekordów BZP (Parquet, CC BY 4.0, FREE)
- Schema: `historical_tenders(bzp_number, cpv, value_estimated, value_contract, contractor_nip, buyer_nip, region, date, n_bidders)`
- DuckDB/PostgreSQL OLAP queries: agregacje per CPV × region × quarter
- Endpoint: `GET /api/v2/benchmark/{cpv}?region=PL91&period=2y`
- **Wartość:** "Ile kosztowały podobne projekty w Twoim regionie?"

### Faza 27 — Competitor Intelligence
- Z Atlas Przetargów: build per-competitor profiles
  ```json
  {
    "name": "Budimex SA",
    "nip": "...",
    "won_tenders": 847,
    "avg_value": 12300000,
    "regions": {"PL91": 0.34, "PL22": 0.22},
    "cpv_codes": ["45000000", "45200000"],
    "win_rate": 0.28,
    "avg_n_competitors": 5.2
  }
  ```
- Endpoint: `GET /api/v2/competitors/{nip}/profile`
- "Kto startuje w tych przetargach co Ty?" — matching by CPV + region
- **Wartość:** "W tym przetargu prawdopodobnie startuje 5 firm, w tym Budimex i Strabag"

### Faza 28 — Game Theory: Optimal Bidding (Friedman/Gates)
- Model Friedmana:
  ```python
  def optimal_markup(cost_estimate: float, n_competitors: int, historical_bids: list) -> dict:
      """
      Input: nasz koszt, ile konkurentów, historia bid/cost ratios
      Output: {optimal_markup: 0.113, win_probability: 0.22, expected_profit: 45000}
      """
      markups = np.linspace(0.01, 0.30, 100)
      for m in markups:
          p_win = estimate_win_probability(m, n_competitors, historical_bids)
          e_profit[m] = p_win * (m * cost_estimate)
      return markups[np.argmax(e_profit)]
  ```
- N competitors estimation z Atlas Przetargów data
- Endpoint: `POST /api/v2/analytics/optimal-markup`
- Input: `{cost_estimate, cpv, region, value_range}`
- Output: `{optimal_markup_pct, win_probability, expected_profit, chart_data}`
- **Wartość:** "Daj narzut 11.3% — masz 22% szans wygrać z zyskiem 45K"

### Faza 29 — AHP: Bid/No-Bid Decision Support
- Kryteria (wagi ustawiane per org w Settings):
  ```
  - Fit techniczny (0.25)
  - Marża oczekiwana (0.20)
  - Obciążenie zespołu (0.15)
  - Ryzyko kar (0.15)
  - Strategiczna wartość (0.10)
  - Cash flow impact (0.10)
  - Historia z zamawiającym (0.05)
  ```
- Per tender: user ocenia kryteria → AHP score 0-100
- Ranking: "Z 12 przetargów w pipeline, TOP 3 to: ..."
- Endpoint: `POST /api/v2/decisions/score`
- **Wartość:** "Nie marnuj czasu na ten przetarg — score 34/100. Skup się na tych dwóch (score 87, 79)"

### Faza 30 — NLP Risk Extraction z SWZ
- Claude structured output per dokument:
  ```python
  class SWZRiskExtraction(BaseModel):
      penalties: list[Penalty]        # kary umowne
      deadlines: list[Deadline]       # terminy (realizacja, gwarancja)
      requirements: list[Requirement] # warunki udziału
      payment_terms: PaymentTerms     # terminy płatności
      valorization: bool              # czy jest waloryzacja?
      insurance_min: float | None     # min polisa OC
      warranty_years: int | None      # lata gwarancji
      red_flags: list[str]            # klauzule niebezpieczne
  ```
- Red flags auto-detection:
  - "Kara >0.5%/dzień" 🔴
  - "Brak waloryzacji" 🔴
  - "Ryczałt bez wyjątków" 🔴
  - "Termin <6 miesięcy na budowę >5000m²" 🟡
- Sentence-level citations: "Kara 0.5%/dzień [SWZ str. 14, §12.3]"
- Endpoint: `POST /api/v2/ai/analyze-swz`
- **Wartość:** "W 30 sekund wiesz o karach, terminach i pułapkach — zamiast 3h czytania"

### Faza 31 — Cost Estimation: Hybrid
- Method 1: **Historyczny benchmark** — "podobne projekty kosztowały X PLN/m²" (z Atlas)
- Method 2: **AI parametric** — NGBoost prediction z features projektu
- Method 3: **KNR-based** — normatywy × ceny (manual, ale weryfikowalne)
- Fuzja: show all three, highlight discrepancies
- Endpoint: `POST /api/v2/estimates/predict`
- Input: `{cpv, region, area_m2, floors, material_class, description}`
- Output: `{benchmark_estimate, ai_estimate, confidence_interval_95, similar_projects[]}`
- **Wartość:** "AI mówi 2.3M±200K, benchmark podobnych to 2.1-2.5M. Twój kosztorys 1.9M — sprawdź pozycje instalacyjne"

### Faza 32 — Conformal Prediction: Calibrated Intervals
- MAPIE library — 1 linia kodu na DOWOLNY model
  ```python
  from mapie.regression import MapieRegressor
  mapie = MapieRegressor(estimator=ngboost_model, method="plus")
  mapie.fit(X_train, y_train)
  y_pred, y_intervals = mapie.predict(X_test, alpha=0.05)
  # y_intervals → GUARANTEED 95% coverage
  ```
- Nałożone na prediction z Fazy 31
- Frontend: pasek "koszt mieści się w [X, Y] z 95% pewnością"
- **Wartość:** Pewność zamiast zgadywania. Audytor może zweryfikować kalibrację.

### Faza 33 — SHAP: Explainable Cost Drivers
- Po predykcji → SHAP values:
  ```
  Predykcja: 2.3M PLN
  ├── +340K: duża powierzchnia (>5000 m²)
  ├── +180K: region Warszawa (higher costs)
  ├── +120K: wysoki standard wykończenia
  ├──  -90K: standardowy projekt (nie custom)
  └──  -50K: sezon zimowy (niższy popyt)
  ```
- Waterfall chart w UI
- Per-item SHAP (który element kosztorysu jest ryzykowny)
- **Wartość:** "DLACZEGO tyle" — kosztorysant rozumie i może się nie zgodzić z AI

### Faza 34 — Win Probability Model
- Logistic regression / XGBoost na historical_bids:
  - Features: markup_pct, n_competitors, cpv, region, value, buyer_history
  - Target: won (0/1)
- Output: P(win) per markup level → chart
- Calibration: Platt scaling
- Update: po każdym wyniku przetargu
- Endpoint: `GET /api/v2/analytics/win-probability?markup=12&cpv=45&competitors=5`
- **Wartość:** "Przy narzucie 12% i 5 konkurentach — szansa wygrania: 22%"

### Faza 35 — Cost Trends & Forecasting
- Dane: GUS BDL (kwartalnie), NBP, BZP historical values
- Time-series per CPV × region: jak zmieniają się ceny w czasie
- Simple forecast: linear trend + seasonality (Prophet/statsmodels)
- Charts: "Ceny robocizny w Mazowszu: +8% r/r, prognoza Q4: +3%"
- Waloryzacja calculator: "Jeśli inflacja 4%, waloryzacja = +X PLN"
- **Wartość:** "Nie wyceniaj po dzisiejszych cenach — za 12 miesięcy stal będzie 8% droższa"

### Faza 36 — Sensitivity Analysis
- Tornado diagram: "Które zmienne mają największy wpływ na wynik?"
  - TOP 3: cena robocizny (+/-15%), termin (+/-30 dni), materiały (+/-10%)
- Spider chart: jednoczesna zmiana wielu zmiennych
- Break-even: "Przy jakiej cenie stali tracimy pieniądze?"
- Scenarios: base / optimistic / pessimistic
- **Wartość:** "Wiesz CO monitorować w trakcie realizacji"

### Faza 37 — Bid Recommendation Engine
- Połączenie wszystkich warstw:
  ```json
  {
    "recommendation": "GO",
    "confidence": 0.78,
    "ahp_score": 82,
    "win_probability": 0.22,
    "optimal_markup": "11.3%",
    "expected_profit": 45000,
    "key_risks": ["Kara 0.5%/dzień", "Brak waloryzacji"],
    "key_opportunities": ["Mało konkurentów (3)", "Znamy zamawiającego"],
    "cost_estimate": {"min": 2100000, "expected": 2300000, "max": 2500000}
  }
  ```
- UI: 1-page summary z clear GO/NO-GO recommendation
- Override: manager może zmienić decyzję + podać powód
- **Wartość:** 1 ekran zamiast 3h spotkania o "czy startujemy"

### Faza 38 — Feedback Loop: Learn from Outcomes
- Po wyniku przetargu (wygrany/przegrany/wycofany):
  - Update win probability model
  - Update competitor profiles
  - Recalibrate cost model (jeśli znamy winning price)
- Po zakończeniu projektu:
  - Actual cost vs estimated → calibration metric
  - Display: "Nasze wyceny są średnio 7% za niskie w CPV 45.21"
- **Wartość:** System który się UCZY — im więcej danych, tym lepsze predykcje

### Faza 39 — Report Generator
- PDF export (WeasyPrint lub Puppeteer):
  - Executive Summary (1 strona): rekomendacja + KPI
  - Analiza ryzyka: extracted risks + severity
  - Kosztorys: per-item breakdown
  - Decision rationale: AHP scores + SHAP
- Excel export: kosztorys w formacie standard
- **Wartość:** Gotowy dokument na zarząd / do archiwum

### Faza 40 — Analytics Dashboard
- Charts:
  - Win rate over time (trend)
  - Kalibracja: estimate vs actual (scatter + regression line)
  - Pipeline value: how much in each stage
  - Competitor activity: kto jest aktywny w Twoim segmencie
  - Cost trends: per CPV per region
- **Wartość:** "Data-driven decisions" zamiast gut feeling

---

## BLOK C — INTEGRACJE & SKALA (Fazy 41-60)
### Cel: external data, export/import, team collaboration

---

### Faza 41 — BZP Full Document Fetch
- Auto-download SWZ ZIP po matched tender
- Extract → process → embed → analyze (background job)
- Status tracking: "Przetwarzanie dokumentów: 3/7 gotowe"

### Faza 42 — TED Integration (EU Tenders)
- eForms XML parsing
- Polish tenders above EU thresholds
- Cross-reference BZP ↔ TED

### Faza 43 — GUS BDL API
- Wskaźniki kosztów budowlanych (kwartalnie)
- Średnie wynagrodzenia per region
- Auto-update: cron job co tydzień

### Faza 44 — KRS/CEIDG Verification
- NIP → company info (nazwa, adres, status)
- Verify contractor data during import
- Auto-fill company profile on onboarding

### Faza 45 — Excel Import/Export
- Import: "Kosztorys ślepy" od zamawiającego
- Smart column mapping (AI suggests)
- Export: formatted Excel z formułami
- Template per org (branding)

### Faza 46 — Norma PRO Interop (ATH format)
- Import: ATH/ATH2XML → Terra.OS estimate
- Export: Terra.OS → ATH2XML (openable in Norma)
- KNR codes mapping

### Faza 47 — Kosztorys Editor (TanStack Table)
- Spreadsheet-like: KNR | Opis | Jedn. | Ilość | Cena jedn. | Suma
- Inline editing, instant recalculation
- AI assist: "Dodaj pozycję" → semantic search → suggest
- Hierarchical: rozdziały → grupy → pozycje
- Version history (kto co zmienił)

### Faza 48 — Team Collaboration
- Mentions: @user in comments
- Assignments: per tender × per task
- Activity feed: kto co robił
- Permissions: kto widzi kosztorys (manager vs viewer)

### Faza 49 — Email Notifications
- Resend integration
- Templates: deadline reminder, new match, decision needed
- Digest: daily summary o 7:00 (opcjonalny)
- Preferences: per type per channel

### Faza 50 — Webhook System
- Events: `tender.new`, `tender.deadline_3d`, `decision.made`, `estimate.done`
- Config: URL + secret per org
- Retry: 3x exponential backoff
- Use case: Slack notification, CRM sync

### Faza 51 — MCP Server
- 4 tools (jak vergabe-mcp):
  ```
  terra_search_tenders(cpv, region, value_range)
  terra_get_tender(tender_id)
  terra_get_estimate(tender_id)  
  terra_get_recommendation(tender_id)
  ```
- Usable from Claude Desktop, Hermes Agent
- Open source (GitHub — community + SEO)

### Faza 52 — Real-Time Updates (SSE)
- Server-Sent Events for:
  - Job progress (document processing, AI analysis)
  - New BZP matches
  - Team activity (someone moved a tender)
  - Notification count

### Faza 53 — AI Chat v2 (Context-Aware)
- Chat per tender: knows context (SWZ, kosztorys, decisions)
- Tool calling: "Ile kosztuje m² ściany?" → queries cost DB
- Streaming responses
- History per tender
- Citations: [SWZ str.14]

### Faza 54 — Competitor Network Graph
- D3.js visualization:
  - Nodes: companies
  - Edges: "competed in same tender"
  - Clusters: by region/CPV
- "Your market map" — kto z kim rywalizuje

### Faza 55 — Multi-Model AI Router
- Claude Sonnet: main analysis (SWZ, costs)
- Claude Haiku: classification, simple queries, translations
- Routing logic: task complexity → model selection
- Cost tracking per org: "Your AI usage: X calls this month"
- Savings: 60-70% vs Opus for everything

### Faza 56 — Prompt Library & Versioning
- Versioned prompts per task
- A/B testing (optional): track accuracy per prompt version
- Templates: inject org context, tender data
- Guardrails: Pydantic output validation

### Faza 57 — Data Quality Dashboard
- Completeness: "% fields filled per tender"
- Freshness: "Last BZP sync: 12 min ago"
- Model calibration: "Our P50 estimates hit actual 52% of time ✓"
- Anomaly flag: "Cost estimate 3σ above historical — verify"

### Faza 58 — Waloryzacja Calculator
- Detect waloryzacja clause in SWZ (NLP)
- Auto-calculate: GUS indices × contract value × time
- Forecast: "If inflation stays 4%, waloryzacja = +X PLN"
- Alert: "Brak klauzuli waloryzacyjnej!" 🔴

### Faza 59 — Portfolio View
- All active bids as portfolio:
  - Total exposed value
  - Expected profit (sum)
  - Resource allocation vs capacity
  - Geographic diversification
  - "If you win all → resource conflict in September"

### Faza 60 — Feature Flags & Gradual Rollout
- PostHog integration
- New features: 10% → 50% → 100%
- Kill switch: instant disable
- Per-org overrides (beta testers)

---

## BLOK D — BEZPIECZEŃSTWO & PRODUKCJA (Fazy 61-75)
### Cel: production-ready, security, compliance

---

### Faza 61 — RLS (Row Level Security) hardening
### Faza 62 — Input validation & sanitization everywhere
### Faza 63 — Rate limiting (per-org, per-endpoint)
### Faza 64 — HTTPS everywhere + security headers
### Faza 65 — Backup automation (PostgreSQL pg_dump + WAL)
### Faza 66 — Disaster Recovery plan + tested restore
### Faza 67 — Monitoring & alerting (Sentry + uptime)
### Faza 68 — Load testing (Locust — 100 concurrent users)
### Faza 69 — GDPR compliance (data export, deletion, consent)
### Faza 70 — Audit: penetration test basics (OWASP Top 10)
### Faza 71 — SSO/OIDC (Azure AD, Google Workspace)
### Faza 72 — SOC 2 preparation (policies, evidence)
### Faza 73 — API key management per-org (rotation, scopes)
### Faza 74 — Encryption at rest (sensitive fields)
### Faza 75 — Incident response playbook

---

## BLOK E — LAUNCH & GROWTH (Fazy 76-100)
### Cel: GTM, pricing, users, iteration

---

### Faza 76 — Pricing model (Free / Pro 499 PLN / Business 1499 PLN / Enterprise)
### Faza 77 — Stripe integration (subscriptions, invoices)
### Faza 78 — Landing page (dark, premium, social proof)
### Faza 79 — Demo environment (pre-loaded data, always-on)
### Faza 80 — Documentation & help center
### Faza 81 — Onboarding emails (drip sequence, 7 days)
### Faza 82 — Customer success: health scoring (usage → churn prediction)
### Faza 83 — Blog: "AI w przetargach budowlanych" (SEO)
### Faza 84 — Video tutorials (3 min per feature)
### Faza 85 — Referral system
### Faza 86 — Partnership: Athenasoft (Norma PRO / Intercenbud)
### Faza 87 — Partnership: construction associations (PZITB)
### Faza 88 — Mobile app (React Native / Expo — read-only + decisions)
### Faza 89 — Community: Discord for users + open-source MCP
### Faza 90 — Advanced: BIM integration (IFC import → auto-estimate)
### Faza 91 — Advanced: Digital Twin (project simulation)
### Faza 92 — Advanced: Market Intelligence Reports (weekly AI newsletter)
### Faza 93 — Advanced: Automated bid document generation
### Faza 94 — Expansion: Czech Republic (eForms integration)
### Faza 95 — Expansion: Ukraine (ProZorro API)
### Faza 96 — Advanced analytics: Bayesian Networks (when 200+ projects in system)
### Faza 97 — Advanced analytics: Vine Copulas (when 500+ data points)
### Faza 98 — Advanced analytics: RL bidding agent (when 100+ bid outcomes)
### Faza 99 — Enterprise: dedicated instances, custom SLA
### Faza 100 — Vision: "Construction Intelligence OS" — beyond tenders

---

## PRIORYTETY IMPLEMENTACJI

| Priorytet | Fazy | Co | Dlaczego |
|-----------|------|----|----------|
| 🔴 P0 | 1-13 | Auth + DB + UI shell + Pipeline + BZP | Bez tego nie ma produktu |
| 🟠 P1 | 14-25 | Notifications + Search + Import + Polish | Usable product |
| 🟡 P2 | 26-40 | **SILNIK** — Game Theory + NLP + Predictions | **Differentiator** |
| 🟢 P3 | 41-60 | Integracje + Collaboration + MCP | Growth features |
| 🔵 P4 | 61-75 | Security hardening | Pre-launch |
| ⚪ P5 | 76-100 | Launch + Growth + Advanced | Post-launch |

---

## METRYKI SUKCESU

| Metryka | Target (6 months) | Jak mierzymy |
|---------|-------------------|--------------|
| Time to Bid/No-Bid decision | <10 min (vs 2-3h currently) | Time from tender open to decision |
| Cost estimate accuracy | ±15% vs actual | Post-project comparison |
| Win rate improvement | +5pp vs historical | Won/Total bids ratio |
| User activation | 70% complete onboarding | Funnel tracking |
| Weekly active users | >60% of registered | PostHog |
| NPS | >40 | Quarterly survey |

---

## ANTI-PATTERNS (NIE RÓB TEGO)

1. ❌ **Nie buduj Bayesian Networks bez danych** — potrzebujesz 200+ projektów
2. ❌ **Nie implementuj Vine Copulas przed NGBoost** — copulas to polish, NGBoost to core
3. ❌ **Nie buduj RL agenta z <100 wynikami** — będzie losowy
4. ❌ **Nie rób microservices** — modular monolith wystarczy na 1000 users
5. ❌ **Nie rób offline-first** — core use case jest biurowy
6. ❌ **Nie buduj custom CRDT** — Liveblocks zrób to w 1 dzień (later)
7. ❌ **Nie optymalizuj przed 100 users** — premature optimization
8. ❌ **Nie rób Monte Carlo jako "główną metodę"** — to baseline, nie feature

---

## UWAGI KOŃCOWE

Ten plan to **100 faz od zera do production SaaS**.
140-fazowy plan (PLAN_140.md) zachowany jako referencia — zawiera deep-dive na każdą fazę z Bloku A i B.

Implementacja w kolejności faz. Każda faza = zamknięta funkcjonalność, deployable.
Nie przeskakuj — Faza N+1 może zależeć od N.

**Start: Faza 1 (Auth System)**
