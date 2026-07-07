# TERRA.OS — 140-FAZOWY PLAN BUDOWY PLATFORMY STATE-OF-THE-ART
## Wersja: 1.0 | Data: 30.06.2026

---

## METODOLOGIA ANALITYCZNA (zamiast naiwnego Monte Carlo)

### Silnik Ryzyka — Architektura Wielowarstwowa:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    TERRA.OS RISK & DECISION ENGINE                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  WARSTWA 1 — EXTRACTION (NLP/LLM)                                           │
│  ContextGem + Claude → structured risk factors z SWZ                        │
│  Output: {penalties, deadlines, scope_gaps, requirements, payment_terms}     │
│                                                                              │
│  WARSTWA 2 — PROBABILISTIC MODELING                                          │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐         │
│  │ Bayesian Network │  │ Copula Functions │  │ Gaussian Process   │         │
│  │ (pgmpy)         │  │ (vine copulas)   │  │ Regression (GPy)   │         │
│  │                 │  │                  │  │                    │         │
│  │ Modeluje:       │  │ Modeluje:        │  │ Modeluje:          │         │
│  │ - zależności    │  │ - korelacje      │  │ - predykcja z      │         │
│  │   między        │  │   kosztów        │  │   uncertainty      │         │
│  │   ryzykami      │  │   (materiały ↔   │  │   bands            │         │
│  │ - conditional   │  │   robocizna ↔    │  │ - learning from    │         │
│  │   probabilities │  │   sprzęt)        │  │   historical bids  │         │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘         │
│                                                                              │
│  WARSTWA 3 — DECISION SCIENCE                                                │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐         │
│  │ Game Theory     │  │ CVaR / Tail Risk │  │ AHP/TOPSIS         │         │
│  │ (Auction Models)│  │ (Portfolio Opt.) │  │ (Multi-Criteria)   │         │
│  │                 │  │                  │  │                    │         │
│  │ - Friedman/     │  │ - P(loss) nie    │  │ - Go/No-Bid        │         │
│  │   Gates/Carr    │  │   wystarczy      │  │   scoring           │         │
│  │ - Optimal       │  │ - "Ile tracę w   │  │ - 15+ kryteriów    │         │
│  │   markup calc   │  │   najgorszym 5%?"│  │ - Ważone priorytety│         │
│  │ - N competitors │  │ - Robust optim.  │  │   firmy            │         │
│  │   estimation    │  │                  │  │                    │         │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘         │
│                                                                              │
│  WARSTWA 4 — REINFORCEMENT LEARNING (long-term)                              │
│  - Multi-armed bandit: explore/exploit pricing strategies                    │
│  - Thompson Sampling: update beliefs after each bid result                   │
│  - Policy gradient: optimize win_rate × margin across portfolio              │
│                                                                              │
│  WARSTWA 5 — EXPLAINABILITY                                                  │
│  - SHAP values per cost driver                                               │
│  - Sentence-level SWZ citations per risk flag                                │
│  - Confidence intervals z Conformal Prediction (guaranteed coverage)          │
│  - "Dlaczego ta cena?" — full audit trail                                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Kluczowe przewagi nad naiwnym Monte Carlo:

| Aspekt | Monte Carlo (naiwny) | Terra.OS State-of-the-Art |
|--------|---------------------|---------------------------|
| Korelacje kosztów | Ignoruje (zakłada niezależność) | Vine Copulas modelują prawdziwe zależności |
| Zależności ryzyk | Flat lista ryzyk | Bayesian Network — ryzyko A → ryzyko B |
| Predykcja kosztu | Losowanie z PERT | Gaussian Process z historii wygranych |
| Tail risk | P10/P90 (arbitrary) | CVaR — "expected loss in worst 5%" |
| Strategia cenowa | Narzut × koszt | Game Theory — optimum vs N competitors |
| Go/No-Bid | Single score | AHP/TOPSIS — multi-criteria z wagami |
| Uczenie się | Brak | RL — Thompson Sampling z wyników przetargów |
| Niepewność | Assumed distributions | Conformal Prediction — gwarantowane pokrycie |
| Wyjaśnialność | Histogram | SHAP + sentence-level evidence |

---

## 140 FAZ — PLAN WYKONAWCZY

---

### BLOK A — FUNDAMENT (Fazy 1-20)
**Cel: Architektura, DDD, event-driven core, auth, multi-tenant**

#### Faza 1 — Domain-Driven Design: Bounded Contexts
- Zdefiniuj 6 domen: `Tender Discovery`, `Document Analysis`, `Cost Estimation`, `Risk Engine`, `Decision Support`, `Bid Management`
- Event Storming → domain events, commands, aggregates
- Ubiquitous language PL (słownik biznesowy)
- Output: `/docs/ddd/` — context map, event catalog

#### Faza 2 — Event Sourcing Core
- PostgreSQL + event store (tabela `domain_events`)
- Event replay capability — odtwarzanie stanu przetargu z historii
- Snapshot mechanism (performance)
- Schema: `{event_type, aggregate_id, payload, metadata, timestamp, version}`

#### Faza 3 — CQRS: Command/Query Separation
- Write model: FastAPI commands → event store → projections
- Read model: materialized views / DuckDB dla analytics
- Eventual consistency z event handlers
- Separate read/write DB connections

#### Faza 4 — Multi-Tenant Architecture
- Organization model: `{org_id, name, nip, plan, settings}`
- Row-Level Security (RLS) na PostgreSQL
- `org_id` w każdej tabeli, enforced na DB level
- API middleware: extract org from JWT → inject into queries

#### Faza 5 — Auth & RBAC
- Supabase Auth (JWT) lub custom: email + magic link + SSO (OIDC)
- Roles: `owner`, `manager`, `estimator`, `viewer`
- Permissions per module (kto widzi kosztorys, kto decyduje go/no-bid)
- Audit log: każda zmiana → event z user_id, timestamp

#### Faza 6 — Database Schema v2
- PostgreSQL 16 + pgvector (embeddings SWZ)
- TimescaleDB hypertable: `cost_observations(time, item_id, price, source)`
- DuckDB sidecar: OLAP analytics na historycznych przetargach
- Migrations: Alembic z CI/CD gate

#### Faza 7 — API Gateway & Rate Limiting
- FastAPI router groups per bounded context
- Rate limiting per org/user (Redis token bucket)
- API versioning (`/api/v2/...`)
- OpenAPI 3.1 auto-generated docs
- Webhook registry (notify on tender changes)

#### Faza 8 — Background Job System
- Celery + Redis (lub Dramatiq) dla heavy jobs
- Job types: `bzp_sync`, `document_parse`, `cost_estimate`, `risk_analysis`
- Priority queues: `critical` (deadline <3d), `normal`, `batch`
- Dead letter queue + retry with exponential backoff
- Job status tracking → real-time frontend updates via SSE

#### Faza 9 — File Processing Pipeline
- S3-compatible storage (MinIO local / Supabase Storage / R2)
- Upload: ZIP/RAR/7z up to 2GB → unpack → classify files
- Pipeline: `upload → unpack → OCR → classify → parse → embed → store`
- Virus scanning (ClamAV) before processing
- Temporary presigned URLs for frontend preview

#### Faza 10 — Real-Time Infrastructure
- Server-Sent Events (SSE) for job progress & notifications
- WebSocket for collaborative editing (kosztorys cells)
- Presence system: who's viewing which tender
- Notification center: in-app + email + webhook

#### Faza 11 — Design System Foundation
- Tailwind v4 + CSS custom properties (design tokens)
- Dark-first palette: zinc-900 base, earth-* accents
- Component library: `glass-card`, `metric-badge`, `status-pill`
- Typography: Inter (UI) + JetBrains Mono (data/numbers)
- Motion: `motion/react` — subtle, functional, never decorative
- Responsive: desktop-first, tablet usable, mobile read-only

#### Faza 12 — Navigation & Layout Shell
- Sidebar: collapsible, keyboard shortcuts (G+D=Dashboard, G+Z=Zwiad...)
- Command Palette (cmdk): Cmd+K → search tenders, actions, navigation
- Breadcrumbs: Org → Module → Tender → Section
- Tab system: multiple tenders open simultaneously
- Personal vs Team views (toggle)

#### Faza 13 — Data Fetching Layer
- TanStack Query v5: caching, prefetching, optimistic updates
- Typed API client (generated from OpenAPI schema)
- Infinite scroll + cursor-based pagination
- Stale-while-revalidate pattern
- Error boundaries per module (nie crashuje całej app)

#### Faza 14 — Kanban Foundation (dnd-kit)
- Pipeline stages (configurable per org):
  `MONITORING → ANALIZA → GO/NO-GO → KOSZTORYS → WERYFIKACJA → ZŁOŻENIE → WYNIK → ARCHIWUM`
- Drag & drop between stages (optimistic update + API PATCH)
- Card compact view: title, value, deadline countdown, risk badge
- Swimlanes: by assignee, by CPV, by region, by deadline urgency
- Keyboard: arrow keys to navigate, Enter to open, Space to move

#### Faza 15 — Tender Card Detail View
- Split view: left = metadata/actions, right = SWZ preview
- Tabs: Przegląd | Dokumenty | Kosztorys | Ryzyko | Decyzja | Historia
- Activity timeline (event sourcing → rendered as timeline)
- Comments & mentions (@user)
- File attachments per section

#### Faza 16 — BZP Sync Engine v2
- Scheduler: every 15 min poll e-Zamówienia API
- Incremental sync (only new/modified since last_sync)
- Deduplication: match by bzp_number
- Auto-classify: CPV → category, region → NUTS, value → tier
- Change detection: "Zmieniono termin składania ofert!" → alert

#### Faza 17 — Document Ingestion Pipeline
- Supported: PDF, DOCX, XLSX, ZIP/RAR/7z, scanned images
- OCR: Tesseract 5 + PaddleOCR (for tables)
- Table extraction: Camelot / Tabula for PDF tables
- Embedding: text-embedding-3-small → pgvector
- Classification: AI labels each doc (SWZ, przedmiar, projekt, umowa...)

#### Faza 18 — SWZ Parser (ContextGem Pattern)
- Declarative extraction:
  ```python
  aspects = ["Przedmiot zamówienia", "Warunki udziału", "Kryteria oceny",
             "Terminy", "Kary umowne", "Warunki płatności", "Gwarancja"]
  concepts = ["wadium_amount", "deadline", "contract_duration",
              "penalty_rate", "required_experience", "insurance_min"]
  ```
- Sentence-level source mapping (każdy fakt → cytat z SWZ)
- Confidence score per extracted field
- Human-in-the-loop: AI proposes, user confirms/corrects → learns

#### Faza 19 — Testing Infrastructure
- pytest + httpx (API integration tests)
- Playwright (E2E frontend tests)
- Factory Boy (test data generation)
- Coverage: 80%+ backend, 60%+ frontend
- CI: GitHub Actions → test → build → deploy
- Load testing: Locust (concurrent tender processing)

#### Faza 20 — CI/CD & Deployment
- GitHub Actions: lint → test → build → deploy
- Preview deployments per PR (Vercel)
- Database migrations: automated with Alembic
- Feature flags: Statsig (free tier) or PostHog
- Rollback: one-click revert to previous version
- Health checks: /healthz, /readyz

---

### BLOK B — SILNIK ANALITYCZNY (Fazy 21-50)
**Cel: State-of-the-art risk engine, Bayesian inference, Game Theory, Decision Science**

#### Faza 21 — Cost Database Integration: DDC CWICR
- Import PL_WARSAW track (55K pozycji, Parquet)
- Schema: `cost_items(id, description_pl, unit, labor_hours, material_qty, equipment_hours, unit_price_pln, category, source)`
- pgvector embeddings dla semantic search
- FastAPI endpoint: `POST /api/v2/costs/search` (semantic + filters)
- Uwaga: ceny DDC to przeliczenia OECD — flaguj jako "orientacyjne"

#### Faza 22 — Cost Database: Atlas Przetargów Integration
- Import 1.4M rekordów BZP (Parquet, CC BY 4.0)
- Schema: `historical_tenders(bzp_number, cpv, value_estimated, value_contract, contractor_nip, buyer_nip, region, date)`
- DuckDB analytics layer: agregacje per CPV × region × quarter
- Benchmark endpoint: `GET /api/v2/benchmark/{cpv}?region=PL91&period=2y`

#### Faza 23 — Bayesian Network: Risk Dependencies
- Library: `pgmpy` (Python)
- Model zależności ryzyk:
  ```
  Opóźnienie_materiałów → Kara_umowna
  Brak_kwalifikacji → Odrzucenie_oferty
  Niska_cena → Problemy_cashflow → Opóźnienie
  Podwykonawca_zawodny → Opóźnienie → Kara
  ```
- Structure learning z historycznych przetargów (dane Atlas)
- Parameter learning: conditional probability tables z danych
- Inference: `P(Strata | SWZ_features)` — prawdopodobieństwo warunkowe

#### Faza 24 — Copula Functions: Cost Correlations
- Library: `copulas` (SDV) lub `pyvinecopulib`
- Model korelacji:
  ```
  cena_materiałów ↔ cena_robocizny (korelacja 0.6-0.8)
  cena_stali ↔ cena_betonu (korelacja 0.3-0.5)
  pogoda_zima ↔ opóźnienie (tail dependence)
  ```
- Vine Copulas: wielowymiarowe zależności (D-vine, C-vine, R-vine)
- Calibration z danych historycznych (GUS ceny + Atlas umowy)
- Output: realistyczne wielowymiarowe rozkłady kosztów (nie naiwne niezależne!)

#### Faza 25 — Gaussian Process Regression: Cost Prediction
- Library: `GPyTorch` lub `scikit-learn GaussianProcessRegressor`
- Features: `[cpv, region, area_m2, floors, material_class, contractor_size, quarter]`
- Target: `unit_cost_pln_per_m2`
- Output: **mean prediction ± credible interval** (nie point estimate!)
- Acquisition function: gdzie zebrać więcej danych (active learning)
- Update: po każdym wyniku przetargu → posterior update

#### Faza 26 — Conformal Prediction: Guaranteed Intervals
- Library: `MAPIE` (Python) lub `crepes`
- Guarantees: "95% confident cost is within [X, Y] PLN"
- vs Monte Carlo P5/P95: Conformal daje **gwarantowane** pokrycie bez założeń o rozkładzie
- Adaptive: conformal intervals shrink as model improves
- Per-item intervals: każda pozycja kosztorysu z osobnym CI

#### Faza 27 — Game Theory: Optimal Bidding (Friedman-Gates-Carr)
- Competitive bidding model:
  ```python
  # Friedman (1956): maximize E[profit] = P(win) × markup
  # P(win | markup, N_competitors) = estimated from historical data
  
  def optimal_markup(cost_estimate, n_competitors, historical_bids):
      """Find markup that maximizes E[profit]"""
      markups = np.linspace(0.01, 0.30, 100)  # 1% to 30%
      for m in markups:
          p_win = estimate_win_probability(m, n_competitors, historical_bids)
          e_profit = p_win * (m * cost_estimate)
      return markups[np.argmax(e_profits)]
  ```
- Gates model: per-competitor win probability
- Carr model: weighted by contract size
- N_competitors estimation z Atlas Przetargów (ile firm bierze udział w CPV=X?)

#### Faza 28 — CVaR: Tail Risk Quantification
- Conditional Value at Risk (Expected Shortfall)
- "Monte Carlo mówi: P(strata) = 15%. CVaR mówi: jeśli strata nastąpi, ŚREDNIA strata = 180K PLN"
- Portfolio perspective: "Co jeśli 3 z 10 przetargów jednocześnie generują straty?"
- Robust optimization: znajdź cenę minimalizującą CVaR (nie maximizing expected profit)
- Implementation: `scipy.optimize` + custom objective

#### Faza 29 — AHP/TOPSIS: Multi-Criteria Bid Decision
- Analytic Hierarchy Process dla Go/No-Bid:
  ```
  Criteria (wagi ustawiane per org):
  - Fit techniczny (0.25)
  - Marża oczekiwana (0.20)
  - Obciążenie zespołu (0.15)
  - Ryzyko kar (0.15)
  - Strategiczna wartość (0.10)
  - Cash flow impact (0.10)
  - Historia z zamawiającym (0.05)
  ```
- TOPSIS ranking: "Z 15 przetargów, te 3 są optymalne dla Twojej firmy"
- Sensitivity analysis: "Gdyby marża była ważniejsza, ranking zmienia się na..."
- Visual: radar chart per tender, comparison view

#### Faza 30 — Probabilistic Programming: Full Bayesian Model
- PyMC 5 lub NumPyro (JAX-backend, 10x szybszy)
- Hierarchical model:
  ```python
  with numpyro.plate("items", n_items):
      # Prior: informed by DDC CWICR + historical
      cost_mu = numpyro.sample("cost_mu", dist.Normal(prior_mean, prior_std))
      cost_sigma = numpyro.sample("cost_sigma", dist.HalfNormal(scale))
      # Likelihood: observed costs from completed projects
      numpyro.sample("obs", dist.Normal(cost_mu, cost_sigma), obs=observed)
  # Posterior: updated belief about true cost
  posterior = numpyro.infer.MCMC(numpyro.infer.NUTS(model), ...)
  ```
- Posterior predictive: "Given everything we know, P(cost > budget) = X%"
- Sequential update: after each project, beliefs sharpen

#### Faza 31 — Reinforcement Learning: Bidding Strategy
- Multi-Armed Bandit: explore markup strategies
- Thompson Sampling: "Try markup 12% — if we win, update belief upward"
- Contextual bandit: features = [cpv, n_competitors, buyer_history, urgency]
- Reward: `win × (revenue - cost) - lose × (sunk_bid_cost)`
- Long-term: policy gradient — optimize portfolio-level margin over time
- Cold start: initialize from Game Theory optimal (Faza 27)

#### Faza 32 — Explainability Layer (SHAP + Evidence)
- SHAP values: "Dlaczego predykcja wynosi 2.3M PLN?"
  - `+340K: duża powierzchnia (>5000 m²)`
  - `+180K: region Warszawa (higher costs)`
  - `-90K: standardowy projekt (nie custom)`
- Sentence-level evidence: "Kara 0.5%/dzień [SWZ str. 14, §12.3]"
- Confidence badges: 🟢 high | 🟡 medium | 🔴 low (per field)
- Audit trail: every AI decision logged with reasoning

#### Faza 33 — Risk Factor Taxonomy
- ISO 31010 compliant risk categories:
  ```
  TECHNICAL: scope_creep, design_gaps, ground_conditions, materials_availability
  COMMERCIAL: price_volatility, subcontractor_risk, payment_terms, penalties
  LEGAL: contract_ambiguity, compliance_requirements, dispute_clauses
  SCHEDULE: weather_sensitivity, permit_delays, resource_constraints
  STRATEGIC: market_fit, portfolio_balance, relationship_value, learning_value
  ```
- Each risk: P(occurrence) × Impact × Detectability (FMEA-inspired)
- Mitigants: per risk → suggested actions + residual risk

#### Faza 34 — Sensitivity Analysis Engine
- Tornado diagram: "Które zmienne mają największy wpływ na marżę?"
- Spider/radar plots: "Jak zmiana ±10% w cenie stali wpływa na wynik?"
- Scenario manager:
  - Base case (most likely)
  - Optimistic (P90 favorable)
  - Pessimistic (P10 unfavorable)
  - Stress test (tail scenario — everything goes wrong)
- Break-even analysis: "At what steel price do we lose money?"

#### Faza 35 — Cost Estimation: Hybrid AI + Norms
- Method 1: KNR-based (normatywy × ceny RMS) — traditional, verifiable
- Method 2: AI parametric (GP regression from historical) — fast, uncertain
- Method 3: Semantic match (DDC CWICR Qdrant) — similar work items
- Fusion: weighted ensemble based on data availability
  - Lots of historical data → GP regression dominates
  - New/unique project → KNR norms + expert adjustment
  - Quick estimate → semantic match (60 seconds)
- Each method reports confidence; user sees all three + recommended

#### Faza 36 — Competitor Intelligence Engine
- Data source: Atlas Przetargów + BZP API
- Per-competitor profile:
  ```
  Firma: Budimex SA
  Przetargi wygrane (CPV 45): 847
  Średnia wartość: 12.3M PLN
  Regiony: Mazowieckie (34%), Śląskie (22%), Dolnośląskie (18%)
  Win rate: 28% (gdy startuje, wygrywa co 3.5 raz)
  Avg. # competitors when they bid: 5.2
  Typical markup (inferred): 8-14%
  ```
- Alert: "Budimex pobrał SWZ tego przetargu" (jeśli dostępna info)
- Clustering: "Firmy podobne do Twojej — jak bidują?"

#### Faza 37 — Portfolio Optimization
- Treat all active bids as a portfolio
- Markowitz-inspired: maximize E[profit] subject to risk budget
- Constraints: max capacity (team/equipment), min margin, max CVaR
- Linear programming: "Które przetargi startować, żeby zmaksymalizować profit przy ograniczonych zasobach?"
- Rebalancing: "Wygraliśmy tender X — czy nadal opłaca się startować w Y?"

#### Faza 38 — Time-Series: Cost Trends & Forecasting
- TimescaleDB: `(time, item_category, region, avg_price, source)`
- Data: GUS BDL (wskaźniki), BZP (wartości umów), DDC (ceny items)
- Prophet/NeuralProphet: forecast material prices (steel, concrete, labor)
- Seasonality: "Robocizna droższa w Q2-Q3 (sezon budowlany)"
- Waloryzacja: auto-calculate future costs based on trend + inflation

#### Faza 39 — NLP Risk Extraction Pipeline
- Pipeline per SWZ document:
  1. Split into sections (regex + LLM)
  2. Per section → extract risk factors (ContextGem concepts)
  3. Classify severity: `critical | high | medium | low`
  4. Map to ISO 31010 taxonomy (Faza 33)
  5. Generate risk register (structured JSON)
  6. Compare vs. company risk appetite → flags
- Red flags auto-detection: "Kara >0.5%/dzień", "Brak waloryzacji", "Ryczałt bez wyjątków"

#### Faza 40 — Bid/No-Bid Recommendation Engine
- Input: all layers (NLP extraction + BN risk + GP cost + Game Theory + AHP)
- Output:
  ```json
  {
    "recommendation": "GO",
    "confidence": 0.78,
    "expected_margin": "8.4%",
    "win_probability": "22%",
    "optimal_markup": "11.3%",
    "CVaR_5%": "-180K PLN",
    "key_risks": [...],
    "key_opportunities": [...],
    "SHAP_explanation": {...},
    "comparison_vs_portfolio": "fits well — diversifies region exposure"
  }
  ```
- Human-in-the-loop: AI recommends, manager decides, system learns from outcome

#### Faza 41 — Model Training Pipeline
- MLflow: experiment tracking, model registry, versioning
- Training data: historical bids (won/lost) + costs (actual vs estimated)
- Retraining: monthly or when new batch of outcomes arrives
- A/B testing: champion model vs challenger
- Drift detection: alert if model performance degrades

#### Faza 42 — Feedback Loop: Learn from Outcomes
- After bid result (win/loss/withdrew):
  - Update GP posterior
  - Update BN parameters
  - Update competitor profiles
  - RL reward signal
- After project completion:
  - Actual cost vs estimated → calibration
  - Risk events that materialized → BN structure learning
  - "Were our confidence intervals well-calibrated?" → conformal recalibration

#### Faza 43 — Digital Twin: Project Cost Simulation
- Simulate full project lifecycle:
  - Phase 1: Mobilization
  - Phase 2: Foundation/earthworks
  - Phase 3: Structure
  - Phase 4: Installation
  - Phase 5: Finishing
  - Phase 6: Handover
- Per phase: schedule × cost × risk interactions (BN)
- Cash flow projection with uncertainty bands
- "What-if": what if material delivery delayed 2 weeks?

#### Faza 44 — Waloryzacja Engine
- Polish public procurement: mandatory valorization clause since 2022
- Auto-detect waloryzacja clauses in SWZ
- Calculate: GUS indices × contract value × time
- Forecast: "If inflation stays at X%, valorization = +Y PLN"
- Alert: "Waloryzacja clause MISSING — risk of uncompensated cost increases!"

#### Faza 45 — KNR Integration (Polish Norms)
- Import KNR structure (catalogs 2-xx through 9-xx)
- Map: KNR position → DDC CWICR item (semantic matching)
- Calculator: user selects KNR position → auto-fills quantities → prices from Intercenbud/DDC
- Export: ATH2XML format (compatible with Norma PRO)
- Verification: "This estimate uses KNR 2-02/0101 — is this the right norm for reinforced concrete walls?"

#### Faza 46 — Estimate Builder UI
- Spreadsheet-like interface (TanStack Table, virtualized)
- Columns: KNR | Description | Unit | Qty | Unit Price | Total | Confidence
- Inline editing with instant recalculation
- AI assist: "Add item" → semantic search → suggest matching KNR/DDC items
- Version history (event sourcing)
- Collaborative: multiple estimators editing simultaneously (CRDT)

#### Faza 47 — Report Generator
- PDF reports:
  - Executive Summary (1 page): recommendation + key metrics
  - Detailed Cost Estimate (N pages): per-item breakdown
  - Risk Register: categorized risks + mitigants
  - Decision Rationale: AHP scores + SHAP explanations
- Excel export: kosztorys ślepy, kosztorys szczegółowy
- ATH export: compatible with Norma PRO / BIMestiMate
- Branded templates per organization

#### Faza 48 — API: External Integrations
- REST API + OpenAPI 3.1
- Webhook system: `tender.new`, `tender.deadline_approaching`, `decision.made`
- MCP Server (for Claude/AI assistants)
- Zapier/n8n integration endpoints
- Import from: Norma (ATH), ZUZIA (XML), Excel (custom template)
- Export to: Norma, Excel, PDF, JSON

#### Faza 49 — Performance Optimization
- Database: indexes, materialized views, connection pooling (pgBouncer)
- Caching: Redis L1 (hot data), CDN L2 (static)
- API: response compression, pagination, field selection
- Frontend: code splitting, lazy loading, service worker
- Background: prioritize jobs by deadline urgency
- Target: <200ms P95 API response, <3s page load

#### Faza 50 — Analytics & Observability
- PostHog: product analytics (which features used, funnel drops)
- Sentry: error tracking with context
- Axiom/Grafana: infrastructure metrics
- Custom dashboards:
  - Model accuracy over time
  - Win rate by period
  - Cost calibration (predicted vs actual)
  - Usage per organization

---

### BLOK C — FRONTEND PREMIUM (Fazy 51-80)
**Cel: Linear-quality UI, dark theme, keyboard-first, real-time collaboration**

#### Faza 51 — Dashboard: North Star KPIs
- Top-level metrics: Pipeline Value | Win Rate | Active Bids | Avg Margin
- Trend sparklines (last 12 months)
- AI Summary: "Masz 3 przetargi z deadline w tym tygodniu. Priorytet: Przetarg X (deadline pojutrze, kosztorys niegotowy)"
- Quick actions: "Nowy przetarg", "Moje zadania", "Wyniki"

#### Faza 52 — Zwiad (Discovery) v2
- Real-time BZP feed with AI scoring
- Fit Score 0-100 per tender (vs company profile)
- Smart filters: CPV tree, region map, value range, deadline
- Saved searches with notifications
- "Podobne do wygranych" — ML recommendation

#### Faza 53 — Pipeline Kanban v2
- dnd-kit: smooth drag & drop
- Stage configuration per org
- Card preview on hover
- Bulk actions: select multiple → move, assign, archive
- Deadline urgency colors: green (>7d), yellow (3-7d), red (<3d)
- Capacity indicator per stage: "KOSZTORYS: 5/8 (62% load)"

#### Faza 54 — Tender Detail: Split View
- Left panel: metadata, actions, timeline
- Right panel: document viewer (PDF.js) or AI analysis
- Resizable panels (react-resizable-panels)
- Tabs: Przegląd | SWZ | Kosztorys | Ryzyko | Decyzja | Historia | Chat

#### Faza 55 — Document Viewer (PDF.js)
- In-browser PDF rendering (no download needed)
- Text selection → "Analyze this section"
- AI highlights: risk factors marked in document
- Side-by-side: original SWZ + extracted data
- Search within document
- Annotations: comments pinned to specific paragraphs

#### Faza 56 — Kosztorys Editor
- TanStack Table: virtualized, 10K+ rows smooth
- Hierarchical: chapters → sections → items
- Inline formulas: `=qty * unit_price * (1 + overhead%)`
- AI fill: select empty row → "Suggest price" → GP prediction with CI
- Comparison: "vs DDC CWICR" | "vs historical avg" | "vs last similar project"
- Lock/unlock cells (permissions)

#### Faza 57 — Risk Dashboard
- Bayesian Network visualization (D3.js force graph)
- Risk matrix: probability × impact (interactive, drag risks)
- Tornado chart: sensitivity analysis
- Risk timeline: when each risk is most likely to materialize
- Mitigant tracking: assigned owner, status, due date

#### Faza 58 — Decision View
- AHP criteria configuration (drag to reorder, slide weights)
- Comparison table: tender A vs B vs C (normalized scores)
- Radar chart overlay: multiple tenders on one chart
- "What if" sliders: change weight → see ranking change
- Final decision: GO / NO-GO / CONDITIONAL with notes
- Decision audit: who decided, when, based on what data

#### Faza 59 — Competitor Intelligence View
- Company profiles: won tenders, regions, CPV specialization
- "Your competitors for this tender" (based on CPV + region + value)
- Win probability chart: "With 5 known competitors, P(win) = X%"
- Historical price comparison: "They typically bid 8-12% above estimated value"
- Network graph: who works with whom (contractor-subcontractor relationships)

#### Faza 60 — Command Palette (cmdk)
- Cmd+K: search everything (tenders, actions, settings, help)
- Actions: "Create tender", "Run risk analysis", "Export PDF"
- Navigation: "Go to Pipeline", "Open tender #BZP-2026/..."
- AI commands: "Find tenders similar to [X]", "What's my win rate this quarter?"
- Recent items: last 5 tenders viewed
- Keyboard shortcut cheat sheet (Shift+?)

#### Faza 61 — Notifications Center
- In-app bell icon: unread count
- Categories: Deadlines | BZP Changes | Decisions | Team | System
- Priority: Critical (red dot) → Important → Normal
- Preferences: per-category × per-channel (in-app, email, webhook)
- Batch digest: daily summary at 06:30 (like Minerva)

#### Faza 62 — Team Collaboration
- Mentions: @user in comments/notes
- Assignments: per tender × per task (kosztorys, weryfikacja, podpis)
- Activity feed: who did what, when
- Presence: "Kasia przegląda ten przetarg" (avatar dots)
- Real-time comments (Liveblocks or custom WebSocket)

#### Faza 63 — Charts & Visualizations
- Recharts (responsive, dark theme native)
- Chart types: bar (costs), line (trends), area (uncertainty bands), scatter (bid outcomes), radar (multi-criteria), sankey (pipeline flow), treemap (CPV distribution)
- Interactive: hover for details, click to drill down
- Export: PNG, SVG for reports
- Animate on data load (motion/react)

#### Faza 64 — Table: Advanced Data Grid
- TanStack Table v8: sorting, filtering, grouping, pinning
- Column resizing, reordering, visibility toggle
- Row selection for bulk actions
- Inline editing for quick updates
- Export: CSV, XLSX
- Saved views per user ("Moje przetargi budowlane w Mazowszu")

#### Faza 65 — Forms & Validation
- React Hook Form + Zod schemas
- Multi-step wizards (new tender, new estimate)
- Auto-save (debounced, with conflict detection)
- File upload: drag & drop zone, progress bar, preview
- Conditional fields: show/hide based on selections

#### Faza 66 — Onboarding Wizard
- First-time experience: 4 steps
  1. Company profile (NIP, CPV codes, regions, team size)
  2. Risk appetite settings (AHP weights)
  3. Connect BZP account (monitoring preferences)
  4. Import first tender (or use demo data)
- Time to first value: <5 minutes
- Skip option: "I'll configure later" → defaults

#### Faza 67 — Settings & Configuration
- Organization: name, NIP, logo, branding
- Team: invite members, assign roles
- Pipeline: stage names, colors, rules (auto-move after X days)
- Risk: criteria weights, risk appetite thresholds
- Integrations: BZP sync frequency, webhooks, API keys
- Billing: plan, usage, invoices (Stripe)

#### Faza 68 — Responsive & Mobile
- Desktop: full experience (1440px+)
- Tablet: simplified layout, touch-friendly (768-1440px)
- Mobile: read-only overview + notifications + quick decisions
- PWA: installable, offline tender viewing (cached)
- Push notifications (mobile)

#### Faza 69 — Accessibility (a11y)
- WCAG 2.1 AA compliance
- Keyboard navigation: all actions reachable
- Screen reader labels (aria-*)
- Focus management: modals, drawers, toasts
- Reduced motion mode
- High contrast mode (optional)

#### Faza 70 — Error Handling & Empty States
- Error boundaries: per module, graceful fallback
- Empty states: helpful illustrations + CTAs ("Dodaj pierwszy przetarg")
- Loading states: skeleton screens (not spinners)
- Offline state: banner + queue actions for sync
- 404/500: branded error pages with recovery actions

#### Faza 71 — Search: Full-Text + Semantic
- Full-text: PostgreSQL tsvector (Polish stemming)
- Semantic: pgvector cosine similarity (find similar tenders)
- Faceted: filter by CPV, region, value, status, assignee, date
- Autocomplete: as-you-type suggestions
- Search analytics: popular queries, no-results tracking

#### Faza 72 — Audit & History View
- Event sourcing → rendered as timeline
- "Kto zmienił cenę pozycji X?" → exact user, timestamp, old/new value
- Compare versions: diff view for estimates
- Restore point: "Revert to version from Tuesday 14:30"
- Export audit log (compliance requirement)

#### Faza 73 — Print & Export Center
- PDF generation: server-side (Puppeteer or WeasyPrint)
- Templates: configurable per report type
- Batch export: "Export all active estimates as ZIP"
- Scheduled reports: weekly summary PDF to email
- Branding: company logo, colors, footer

#### Faza 74 — AI Chat Interface v2
- Context-aware: knows current tender, user, org
- Multi-turn: follow-up questions
- Tool calling: "Ile kosztuje m² ściany żelbetowej?" → queries cost DB
- Streaming: token-by-token response
- Citations: "Zgodnie z SWZ [str. 14, §3.2]..."
- History: past conversations per tender

#### Faza 75 — Dark Theme Polish
- Color tokens: `--surface-{0-4}`, `--accent-*`, `--status-*`
- Glass morphism for cards: `backdrop-blur + subtle border`
- Hover/focus states: consistent glow effect
- Data density: more info per screen than competitors
- Typography: numbers in monospace, labels in sans
- Micro-animations: state transitions (200ms ease-out)

#### Faza 76 — Performance Monitoring (Frontend)
- Web Vitals: LCP <2.5s, FID <100ms, CLS <0.1
- Bundle size budget: <200KB initial JS
- Lazy loading: routes, heavy components (charts, PDF viewer)
- Image optimization: next/image + WebP
- Prefetching: predict next navigation, load ahead

#### Faza 77 — Internationalization (i18n)
- Default: Polish (PL)
- Prepared for: English (EN), Ukrainian (UA), Czech (CS)
- ICU message format (plurals, dates, currencies)
- RTL support (future: Arabic for GCC markets)
- Date/number formatting per locale

#### Faza 78 — Feature Flags & A/B Testing
- PostHog or Statsig integration
- Gradual rollout: 10% → 50% → 100%
- A/B test: "Does AI summary increase Go/No-Bid decision speed?"
- User segments: by plan, by org size, by usage
- Kill switch: instant disable problematic features

#### Faza 79 — Storybook: Component Documentation
- Every component documented with variants
- Interactive playground
- Dark/light theme toggle
- Responsive preview
- Accessibility audit per component
- Design tokens visualization

#### Faza 80 — End-to-End Testing (Playwright)
- Critical paths: login → create tender → estimate → decide → export
- Visual regression: screenshot comparison
- API mocking for deterministic tests
- CI: run on every PR, block merge on failure
- Test data: seeded database with realistic Polish tenders

---

### BLOK D — INTEGRACJE & DANE (Fazy 81-100)
**Cel: Real-world data sources, external systems, ecosystem**

#### Faza 81 — BZP API v2: Full Sync
- All notice types: ogłoszenie, zmiana, wynik, unieważnienie
- Document download: auto-fetch SWZ ZIPs
- Parse structured XML fields → PostgreSQL
- Deduplication: handle corrections/amendments
- Monitoring: per-org saved searches → instant alerts

#### Faza 82 — TED (EU Tenders) Integration
- eForms XML parsing (OP-TED/eForms-SDK)
- Polish tenders above EU thresholds
- Cross-reference: BZP ↔ TED (same tender, two systems)
- Filter: CPV 45xxx + country=PL

#### Faza 83 — GUS BDL API: Economic Indicators
- Quarterly cost indices (construction sector)
- Inflation data (CPI, PPI construction)
- Regional wage data (labor costs per voivodeship)
- Auto-apply: waloryzacja calculations
- Trend charts: cost escalation forecasts

#### Faza 84 — NBP API: Currency & Interest Rates
- Exchange rates (EUR/PLN) — for EU-funded projects
- Reference rate — for cost of capital calculations
- Bond yields — proxy for discount rates in NPV
- Auto-update daily

#### Faza 85 — Weather Data Integration
- Open-Meteo API (free, no key)
- 14-day forecast for project location
- Historical: avg precipitation, frost days per region per month
- Risk input: "Grudzień w Podkarpackim: 12 frost days avg → schedule risk +15%"

#### Faza 86 — Company Registry (KRS/CEIDG) Integration
- Verify contractor data: NIP → company info
- Financial data: revenue, employee count (from KRS filings)
- Auto-populate company profile during onboarding
- Competitor enrichment: size, age, specialization

#### Faza 87 — Email Integration
- Send bid decision notifications
- Parse incoming: "Nowe pytania od zamawiającego" → create task
- Calendar: deadline sync (Google Calendar, Outlook)
- Templates: question to buyer, team notification, management report

#### Faza 88 — Norma PRO / BIMestiMate Interop
- Import: ATH/ATH2XML files → Terra.OS estimate
- Export: Terra.OS estimate → ATH2XML (openable in Norma)
- Field mapping: KNR codes, quantities, prices, overheads
- Validation: "This export is Norma-compatible ✓"

#### Faza 89 — Excel Import/Export
- Import: "Kosztorys ślepy" (blank estimate from buyer)
- Smart mapping: AI suggests column → field mapping
- Export: formatted Excel with formulas, totals, subtotals
- Template: organization-branded Excel template

#### Faza 90 — Supabase/PostgreSQL: Realtime
- Realtime subscriptions: table changes → instant UI update
- Presence: who's online, who's viewing what
- Collaborative: simultaneous editing with conflict resolution
- Broadcast: notifications, chat messages

#### Faza 91 — File Storage System
- Supabase Storage or S3-compatible (MinIO)
- Organization: `/{org_id}/{tender_id}/{category}/{filename}`
- Categories: swz, offers, correspondence, internal, exports
- Virus scanning before store
- Thumbnail generation for images
- Version history per file

#### Faza 92 — Webhook System
- Events: `tender.created`, `tender.deadline_7d`, `decision.made`, `estimate.completed`
- Configuration: per org, per event type → URL + secret
- Retry: 3 attempts with exponential backoff
- Logs: delivery status, response codes
- Use cases: Slack notification, CRM update, custom automation

#### Faza 93 — MCP Server: AI Native Integration
- 4 tools (like vergabe-mcp):
  ```
  terra_search_tenders(cpv, region, value_range, deadline)
  terra_get_tender_detail(tender_id)
  terra_get_estimate(tender_id)
  terra_get_risk_analysis(tender_id)
  ```
- Usable from Claude Desktop, Hermes Agent, other MCP clients
- Authentication: API key per org
- Open source: GitHub (community + SEO)

#### Faza 94 — n8n / Zapier Integration
- Pre-built workflows:
  - "New BZP tender matching profile → Slack notification"
  - "Decision = GO → Create Asana/Jira task for team"
  - "Deadline T-3 days → Email reminder to assigned estimator"
- Custom webhook triggers
- OAuth2 app registration (for Zapier native integration)

#### Faza 95 — Data Import: Historical Projects
- CSV/Excel import wizard
- Fields: project name, CPV, value, actual_cost, region, date, outcome
- This data feeds:
  - GP regression training
  - Bayesian Network parameter learning
  - Competitor analysis calibration
  - Cost calibration (predicted vs actual)
- "Import 50+ historical projects → model accuracy improves 40%"

#### Faza 96 — Multi-Model AI Router
- Claude Opus: complex reasoning (risk analysis, decision support)
- Claude Sonnet: standard extraction, chat, summaries
- Claude Haiku: quick classifications, translations, simple queries
- Routing logic: by task complexity, user tier, response time requirement
- Fallback chain: if Opus fails → Sonnet → Haiku
- Cost tracking per org: "Your AI usage this month: $X"

#### Faza 97 — Prompt Library & Versioning
- Versioned prompts per task type (extraction, risk, decision, chat)
- A/B testing: "Prompt v3 extracts penalties with 94% accuracy vs v2's 87%"
- Prompt templating: inject org profile, tender data, historical context
- Guardrails: output validation (Pydantic models)
- Monitoring: latency, token usage, error rate per prompt version

#### Faza 98 — Embedding Pipeline
- text-embedding-3-small (OpenAI) or open source (BGE-M3)
- Embed: SWZ sections, cost items, risk descriptions, chat messages
- Store: pgvector (same PostgreSQL instance)
- Use cases:
  - "Find similar tenders to this one"
  - "Find matching cost items for this description"
  - "Which SWZ section discusses penalties?"
- Batch: nightly re-embed new content

#### Faza 99 — Data Quality & Monitoring
- Completeness: % of fields filled per tender
- Freshness: "Last BZP sync: 12 min ago"
- Accuracy: model calibration metrics (displayed to admins)
- Anomaly detection: "Cost estimate 3σ above historical — verify"
- Data lineage: where does each data point come from?

#### Faza 100 — Migration & Backward Compatibility
- Database migrations: zero-downtime (expand-contract pattern)
- API versioning: v1 (legacy) lives alongside v2 (new)
- Feature gates: new features behind flags until stable
- Data migration scripts: from current Terra.OS → new schema
- Rollback plan: every deploy reversible within 5 minutes

---

### BLOK E — BEZPIECZEŃSTWO & SKALOWALNOŚĆ (Fazy 101-120)
**Cel: Enterprise-grade security, multi-tenant isolation, compliance**

#### Faza 101 — Authentication v2
- Supabase Auth: email + password, magic link, Google SSO
- Enterprise: SAML 2.0, OIDC (Azure AD, Okta)
- MFA: TOTP (Google Authenticator)
- Session management: token refresh, device tracking
- Password policy: configurable per org

#### Faza 102 — Authorization: RBAC + ABAC
- Roles: Owner, Admin, Manager, Estimator, Viewer, External
- Permissions matrix: per module × per action (view/create/edit/delete/decide)
- Attribute-based: "Can only see tenders in region X" or "CPV 45xxx only"
- API enforcement: middleware checks on every request
- UI enforcement: hide buttons/tabs user can't access

#### Faza 103 — Multi-Tenant Isolation
- Database: RLS policies on every table (org_id filter)
- Storage: isolated buckets per org
- AI: no cross-org data leakage in prompts/embeddings
- Network: rate limiting per org
- Billing: isolated usage tracking

#### Faza 104 — Audit Logging
- Every state change: who, what, when, old_value, new_value
- Immutable: append-only audit table (no deletes)
- Queryable: "Show me all changes to Tender X in last 7 days"
- Export: CSV for compliance audits
- Retention: configurable (default 7 years — legal requirement PL)

#### Faza 105 — Encryption
- At rest: PostgreSQL + storage encryption (AES-256)
- In transit: TLS 1.3 everywhere
- Application-level: sensitive fields (pricing strategy) encrypted
- Key management: envelope encryption (Vault or KMS)
- Backup encryption: separate key from production

#### Faza 106 — GDPR Compliance
- Data mapping: what personal data, where stored, why
- Consent management: for AI processing of bid data
- Right to erasure: "Delete all our data" → automated pipeline
- Data portability: export all org data as ZIP (JSON + files)
- DPA: template for enterprise clients
- Cookie consent: PostHog/analytics opt-in

#### Faza 107 — SOC 2 Type II Preparation
- Policies: security, access control, change management, incident response
- Controls: 70+ mapped to Trust Service Criteria
- Evidence collection: automated (Vanta, Drata, or manual)
- Penetration testing: annual (reported)
- Vendor management: list all subprocessors (Supabase, Anthropic, etc.)

#### Faza 108 — Rate Limiting & DDoS Protection
- Per-org API limits (tier-based)
- Per-endpoint limits (heavy operations: AI analysis, file processing)
- Cloudflare: WAF, DDoS protection, bot management
- Graceful degradation: queue requests, don't reject
- Circuit breaker: if external API (BZP, Claude) down → cached response

#### Faza 109 — Disaster Recovery
- RPO: <1 hour (point-in-time recovery)
- RTO: <4 hours
- Automated backups: PostgreSQL pg_dump + WAL archiving
- Cross-region replication (for enterprise tier)
- Runbook: step-by-step recovery procedures
- DR drill: quarterly test

#### Faza 110 — Infrastructure as Code
- Terraform/Pulumi: all infra defined in code
- Environments: dev, staging, production (isolated)
- Secrets management: Vault or environment-specific stores
- Reproducible: spin up entire stack from scratch in <30 minutes

#### Faza 111 — Horizontal Scaling
- Stateless API servers (scale out with load balancer)
- Database: read replicas for analytics queries
- Background workers: auto-scale based on queue depth
- File processing: parallel workers (one per uploaded ZIP)
- Cost optimization: scale down during off-hours (nights, weekends)

#### Faza 112 — Monitoring & Alerting
- Infrastructure: CPU, memory, disk, network (Grafana/Datadog)
- Application: error rates, latency P50/P95/P99 (Sentry)
- Business: daily active users, tenders processed, AI calls
- Alerts: PagerDuty/OpsGenie for critical (5xx spike, DB down)
- SLA: 99.9% uptime target

#### Faza 113 — Cost Optimization
- AI costs: cache frequent queries, batch embeddings, use Haiku for simple tasks
- Database: vacuum, analyze, index optimization quarterly
- Storage: lifecycle policies (archive old files after 1 year)
- Compute: right-sizing instances, spot instances for batch jobs
- Monthly cost review: budget vs actual

#### Faza 114 — API Security
- API keys: per-org, rotatable, scoped (read-only vs full)
- OAuth2: for third-party integrations
- CORS: strict origin whitelist
- Input validation: Pydantic models on every endpoint
- SQL injection: parameterized queries (SQLAlchemy ORM)
- Rate limiting: per-key, per-IP

#### Faza 115 — Vulnerability Management
- Dependencies: Dependabot/Renovate (auto-update)
- SAST: Semgrep in CI (catch security issues before merge)
- Container scanning: Trivy for Docker images
- Secret scanning: prevent committed credentials
- Regular audits: quarterly security review

#### Faza 116 — Data Retention & Archival
- Active data: <2 years in primary DB
- Archive: >2 years → cold storage (cheaper, queryable)
- Legal hold: prevent deletion during disputes
- Cleanup: orphaned files, expired sessions, old embeddings
- GDPR: automatic deletion after retention period

#### Faza 117 — Tenant Onboarding Automation
- Self-serve: sign up → verify email → configure org → start
- Provisioning: automatic (no manual steps)
- Seed data: sample tender for "try before you commit"
- Health check: "Your setup is 80% complete — finish these 3 steps"

#### Faza 118 — SLA & Status Page
- Public status page: uptime, incidents, maintenance windows
- SLA tiers: Free (99%), Pro (99.5%), Enterprise (99.9%)
- Incident response: playbook for each severity level
- Post-mortem: published for major incidents (trust building)

#### Faza 119 — Compliance: Polish Legal Requirements
- Archiwizacja ofert: minimum 4 years (Ustawa PZP)
- NIP verification: real-time check against MF whitelist
- RODO (Polish GDPR): DPO appointment for enterprise
- Rejestr czynności przetwarzania
- Umowa powierzenia danych (template for clients)

#### Faza 120 — Penetration Testing & Bug Bounty
- Annual pentest by external firm
- Bug bounty program (HackerOne / Intigriti) — after market launch
- Responsible disclosure policy
- Security headers: CSP, HSTS, X-Frame-Options
- Regular OWASP Top 10 review

---

### BLOK F — LAUNCH & GROWTH (Fazy 121-140)
**Cel: GTM, pricing, community, scaling**

#### Faza 121 — Pricing Model Design
- Tiers:
  - **Starter** (free): 5 tenders/month, basic AI, 1 user
  - **Pro** (499 PLN/mo): unlimited tenders, full AI, 5 users, Monte Carlo
  - **Business** (1499 PLN/mo): everything + API, SSO, priority support, advanced analytics
  - **Enterprise** (custom): SLA 99.9%, dedicated instance, custom integrations
- Usage-based add-on: AI analysis credits (beyond included)
- Annual discount: 20%

#### Faza 122 — Billing & Payments (Stripe)
- Stripe subscription management
- Polish invoices (faktury VAT): auto-generated
- Payment methods: card, BLIK, przelew bankowy
- Dunning: retry failed payments, grace period, downgrade
- Usage metering: AI calls, storage, team members

#### Faza 123 — Landing Page & Marketing Site
- Dark theme, premium feel (Vercel/Linear inspiration)
- Above fold: value prop + CTA + social proof
- Sections: features, pricing, testimonials, demo video
- SEO: target "AI przetargi Polska", "kosztorysowanie AI", "zarządzanie przetargami SaaS"
- Blog: construction AI thought leadership

#### Faza 124 — Demo & Free Trial
- Interactive demo: pre-loaded with real (anonymized) BZP data
- "See AI in action": analyze sample SWZ live
- 14-day free trial of Pro plan (no credit card required)
- Guided tour: tooltips showing key features
- Exit intent: "Want to see results for YOUR tenders?"

#### Faza 125 — Documentation & Help Center
- Docs site: getting started, features, API reference, FAQ
- Video tutorials: 2-3 min per feature
- In-app help: contextual tooltips, "?" icon → relevant docs
- Changelog: weekly updates, new features
- Community: Discord or forum for users

#### Faza 126 — Customer Success & Onboarding
- White-glove onboarding for Business/Enterprise
- Setup call: configure profile, import historical data, train team
- Health scores: usage metrics → churn prediction
- Quarterly business reviews (Enterprise)
- NPS surveys: monthly

#### Faza 127 — Content Marketing & SEO
- Blog posts: "Jak AI zmienia kosztorysowanie budowlane w Polsce"
- Case studies: "Firma X zwiększyła win rate o 40%"
- Webinars: monthly, construction industry topics
- Newsletter: weekly tender market insights (AI-generated from BZP data)
- Social: LinkedIn (B2B), YouTube (tutorials)

#### Faza 128 — Sales Process
- Product-Led Growth (PLG): self-serve → upgrade
- Sales-assisted for Business/Enterprise
- CRM: HubSpot or Pipedrive
- Sales collateral: pitch deck, ROI calculator, case studies
- Demo environment: always-on, impressive data

#### Faza 129 — Partnerships
- Athenasoft (Norma PRO / Intercenbud): data partnership
- Construction industry associations (PZITB, IGP)
- BIM software vendors (BIMestiMate integration)
- Banks: "Terra.OS risk report" as part of project financing
- Insurance: risk data → contractor insurance pricing

#### Faza 130 — Community & Open Source
- BZP MCP Server: open source (GitHub)
- Blog: technical articles on Bayesian estimation, NLP for SWZ
- Conference talks: DataMass (Gdańsk), ML Warsaw, PyCon PL
- Discord community: tips, feature requests, beta testers
- Contribution rewards: bug reporters, feature suggesters

#### Faza 131 — Mobile App (React Native / Expo)
- Read-only: dashboard, pipeline, notifications
- Quick actions: Go/No-Bid decision, approve estimate, respond to comment
- Push notifications: deadline alerts, new matching tenders
- Offline: view cached tenders on construction site
- Biometric auth: FaceID/fingerprint

#### Faza 132 — Analytics Dashboard for Organizations
- Win rate over time (trend + target)
- Cost accuracy: estimated vs actual (calibration)
- Team productivity: tenders processed per person
- Revenue from won tenders (pipeline conversion)
- Benchmark: "You're in top 20% of firms your size for win rate"

#### Faza 133 — AI Continuous Improvement
- A/B test new prompts: deploy to 10% of analysis, compare accuracy
- User feedback loop: "Was this risk assessment accurate?" → retrain
- Active learning: AI asks for human label on uncertain cases
- Model monitoring: accuracy drift → auto-alert to retrain
- Quarterly model refresh with new data

#### Faza 134 — Internationalization: CEE Expansion
- Czech Republic: Czech tender portal integration
- Slovakia: shared procurement with CZ
- Ukraine: ProZorro API integration (post-war reconstruction)
- Romania: SEAP integration
- Localization: language + legal + procurement rules per country

#### Faza 135 — Advanced: Digital Twin Integration
- BIM model → quantities extraction → auto-estimate
- IFC file import → parse building elements → map to KNR
- 3D visualization of cost breakdown (by floor, by system)
- Schedule simulation: 4D BIM + cost = 5D BIM
- Integration: Revit (IFC export), ArchiCAD, Tekla

#### Faza 136 — Advanced: Predictive Analytics
- "Which tenders will be published next month?" (based on patterns)
- "What will steel prices be in Q4 2026?" (time-series forecast)
- "Which of my current bids will I likely win?" (win probability)
- "Where should I focus next quarter?" (market opportunity scoring)
- Dashboard: forward-looking, not just retrospective

#### Faza 137 — Advanced: Automated Bid Generation
- From SWZ → complete bid document draft:
  - Kosztorys ofertowy (filled estimate)
  - Oświadczenia (JEDZ, wykaz usług, polisa)
  - Harmonogram
  - Wykaz osób (based on org team database)
- Human review: AI draft → expert edits → submit
- Version comparison: "What changed between draft 1 and 2?"

#### Faza 138 — Advanced: Market Intelligence Platform
- Construction market report: weekly AI-generated summary
- Trends: which sectors growing (energy, roads, housing)?
- Regional analysis: where is demand concentrated?
- Price index: Terra.OS Construction Cost Index (own publication)
- API: sell anonymized market data to analysts/banks

#### Faza 139 — Scale: Enterprise Features
- Dedicated instance: single-tenant deployment
- Custom SLA: 99.99% uptime
- Custom integrations: SAP, Oracle, MS Dynamics
- Advanced reporting: custom SQL queries, scheduled exports
- Multi-org hierarchy: holding → subsidiaries
- Data residency: choose EU region for storage

#### Faza 140 — Vision: Construction Intelligence OS
- From "tender management tool" → "Construction Intelligence Platform"
- Expand beyond tenders: project execution tracking, quality control, HSE
- Marketplace: connect contractors with subcontractors (network effects)
- Financing: connect with banks/funds (credit scoring from bid data)
- Industry benchmark: "Terra.OS Construction Index" (like S&P but for PL construction)
- Long-term moat: proprietary dataset of outcomes (15K+ bid results → unbeatable ML)

---

## PODSUMOWANIE PRIORYTETÓW

### MVP (Fazy 1-50): 3-4 miesiące
- Fundament: DDD + Event Sourcing + Multi-tenant + Auth
- Silnik: Bayesian Network + GP Regression + Copulas + Game Theory
- Data: DDC CWICR + Atlas Przetargów + BZP API + GUS
- Core UX: Kanban + SWZ Parser + Kosztorys Editor

### Beta (Fazy 51-80): 2-3 miesiące
- Premium frontend: Linear-quality dark SaaS
- Collaboration: real-time editing, comments, presence
- Document viewer + AI chat
- Mobile PWA

### Launch (Fazy 81-120): 2-3 miesiące
- Integrations: BZP v2, TED, Norma export, Excel
- Security: SOC 2 prep, RLS, audit logging, encryption
- Scale: horizontal scaling, DR, monitoring

### Growth (Fazy 121-140): ongoing
- GTM: pricing, marketing, partnerships
- Expansion: CEE, BIM, market intelligence
- Moat: proprietary data, network effects

---

## TECH STACK DOCELOWY

```
FRONTEND:     Next.js 15 (App Router) + TypeScript 5.4
UI:           Tailwind v4 + Radix UI + shadcn/ui (dark)
STATE:        Zustand + TanStack Query v5
KANBAN:       @dnd-kit/core + @dnd-kit/sortable
CHARTS:       Recharts (KPIs) + Nivo (complex) + D3 (custom)
PDF:          PDF.js (viewer) + WeasyPrint (generation)
EDITOR:       TanStack Table v8 (virtualized spreadsheet)
CMD:          cmdk (command palette)
MOTION:       motion/react (animations)

BACKEND:      FastAPI + Python 3.12 + Pydantic v2
DATABASE:     PostgreSQL 16 + pgvector + TimescaleDB
OLAP:         DuckDB (analytics, competitor intelligence)
QUEUE:        Celery + Redis (background jobs)
STORAGE:      S3/MinIO (files) + Redis (cache)
AUTH:         Supabase Auth (or custom JWT + OIDC)
REALTIME:     SSE (notifications) + WebSocket (collaboration)

AI/LLM:       Claude 3.5 Sonnet (main) + Haiku (fast) + Opus (complex)
EXTRACTION:   ContextGem + Unstructured.io
EMBEDDINGS:   text-embedding-3-small → pgvector
VECTOR:       pgvector (built into PostgreSQL, no separate Qdrant needed)

ANALYTICS:    
  Bayesian:   PyMC 5 / NumPyro (JAX)
  Copulas:    pyvinecopulib
  GP:         GPyTorch / scikit-learn
  Game:       Custom (Friedman/Gates/Carr)
  Decision:   Custom AHP/TOPSIS + scipy.optimize (CVaR)
  RL:         Custom Thompson Sampling + contextual bandit
  Explain:    SHAP + MAPIE (conformal prediction)
  Graphs:     pgmpy (Bayesian Networks)
  TimeSeries: Prophet / NeuralProphet

INFRA:        
  Deploy:     Vercel (frontend) + Railway/Render (API) or VPS
  CI/CD:      GitHub Actions
  Monitoring: Sentry + PostHog + Grafana
  CDN:        Cloudflare
  Email:      Resend
```
