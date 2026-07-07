# Terra.OS — Plan Rozwojowy 450 Zadań
**NEXUS NEXUS-Full — 7 faz, 450 tasków, platforma SaaS dla firm budowlanych**

> Wygenerowany: 2026-07-07 przez NEXUS Orchestrator (3 batche agencyjne równoległe)

---

## STAN BAZOWY (2026-07-07)

| Warstwa | Status | Pokrycie |
|---|---|---|
| Monorepo / scaffold | ✅ done | M0 |
| DB schema (54 tables) | ✅ done | M0+M1 |
| FastAPI (40 routers) | ✅ done | M0-M6 partial |
| Next.js UI (15 stron) | ✅ demo-live | M1-M3 UI |
| Engine L1 (clingo) | ✅ done | M4 partial |
| Engine L2 (Monte Carlo) | 🔄 partial | M5 partial |
| Email/RFQ broker | 🔄 partial | M6 partial |
| Module 3 (Mózg / OR-Tools) | ❌ todo | M7 |
| Flutter mobile | ❌ todo | M8 |
| LangGraph orchestration | ❌ todo | M9 |
| Tests (pytest) | 🔄 partial | ~40% coverage |
| CI/CD | 🔄 partial | GitHub Actions |
| Multi-tenancy | ✅ schema | prod wiring todo |
| Auth / billing | 🔄 partial | Stripe schema |

---

## ARCHITEKTURA DOCELOWA

```
Terra.OS SaaS
├── Layer 0: Ingestion (BZP/TED/BK connectors, CPV/geo filter, scorer)
├── Layer 1: Analysis (OCR, agentic RAG, przedmiar parser, embed)
├── Layer 2: Estimation (Kosztorys A/B, rate_card, compare)
├── Layer 3: Engine L1+L2 (clingo+Z3 symbolic + Monte Carlo Bayesian)
├── Layer 4: Decision (RFQ broker, email, chat edits, auto-fill gated)
├── Layer 5: Module 3 (OR-Tools logistics, equipment/employees/contracts)
├── Layer 6: Mobile (Flutter, offline, field sync)
└── Layer 7: Orchestration (LangGraph M1→M9, dispatch, learning loop)
```

---

## FAZA 0 — DISCOVER (Taski 1–40)

### Obszar 1: Analiza rynku i konkurencji (1–10)
1. Analiza konkurencji — 8 systemów PL (Budimex, Strabag narzędzia, BZP boty)
2. Mapa segmentów klientów — mikro (<20 os), SMB (20-200), enterprise (200+)
3. Wywiad z 5 PM budowlanymi — pain points przetargowe
4. Analiza CPV top-50 (roboty ziemne PL 2023-2025) — wolumeny, progi
5. Benchmarking UX — 3 konkurentów (Procore, PlanRadar, eBuilder)
6. Regulatory scan — PZP 2024 nowelizacja, KSeF dla budownictwa
7. Analiza NPS potencjalnych klientów (ankieta 20 firm)
8. TAM/SAM/SOM — rynek oprogramowania budowlanego PL 2026-2030
9. Pricing benchmark — subskrypcje SaaS budownictwo PL/EU
10. Feature gap analysis vs top-3 konkurentów

### Obszar 2: User Research (11–20)
11. Journey map — Kierownik Przetargów (odkrycie → złożenie oferty)
12. Journey map — Prezes SMB budowlanej (decyzja go/no-go)
13. Journey map — Kosztorysant (wycena → zatw. oferty)
14. Journey map — Kierownik Budowy (logistyka placu)
15. Job stories — Zwiad: "Gdy widzę nowy przetarg BZP, chcę..."
16. Job stories — Kosztorys: "Gdy muszę wycenić roboty ziemne, chcę..."
17. Job stories — Decyzja: "Gdy mam go/no-go deadline, chcę..."
18. Personas — 5 archetypów użytkowników (z cytatami)
19. Pain points ranking — top-20 problemów (RICE scoring)
20. Accessibility audit — WCAG 2.1 AA wymagania dla UI

### Obszar 3: Domain Expert Input — Budownictwo (21–30)
21. Taksonomia CPV dla robót ziemnych (45112xxx) — pełna mapa
22. Słownik terminów budowlanych PL → model danych
23. Axiom corpus L1 — zbiór 50 reguł check-list klasy C
24. Wzorzec kosztorysu inwestorskiego (KNR, KNNR) → schemat
25. Wzorzec kosztorysu ofertowego (SEKOCENBUD) → schemat
26. Rate card — katalog stawek maszynowych 2026 (Dolny Śląsk baseline)
27. Masa ziemna — baza przeliczników (luzowanie, wskaźnik Proctora)
28. Specyfikacja robót ziemnych — typowe klauzule SIWZ/SWZ
29. Harmonogram prac — format MS Project vs. Terra format
30. Dokumenty przetargowe PL — taksonomia (PFU, SIWZ, OPZ, PT, PB, PW)

### Obszar 4: Techniczny Discovery (31–40)
31. API audit — BZP API v3 (wszystkie endpointy, limity, błędy)
32. API audit — TED (EU Open Data, format JSON, pagination)
33. NBP API — stabilność, fallback, cache strategy
34. GUS BDL — jakie dane ekonomiczne dostępne per region
35. KRS API — weryfikacja wykonawców, rate limits
36. SMSAPI / Twilio — koszt, reliability, GDPR compliance
37. OCR benchmark — Tesseract vs. Gemma vs. Claude Vision (przedmiary)
38. clingo performance — max axiomów, czas solve przy 200 przetargach
39. OR-Tools benchmark — max assignments, solve time dla 50 wykonawców
40. LangGraph vs. Airflow vs. Prefect — wybór orchestratora M9

---

## FAZA 1 — STRATEGIZE (Taski 41–100)

### Obszar 5: Architektura (41–55)
41. ADR-001: Monolith vs. microservices (decyzja + uzasadnienie)
42. ADR-002: FastAPI sync vs. async — wybór dla IO-heavy endpoints
43. ADR-003: pgvector vs. Qdrant vs. Weaviate — embedding store
44. ADR-004: Celery vs. ARQ vs. RQ — task queue dla ingestion
45. ADR-005: JWT vs. session tokens — auth dla multi-tenant
46. ADR-006: S3 vs. local vs. Cloudflare R2 — document storage
47. ADR-007: WebSocket vs. SSE vs. polling — real-time UI updates
48. ADR-008: LangGraph vs. custom orchestrator — M9 wiring
49. ADR-009: Flutter vs. React Native vs. PWA — mobile M8
50. ADR-010: Tauri vs. Electron vs. web-only — desktop M9
51. Diagram C4 — Context (Terra.OS w ekosystemie PZP/NBP/GUS)
52. Diagram C4 — Container (API, UI, Mobile, DB, Queue, Storage)
53. Diagram C4 — Component (Router breakdown per domain)
54. Diagram sekwencji — ingest → analyze → estimate → engine → decision
55. Diagram ER — finalne 60 tabel (delta od obecnego schema)

### Obszar 6: DB Schema rozszerzenia (56–70)
56. Tabela `rate_card` — stawki maszynowe + robocizna per region/rok
57. Tabela `axiom` — corpus L1, version, active flag, last_tested
58. Tabela `plan_header` + `plan_assignment` — OR-Tools output
59. Tabela `equipment` — maszyny, availability calendar, cost_hour
60. Tabela `employee` — competency[], availability[], assignment_history
61. Tabela `contract` — powiązanie tender→plan→faktura
62. Tabela `mobile_device` — rejestracja urządzeń Flutter
63. Tabela `field_status` — offline queue, sync_at, conflict_resolution
64. Tabela `learning_event` — feedback po zamknięciu kontraktu
65. Tabela `notification` — kanały (email, SMS, push), delivery log
66. Tabela `api_key` — zakres, expiry, usage_counter
67. Tabela `billing_subscription` — Stripe webhook integration
68. Tabela `gdpr_consent` — art.13 RODO per user
69. Tabela `audit_log` — immutable, append-only per tenant
70. Alembic migration plan — 56-69 jako jednoatomowa migracja M7

### Obszar 7: Multi-tenant architecture (71–80)
71. Tenant isolation strategy — Row-Level Security (RLS) w PostgreSQL
72. RLS policies — CREATE POLICY dla każdej tabeli wrażliwej
73. Tenant provisioning flow — rejestracja → org → pierwszy user
74. Subdomain routing — `{slug}.terra-os.pl` plan
75. Tenant settings — logo, brandy, limits (tender count, users)
76. Cross-tenant search (admin panel) — bezpieczny bypass RLS
77. Tenant data export (GDPR art.20) — pełny eksport JSON/ZIP
78. Tenant deletion (GDPR art.17) — cascade, audit trail
79. Demo tenant — izolacja, auto-reset cron co 24h
80. Rate limiting per tenant — Redis + slowapi middleware

### Obszar 8: Sprint Plan (81–100)
81. Sprint 1 (tydz 1-2): M5 L2 Monte Carlo — dokończenie + testy
82. Sprint 2 (tydz 3-4): M6 Email broker + RFQ flow
83. Sprint 3 (tydz 5-6): Multi-tenancy RLS + billing Stripe
84. Sprint 4 (tydz 7-8): M7 Module 3 core (OR-Tools scaffold)
85. Sprint 5 (tydz 9-10): M7 — equipment/employees/logistics optimizer
86. Sprint 6 (tydz 11-12): M8 Flutter — scaffold + offline + field sync
87. Sprint 7 (tydz 13-14): M8 Flutter — maps, photos, drawings
88. Sprint 8 (tydz 15-16): M9 LangGraph orchestration M1→M6
89. Sprint 9 (tydz 17-18): M9 Tauri desktop + auto-update
90. Sprint 10 (tydz 19-20): Hardening — load tests, observability
91. Sprint 11 (tydz 21-22): Launch prep — onboarding, docs, pricing
92. Sprint 12 (tydz 23-24): Beta launch — 3 klientów pilotażowych
93. OKR Q3 2026: 3 beta clients, 100% M0-M6 coverage, 80% test coverage
94. OKR Q4 2026: 10 paying clients, M7-M9 GA, App Store submission
95. OKR Q1 2027: 50 clients, 1M ARR run-rate, Series A deck ready
96. KPI dashboard definicja — DAU, MAU, activation rate, churn
97. Pricing tiers: Starter (299/mies), Pro (799/mies), Enterprise (custom)
98. Feature flags — LaunchDarkly vs. own (Redis-backed flags)
99. DECISIONS.md — template + initial entries
100. CHANGELOG.md — format, automation plan

---

## FAZA 2 — SCAFFOLD (Taski 101–140)

### Obszar 9: CI/CD & DevOps (101–115)
101. GitHub Actions — workflow: lint + typecheck + pytest (offline)
102. GitHub Actions — workflow: build Docker image + push ECR
103. GitHub Actions — workflow: deploy staging (auto on main merge)
104. GitHub Actions — workflow: deploy prod (manual approval gate)
105. Docker Compose prod — API + UI + Nginx + Redis + Postgres
106. Dockerfile API — multi-stage, Python 3.12, non-root user
107. Dockerfile UI — Next.js standalone output, <50MB image
108. Health checks — `/health/live`, `/health/ready`, `/health/detailed`
109. Secrets management — AWS Secrets Manager / Vault integration
110. Environment parity — dev/staging/prod config matrix
111. Database backup — pg_dump cron, S3 upload, retention 30d
112. Monitoring — Prometheus metrics export (FastAPI middleware)
113. Alerting — Grafana Cloud alerty (API 500s, DB slow queries)
114. Log aggregation — Loki / CloudWatch structured JSON logs
115. SLA definition — 99.5% uptime, p99 < 500ms API response

### Obszar 10: Security hardening (116–130)
116. OWASP Top 10 audit — bieżący kod vs. checklist
117. SQL injection protection — SQLAlchemy parameterized queries audit
118. XSS protection — Content Security Policy headers w Caddy
119. CSRF protection — SameSite cookies + double-submit token
120. Rate limiting — 100 req/min per IP na auth endpoints
121. JWT rotation — refresh token flow, 15min access / 7d refresh
122. Secrets scanning — truffleHog w CI, pre-commit hook
123. Dependency audit — pip-audit + npm audit w CI (weekly)
124. Pentest scope — zdefiniowanie zakresu dla zewnętrznego audytora
125. GDPR compliance check — art.13 notice, consent log, DPA template
126. RODO — rejestr czynności przetwarzania (RCP) dla Terra.OS
127. Art.50 PZP — disclosure requirement w UI (AI-generated content)
128. AI literacy doc — użytkownicy Terra.OS (wymagane przez EU AI Act)
129. Backup encryption — AES-256 dla backupów DB
130. Incident response plan — runbook (breach, outage, data leak)

### Obszar 11: Design System (131–140)
131. Token system — kolory (earth palette), typografia, spacing, shadows
132. Component library — Button, Input, Select, Modal, Toast (Storybook)
133. DataTable component — sortowanie, paginacja, filtrowanie (reusable)
134. Form components — React Hook Form + Zod validation wrappers
135. Chart components — Recharts wrapper z Terra.OS theme
136. Map component — Leaflet + OpenStreetMap dla lokalizacji przetargów
137. PDF export component — react-pdf template (kosztorys, decyzja)
138. Excel import component — drop zone + parser + preview table
139. Mobile-responsive breakpoints — sidebar collapse, table scroll
140. Dark mode — Tailwind class strategy, prefers-color-scheme

---

## FAZA 3 — BUILD (Taski 141–320)

### Obszar 12: M5 — Engine L2 Monte Carlo (141–160)
141. `MonteCarloSampler` class — Sobol quasi-random sequences (scipy)
142. Bayesian priors — prior distributions per cost category (unit tests)
143. L1 constraint enforcer — każda próbka respektuje hard axioms
144. Win probability estimator — logistic regression vs. price ratio
145. Sensitivity analysis — Sobol indices (S1, S2, total) per cost driver
146. `risk{}` block w `EngineResult` — p10/p50/p90, win_prob, drivers
147. `/engine/run` endpoint — integracja L1+L2 w jednym callout
148. Seed-determinism test — `test_l2_deterministic_under_seed()`
149. Monotonicity test — `test_win_prob_monotone_vs_price()`
150. No-violation test — żadna próbka nie narusza hard constraints
151. Golden fixture — M5 (fixed seed → expected p10/p50/p90)
152. Performance test — L2 ≤ 2s dla 10,000 próbek
153. Cache L2 results — Redis z TTL 1h (kosztowne obliczenia)
154. UI — SilnikPage risk chart (p10/p50/p90 violin plot)
155. UI — win_prob display z gauge / speedometer component
156. UI — sensitivity waterfall chart (top-5 cost drivers)
157. UI — "Czy ta cena jest do obrony?" — plain-text wyjaśnienie
158. API — `/engine/explain` — LLM-generated reasoning (gated)
159. E2E test — estimate → engine → risk distribution → UI render
160. M5 DoD gate — wszystkie acceptance testy zielone

### Obszar 13: M6 — Email broker + RFQ (161–185)
161. IMAP poller — asyncio loop, IDLE support, multi-account
162. Email parser — regex + LLM extract (cena, termin, warunki płatności)
163. RFQ template engine — Jinja2 + tenant logo merge
164. RFQ send — gated (requires explicit user confirm), audit log
165. RFQ reply tracker — status: sent/viewed/replied/expired
166. `/rfq` POST — create RFQ draft (no send without confirm)
167. `/rfq/{id}/send` PUT — explicit gate (returns 402 if not confirmed)
168. `/rfq/{id}/replies` GET — parsed replies list
169. Chat brain edits — structured JSON patch z NLP intents
170. Variable sidebar — PATCH `/estimates/{id}/params` (live recalc)
171. Live rule-violation check — WebSocket push na każdy PATCH
172. Auto-fill draft — `/tenders/{id}/autofill` (gated, returns diff)
173. Email webhook — incoming email → queue → parser
174. Unit tests — email parser (10 fixture emails)
175. Unit tests — RFQ send gate (cannot send without confirm)
176. Integration test — RFQ round-trip (gated send → fixtured reply)
177. UI — RfqPage refactor (send button disabled until confirmed)
178. UI — email thread viewer (replies with parse preview)
179. UI — chat edits panel w KosztorysPage
180. UI — live violation badges na line items
181. UI — auto-fill diff viewer (before/after + accept/reject)
182. E2E test M6 — estimate → engine → RFQ draft → confirm → send
183. Security test — no email sent without explicit user action
184. Load test — 100 concurrent IMAP pollers
185. M6 DoD gate — acceptance A2 zielone

### Obszar 14: Multi-tenancy + Billing (186–210)
186. RLS enable — `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` (wszystkie)
187. RLS policies — `CREATE POLICY` per tabela (CRUD breakdown)
188. Tenant middleware — `set_config('app.current_tenant', tid)` per request
189. Tenant provisioning endpoint — POST `/tenants` → org + admin user
190. Stripe integration — Product catalog (3 plany)
191. Stripe webhook handler — checkout.session.completed → activate plan
192. Stripe webhook handler — invoice.payment_failed → grace period
193. Stripe customer portal — self-service upgrade/downgrade/cancel
194. Billing middleware — check subscription status per request
195. Usage tracking — tender count per tenant per month
196. Overage logic — soft limit (warning) + hard limit (block ingest)
197. Admin panel — tenant list, usage, ARR, churn indicators
198. Tenant self-service — settings page (logo, name, users, billing)
199. User invitation flow — email invite + accept link
200. Role system — Owner, Admin, Kosztorysant, Readonly (4 roles)
201. API keys management — create, revoke, scope, usage log
202. GDPR export endpoint — `/tenants/{id}/export` → ZIP + JSON
203. GDPR delete endpoint — DELETE `/tenants/{id}` → cascade + audit
204. Multi-tenant tests — RLS isolation (Tenant A cannot see Tenant B data)
205. Demo tenant auto-reset — cron job `/admin/reset-demo` (24h)
206. UI — PricingPage integration z Stripe Checkout redirect
207. UI — SettingsPage billing tab (plan, usage, invoices)
208. UI — user management table (invite, remove, role change)
209. Multi-tenant load test — 50 concurrent tenants, RLS performance
210. Billing DoD gate — Stripe end-to-end test (sandbox)

### Obszar 15: M7 — Module 3 / Mózg (211–250)
211. Tabela `equipment` migration — create + seed (10 maszyn baseline)
212. Tabela `employee` migration — create + seed (20 pracowników)
213. Tabela `plan_header` + `plan_assignment` migration
214. Tabela `contract` migration — powiązanie tender→plan→faktura
215. `/resources/equipment` CRUD — list, create, update, availability
216. `/resources/employees` CRUD — list, create, competency update
217. Availability calendar — equipment downtime, employee leaves
218. OR-Tools CP-SAT solver — model przynaleźności maszyna/operator
219. Constraint: competency match — operator musi mieć certyfikat
220. Constraint: availability window — nie w dni niedostępności
221. Constraint: no double-assignment — 1 maszyna = 1 kontrakt na raz
222. Objective: minimize total cost (stawki maszynowe + robocizna)
223. `/plans` POST — trigger OR-Tools solve (async task)
224. `/plans/{id}` GET — status (solving/feasible/infeasible) + result
225. Infeasibility explainer — co blokuje rozwiązanie (unmet constraints)
226. Fixture test — 2 kontrakty / 7 pracowników / ograniczone koparki
227. Infeasibility test — over-constrained fixture → `engine_infeasible`
228. Performance test — OR-Tools ≤ 5s dla 50 pracowników / 20 maszyn
229. UI — LogistykaPage — mapa przetargów + dostępne zasoby
230. UI — calendar view — oś czasu przydziałów (Gantt-like)
231. UI — equipment list z availability indicators
232. UI — employee roster z kompetencjami i dostępnością
233. UI — plan detail — przydziały + koszt total
234. UI — infeasibility alert z wyjaśnieniem (plain text)
235. Rate card editor — UI do zarządzania stawkami per region
236. `/rate-card` CRUD — list, create, update, import CSV
237. Rate card versioning — historyczne stawki (kosztorys snapshot)
238. Contract tracking — tender → plan → execution → close
239. Learning event — po zamknięciu kontraktu (actual vs. estimate delta)
240. Learning loop seeder — na podstawie historycznych kontraktów
241. `/contracts` CRUD + status workflow (draft/active/closed)
242. Invoice integration — faktura VAT → kontrakt → cashflow
243. Cashflow projection — prognoza 12-miesięczna per tenant
244. UI — DecyzjaPage upgrade — powiązanie z planem + kontraktem
245. UI — cashflow chart (Recharts) z projected vs. actual
246. M7 fixture suite — pełne testy acceptance T-M7
247. M7 performance suite — OR-Tools benchmark (10/50/200 workers)
248. M7 integration test — end-to-end tender→plan→contract
249. Code review M7 — security (RLS, input validation, rate limits)
250. M7 DoD gate — acceptance T-M7 zielone

### Obszar 16: API jakość + testy (251–280)
251. Pydantic v2 migration — wszystkie Schematy (Response/Request)
252. OpenAPI spec — `openapi.json` export + Swagger UI `/docs`
253. Async SQLAlchemy — migracja sync→async dla heavy endpoints
254. Connection pool tuning — pool_size=20, max_overflow=10
255. Query optimization — EXPLAIN ANALYZE na top-10 slow queries
256. Index audit — brakujące indeksy (tenant_id, match_score, deadline)
257. N+1 query fix — selectinload() dla relacji w `/tenders` list
258. Endpoint response time — p99 < 200ms dla listy przetargów
259. Test coverage — pytest coverage ≥ 80% (wszystkie routery)
260. Unit tests — engine L1 (każdy axiom ma test)
261. Unit tests — engine L2 (seed, monotonicity, no-violation)
262. Unit tests — estimator (sum reconciliation, variant A vs B)
263. Unit tests — email parser (10 fixtures)
264. Integration tests — ingest → analyze → estimate → engine
265. Integration tests — multi-tenant RLS (A nie widzi B)
266. Integration tests — billing lifecycle (Stripe sandbox)
267. E2E tests — A1 full offline (ingest→estimate→compare)
268. E2E tests — A2 full (A1 + engine + RFQ round-trip)
269. Load tests — k6 (100 concurrent users, 10min, p99 < 500ms)
270. Chaos test — DB connection drop → graceful degradation
271. API versioning — `/api/v1` frozen, `/api/v2` current, `/api/v3` beta
272. Deprecation notices — `Deprecation` header na v1 endpoints
273. Error response standard — `{code, message, detail, request_id}`
274. Request ID middleware — `X-Request-ID` header propagation
275. Idempotency keys — POST endpoints (ingest, RFQ send)
276. Webhook retry — exponential backoff (3 retries, max 24h)
277. API changelog — każda breaking zmiana dokumentowana
278. API SDK — Python client auto-generated z OpenAPI
279. API SDK — TypeScript client auto-generated (orval)
280. API docs — Mintlify / Readme.io setup

### Obszar 17: Frontend jakość + nowe strony (281–320)
281. TypeScript strict mode — `strict: true` w tsconfig, zero `any`
282. ESLint rules — `@typescript-eslint/recommended-strict`
283. Prettier config — formatowanie, import ordering
284. Storybook — setup + 20 komponentów z dokumentacją
285. Vitest — unit testy komponentów (coverage ≥ 60%)
286. Playwright E2E — login + dashboard + tender detail flow
287. Playwright E2E — kosztorys create + engine run + decision
288. Bundle analyzer — next-bundle-analyzer, cel < 200KB initial JS
289. Core Web Vitals — LCP < 2.5s, FID < 100ms, CLS < 0.1
290. Image optimization — next/image dla wszystkich assetów
291. Nowa strona: `ImportPage` refactor — Excel drag-drop + preview
292. Nowa strona: `ReportsPage` — generowanie raportów PDF
293. Nowa strona: `TeamPage` — zarządzanie użytkownikami + rolami
294. Nowa strona: `BillingPage` — Stripe portal embed + faktury
295. Nowa strona: `AuditLogPage` — immutable log per tenant
296. Nowa strona: `LearningPage` — historia kontraktów + deltas
297. Nowa strona: `ResourcesPage` — sprzęt + pracownicy + availability
298. Nowa strona: `ContractsPage` — kontrakt tracker + cashflow
299. Nowa strona: `AdminPage` (owner-only) — tenant management
300. DashboardPage upgrade — real analytics cards (nie mock)
301. ZwiadPage upgrade — advanced filters (CPV tree, value range)
302. KosztorysPage upgrade — live violation badges + chat edits
303. SilnikPage upgrade — L2 risk charts (violin + waterfall)
304. DecyzjaPage upgrade — decision audit trail + signatories
305. PipelinePage upgrade — Kanban drag-drop (status update)
306. AnalyticsPage upgrade — real win-rate trend (nie mock)
307. PogodaPage upgrade — forecast 14d + impact alerts
308. Asystent AI — ChatPanel upgrade (SSE streaming response)
309. Onboarding flow — 5-step wizard (org setup + first tender)
310. Empty states — każda strona ma sensowny empty state
311. Error boundaries — per-page error boundary z retry
312. Loading skeletons — zamiast spinnerów (wszystkie heavy pages)
313. Keyboard navigation — Tab flow, ARIA labels, focus traps
314. Mobile responsive — wszystkie strony (375px baseline)
315. Toast notifications — unified system (success/error/warning/info)
316. Confirmation dialogs — destructive actions (delete, send email)
317. Help tooltips — tooltips na skomplikowanych polach
318. Shortcuts — Ctrl+K command palette (search + navigation)
319. Print styles — `/kosztorys/{id}/print` → CSS @media print
320. SEO — meta tags, og:image, canonical URLs (marketing pages)

---

## FAZA 4 — HARDEN (Taski 321–370)

### Obszar 18: M8 — Flutter Mobile (321–345)
321. Flutter project scaffold — `terra_mobile/` w monorepo
322. Flutter CI — GitHub Actions (flutter analyze + test)
323. Device registration — `/mobile/register` endpoint + Flutter flow
324. Auth flow — JWT token z backend, secure storage (flutter_secure_storage)
325. Plan fetch — `GET /plans/{id}` → local Drift DB cache
326. Offline mode — plan dostępny bez sieci (Drift SQLite)
327. Map pins — Leaflet WebView lub `flutter_map` + pin per przetarg
328. Navigation — turn-by-turn link (Google Maps / Apple Maps deeplink)
329. Photos — kamera → resize → upload S3 (gated, offline queue)
330. Drawings — PDF viewer (flutter_pdfview) z annotacje overlay
331. Field status update — zmiana statusu (gated) → offline queue
332. Sync on reconnect — queue drain → backend PATCH
333. Conflict resolution — "last write wins" z notification użytkownikowi
334. Push notifications — FCM/APNs (plan dispatch, status change)
335. Biometric auth — Face ID / fingerprint dla szybkiego logowania
336. Dark mode — Flutter MaterialApp z SystemUiOverlayStyle
337. Accessibility — TalkBack / VoiceOver support (semantic labels)
338. Unit tests — Drift queries (offline CRUD)
339. Widget tests — plan detail screen (offline data)
340. Integration test — register device → fetch plan → update status → sync
341. Performance test — plan load < 1s offline
342. App store preparation — icons, screenshots, privacy policy
343. iOS build — Xcode + certificates + TestFlight
344. Android build — AAB + Play Console internal testing
345. M8 DoD gate — `flutter analyze` clean + T-M8 tests green

### Obszar 19: M9 — LangGraph Orchestration (346–360)
346. LangGraph scaffold — `packages/orchestrator/` moduł
347. Node M1 — IngestNode (trigger ingest, wait for completion)
348. Node M2 — AnalysisNode (trigger analyze, wait for RAG summary)
349. Node M3 — EstimateNode (trigger estimate A+B, wait for both)
350. Node M4/M5 — EngineNode (L1+L2, collect EngineResult)
351. Node M6 — DecisionNode (gated: human-in-loop przed RFQ send)
352. LangGraph state — `TenderPipeline` state schema (Pydantic)
353. Checkpointing — SQLite checkpointer (durable pipeline state)
354. Error recovery — retry node na transient failures (max 3)
355. Human-in-loop gate — `interrupt_before=["DecisionNode"]`
356. Observability — LangSmith tracing / self-hosted trace log
357. `/pipeline/run` POST — trigger full pipeline dla tender_id
358. `/pipeline/{id}/status` GET — current node, state, artifacts
359. `/pipeline/{id}/resume` POST — human approve decision node
360. M9 orchestration tests — full pipeline fixture (offline, mocked LLMs)

### Obszar 20: Tauri Desktop + Packaging (361–370)
361. Tauri setup — `apps/desktop/` wrapping UI build
362. Auto-update — Tauri updater + GitHub Releases
363. First-run setup wizard — DB connection, license key, offline mode
364. System tray — notifications + quick open
365. Windows installer — NSIS .exe build w CI
366. macOS DMG — code signing + notarization
367. Linux AppImage — CI build
368. Offline license validation — no-phone-home mode (enterprise)
369. Data sync toggle — cloud vs. local-only mode selection
370. Tauri tests — install → first-run → open app → render check

---

## FAZA 5 — LAUNCH (Taski 371–410)

### Obszar 21: Go-to-Market (371–385)
371. Landing page — terra-os.pl (osobne repo, Astro)
372. Landing sections — hero, features, pricing, testimonials, CTA
373. Blog — pierwszy post "Jak AI zmienia przetargi budowlane w Polsce"
374. Case study template — format (problem → rozwiązanie → wynik)
375. Demo video — 3-minutowy screencast (Loom + edycja)
376. Product Hunt launch kit — tagline, screenshots, hunter outreach
377. LinkedIn strategy — 12-tygodniowy plan postów (Mateusz + QA10)
378. Cold email sequence — 500 firm budowlanych PL (targeting CPV 45112)
379. ClickUp CRM — pipeline "Terra.OS Beta" (5 etapów, 50 leadów)
380. Partner program — integratorzy BIM/CAD (2-3 firmy PL)
381. PR — branżowe media (Builder, Murator, Property Design)
382. SEO content plan — 20 artykułów (przetargi budowlane + AI)
383. YouTube — kanał "Terra.OS Academy" (how-to seria)
384. Webinar — "AI w przetargach publicznych" (50 zapisanych cel)
385. Trial onboarding email sequence — 7-dniowy drip (Mailerlite)

### Obszar 22: Onboarding + Support (386–400)
386. Onboarding checklist — 5 kroków do pierwszego go/no-go
387. In-app guidance — Shepherd.js guided tour (per moduł)
388. Knowledge base — Mintlify (20 artykułów helpdesk)
389. Video tutorials — 10 x 5-min screencasts (każdy moduł)
390. Changelog page — `terra-os.pl/changelog` (public)
391. Status page — `status.terra-os.pl` (Uptimerobot / Betterstack)
392. Support chat — Crisp / Intercom embed w UI
393. Ticket routing — support@terra-os.pl → ClickUp task
394. SLA response times — Starter 48h, Pro 24h, Enterprise 4h
395. Beta feedback form — w UI po każdej sesji (NPS + open text)
396. Bug report flow — "Zgłoś błąd" button → GitHub Issues
397. Customer success playbook — onboarding week 1/2/4/8
398. Churn prevention — alert gdy DAU < 1 przez 7 dni
399. Feature request tracking — Canny.io lub ClickUp voting
400. Beta program agreement — NDA + data processing agreement

---

## FAZA 6 — OPERATE (Taski 401–450)

### Obszar 23: Observability + Reliability (401–415)
401. Prometheus metrics — request rate, error rate, latency per endpoint
402. Grafana dashboard — API health, DB connections, queue depth
403. Grafana dashboard — business metrics (tenants, tenders, plans)
404. AlertManager — PagerDuty/SMS dla p99 > 1s lub error rate > 1%
405. Distributed tracing — OpenTelemetry → Jaeger / Tempo
406. Real user monitoring — Sentry (frontend errors + performance)
407. Synthetic monitoring — Playwright checks co 5min (login + dashboard)
408. Capacity planning — autoscale rules (API: CPU > 70% → +1 instance)
409. DB connection pooling — PgBouncer przed PostgreSQL
410. Read replicas — PostgreSQL streaming replication (analytics queries)
411. WAF — Cloudflare WAF rules (SQLi, XSS, bot protection)
412. DDoS mitigation — Cloudflare rate rules per IP / tenant
413. Disaster recovery test — monthly restore drill z backupu
414. Runbook — API down (przyczyny, kroki naprawy, eskalacja)
415. Runbook — DB corruption (przywracanie z backup, point-in-time)

### Obszar 24: Learning Loop + AI ulepszenia (416–430)
416. Contract close event — hook na status "closed" → learning_event
417. Delta analysis — actual_cost vs. estimate_cost per kategoria
418. Prior update — Bayesian prior recalibration po 10 zamkniętych kontraktach
419. Axiom feedback — per-axiom false positive rate tracking
420. Model fine-tuning pipeline — LoRA fine-tune na domenie budowlanej
421. A/B test framework — feature flags dla nowych modeli LLM
422. Recommendation engine — "podobne przetargi wygrała firma X za Y PLN"
423. Benchmark reports — kwartalny raport win-rate dla segmentu
424. Predictive scoring — model ML (XGBoost) dla match_score
425. NLP pipeline — ekstrakcja klauzul SIWZ (clingo axiom auto-suggest)
426. Document similarity — wykrycie plagiatu/reużycia OPZ
427. Price forecasting — ARIMA na indeksach SEKOCENBUD
428. Risk model upgrade — L2 + historyczne delty kontraktów
429. Competitor intelligence — monitoring wygranych przetargów BZP
430. LLM router v2 — model selection per task (cost vs. quality tradeoff)

### Obszar 25: Skalowanie + Enterprise (431–450)
431. SSO — SAML 2.0 / Azure AD integration (enterprise tier)
432. SCIM provisioning — automatyczne zarządzanie użytkownikami
433. Custom branding — white-label UI (logo, kolory, domena)
434. Enterprise SLA — 99.9% uptime, dedicated support, private deployment
435. On-premise option — Docker Compose bundle z local LLM (Ollama)
436. Data residency — EU-only storage (GDPR enterprise)
437. Audit-ready exports — ISO 27001 / SOC 2 evidence packages
438. Multi-region deployment — EU-West + EU-Central failover
439. Enterprise trial → POC program — 30-dniowy pilot z CS support
440. Integration marketplace — ERP (SAP, Comarch), BIM (Revit, ArchiCAD)
441. Webhook API — zdarzenia (tender.matched, engine.complete, plan.ready)
442. Zapier / Make integration — no-code automations
443. Power BI connector — OData feed z Analytics API
444. Excel add-in — push kosztorys z Excel do Terra.OS
445. Mobile app v2 — tablet-optimized layout (iPad, Samsung Tab)
446. AR feature — overlay planu na zdjęciach terenowych (iOS ARKit)
447. Drone integration — import orthofoto do mapy (GeoTIFF)
448. BIM integration — IFC parser → CPV auto-classification
449. Series A readiness — data room, financial model, pitch deck
450. Terra.OS v2.0 — pełna roadmapa następnego roku (post-Series A)

---

## MATRYCA PRIORYTETÓW (RICE)

| Obszar | Reach | Impact | Confidence | Effort | RICE |
|---|---|---|---|---|---|
| M5 L2 Monte Carlo | 100% | 3 | 90% | 2 | **135** |
| Multi-tenancy RLS | 100% | 3 | 85% | 3 | **85** |
| M7 OR-Tools | 60% | 3 | 70% | 4 | **31** |
| Billing Stripe | 100% | 3 | 85% | 2 | **127** |
| M8 Flutter | 40% | 2 | 60% | 5 | **10** |
| M9 LangGraph | 80% | 3 | 70% | 4 | **42** |
| Landing page | 100% | 2 | 90% | 1 | **180** |
| Test coverage 80% | 100% | 2 | 95% | 3 | **63** |
| CI/CD full | 100% | 2 | 90% | 2 | **90** |
| Enterprise SSO | 20% | 3 | 60% | 3 | **12** |

---

## HARMONOGRAM (Gantt na poziomie fazowym)

```
2026-07-07  ████ FAZA 2 SCAFFOLD (CI/CD, Security, Design System)
2026-07-21  ████████ FAZA 3 BUILD — M5 L2 + M6 Email + Multi-tenant
2026-08-04  ████████████ FAZA 3 BUILD — M7 OR-Tools + API Quality + Frontend
2026-08-18  ████████████████ FAZA 4 HARDEN — M8 Flutter + M9 LangGraph + Tauri
2026-09-01  ████ FAZA 5 LAUNCH — GTM + Onboarding + Beta
2026-09-15  ████████████████ FAZA 6 OPERATE — Observability + Learning + Scale
2026-10-01  🚀 GA v1.0 — pierwsi płacący klienci
2027-01-01  🚀 Series A readiness — 50 klientów, 1M ARR
```

---

## AGENCI NEXUS — PRZYPISANIE

| Batch | Agent | Odpowiada za taski |
|---|---|---|
| BATCH 1 | Sprint Prioritizer | 81-100, 371-400 (roadmap + GTM) |
| BATCH 1 | Software Architect | 41-70, 251-280 (ADRs + API quality) |
| BATCH 1 | Civil Engineer | 21-30 (domain expertise + axiom corpus) |
| BATCH 2 | Backend Architect | 56-80, 141-185, 186-210 (DB + M5/M6 + multi-tenant) |
| BATCH 2 | Frontend Developer | 131-140, 281-320 (design system + UI) |
| BATCH 2 | Senior Developer | 101-130, 321-370 (CI/CD + M8 + M9) |
| BATCH 3 | AI Engineer | 141-160, 416-430 (L2 engine + learning loop) |
| BATCH 3 | Product Manager | 1-20, 431-450 (discovery + enterprise) |
| BATCH 3 | Technical Writer | 280, 386-400 (docs + support) |

---

*Plan wygenerowany przez NEXUS Orchestrator — Terra.OS 2026-07-07*
*Następne uruchomienie: BATCH 1 + BATCH 2 + BATCH 3 równolegle*
