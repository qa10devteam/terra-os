# 🎯 Terra.OS — Sprint Prioritizer Master Plan
**Sprint Prioritizer Agent | Agency Agents | Batch 1**
**Data:** 2026-07-07 | **Horyzont:** 24 tygodnie (Sprinty 1–12)
**Status bazowy:** M0–M4 ✅ | M5–M6 🔄 | M7–M9 ❌ | Coverage ~40%

---

## EXECUTIVE SUMMARY

Terra.OS to platforma SaaS AI dla polskich SMB budowlanych (segment CPV 45112xxx — roboty ziemne). Projekt osiągnął dojrzałość technologiczną M0–M4 (fundament + silnik symboliczny). Przed nami 24 tygodnie krytycznej pracy: dokończenie silnika probabilistycznego, wdrożenie multi-tenancy, budowa modułu logistyki (OR-Tools), aplikacji mobilnej Flutter i orkiestracji LangGraph — a następnie pozyskanie 3 beta klientów i przejście do monetyzacji.

**Główne priorytety planistyczne:**
1. Zamknięcie luki technicznej M5–M6 (Sprinty 1–2)
2. Multi-tenancy + billing jako fundament komercyjny (Sprint 3)
3. Mózg / Logistyka / Mobile (Sprinty 4–7)
4. Hardening + launch readiness (Sprinty 8–10)
5. Beta → Commercial (Sprinty 11–12)

---

## CZĘŚĆ I — PLAN 12 SPRINTÓW (tygodnie 1–24)

> **Konwencja:** 1 Sprint = 2 tygodnie | Velocity: 40–50 SP/sprint (zakładany 1 senior dev + 1 mid dev + 0.5 QA)
> **Story Points:** Fibonacci (1, 2, 3, 5, 8, 13, 21)
> **Daty startowe:** Sprint 1 = 2026-07-07

---

### 🏃 SPRINT 1 (Tygodnie 1–2 | 2026-07-07 → 2026-07-18)
**Cel sprintu:** Zamknąć M5 Engine L2 (Monte Carlo) + naprawić krytyczny bug multi-tenancy (demo user = 0 tenderów)

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S1-01 | **[BUG-KRYT]** Fix tenant_id mismatch — demo@terra-os.pl widzi 0 przetargów (AUDIT_REPORT §4) | 3 | P0 | — |
| S1-02 | **[M5]** Dokończenie `run_l2`: constrained Monte Carlo sampler z Bayesian priors | 8 | P0 | M4 ✅ |
| S1-03 | **[M5]** Sobol sensitivity index dla top-5 driverów ryzyka | 5 | P1 | S1-02 |
| S1-04 | **[M5]** RiskResult model: `{p10, p50, p90, win_prob, drivers[], seed}` | 3 | P0 | S1-02 |
| S1-05 | **[M5]** Deterministyczny seed — reproducibility test | 2 | P0 | S1-04 |
| S1-06 | **[M5]** Testy jednostkowe: `test_m5_risk.py` rozszerzenie do 100% coverage M5 | 5 | P0 | S1-04 |
| S1-07 | **[M5]** Walidacja: żadna próbka MC nie narusza constraintów L1 | 3 | P0 | S1-02, M4 |
| S1-08 | **[INFRA]** Fix alembic dual-head: merge migration `0003_notifications` + `0005_phases_41_60` | 2 | P1 | — |
| S1-09 | **[INFRA]** Fix FK: user test41@terra.os z org_id=NULL | 1 | P1 | — |
| S1-10 | **[INFRA]** Fill empty tables: `axiom` seed (10 podstawowych reguł L1 earthworks) | 3 | P1 | — |
| S1-11 | **[QA]** CI: dodaj M5 do pipeline GitHub Actions | 2 | P1 | S1-06 |
| S1-12 | **[DOCS]** DECISIONS.md — update z decyzjami M5 (seed strategy, prior selection) | 1 | P2 | — |

**Total SP: 38** | **DoD Sprint 1:**
- [ ] `run_l2(seed=42)` reprodukuje identyczne `p10/p50/p90` (test deterministyczny)
- [ ] Win probability monotonicznie rośnie ze spadkiem ceny (test walidacyjny)
- [ ] Zero próbek narusza hard constraint z L1 (guard test)
- [ ] Demo user widzi przetargi po zalogowaniu (smoke test)
- [ ] Alembic ma 1 active head, migracja clean up/down
- [ ] `pytest tests/test_m5_risk.py` — zielony, coverage ≥ 90%

---

### 🏃 SPRINT 2 (Tygodnie 3–4 | 2026-07-21 → 2026-08-01)
**Cel sprintu:** Zamknąć M6 (Email/RFQ broker) + interactive kosztorys sidebar

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S2-01 | **[M6]** RFQ agent: compose RFQ email z structured template (DOCX/HTML) | 5 | P0 | M3 ✅ |
| S2-02 | **[M6]** Gated send flow: `POST /rfq` → approval_request → gate → send | 5 | P0 | S2-01 |
| S2-03 | **[M6]** IMAP parser: odbieranie odpowiedzi RFQ, idempotent na `message_uid` | 8 | P0 | S2-02 |
| S2-04 | **[M6]** `parsed_offer` model + linkowanie do RFQ | 3 | P0 | S2-03 |
| S2-05 | **[M6]** Chat-brain edits: `/estimates/{id}/chat` SSE endpoint | 8 | P1 | M3 ✅ |
| S2-06 | **[M6]** Variable sidebar: `PATCH /estimates/{id}/params` z recompute | 5 | P1 | M3 ✅ |
| S2-07 | **[M6]** Live rule-violation check: `/tenders/{id}/rules/check` → Flag[] | 3 | P1 | M4 ✅ |
| S2-08 | **[M6]** Auto-fill draft: generator JEDZ-style z owner_profile (GATED, nigdy nie submituje) | 5 | P1 | M2 ✅ |
| S2-09 | **[TEST]** Tier-2 end-to-end: A1 + engine + risk + RFQ round-trip (Acceptance A2) | 5 | P0 | wszystkie M6 |
| S2-10 | **[QA]** `test_m6_rfq.py` — pełna coverage RFQ flow | 3 | P0 | S2-04 |
| S2-11 | **[DOCS]** OpenAPI spec update: wszystkie M6 endpointy | 2 | P1 | — |

**Total SP: 52** | **DoD Sprint 2:**
- [ ] RFQ creation zwraca `approval_id`; po approval → send zapisany w audit_log
- [ ] Fixture inbound reply parsowany do `parsed_offer` + linked do RFQ
- [ ] Chat edit "podnieś narzut do 12%" → structured param change + recompute + audit row
- [ ] `/rules/check` zwraca Flag[] dla broken fixture (suma ≠ planowana)
- [ ] Auto-fill produkuje draft, nigdy nie submituje (guard test)
- [ ] `pytest tests/test_m6_rfq.py` green
- [ ] Acceptance A2 (Tier-2 end-to-end) przechodzi na fixtured data

---

### 🏃 SPRINT 3 (Tygodnie 5–6 | 2026-08-04 → 2026-08-15)
**Cel sprintu:** Multi-tenancy RLS produkcyjny + Stripe billing integration

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S3-01 | **[MULTI-T]** PostgreSQL RLS: CREATE POLICY dla 15 kluczowych tabel (tender, estimate, document, etc.) | 8 | P0 | schema done |
| S3-02 | **[MULTI-T]** FastAPI middleware: `set_config('app.tenant_id', ...)` per request | 3 | P0 | S3-01 |
| S3-03 | **[MULTI-T]** Tenant provisioning flow: POST /register → org → first user → demo data seed | 5 | P0 | S3-02 |
| S3-04 | **[MULTI-T]** RLS test suite: cross-tenant query isolation guard (0 cross-leakage) | 5 | P0 | S3-02 |
| S3-05 | **[MULTI-T]** Demo tenant auto-reset: cron job co 24h, izolacja | 3 | P1 | S3-03 |
| S3-06 | **[MULTI-T]** Rate limiting per tenant: Redis + slowapi (`100 req/min` na auth) | 2 | P1 | S3-02 |
| S3-07 | **[BILLING]** Stripe webhook integration: `customer.subscription.created/updated/deleted` | 8 | P0 | billing schema done |
| S3-08 | **[BILLING]** Plan enforcement: Starter (5 aktywnych przetargów) / Pro (50) / Enterprise (∞) | 5 | P0 | S3-07 |
| S3-09 | **[BILLING]** Checkout flow: `POST /billing/checkout` → Stripe Checkout Session | 3 | P1 | S3-07 |
| S3-10 | **[BILLING]** Customer portal: `GET /billing/portal` → Stripe portal link | 2 | P1 | S3-07 |
| S3-11 | **[BILLING]** Trial period: 14 dni Pro bez karty — auto-downgrade do Starter | 3 | P1 | S3-08 |
| S3-12 | **[SECURITY]** JWT rotation: 15min access / 7d refresh token, Redis blacklist | 3 | P1 | — |
| S3-13 | **[QA]** Multi-tenant smoke test suite w CI | 3 | P0 | S3-04 |

**Total SP: 53** | **DoD Sprint 3:**
- [ ] Cross-tenant query zwraca 0 wierszy obcego tenant (automated guard test)
- [ ] Rejestracja nowego tenanta: `/register` → org → user → seed data w < 10s
- [ ] Stripe webhook: subscription create → plan upgrade w DB (e2e test z Stripe CLI)
- [ ] Plan enforcement: Starter nie może dodać przetargu #6 (HTTP 402)
- [ ] `pytest tests/ -k tenant` — zielony, coverage ≥ 85%
- [ ] Demo tenant auto-reset działa (cron smoke test)

---

### 🏃 SPRINT 4 (Tygodnie 7–8 | 2026-08-18 → 2026-08-29)
**Cel sprintu:** M7 Module 3 scaffold — rejestry zasobów (sprzęt, pracownicy, kompetencje)

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S4-01 | **[M7]** Alembic migration M7: tabele `equipment`, `employee`, `competency`, `availability`, `contract`, `plan_header`, `plan_assignment` | 5 | P0 | Sprint 3 done |
| S4-02 | **[M7]** CRUD API: `GET/POST/PUT/DELETE /equipment` | 3 | P0 | S4-01 |
| S4-03 | **[M7]** CRUD API: `GET/POST/PUT/DELETE /employees` z competency links | 3 | P0 | S4-01 |
| S4-04 | **[M7]** Competency registry: `GET/POST /competencies` — kategorie uprawnień (SEP, UDT, etc.) | 2 | P0 | S4-01 |
| S4-05 | **[M7]** Availability calendar: `/employees/{id}/availability` — CRUD z conflict detection | 5 | P0 | S4-03 |
| S4-06 | **[M7]** Equipment availability: `/equipment/{id}/availability` — calendar API | 3 | P0 | S4-02 |
| S4-07 | **[M7]** Contract model: link `tender_id → contract → assignments` | 5 | P1 | S4-01, M3 ✅ |
| S4-08 | **[M7]** Seed data: 30 pracowników, 12 maszyn, 42 dostępności (z AUDIT) — production-like fixtures | 3 | P1 | S4-01 |
| S4-09 | **[M7]** Unit tests dla CRUD registries (pytest fixtures) | 5 | P0 | S4-02–S4-06 |
| S4-10 | **[UI]** Frontend: strona Zasoby — lista pracowników + maszyn (Next.js) | 8 | P1 | S4-02–S4-04 |
| S4-11 | **[UI]** Frontend: modal Dodaj/Edytuj pracownika + kompetencje | 5 | P1 | S4-10 |

**Total SP: 47** | **DoD Sprint 4:**
- [ ] CRUD endpoints dla equipment/employees zwracają poprawne dane (pytest green)
- [ ] Availability conflict detection: dodanie overlapping slot → HTTP 409
- [ ] Frontend strona Zasoby renderuje 30 pracowników z filtrami
- [ ] Seed data załadowana poprawnie do bazy (30 emp, 12 equipment)
- [ ] Alembic migration M7 up/down clean

---

### 🏃 SPRINT 5 (Tygodnie 9–10 | 2026-09-01 → 2026-09-12)
**Cel sprintu:** M7 OR-Tools logistics optimizer — sercem Modułu 3

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S5-01 | **[M7]** OR-Tools MILP model: zmienne decyzyjne (sprzęt×kontrakt×dzień) | 13 | P0 | Sprint 4 done |
| S5-02 | **[M7]** Constraints: availability, competency, equipment capacity | 8 | P0 | S5-01 |
| S5-03 | **[M7]** Objective function: minimalizacja kosztów transportu + idle time | 5 | P0 | S5-02 |
| S5-04 | **[M7]** `/logistics/optimize` endpoint — solver call + response `assignments[]` + `routes[]` | 5 | P0 | S5-03 |
| S5-05 | **[M7]** Infeasible detection: `engine_infeasible` z reason explanation (PL) | 3 | P0 | S5-04 |
| S5-06 | **[M7]** Plan assembly: `POST /plans` — lokalizacja + zdjęcia + rysunki tech + pin GPS + notatki | 5 | P1 | S5-04 |
| S5-07 | **[TEST-M7]** Fixture: 2 kontrakty / 7 pracowników / ograniczone koparki → valid assignment | 5 | P0 | S5-04 |
| S5-08 | **[TEST-M7]** Fixture over-constrained → `engine_infeasible` z reason | 3 | P0 | S5-05 |
| S5-09 | **[UI]** Frontend: widok Plan — Gantt chart z przypisaniami (Recharts/react-big-calendar) | 8 | P1 | S5-06 |
| S5-10 | **[PERF]** OR-Tools benchmark: max 50 pracowników, solve < 30s | 3 | P1 | S5-04 |

**Total SP: 58** | **DoD Sprint 5:**
- [ ] Fixture (2 kontrakty/7 prac./limited excavators) → feasible assignment (Acceptance T-M7)
- [ ] Over-constrained fixture → `engine_infeasible` z powodem (PL)
- [ ] `/logistics/optimize` odpowiada < 30s dla 50 pracowników
- [ ] Plan assembly tworzy `plan_header` z GPS pin + notatką kierownika
- [ ] Gantt chart w UI renderuje przypisania z drag-resize
- [ ] `pytest tests/test_m7_logistics.py` — zielony

---

### 🏃 SPRINT 6 (Tygodnie 11–12 | 2026-09-15 → 2026-09-26)
**Cel sprintu:** M8 Flutter — scaffold, autentykacja, offline cache, field status sync

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S6-01 | **[M8]** Flutter projekt scaffold: `flutter create terra_mobile` + pubspec.yaml (Drift, dio, riverpod) | 5 | P0 | Sprint 5 done |
| S6-02 | **[M8]** Device registration API: `POST /mobile/devices` → JWT per device | 3 | P0 | S3-02 |
| S6-03 | **[M8]** Push notifications: FCM setup + `POST /mobile/devices/{id}/notify` | 5 | P0 | S6-02 |
| S6-04 | **[M8]** Plan fetch: `GET /mobile/plans` (dla zalogowanego pracownika) | 3 | P0 | S5-06 |
| S6-05 | **[M8]** Offline cache: Drift SQLite schema — plans, assignments, photos_queue | 8 | P0 | S6-04 |
| S6-06 | **[M8]** Field status sync: queue podczas offline → bulk push po reconnect | 5 | P0 | S6-05 |
| S6-07 | **[M8]** Conflict resolution: server-wins strategy z local diff log | 3 | P1 | S6-06 |
| S6-08 | **[M8]** Auth flow: login + JWT refresh w Flutter (secure storage) | 5 | P0 | S6-02 |
| S6-09 | **[M8]** Ekran: Lista Planów — kalendarz tygodniowy z zadaniami | 5 | P1 | S6-04 |
| S6-10 | **[M8]** CI: `flutter analyze` w GitHub Actions (zero warnings) | 2 | P0 | S6-01 |
| S6-11 | **[API]** Gated dispatch: `POST /plans/{id}/dispatch` → approval_request → FCM push | 5 | P1 | S5-06, S6-03 |

**Total SP: 49** | **DoD Sprint 6:**
- [ ] `flutter analyze` clean (zero warnings)
- [ ] Device registration → JWT → plan fetch works (integration test)
- [ ] Offline: załaduj plan, odłącz internet, otwórz plan → dane dostępne (Acceptance T-M8 partial)
- [ ] Field status queue: 3 updates offline → sync po reconnect → server updated
- [ ] Dispatch gated: `POST /plans/{id}/dispatch` zwraca `approval_id`

---

### 🏃 SPRINT 7 (Tygodnie 13–14 | 2026-09-29 → 2026-10-10)
**Cel sprintu:** M8 Flutter — mapy, zdjęcia, rysunki techniczne, finalizacja mobilna

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S7-01 | **[M8]** Google Maps integration: pin lokalizacji + nawigacja (flutter_map / google_maps_flutter) | 8 | P0 | Sprint 6 done |
| S7-02 | **[M8]** Ekran: Szczegół Planu — GPS pin + adres + cautions_md (markdown render) | 5 | P0 | S7-01 |
| S7-03 | **[M8]** Zdjęcia: camera_picker → upload do S3/local + link do plan | 5 | P0 | S6-05 |
| S7-04 | **[M8]** Rysunki techniczne: PDF viewer (flutter_pdfview) + pinch-zoom | 3 | P1 | S6-04 |
| S7-05 | **[M8]** Status update: przycisk "Rozpoczęto/Zakończono/Problem" → field_status record | 3 | P0 | S6-06 |
| S7-06 | **[M8]** Push notification: po dispatch approval → ekran otwiera plan | 3 | P0 | S6-03, S6-11 |
| S7-07 | **[M8]** Acceptance T-M8: full test — device register → fetch plan → open pin → offline → sync | 5 | P0 | S7-01–S7-06 |
| S7-08 | **[M8]** Dark mode + design system (Terra colors, typography w Flutter) | 3 | P2 | S6-01 |
| S7-09 | **[API]** Learning loop scaffold: `POST /contracts/{id}/close` → calibration update trigger | 5 | P1 | M3, M7 |
| S7-10 | **[UI]** Web: widok dispatch history + approval queue | 5 | P1 | S6-11 |
| S7-11 | **[QA]** Flutter integration tests (patrol lub flutter_test) | 3 | P1 | S7-07 |

**Total SP: 48** | **DoD Sprint 7:**
- [ ] Acceptance T-M8 full: fresh install → register device → fetch plan → offline → sync status
- [ ] GPS pin otwiera nawigację w Google Maps
- [ ] Zdjęcie robione w aplikacji → uploadowane → widoczne w web dashboardzie
- [ ] PDF rysunku techniczny renderuje się w mobilce offline
- [ ] `flutter test` — zielony na integration tests

---

### 🏃 SPRINT 8 (Tygodnie 15–16 | 2026-10-13 → 2026-10-24)
**Cel sprintu:** M9 LangGraph orchestration M1→M6 jako durable pipeline

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S8-01 | **[M9]** LangGraph supervisor wiring: M1 → M2 → M3 → M4 → M5 → M6 nodes | 13 | P0 | Sprint 7 done |
| S8-02 | **[M9]** State machine: `PipelineState` Pydantic model z checkpoints | 5 | P0 | S8-01 |
| S8-03 | **[M9]** Durable pipeline: Redis persistence dla state (resume po crash) | 5 | P0 | S8-02 |
| S8-04 | **[M9]** Gated actions: każdy side-effect przez ApprovalGate (send, submit, dispatch) | 5 | P0 | S8-01 |
| S8-05 | **[M9]** Observability: structured logging per node + `agent_run` table updates | 3 | P1 | S8-01 |
| S8-06 | **[M9]** Error handling: node failure → graceful degrade + user notification | 3 | P1 | S8-01 |
| S8-07 | **[M9]** Learning loop: contract close → `calibration_coeff` Bayesian update (deterministyczny) | 5 | P0 | S7-09 |
| S8-08 | **[M9]** Acceptance A3: full e2e na fixtures (ingest→analyze→engine→estimate→decision→logistics→dispatch→sync→calibrate) | 8 | P0 | wszystkie M1-M8 |
| S8-09 | **[M9]** Tauri desktop shell: web-view wrapper + systemd/auto-start config | 8 | P1 | S8-01 |
| S8-10 | **[TEST]** `test_m9_orchestration.py` pełna coverage | 3 | P0 | S8-01 |

**Total SP: 58** | **DoD Sprint 8:**
- [ ] Full pipeline M1→M9 uruchamia się na fixtures bez błędów
- [ ] Każdy side-effect pisze do `audit_log` z `approval_id` (guard test)
- [ ] Pipeline wznawia się po symulowanym crash (Redis checkpoint test)
- [ ] Acceptance A3 (Tier-3 full e2e) przechodzi
- [ ] `calibration_coeff` version inkrementuje po contract close
- [ ] Tauri app buduje się i uruchamia lokalnie

---

### 🏃 SPRINT 9 (Tygodnie 17–18 | 2026-10-27 → 2026-11-07)
**Cel sprintu:** Hardening — test coverage 80%, load tests, observability stack

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S9-01 | **[QA]** Coverage audit: zidentyfikuj <60% modules, napisz testy do 80% global | 13 | P0 | Sprint 8 done |
| S9-02 | **[QA]** Load test: Locust — 100 concurrent users, `/tenders` + `/estimates` + `/engine/run` | 5 | P0 | S9-01 |
| S9-03 | **[QA]** p99 target: < 500ms dla `/tenders`, < 5s dla `/engine/run` (enforce) | 3 | P0 | S9-02 |
| S9-04 | **[INFRA]** Prometheus metrics: FastAPI middleware → Grafana Cloud dashboard | 5 | P1 | — |
| S9-05 | **[INFRA]** Alerting: Grafana alerty — API 5xx rate > 1%, DB slow query > 1s | 3 | P1 | S9-04 |
| S9-06 | **[INFRA]** Log aggregation: structured JSON → Loki | 3 | P1 | — |
| S9-07 | **[INFRA]** DB backup: pg_dump cron co 6h, S3 upload, retention 30 dni | 3 | P0 | — |
| S9-08 | **[SECURITY]** OWASP Top 10 audit: SQL injection, XSS, CSRF, rate limiting | 5 | P0 | — |
| S9-09 | **[SECURITY]** Secrets scanning: truffleHog w CI | 2 | P1 | — |
| S9-10 | **[SECURITY]** Dependency audit: pip-audit + npm audit w CI (weekly) | 2 | P1 | — |
| S9-11 | **[GDPR]** Art.13 RODO notice w UI + consent log (GDPR table) | 3 | P0 | S3-03 |
| S9-12 | **[GDPR]** Rejestr czynności przetwarzania (RCP) dokument | 2 | P1 | — |
| S9-13 | **[PERF]** Redis caching: `/tenders` list (TTL 60s), `/estimates/{id}` (TTL 30s) | 3 | P1 | — |

**Total SP: 52** | **DoD Sprint 9:**
- [ ] Global test coverage ≥ 80% (`pytest --cov`)
- [ ] Locust test: 100 users, p99 `/tenders` < 500ms, p99 `/engine/run` < 5s
- [ ] Grafana dashboard live z alertami
- [ ] pg_dump backup działa + test restore na staging
- [ ] OWASP checklist zielony (zero critical findings)
- [ ] RODO notice wyświetla się przy rejestracji

---

### 🏃 SPRINT 10 (Tygodnie 19–20 | 2026-11-10 → 2026-11-21)
**Cel sprintu:** Launch readiness — onboarding flow, dokumentacja, pricing page, SaaS polish

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S10-01 | **[ONBOARD]** First-run wizard: 5-krokowy setup (firma, CPV, region, maszyny, pierwsze przetargi) | 8 | P0 | Sprint 9 done |
| S10-02 | **[ONBOARD]** Interactive demo tour (react-joyride / shepherd.js) | 5 | P1 | S10-01 |
| S10-03 | **[ONBOARD]** Email sequences: welcome → day3 → day7 → day14 (onboarding drip) | 3 | P1 | S3-03 |
| S10-04 | **[UI]** Pricing page: Starter/Pro/Enterprise karty z feature comparison | 5 | P0 | S3-09 |
| S10-05 | **[UI]** Landing page: terra-os.pl — hero, how-it-works, case study placeholder, CTA | 8 | P0 | — |
| S10-06 | **[DOCS]** Dokumentacja API: auto-generated OpenAPI → docs.terra-os.pl | 3 | P1 | — |
| S10-07 | **[DOCS]** Help center: 5 artykułów (getting started, przetargi, kosztorys, silnik, mobile) | 5 | P1 | — |
| S10-08 | **[UI]** Dashboard: NPS widget (Delighted/Survicate) po 7 dniach aktywności | 2 | P2 | — |
| S10-09 | **[UI]** Error boundaries + empty states dla wszystkich widoków | 3 | P1 | — |
| S10-10 | **[UI]** Accessibility audit: WCAG 2.1 AA — kontrast, ARIA, keyboard nav | 3 | P1 | — |
| S10-11 | **[INFRA]** Staging environment: pełna kopia produkcji z anonymized data | 5 | P0 | Sprint 9 done |
| S10-12 | **[INFRA]** Domain setup: terra-os.pl + Cloudflare CDN + SSL (Caddy auto-cert) | 2 | P0 | — |

**Total SP: 52** | **DoD Sprint 10:**
- [ ] First-run wizard przechodzi bez błędów end-to-end (smoke test)
- [ ] Landing page live na terra-os.pl z Lighthouse score ≥ 85
- [ ] Pricing page z działającym Checkout (Stripe test mode)
- [ ] OpenAPI docs live na docs.terra-os.pl
- [ ] Staging environment gotowy + deploy script
- [ ] WCAG 2.1 AA — zero critical issues (axe scan)

---

### 🏃 SPRINT 11 (Tygodnie 21–22 | 2026-11-24 → 2026-12-05)
**Cel sprintu:** Beta launch preparation — 3 beta klientów onboarding, feedback loops

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S11-01 | **[BETA]** Beta program setup: Notion page + umowa pilotażowa (90 dni, Pro gratis) | 3 | P0 | Sprint 10 done |
| S11-02 | **[BETA]** Onboarding call playbook: 45-min call structure + demo script (Terra.OS dla CPV 45112) | 3 | P0 | — |
| S11-03 | **[BETA]** Beta tenant provisioning: dane firmy, CPV profil, pierwsze 5 przetargów | 5 | P0 | S3-03 |
| S11-04 | **[BETA]** Feedback channel: Slack shared channel per beta klient | 2 | P1 | — |
| S11-05 | **[BETA]** Usage analytics: Posthog / Mixpanel — activation events (first tender, first estimate, first decision) | 5 | P0 | S10-01 |
| S11-06 | **[BETA]** Weekly check-in template: metrics (tenders processed, estimates created, decisions made) | 2 | P1 | — |
| S11-07 | **[FEATURE]** BZP live sync: podłączenie produkcyjnego API e-Zamówienia (nie tylko fixtures) | 8 | P0 | M1 ✅ |
| S11-08 | **[FEATURE]** Alert system: email/SMS gdy nowy przetarg matches CPV + region profilu | 5 | P0 | S11-07 |
| S11-09 | **[FEATURE]** Export: kosztorys → XLSX + DOCX (format branżowy) | 5 | P0 | M3 ✅ |
| S11-10 | **[FEATURE]** Competitor atlas: historia wygranych przetargów per NIP (z BZP) | 5 | P1 | S11-07 |
| S11-11 | **[OPS]** Runbook: deploy, rollback, backup restore, incident response | 3 | P0 | Sprint 9 done |
| S11-12 | **[SALES]** LinkedIn outreach: 50 firm budowlanych CPV 451 → personalized message (template) | 2 | P2 | — |

**Total SP: 48** | **DoD Sprint 11:**
- [ ] ≥ 3 firmy zarejestrowane w systemie jako beta tenants
- [ ] BZP live sync przetwarza prawdziwe przetargi (min. 3 z ostatnich 7 dni)
- [ ] Alert email wysłany do co najmniej 1 beta użytkownika za matching tender
- [ ] Export XLSX działa dla kosztorysu z ≥ 5 pozycjami
- [ ] Posthog tracking: activation event "first_estimate_created" monitorowany
- [ ] Runbook przetestowany na staging

---

### 🏃 SPRINT 12 (Tygodnie 23–24 | 2026-12-08 → 2026-12-19)
**Cel sprintu:** Beta live + iteracja na feedbacku + pierwsze konwersje na płatne plany

#### Taski i Story Points

| ID | Task | SP | Priorytet | Zależności |
|----|------|----|-----------|------------|
| S12-01 | **[BETA]** 3 beta klientów aktywnie używają systemu — weryfikacja DAU | 0 | P0 | Sprint 11 done |
| S12-02 | **[ITER]** Bug fixes z feedbacku beta (priorytetyzowane z Severity: Critical/High) | 8 | P0 | S11-03 |
| S12-03 | **[ITER]** Performance fix: konkretne bottlenecki raportowane przez beta klientów | 5 | P1 | S12-02 |
| S12-04 | **[COMMERCIAL]** Upgrade flow: beta → płatny plan (Starter/Pro) — 3 kliknięcia | 3 | P0 | S3-09 |
| S12-05 | **[COMMERCIAL]** Invoice: auto-generacja faktury PDF (polskie przepisy, NIP, VAT 23%) | 5 | P0 | S3-07 |
| S12-06 | **[COMMERCIAL]** Case study: 1 beta klient → write-up (oszczędności czasu, wygrane przetargi) | 3 | P1 | S12-01 |
| S12-07 | **[GROWTH]** Referral program: beta klient → poleca → 1 miesiąc gratis | 2 | P2 | S12-04 |
| S12-08 | **[GROWTH]** Webinar #1: "Jak wygrywać przetargi CPV 45112 z AI" — invitacja 100 firm | 3 | P1 | — |
| S12-09 | **[ANALYTICS]** MRR tracking dashboard: Stripe data → internal dashboard | 3 | P0 | S3-07 |
| S12-10 | **[OKR CHECK]** Q3 OKR retrospective + Q4 plan adjustment | 2 | P0 | — |
| S12-11 | **[FEATURE]** AI summary weekly report: email per tenant (top tenders, pipeline value) | 5 | P1 | S11-07 |
| S12-12 | **[DOCS]** Release notes v1.0 + changelog public | 2 | P1 | — |

**Total SP: 41** (+ 8 SP bufor na bug fixes) | **DoD Sprint 12:**
- [ ] ≥ 3 beta klientów aktywnych (DAU ≥ 1 z każdej firmy)
- [ ] ≥ 1 płatna subskrypcja aktywna (Stripe)
- [ ] MRR dashboard live
- [ ] Faktura PDF generuje się poprawnie (test z prawdziwym NIP)
- [ ] Webinar zaplanowany z ≥ 20 zapisami
- [ ] Q3 OKR retrospective — wszystkie Key Results ocenione

---

## PODSUMOWANIE VELOCITY I TIMELINE

| Sprint | Tygodnie | SP | Główny cel | Go/No-Go Gate |
|--------|----------|----|-----------|----------------|
| S1 | 1–2 | 38 | M5 Monte Carlo + bugfix tenancy | M5 acceptance tests pass |
| S2 | 3–4 | 52 | M6 RFQ + kosztorys interaktywny | Acceptance A2 pass |
| S3 | 5–6 | 53 | Multi-tenancy RLS + Stripe billing | Zero cross-tenant leakage |
| S4 | 7–8 | 47 | M7 registries (sprzęt/pracownicy) | CRUD + seed OK |
| S5 | 9–10 | 58 | M7 OR-Tools optimizer | Acceptance T-M7 pass |
| S6 | 11–12 | 49 | M8 Flutter scaffold + offline | `flutter analyze` clean |
| S7 | 13–14 | 48 | M8 mapy + zdjęcia + finalizacja | Acceptance T-M8 pass |
| S8 | 15–16 | 58 | M9 LangGraph + Tauri | Acceptance A3 pass |
| S9 | 17–18 | 52 | Hardening + 80% coverage | Locust p99 pass |
| S10 | 19–20 | 52 | Launch readiness + landing page | Lighthouse ≥ 85 |
| S11 | 21–22 | 48 | Beta prep + 3 klientów signup | 3 beta tenants live |
| S12 | 23–24 | 41 | Beta live + pierwsze przychody | ≥1 płatna sub |
| **TOTAL** | | **596 SP** | | |

**Średnie velocity:** ~49.7 SP/sprint ✅ (mieści się w założeniu 40–50 SP przy 2 devs + 0.5 QA)

---

## CZĘŚĆ II — OKR FRAMEWORK

### Q3 2026 (Lipiec – Wrzesień 2026)
**Objective: Zbudować kompletny produkt gotowy do beta testów**

| Key Result | Cel | Metryka | Tracking |
|-----------|-----|---------|----------|
| KR1 | M5+M6 zamknięte i przetestowane | Acceptance A2 pass | Sprint 2 DoD |
| KR2 | Multi-tenancy RLS zero-leakage | 0 cross-tenant queries w automated test | Sprint 3 DoD |
| KR3 | Test coverage global ≥ 60% | `pytest --cov` report | CI pipeline |
| KR4 | M7 OR-Tools optimizer gotowy | Acceptance T-M7 pass | Sprint 5 DoD |
| KR5 | ≥ 3 beta klientów zrekrutowanych (umowa pilotażowa podpisana) | Signed agreements | Notion tracking |
| KR6 | BZP live sync aktywny (nie fixtures) | ≥ 10 real tenders/dzień | Monitoring |
| KR7 | Landing page live z waitlistą | ≥ 50 leadów zebranych | Mailchimp/Notion |

**Q3 Ambition Level:** 70% confidence → 5/7 KR osiągniętych = Q3 SUCCESS

---

### Q4 2026 (Październik – Grudzień 2026)
**Objective: Walidacja produktu na rynku + pierwsze przychody**

| Key Result | Cel | Metryka | Tracking |
|-----------|-----|---------|----------|
| KR1 | 3 aktywnych beta klientów (DAU ≥ 3/tydzień) | Posthog DAU metric | Weekly review |
| KR2 | ≥ 10 płacących klientów | Stripe MRR > 0 | Stripe dashboard |
| KR3 | MRR ≥ 5,000 PLN (np. 10 × Starter 299 + 2 × Pro 799) | Stripe MRR report | Automated |
| KR4 | NPS beta klientów ≥ 40 | Delighted NPS widget | Monthly survey |
| KR5 | M8 Flutter app dostępny na Google Play (beta) | App Store listing | Play Console |
| KR6 | M9 LangGraph orchestration na produkcji | Acceptance A3 na prod | Monitoring |
| KR7 | Test coverage ≥ 80% | CI coverage report | GitHub Actions |
| KR8 | Czas onboardingu nowego klienta ≤ 30 min | Onboarding funnel tracking | Posthog |
| KR9 | Webinar #1 z ≥ 50 uczestnikami | Registration count | EventBrite |
| KR10 | Churn rate beta ≤ 10% | Churned/Total | Manual tracking |

**Q4 Ambition Level:** 70% confidence → 7/10 KR = Q4 SUCCESS

---

### Q1 2027 (Styczeń – Marzec 2027)
**Objective: Skalowanie do 50 klientów i 1M ARR run-rate**

| Key Result | Cel | Metryka | Tracking |
|-----------|-----|---------|----------|
| KR1 | ≥ 50 płacących klientów | Stripe Customer count | Stripe dashboard |
| KR2 | ARR run-rate ≥ 1,000,000 PLN | MRR × 12 ≥ 83,333 PLN/mies | Stripe MRR |
| KR3 | CAC ≤ 2,000 PLN (Starter/Pro blended) | Marketing spend / new customers | Manual |
| KR4 | LTV/CAC ratio ≥ 5:1 | (ARPU × avg tenure) / CAC | Manual |
| KR5 | Churn MRR ≤ 3% miesięcznie | Churned MRR / Total MRR | Stripe + Manual |
| KR6 | Activation rate ≥ 60% | Users who created ≥1 estimate in 7d | Posthog |
| KR7 | ≥ 3 Enterprise deals w pipeline (>5k PLN/mies) | CRM pipeline | Notion CRM |
| KR8 | Series A deck gotowy (20 slajdów, metrics validated) | Deck review | Founder |
| KR9 | ≥ 2 integracje zewnętrzne (SEKOCENBUD, KSeF) | Live integration | Feature flag |
| KR10 | NPS ≥ 50 (Promoters majority) | Delighted NPS | Quarterly survey |

**Q1 2027 Ambition Level:** 60% confidence → stretch goal | 7/10 KR = Q1 SUCCESS

---

### OKR Dashboard Metryki Tygodniowe

```
📊 WEEKLY REVIEW SCORECARD (co poniedziałek)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sprint velocity:        [X SP] / 45 SP target
Test coverage:          [X%] / 80% target  
Active beta users:      [X] / 3 target
MRR:                    [X PLN] / 5,000 PLN target
BZP tenders synced:     [X] today
Pipeline value tracked: [X PLN] across all tenants
New leads (waitlist):   [X] this week
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## CZĘŚĆ III — GO-TO-MARKET STRATEGY

### 3.1 Segmentacja ICP (Ideal Customer Profile)

#### Segment Główny: SMB Roboty Ziemne (ICP-A)
```
Firma: 20–200 pracowników
Specjalizacja: CPV 45112xxx (roboty ziemne), 45233xxx (drogi)
Przychód: 5–50M PLN/rok
Przetargi: 20–100 startów/rok (głównie zamówienia publiczne)
Region: Dolny Śląsk, Mazowsze, Śląsk, Małopolska (największe kontrakty)
Persona decydenta: Prezes / Dyrektor Techniczny / Kierownik Przetargów
Pain points: "Przegapiamy przetargi", "Kosztorys trwa tydzień", "Nie wiemy kto konkuruje"
Willingness to pay: 299–799 PLN/mies (Starter/Pro)
```

#### Segment Uzupełniający: Generalni Wykonawcy z Działem Ziemnym (ICP-B)
```
Firma: 100–500 pracowników (GW z własnym sprzętem)
Specjalizacja: budownictwo ogólne + roboty ziemne jako core
Przetargi: 5–20/rok (większe wartości, >1M PLN)
Willingness to pay: Enterprise custom
Decision timeline: 3–6 miesięcy
```

#### Segment Odroczone: Mikrofirmy (<20 os) — NIE W Q3/Q4
- Za mały ARR, zbyt wysoki CAC, niska dojrzałość cyfrowa
- Rozważyć Q2 2027 z tańszym planem "Solo" ~149 PLN/mies

---

### 3.2 Positioning i Messaging

#### Główne Przesłanie (Headline)
> **"Wygrywaj więcej przetargów ziemnych. Kosztorys w 12 minut, nie 4 dni."**

#### Supporting Claims
1. *"Przetargi BZP dopasowane do Twojego profilu — rano w skrzynce, nie po przeszukiwaniu 200 pozycji"*
2. *"Silnik AI analizuje ryzyko kontraktu zanim podpiszesz — kary umowne, termin, warunki"*
3. *"Twój kosztorysant wycenia robotę. Terra.OS sprawdza: czy to realne? Czy wygrasz?"*

#### Proof Points (do zbudowania w Q3)
- Beta Case Study: "[Firma X] zmniejszyła czas kosztorysowania z 4 dni do 2 godzin"
- Benchmark: "Terra.OS wykrywa 94% red flagów w SIWZ (vs. 60% ręcznie)"
- ROI: "1 wygrany przetarg więcej w kwartale = zwrot z 24 miesięcy subskrypcji Pro"

#### Messaging per Persona

| Persona | Ból | Obietnica Terra.OS | CTA |
|---------|-----|---------------------|-----|
| Prezes SMB | "Tracimy przetargi przez opóźnienia" | "Nigdy więcej przegapionego przetargu" | "Zacznij 14-dniowy trial" |
| Kierownik Przetargów | "Ręczne przeglądanie BZP 2h/dzień" | "Automatyczny feed dopasowanych przetargów" | "Zobacz demo" |
| Kosztorysant | "Excel kosztorys = 3 dni i błędy" | "Kosztorys z przedmiaru w 12 minut" | "Wypróbuj z własnym przedmiarem" |
| Kierownik Budowy | "Nie wiem co zaplanowano na jutro" | "Plan dnia na telefonie, offline" | "Demo mobilne" |

---

### 3.3 Kanały GTM i Taktyki

#### Kanał 1: LinkedIn Cold Outreach (Primary — Q3)
**Target:** Prezesi + Dyrektorzy Techniczni firm budowlanych CPV 45112xxx

**Taktyka:**
```
Krok 1: Buduj listę w Sales Navigator
  → Filtr: "Budownictwo" + "11-200 pracowników" + Polska
  → Tytuł: "Prezes" OR "Dyrektor Techniczny" OR "Kierownik Przetargów"
  → Dodaj 20 osób/dzień

Krok 2: Connection request + personalizacja
  "Hej [Imię], widzę że [Firma] bierze udział w przetargach CPV 45112 
   na [region]. Budujemy narzędzie które skraca analizę SWZ z 4h do 15 min.
   Czy mógłbym pokazać Ci demo? 15 minut."

Krok 3: Follow-up po 5 dniach
  "Niedawno pisałem — czy natrafiacie na problem z czasem kosztorysowania? 
   Chętnie pokażę jak [podobna firma] rozwiązała to z Terra.OS."

Krok 4: Value add (bez sprzedaży)
  "Przygotowałem checklistę 10 najczęstszych red flagów w SIWZ dla robót 
   ziemnych — chętnie podeślę jeśli przydatna."
```

**KPI:** 20 wiadomości/dzień → 15% response rate → 3% konwersja na demo → 
~6 demo/tydzień → 2 beta signups/miesiąc

**Narzędzia:** Sales Navigator (89$/mies), Clay.earth (personalizacja), Lemlist/Apollo

---

#### Kanał 2: CPV Targeting — Przetargi jak Reklamy (Primary — Q3/Q4)
**Insight:** Firmy które składają oferty w CPV 45112xxx to nasi dokładni ICP. Ich NIP jest publiczny w BZP.

**Taktyka:**
```
1. Pobierz z BZP listę wykonawców z ostatnich 12 mies. w CPV 45112xxx (public data)
2. Wzbogać o KRS → adres email, telefon, LinkedIn URL firmy
3. Cold email:
   "Widzieliśmy że [Firma] złożyła ofertę w przetargu [BZP numer].
    Ile czasu zajął Wam kosztorys tej pozycji?
    Nasze narzędzie robi to w 12 minut — mogę pokazać?"
4. Retargeting LinkedIn: upload listy NIP/email → LinkedIn Matched Audiences
```

**KPI:** 200 firm w outreach → 8% reply → 3 demo/tydzień → 1 beta/miesiąc

---

#### Kanał 3: Content + Webinary (Long-term — Q4/Q1)
**Format:** Seria "Roboty Ziemne z AI" — edukacja rynku, budowanie authority

**Plan:**
```
Webinar #1 (Sprint 12): "Jak zautomatyzować monitoring przetargów BZP w 2026"
  → Target: 100 zapisanych, 40% attendance rate
  → Lead capture: ebook "20 red flagów w SIWZ ziemnej"
  → Follow-up: 3-mailowa sekwencja → CTA demo

Webinar #2 (Q4): "Kosztorys ziemny AI vs. Excel — live demo"
  → Target: 150 zapisanych (z polecenia beta klientów)
  → Format: 30 min edukacja + 20 min Q&A + 10 min CTA

LinkedIn Articles (tygodniowo):
  - "5 błędów kosztorysowych które przegrywają przetargi"
  - "Jak czytać SIWZ w 15 minut — NLP dla kierownika przetargów"
  - "Historia: firma z Wrocławia wygrała 3 przetargi z Terra.OS"

YouTube (Q4): 3 krótkie filmy (2-3 min) — demo modułów Zwiad/Kosztorys/Silnik
```

**KPI:** 500 LinkedIn followers (Q4), 50 leads z webinarów (Q4), 1000 views/artykuł

---

#### Kanał 4: Partnerstwa (Q4/Q1)
- **Stowarzyszenia branżowe:** PZPB, Polskie Stowarzyszenie Budownictwa Ekologicznego — newsletter, sponsoring
- **Biura rachunkowe + kancelarie prawa budowlanego** — referrals (oni obsługują dokładnie nasze ICP)
- **SEKOCENBUD** — potencjalna integracja danych + co-marketing
- **BHP/szkolenia budowlane** — cross-sell do firm które już szkolą pracowników

---

### 3.4 Akwizycja 3 Beta Klientów — Plan Taktyczny

#### Profil Beta Klienta (targetowany)
```
✓ 20–100 pracowników
✓ Specjalizacja CPV 45112xxx (roboty ziemne)
✓ Dolny Śląsk / Mazowsze / Śląsk (bliskość do weryfikacji)
✓ Startuje w ≥ 10 przetargach/rok
✓ Ma kosztorysanta (wie o problemie)
✓ Prezes/DT otwarty na technologię
✓ Nie używa zaawansowanego oprogramowania (Excel + PDF)
```

#### Timeline Akwizycji (Sprint 9–11, tydz. 17–22)

**Tydzień 17–18 (Sprint 9):**
- Lista 100 firm z BZP (CPV 45112, ostatnie 12 mies., min. 5 ofert)
- Wzbogacenie o KRS/LinkedIn (email/tel/LinkedIn URL)
- Przygotowanie decku "Beta Program Terra.OS" (Canva, 10 slajdów)
- LinkedIn connection request do 50 osób z listy

**Tydzień 19–20 (Sprint 10):**
- Cold outreach 50 firm (LinkedIn + email)
- Cel: 8 demo calls umówionych
- Demo script: 45 min, własne dane klienta jeśli możliwe

**Tydzień 21–22 (Sprint 11):**
- Onboarding 3 beta klientów
- "Beta Pilot Agreement" — 90 dni Pro bezpłatnie
- Zobowiązanie klienta: 2h/tydzień (testy + feedback call co 2 tygodnie)
- Slack shared channel + dedicated support

**Kluczowe Argumenty dla Klientów Beta:**
1. "Bezpłatny dostęp Pro (wartość 799 PLN/mies) przez 90 dni"
2. "Wasz feedback kształtuje produkt — priority roadmap access"
3. "Case study z Waszą firmą (jeśli zgoda) = darmowa reklama"
4. "Gwarancja: jeśli nie zaoszczędzi 4h/tydzień, odchodzimy bez pytań"

---

### 3.5 Sales Funnel i Conversion Metrics

```
AWARENESS → CONSIDERATION → DECISION → ONBOARDING → RETENTION
   |              |              |             |            |
LinkedIn        Demo call     Beta agree    First tender  Weekly use
outreach        booked        signed        analyzed      3+ logins/week
   |              |              |             |            |
 1000 kontaktów → 50 demo → 10 offers → 3 beta → 1 płacący
  (100%)         (5%)        (20%)       (30%)    (33%)

Target Q4: 10 paying customers
Pipeline needed: 10 / 0.033 = ~300 qualified leads
Monthly outreach needed: ~100 contacts/mies
```

---

## CZĘŚĆ IV — RICE SCORING TOP-20 FEATURES

> **RICE = (Reach × Impact × Confidence) / Effort**
> Reach (1–10): liczba użytkowników dotkniętych w kwartale
> Impact (1–5): wpływ na kluczową metrykę (retencja, konwersja, revenue)
> Confidence (10–100%): pewność szacunków
> Effort (SP): story points implementacji

| # | Feature | Reach | Impact | Conf % | Effort SP | RICE Score | Sprint |
|---|---------|-------|--------|--------|-----------|------------|--------|
| 1 | **BZP Live Sync** (prawdziwe przetargi, nie fixtures) | 10 | 5 | 90% | 8 | **56.25** | S11 |
| 2 | **Multi-tenancy RLS** (izolacja danych) | 10 | 5 | 95% | 21 | **22.62** | S3 |
| 3 | **Alert email/SMS** (nowy przetarg matches profil) | 9 | 5 | 85% | 5 | **76.50** | S11 |
| 4 | **Stripe Billing** (checkout + plan enforcement) | 8 | 5 | 90% | 13 | **27.69** | S3 |
| 5 | **M5 Monte Carlo L2** (risk distribution) | 7 | 5 | 95% | 16 | **20.78** | S1 |
| 6 | **Export XLSX/DOCX kosztorys** (branżowy format) | 8 | 4 | 90% | 5 | **57.60** | S11 |
| 7 | **OR-Tools Logistics Optimizer** (M7) | 5 | 5 | 80% | 26 | **7.69** | S5 |
| 8 | **Flutter Mobile App** (M8 — offline + sync) | 6 | 4 | 75% | 30 | **6.00** | S6–S7 |
| 9 | **Interactive Kosztorys Chat** (chat-brain edits) | 7 | 4 | 85% | 13 | **18.31** | S2 |
| 10 | **First-Run Wizard** (onboarding 5 kroków) | 9 | 4 | 85% | 8 | **38.25** | S10 |
| 11 | **Competitor Atlas** (historia wygranych per NIP) | 7 | 4 | 70% | 8 | **24.50** | S11 |
| 12 | **RFQ Email Broker** (zapytania ofertowe gated) | 5 | 4 | 80% | 21 | **7.62** | S2 |
| 13 | **Auto-fill Draft** (JEDZ z owner_profile, gated) | 6 | 3 | 75% | 8 | **16.88** | S2 |
| 14 | **Landing Page + Pricing** | 10 | 3 | 95% | 13 | **21.92** | S10 |
| 15 | **LangGraph Orchestration** (M9 full pipeline) | 4 | 5 | 70% | 34 | **4.12** | S8 |
| 16 | **NPS Widget** (feedback loop) | 8 | 3 | 90% | 2 | **108.00** | S10 |
| 17 | **Weekly AI Summary Email** (per tenant) | 7 | 3 | 80% | 5 | **33.60** | S12 |
| 18 | **Tauri Desktop App** (installer + auto-update) | 4 | 2 | 65% | 13 | **4.00** | S8 |
| 19 | **Demo Interactive Tour** (react-joyride) | 9 | 3 | 85% | 5 | **45.90** | S10 |
| 20 | **Referral Program** (beta klient poleca) | 6 | 3 | 60% | 3 | **36.00** | S12 |

**Top-5 najwyższy RICE:**
1. 🥇 NPS Widget (108.0) — mały effort, duży reach + feedback value
2. 🥈 Alert email/SMS (76.5) — kluczowy dla daily active use
3. 🥉 BZP Live Sync (56.25) — fundament dla real value
4. Export XLSX/DOCX (57.6) — branżowy dealbreaker
5. Demo Interactive Tour (45.9) — conversion booster

---

## CZĘŚĆ V — TOP-5 RYZYK I MITIGATION STRATEGIES

### 🔴 RYZYKO 1: Wolna adopcja (brak 3 beta klientów w Q3)
**Prawdopodobieństwo:** Wysokie (60%) | **Impact:** Krytyczny

**Opis:** Rynek budowlany SMB PL charakteryzuje się niską dojrzałością cyfrową. Decyzja zakupowa wymaga 3–6 miesięcy i akceptacji przez prezesa. Brak referencji w Q3 blokuje Q4 revenue.

**Mitigation Strategies:**
1. **Rozszerz net:** Celuj w 150 firm (nie 100) — wyższy pipeline buffer
2. **"Done for you" onboarding:** Pierwsze 5 przetargów skonfiguruj SAM dla klienta (hands-on)
3. **Niższy próg wejścia:** Zaproponuj "free tier" z 2 przetargami/mies (Freemium — zachęta do próby)
4. **Warm intros:** Zidentyfikuj 3 koneksje w branży (LinkedIn 2nd degree w CPV 45112)
5. **Event-based:** Targi BUDMA (Poznań, Jan 2027) — book stoisko już teraz, beta klientów jako "case study prelegenci"

**Trigger:** Tydzień 16 — jeśli < 1 signed beta agreement → aktywuj "Emergency Outreach" (podwój liczbę kontaktów/dzień)

---

### 🔴 RYZYKO 2: Dług techniczny blokuje produkt (M7/M8 nie gotowe na czas)
**Prawdopodobieństwo:** Średnie (40%) | **Impact:** Wysoki

**Opis:** OR-Tools MILP + Flutter to dwa nieznane technologiczne. Sprinty 5 i 6–7 mają najwyższe SP. Poślizg 2 tygodni = beta bez modułu logistyki/mobile.

**Mitigation Strategies:**
1. **Scope cut:** Zdefine MBI (Minimum Billable Increment) bez M7/M8 — platforma jest wartościowa już jako ZWIAD + KOSZTORYS + SILNIK (Tier 1+2)
2. **Parallel track:** Rekrutuj kontraktora na Flutter (Upwork/Toptal) w Sprint 4 — "Flutter specialist, 3 miesiące"
3. **OR-Tools spike:** Poświęć pierwsze 2 dni Sprint 4 na proof-of-concept solver — jeśli blokujące, szukaj alternatywy (Google OR-Tools → GLPK → heurystyki)
4. **Early decision gate:** Sprint 4 DoD = decyzja: "OR-Tools viable? TAK/NIE" — jeśli NIE, scope zmiana na Sprint 5
5. **Beta bez M7:** Zaoferuj beta klientom "Tier 1+2 only" — logistyka jako Q4 bonus

**Trigger:** Sprint 5, dzień 3 — jeśli solver nie rozwiązuje fixture w < 60s → scope cut decyzja

---

### 🟡 RYZYKO 3: BZP API niestabilne / zmiany API (disruption danych)
**Prawdopodobieństwo:** Średnie (35%) | **Impact:** Wysoki (core feature)

**Opis:** e-Zamówienia/BZP API ma historię nieplanowanych przestojów i zmian schematu bez notice. Brak przetargów = zero wartości dla klienta = churn.

**Mitigation Strategies:**
1. **Multi-source:** Równolegle integruj tenders.guru jako backup feed (JSON, darmowy, dzienny)
2. **TED EU:** Dla dużych kontraktów (>5.38M EUR) — TED Open Data jako alternative source
3. **Cache agresywny:** Trzymaj ostatnie 7 dni przetargów w cache — nawet przy API downtime user widzi dane
4. **API monitoring:** Pingdom/UptimeRobot na BZP API endpoint — alert gdy >5s response
5. **Graceful degradation:** UI "Dane z [data_ostatniej_synchronizacji] — API tymczasowo niedostępne"
6. **Scraping fallback:** Podstawowy HTML scraper BZP jako last resort (legal grey zone — sprawdź T&C)

**Trigger:** BZP downtime > 4h → automatyczne włączenie tenders.guru feed

---

### 🟡 RYZYKO 4: Konkurencja / kopia przez większego gracza
**Prawdopodobieństwo:** Niskie–Średnie (25%) | **Impact:** Wysoki długoterminowo

**Opis:** Procore, PlanRadar lub polski startup mogą skopiować core feature (BZP monitoring + AI kosztorys) w 6–12 miesięcy. Data network effect jest kluczowy dla defensibility.

**Mitigation Strategies:**
1. **Speed moat:** Bądź na rynku z 50+ klientami zanim konkurencja zareaguje (Q1 2027 cel)
2. **Data moat:** `calibration_coeff` per tenant + `historical_bids` — im dłużej klient używa, tym lepszy model. Trudne do replicate.
3. **CPV specialization:** Nie buduj generalnego narzędzia — bądź "najlepszym narzędziem dla robót ziemnych". Niche = defensible.
4. **Switching cost:** Dane rate_card + historia ofert + competitor atlas klienta = lock-in
5. **Patent/IP:** Rozważ patent na metodę "constrained Monte Carlo z L1 symbolic constraints dla kosztorysowania" — nawet zgłoszenie daje 12 mies. ochrony

**Trigger:** Monitoring: Google Alerts "BZP AI", "kosztorys AI SaaS" — tygodniowy przegląd

---

### 🟡 RYZYKO 5: RODO/Compliance block — dane przetargowe i dane pracowników
**Prawdopodobieństwo:** Niskie (20%) | **Impact:** Średni–Wysoki

**Opis:** Przetwarzanie danych osobowych pracowników (moduł M7: employees, availability, field status) + dane z KRS/BZP (NIP, email, tel firm) wymaga poprawnej podstawy prawnej. Niezgodność = kara UODO do 4% obrotu.

**Mitigation Strategies:**
1. **Klauzula RODO w umowie** — DPA (Data Processing Agreement) jako attachment do umowy SaaS
2. **Art.13 notice** — wyświetlaj przy rejestracji (Sprint 9 task S9-11 — already planned)
3. **Dane BZP są publiczne** — nie wymagają zgody (art.6 ust.1 lit.e/f RODO — uzasadniony interes)
4. **Dane pracowników** — pracodawca (tenant) jest administratorem, Terra.OS jest procesorem → DPA konieczna
5. **Konsultacja prawna** — Sprint 7: 2h konsultacja z prawnikiem RODO/IT (koszt ~800 PLN)
6. **Rejestr czynności przetwarzania** — Sprint 9 task S9-12 — already planned

**Trigger:** Sprint 3 (before first real tenant data) — DPA template gotowy i podpisany

---

## CZĘŚĆ VI — DEPENDENCIES MAP

```
M5 (S1) ──────────────────────────────────────────────┐
M6 (S2) ──────────────────────────────────────────────┤
                                                        ↓
Multi-Tenancy + Billing (S3) ──────────────────────→ Beta Readiness (S11)
                                ↓
M7 Registries (S4) ──────────→ OR-Tools Optimizer (S5) ──→ Plans API
                                                              ↓
M8 Flutter (S6) ──────────→ Maps + Photos (S7) ──────────→ Dispatch
                                                              ↓
M9 LangGraph (S8) ────────────────────────────────────→ Full Pipeline
                                                              ↓
Hardening (S9) ──→ Launch Readiness (S10) ──→ Beta (S11) ──→ Revenue (S12)
```

**Krytyczna ścieżka:** M5 → M6 → RLS → M7 → M8 → M9 → Hardening → Launch
**Najkrótszy path do revenue:** M5 → M6 → RLS + Billing → Beta (możliwy w S3 bez M7/M8)

---

## APPENDIX: Definition of Done (Globalna)

Każdy task jest "Done" gdy spełnia WSZYSTKIE:
- [ ] Kod na feature branch → PR → review → merge to `main`
- [ ] Testy napisane (unit lub integration, nie smoke only)
- [ ] `pytest` zielony (lub `flutter test`) — zero failures
- [ ] Żaden secret nie jest w kodzie (truffleHog clean)
- [ ] OpenAPI spec zaktualizowane (jeśli nowy endpoint)
- [ ] DECISIONS.md zaktualizowane (jeśli nowa decyzja architektoniczna)
- [ ] Żaden side-effect (email, SMS, BZP write) bez audit_log zapisu
- [ ] Dla endpoints z danymi tenant: cross-tenant guard test napisany i zielony

---

*Dokument wygenerowany przez Sprint Prioritizer Agent (🎯) — Agency Agents*
*Terra.OS Project | Data: 2026-07-07 | Wersja: 1.0*
*Następna rewizja: po Sprint 3 retrospective (2026-08-15)*
