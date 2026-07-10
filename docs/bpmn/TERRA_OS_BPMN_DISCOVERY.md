# Terra.OS — BPMN 2.0 Discovery & Process Architecture
**Wersja:** 1.0 | **Data:** 2026-07-10 | **Metodyka:** Lean + BPMN 2.0 (ISO 19510)

---

## 1. KONTEKST DISCOVERY

### 1.1 Cel
Zidentyfikować, nazwać i skategoryzować wszystkie przepływy wewnątrz platformy Terra.OS
jako procesy BPMN 2.0, wykryć straty lean (muda), zaprojektować TO-BE i wdrożyć
optymalną architekturę procesową w 4 fazach po 45 sprintów.

### 1.2 Metodyka
- **Discovery** — code-first analysis: czytamy implementację jako AS-IS model
- **Lean waste audit** — 7 mudas + 3 terra-specific
- **BPMN 2.0** — elementy: Pool, Lane, Task (User/Service/Script), Gateway (XOR/AND/OR),
  Event (Start/End/Intermediate: Timer/Message/Error/Signal), Sub-Process, Data Object,
  Annotation, Sequence Flow, Message Flow
- **Sprint = 2 tygodnie**, każda faza = 90 dni (45 × 2-tygodniowe = 22.5 mies. łącznie)

---

## 2. MAPA DOMEN (Process Architecture Level 0)

```
┌─────────────────────────────────────────────────────────────────┐
│                         TERRA.OS PLATFORM                        │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  D1: ZWIAD  │  │ D2: INTELI-  │  │  D3: DECYZJA & OFERTA  │ │
│  │  Ingestion  │→ │  GENCJA      │→ │  (Kosztorys/Wycena)    │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
│         ↓                ↓                      ↓               │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ D4: DOKU-   │  │ D5: CRM &    │  │  D6: ANALITYKA &       │ │
│  │ MENTY SWZ   │  │ RYNEK        │  │  REPORTING             │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           D0: PLATFORMA (Auth, Tenant, Billing, Audit)    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. AS-IS PROCESS INVENTORY (Discovery)

### D1 — ZWIAD / INGESTION

#### P1.1 — Daily BZP Ingest `[Automated Service Process]`
```
BPMN Pool: Terra.OS System
BPMN Lane: Ingestion Service

[Timer Start: 04:00 UTC]
  → [Script Task: Fetch BZP notices (days_back=2)]
      → [Script Task: Fetch TED EU notices]
          → [AND Gateway: parallel normalize]
              → [Service Task: normalize_bzp_notice()]
              → [Service Task: normalize_ted_notice()]
          ← [AND Join]
      → [Service Task: apply_filters(CPV + geo)]
          → [XOR Gateway: passed filter?]
              → NO → [Script Task: drop + log]
              → YES → [Service Task: score_tender()]
                        → [Service Task: upsert_tender()]
  → [Timer End]

LEAN WASTE AUDIT:
  ✗ MUDA Overprocessing: TED fetch = 7 dni wstecz, BZP = 2 dni → niespójność
  ✗ MUDA Waiting: brak retry na timeout HTTP, brak circuit-breaker
  ✗ MUDA Defects: duplicate score na re-ingest (score override bez historii)
  ✗ MUDA Inventory: bzp_documents nie fetched automatycznie po ingest
```

#### P1.2 — BIP Ingest `[Automated Service Process]`
```
BPMN Pool: Terra.OS System
BPMN Lane: BIP Connector

[Timer Start: 04:00 UTC]
  → [Script Task: load_site_index()]
      → [XOR Gateway: site index exists?]
          → NO → [Service Task: build_site_index(GROUP_GMINY + GROUP_POWIATY)]
          → YES → [Script Task: load from cache]
      → [Parallel Multi-Instance: scrape each site]
          → [Service Task: scrape RSS / HTML per site]
          → [Service Task: normalize BIP tender]
          → [Service Task: store_tenders()]
  → [Timer End]

LEAN WASTE AUDIT:
  ✗ MUDA Overproduction: max_sites=50 bez filtra regionu w default run
  ✗ MUDA Transport: site_index na dysku nie ma TTL → stale cache
  ✗ MUDA Waiting: workers=10 hardcoded, nie adaptive
```

#### P1.3 — Manual Ingest via API `[User-Triggered Service Process]`
```
BPMN Pool: Użytkownik → API
BPMN Lane: zwiad.py router

[Message Start: POST /api/v1/ingest/run]
  → [User Task: set params (days_back, include_ted, include_bip)]
      → [Call Activity: run_ingest()]  ← P1.1 + P1.2
          → [Service Task: return IngestRunResponse]
  → [Message End: 200 OK JSON]

LEAN WASTE AUDIT:
  ✗ MUDA Waiting: endpoint synchronous — blokuje HTTP 30-120s
  ✗ MUDA Defects: brak task_id, brak progress tracking, brak retry w UI
```

---

### D2 — INTELIGENCJA / TENDER INTELLIGENCE

#### P2.1 — Tender Scoring `[Automated Service Process]`
```
BPMN Pool: Terra.OS System
BPMN Lane: Scorer + DB

[Sub-Process: score_tender(tender, profile, weights)]
  → [Script Task: _cpv_score()]          → weight W1
  → [Script Task: _value_score()]        → weight W2
  → [Script Task: _region_score()]       → weight W3
  → [Script Task: _deadline_score()]     → weight W4
  → [Script Task: _cpv_win_rate_score()] → weight W5
  → [Service Task: weighted_sum → match_score]
  → [Service Task: upsert match_score to DB]

LEAN WASTE AUDIT:
  ✗ MUDA Defects: re-scoring przy każdym ingest bez wersjonowania
  ✗ MUDA Overprocessing: load_scoring_config() wywołane N razy (N=przetargi) — brak cache
  ✗ MUDA Defects: win_rate loaded per-CPV ale bez tenant-specific historii ofert
```

#### P2.2 — Alert Pipeline `[Automated Timer + Service]`
```
BPMN Pool: Terra.OS System
BPMN Lane: Alert Dispatcher

[Timer Start: co 1h (terra-alert-dispatcher.timer)]
  → [Service Task: check_new_tenders_for_alerts(since=65min)]
      → [Service Task: load active alerts per tenant]
          → [Multi-Instance: for each alert]
              → [Service Task: _match_tenders_since()]
                  → [XOR Gateway: tenders_found > 0?]
                      → NO → skip
                      → YES → [XOR Gateway: channel?]
                                  → email → [Service Task: send digest email]
                                  → webhook → [Service Task: POST webhook]
                                  → in-app → [Service Task: insert notification]
              → [Service Task: update last_fired_at]
  → [Timer End]

LEAN WASTE AUDIT:
  ✓ OK: last_fired_at zapobiega duplikatom
  ✗ MUDA Defects: SMTP niekonfigurowalny przez UI, tylko przez env
  ✗ MUDA Waiting: brak retry na failed email (hard fail, brak DLQ)
  ✗ MUDA Overprocessing: brak batch email — każdy alert = osobny SMTP connect
```

#### P2.3 — Competitor Watch `[Automated Polling]`
```
BPMN Pool: Terra.OS System  
BPMN Lane: competitor_watch.py

STATUS: [Stub — router exists, logic incomplete]

LEAN WASTE AUDIT:
  ✗ MUDA Defects: endpoint zdefiniowany ale brak implementacji background job
```

---

### D3 — DECYZJA & OFERTA

#### P3.1 — Tender Decision Flow `[User Process]`
```
BPMN Pool: Użytkownik (Handlowiec / Prezes)
BPMN Lane: decisions_v2.py

[Message Start: user views tender detail]
  → [User Task: review tender data + score]
      → [User Task: set decision (bid/no-bid/watch)]
          → [XOR Gateway: decision?]
              → bid → [User Task: create estimate request]
                        → [Call Activity: P3.2 Kosztorys]
              → watch → [Service Task: bookmark tender]
              → no-bid → [Service Task: log reason]
  → [Message End: decision saved]

LEAN WASTE AUDIT:
  ✗ MUDA Motion: brak keyboard shortcut / bulk decision w UI
  ✗ MUDA Waiting: decyzja i kosztorys to osobne ekrany — context switch
  ✗ MUDA Defects: brak automatic escalation (high-value tender → powiadomienie managera)
```

#### P3.2 — Kosztorys / Cost Estimation `[User + AI Process]`
```
BPMN Pool: Użytkownik + AI Engine
BPMN Lane: kosztorys_v2.py + intelligence/kosztorys_engine.py

[Message Start: POST /api/v1/kosztorys/v2/generate]
  → [User Task: upload SWZ document OR link BZP number]
      → [Service Task: parse_przedmiar() — extract bill of quantities]
          → [Service Task: AI: extract line items]
              → [Service Task: price_intelligence — fetch market prices]
                  → [Service Task: apply material_risk adjustments]
                      → [Service Task: generate estimate rows]
                          → [User Task: review + edit rows]
                              → [Service Task: export XLSX/DOCX]
  → [Message End: estimate ready]

LEAN WASTE AUDIT:
  ✗ MUDA Overprocessing: parse_przedmiar + AI extraction = double processing
  ✗ MUDA Waiting: brak progress SSE — user nie wie co się dzieje
  ✗ MUDA Defects: brak wersjonowania kosztorysów (v1 → v2 → final)
  ✗ MUDA Inventory: wygenerowane kosztorysy nie linkowane do przetargu w DB
```

#### P3.3 — Offer Management `[User Process]`
```
BPMN Pool: Użytkownik
BPMN Lane: offers.py

[Message Start: create offer]
  → [User Task: assign tender + kosztorys]
      → [User Task: set offer value + strategy]
          → [Service Task: calculate win_probability()]
              → [User Task: review probability + submit]
                  → [Service Task: save offer to DB]
                      → [Service Task: update CRM buyer record]
  → [Message End: offer saved]

LEAN WASTE AUDIT:
  ✗ MUDA Defects: win_probability obliczana bez historii branżowej (tylko score)
  ✗ MUDA Motion: RFQ (rfq.py) osobny flow — brak integracji z offer
```

---

### D4 — DOKUMENTY SWZ

#### P4.1 — BZP Document Fetch `[Automated + On-Demand]`
```
BPMN Pool: Terra.OS System + Użytkownik
BPMN Lane: bzp_document_scraper.py + bzp_documents.py

[XOR Start Gateway: trigger type]
  → Manual: POST /api/v1/bzp/documents/{tender_id}/fetch
  → Auto: background task po ingest

  → [Script Task: _resolve_to_bzp_number()]
      → [Script Task: list_documents() — BZP API]
          → [Parallel Multi-Instance: for each doc]
              → [Script Task: _find_valid_pdf_url()]
                  → [Service Task: _download_with_retry(max=3)]
                      → [Script Task: validate magic bytes %PDF]
                          → [Service Task: store to /var/lib/terra-os/documents/]
                              → [Service Task: _store_results() → DB]
      → [Script Task: _get_swz_platform_url() — noticeNumber query]
  → [Message End: FetchResult]

LEAN WASTE AUDIT:
  ✓ OK: noticeNumber direct query (naprawione)
  ✓ OK: retry z backoff
  ✗ MUDA Inventory: download nie triggerowany automatycznie po ingest
  ✗ MUDA Defects: brak deduplication — ten sam plik może być pobrany 2x
  ✗ MUDA Overprocessing: content TEXT w DB (duplikacja — plik jest też na dysku)
```

---

### D5 — CRM & RYNEK

#### P5.1 — Buyer CRM `[User Process]`
```
BPMN Pool: Użytkownik (Handlowiec)
BPMN Lane: buyer_crm.py

[CRUD: buyers / contacts / history]

LEAN WASTE AUDIT:
  ✗ MUDA Defects: brak auto-enrichment z KRS/GUS po NIP (krs_verify.py istnieje ale
    nie jest podłączony do CRM flow)
  ✗ MUDA Motion: buyer nie linkowany automatycznie do tender (trzeba ręcznie)
```

#### P5.2 — Market Intelligence `[Automated Polling]`
```
BPMN Pool: Terra.OS System
BPMN Lane: market_intelligence.py + market_data.py

STATUS: [Partial — endpoints exist, background polling not wired]

LEAN WASTE AUDIT:
  ✗ MUDA Defects: competitor_watch i market_intelligence = dwa overlapping moduły
```

---

### D6 — ANALITYKA & REPORTING

#### P6.1 — Dashboard Aggregation `[On-Demand Query]`
```
BPMN Pool: Użytkownik
BPMN Lane: dashboard.py + analytics_v2.py

[Message Start: GET /api/v1/dashboard]
  → [Service Task: aggregate tenders by source/cpv/region/score]
      → [Service Task: compute KPIs (win_rate, avg_score, open_count)]
          → [Service Task: return JSON]
  → [Message End: dashboard data]

LEAN WASTE AUDIT:
  ✗ MUDA Overprocessing: aggregation on every request — brak materialized view / cache
  ✗ MUDA Defects: analytics_v2 i advanced_analytics = duplikacja endpointów
```

---

## 4. LEAN WASTE SUMMARY (Muda Inventory)

| # | Muda | Kategoria | Priorytet |
|---|------|-----------|-----------|
| W1 | Ingest sync HTTP blokuje 30-120s | Waiting | P0-KRYTYCZNY |
| W2 | Scoring config ładowany N razy per run | Overprocessing | P1 |
| W3 | BZP docs nie fetched auto po ingest | Inventory | P1 |
| W4 | Dashboard aggregation on every request | Overprocessing | P1 |
| W5 | Email SMTP retry brak / DLQ brak | Defects | P1 |
| W6 | KRS/GUS nie auto-enrichment CRM | Motion | P2 |
| W7 | Kosztorys nie linkowany do tender | Defects | P2 |
| W8 | Competitor watch stub (nie działa) | Defects | P2 |
| W9 | win_probability bez historii ofert | Defects | P2 |
| W10 | bzp_documents content TEXT duplikacja | Inventory | P3 |
| W11 | analytics_v2 + advanced_analytics overlap | Overproduction | P3 |
| W12 | BIP site_index brak TTL | Inventory | P3 |

---

## 5. TO-BE PROCESS ARCHITECTURE

### Zasady projektowe (Lean Principles applied to BPMN)
1. **Pull over Push** — document fetch triggerowany przez event (ingest complete), nie polling
2. **One-piece flow** — tender przechodzi przez cały pipeline bez bufferów
3. **Zero waiting** — wszystkie long-running tasks async z SSE progress
4. **Single source of truth** — jeden rekord tender linkuje: score, documents, decisions, kosztorysy
5. **Error-first** — każdy service task ma explicit Error Boundary Event → retry → DLQ
6. **Kaizen gates** — po każdym fazie: metryki jakości procesów (throughput, error rate, latency)

### TO-BE Core Flow (Level 1 — Unified Tender Lifecycle)

```
╔══════════════════════════════════════════════════════════════════╗
║          TERRA.OS — UNIFIED TENDER LIFECYCLE (TO-BE)             ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  [Timer: 04:00]──→ INTAKE ──→ ENRICH ──→ SCORE ──→ ROUTE        ║
║                     │           │          │          │          ║
║                   fetch      doc+geo    profile    alert/        ║
║                  BZP/TED     enrichment  match     bookmark/     ║
║                  /BIP                              queue         ║
║                                                       │          ║
║                                                    DECIDE        ║
║                                                       │          ║
║                                              bid/watch/skip      ║
║                                                       │          ║
║                                              bid ──→ ESTIMATE    ║
║                                                       │          ║
║                                                  kosztorys+AI    ║
║                                                       │          ║
║                                                    OFFER         ║
║                                                       │          ║
║                                                 submit+win_prob  ║
║                                                       │          ║
║                                                   TRACK          ║
║                                                       │          ║
║                                              wynik+CRM update    ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 6. ROADMAP — 4 FAZY × 45 SPRINTÓW

### FAZA 1 — FUNDAMENT PROCESOWY (Sprinty 1–45, ~90 dni)
**Cel:** Wyeliminować P0/P1 muda, async pipeline, event-driven architecture

| Sprint | Epik | Cel BPMN | Task | 
|--------|------|----------|------|
| S01 | Async Ingest | P1.3 → async | POST /ingest/run → task_id + SSE progress |
| S02 | Async Ingest | P1.3 → task store | IngestTask model w DB, status tracking |
| S03 | Async Ingest | P1.3 → retry | Celery/ARQ task z retry + DLQ table |
| S04 | Event Bus | Event model | TenderCreated / TenderUpdated events w DB |
| S05 | Event Bus | Event dispatch | After upsert_tender → emit event |
| S06 | Auto Doc Fetch | P4.1 | Subscribe TenderCreated → fetch_documents() |
| S07 | Auto Doc Fetch | P4.1 | Async doc fetch z queue, max 5 concurrent |
| S08 | Auto Doc Fetch | P4.1 | Dedup hash check przed download |
| S09 | Scorer Cache | P2.1 | load_scoring_config() z LRU cache (TTL=5min) |
| S10 | Scorer Cache | P2.1 | Score history table — wersjonowanie match_score |
| S11 | Alert DLQ | P2.2 | alert_failed table + retry scheduler |
| S12 | Alert DLQ | P2.2 | SMTP batch — jeden SMTP session per dispatch run |
| S13 | Alert Config UI | P2.2 | SMTP settings konfigurowalny przez UI (nie env) |
| S14 | Dashboard Cache | P6.1 | Materialized view: mv_dashboard_stats |
| S15 | Dashboard Cache | P6.1 | Auto-refresh mv po ingest complete event |
| S16 | Analytics Merge | P6.1 | analytics_v2 + advanced_analytics → jeden router |
| S17 | BIP TTL | P1.2 | site_index TTL = 7 dni, auto-rebuild |
| S18 | BIP Region | P1.2 | Default filter region z tenant scoring_config |
| S19 | TED Consistency | P1.1 | TED + BZP days_back spójne (DEFAULT=7) |
| S20 | Error Boundary | All | Boundary Error Events na wszystkich Service Tasks |
| S21 | Error Boundary | All | Global error handler → audit_log table |
| S22 | Progress SSE | P3.2 | Kosztorys generation → SSE stream progress |
| S23 | Progress SSE | P1.3 | Ingest run → SSE stream (steps: fetch/norm/score) |
| S24 | Health Monitor | D0 | sources_health pełny: BZP/TED/BIP latency + uptime |
| S25 | Health Monitor | D0 | Alert jeśli source down > 30min |
| S26 | API Cleanup | All | Deprecated routers (bzp.py, analytics.py v1) → 410 |
| S27 | API Cleanup | All | OpenAPI spec audit — brakujące response schemas |
| S28 | DB Cleanup | All | content TEXT z bzp_documents → usunięcie kolumny |
| S29 | DB Cleanup | All | Indeksy audit: brakujące na match_score, deadline |
| S30 | Tenant Isolation | D0 | RLS audit — każda tabela ma tenant_id guard |
| S31 | Tenant Isolation | D0 | API middleware: tenant_id inject + validate |
| S32 | Audit Trail | D0 | audit_log: każda mutacja CUD zapisywana |
| S33 | Audit Trail | D0 | GET /audit/trail endpoint dla admina |
| S34 | Rate Limiting | D0 | Per-tenant rate limit middleware (istniejący + fix) |
| S35 | GDPR | D0 | gdpr.py — right to deletion flow end-to-end test |
| S36 | Notifications | D2 | in-app notification center — read/unread/dismiss |
| S37 | Notifications | D2 | Notification preferences per user (email/in-app/webhook) |
| S38 | Bookmarks | D3 | tender_bookmarks — collections + tags |
| S39 | Bookmarks | D3 | Bookmark → trigger alert watch |
| S40 | Search | D2 | Full-text search tender title+description (PG tsvector) |
| S41 | Search | D2 | Search filters: CPV tree, region, value range, deadline |
| S42 | Search | D2 | Search → save as alert (1-click) |
| S43 | Export | D6 | export.py — XLSX/CSV tender list z filtrami |
| S44 | Export | D6 | export.py — PDF report: scoring summary |
| S45 | Faza 1 Kaizen | All | Metryki: ingest_latency_p95, alert_fire_rate, doc_fetch% |

---

### FAZA 2 — INTELIGENCJA PRZETARGOWA (Sprinty 46–90, ~90 dni)
**Cel:** P2 muda, pełna inteligencja: scoring ML, win probability, competitor watch

| Sprint | Epik | Cel BPMN | Task |
|--------|------|----------|------|
| S46 | Win History | P3.3 | offer_result table: wyniki przetargów (won/lost/cancelled) |
| S47 | Win History | P3.3 | Import historii ofert z XLS |
| S48 | Win Probability | P3.3 | Regresja logistyczna: win_prob(score, value, cpv, region) |
| S49 | Win Probability | P3.3 | Live update po każdej nowej offer_result |
| S50 | CPV Win Rate | P2.1 | win_rate per CPV z własnych offer_results |
| S51 | CPV Win Rate | P2.1 | Competitor win_rate: z bzp_results scraper |
| S52 | Competitor Watch | P5.2 | competitor_watch — background job: nowe wyniki rywali |
| S53 | Competitor Watch | P5.2 | Alert: rywal wygrał przetarg który obserwujesz |
| S54 | Competitor Watch | P5.2 | Dashboard: udział w rynku vs konkurenci |
| S55 | Market Intel | P5.2 | market_data — ceny materiałów: live feed GUS BDL |
| S56 | Market Intel | P5.2 | market_data — trend: YoY ceny po kategorii CPV |
| S57 | Market Intel | P5.2 | Alerty cenowe: cement > X PLN/t → powiadom |
| S58 | KRS Enrichment | P5.1 | Auto-enrich buyer z krs_verify po NIP przy tworzeniu |
| S59 | KRS Enrichment | P5.1 | Periodic refresh KRS (co 30 dni) |
| S60 | GUS Enrichment | P5.1 | GUS BDL: PKD, zatrudnienie, przychód nabywcy |
| S61 | Buyer Score | P5.1 | buyer_score: wiarygodność kontrahenta (KRS+GUS+historia) |
| S62 | Buyer Score | P5.1 | Alert: nabywca z niskim buyer_score → flag w UI |
| S63 | Scoring ML v2 | P2.1 | ML model: gradient boosting na historii (betatp-style) |
| S64 | Scoring ML v2 | P2.1 | A/B test: stary scorer vs ML scorer |
| S65 | Scoring ML v2 | P2.1 | Auto-retrain co 7 dni na nowych danych |
| S66 | Doc Analysis | P4.1 | OCR SWZ: extract: wartość szacunkowa, termin, warunki |
| S67 | Doc Analysis | P4.1 | Risk extractor: czerwone flagi w SWZ (kary umowne, etc.) |
| S68 | Doc Analysis | P4.1 | Risk score → tender risk_level (low/mid/high) |
| S69 | Doc Analysis | P4.1 | Risk alert: high risk tender → powiadom managera |
| S70 | Kosztorys v3 | P3.2 | Wersjonowanie: v1/v2/final + diff view |
| S71 | Kosztorys v3 | P3.2 | Link kosztorys → tender → offer → wynik |
| S72 | Kosztorys v3 | P3.2 | AI: predict material_risk z trend GUS |
| S73 | Decision Flow | P3.1 | Bulk decision: checkbox + batch bid/no-bid |
| S74 | Decision Flow | P3.1 | Escalation: high-value → auto notify manager |
| S75 | Decision Flow | P3.1 | Deadline reminder: -7d, -3d, -1d przed terminem składania |
| S76 | RFQ Integration | P3.3 | rfq.py → offer flow: RFQ → oferta → tracking |
| S77 | RFQ Integration | P3.3 | RFQ do podwykonawców: email + status tracking |
| S78 | Subcontractors | P3.2 | Subcontractor DB z oceną + historią współpracy |
| S79 | Resources | P3.2 | resources.py: maszyny i ludzie → dostępność kalendarza |
| S80 | Resources | P3.2 | Collision detection: zasób zarezerwowany na 2 przetargi |
| S81 | GANTT | P3.2 | gantt.py: harmonogram realizacji po wygraniu |
| S82 | GANTT | P3.2 | Automatyczny GANTT z SWZ extraction + CPM |
| S83 | Phase Gate | All | Kaizen: precision@top10, recall@alerts, win_rate_delta |
| S84 | Performance | All | DB: EXPLAIN ANALYZE top 10 slow queries → fix |
| S85 | Performance | All | API: p95 latency < 200ms dla /tenders, /dashboard |
| S86 | Caching Layer | All | Redis cache layer: tender detail, dashboard, score |
| S87 | Caching Layer | All | Cache invalidation po ingest event |
| S88 | Load Test | All | Locust: 100 concurrent users → no degradation |
| S89 | Security | D0 | Pen test: OWASP Top 10 audit |
| S90 | Faza 2 Kaizen | All | Metryki: ML_score_corr, win_pred_accuracy, doc_risk_recall |

---

### FAZA 3 — AUTOMATYZACJA PRZEPŁYWÓW (Sprinty 91–135, ~90 dni)
**Cel:** Wdrożyć BPMN engine wewnątrz platformy, automation flows, multi-tenant SaaS

| Sprint | Epik | Cel BPMN | Task |
|--------|------|----------|------|
| S91 | BPMN Engine | Core | Wybór silnika: n8n (istnieje n8n_client.py) vs custom |
| S92 | BPMN Engine | Core | n8n integration: webhook trigger per event type |
| S93 | BPMN Engine | Core | Workflow designer UI: visual BPMN editor (bpmn.js) |
| S94 | Automation Core | automations.py | Condition builder: IF tender.cpv IN [...] AND score > 0.7 |
| S95 | Automation Core | automations.py | Action library: email/webhook/bookmark/decision/task |
| S96 | Automation Core | automations.py | Trigger library: TenderCreated/ScoreUpdated/DeadlineNear |
| S97 | Auto Workflows | D2 | Workflow: High Score → Auto bookmark + alert |
| S98 | Auto Workflows | D2 | Workflow: SWZ pobrany → OCR → risk check → flag |
| S99 | Auto Workflows | D3 | Workflow: Deadline -7d → remind → force decision |
| S100 | Auto Workflows | D3 | Workflow: Decision:bid → create kosztorys draft |
| S101 | Auto Workflows | D5 | Workflow: Offer won → create project → GANTT |
| S102 | Auto Workflows | D5 | Workflow: Offer lost → update win_rate → competitor note |
| S103 | Multi-Tenant | D0 | Tenant onboarding flow: signup → org → config → first ingest |
| S104 | Multi-Tenant | D0 | Tenant isolation audit: żaden wyciek danych między tenantami |
| S105 | Multi-Tenant | D0 | Per-tenant scoring config UI (CPV tree, regiony, wagi) |
| S106 | Billing Flow | D0 | billing.py: plan limits enforcement (tenders/mo, users/org) |
| S107 | Billing Flow | D0 | Upgrade flow: Stripe checkout → unlock features |
| S108 | Billing Flow | D0 | Usage tracking: tenders_viewed, api_calls, doc_downloads |
| S109 | API v3 | All | REST → HATEOAS + webhooks register/manage |
| S110 | API v3 | All | Websocket: real-time tender feed per tenant |
| S111 | API v3 | All | Public API: rate-limited, API key auth, dokumentacja |
| S112 | Integrations | D5 | HubSpot CRM sync: offer → deal |
| S113 | Integrations | D5 | Pipedrive sync: przetarg → pipeline stage |
| S114 | Integrations | D5 | Slack/Teams: alert → channel message |
| S115 | Integrations | D5 | Zapier/Make webhook connector |
| S116 | Mobile Ready | All | API response optimization dla mobile (field masks) |
| S117 | Mobile Ready | All | PWA: push notifications dla alertów |
| S118 | Reporting | D6 | Monthly report: tender activity, win rate, pipeline value |
| S119 | Reporting | D6 | PDF report generator: zarząd summary |
| S120 | Reporting | D6 | Benchmark: wyniki vs branża (aggregate anonymized) |
| S121 | AI Assistant | All | Chat: "pokaż mi przetargi budowlane śląskie > 500k" |
| S122 | AI Assistant | All | Chat: "ile mam szans na wygranie tego przetargu?" |
| S123 | AI Assistant | All | Chat: "generuj kosztorys dla tego SWZ" |
| S124 | AI Assistant | All | SSE streaming chat (sse_mcp_chat.py → produkcja) |
| S125 | Data Quality | All | DQ rules: tender bez CPV, bez wartości, bez deadline → flag |
| S126 | Data Quality | All | DQ dashboard: completeness score per source |
| S127 | Observability | All | OpenTelemetry: traces + metrics + logs |
| S128 | Observability | All | Grafana dashboard: system health + business KPIs |
| S129 | Observability | All | SLA alerts: ingest_lag > 6h → PagerDuty/email |
| S130 | DR & Backup | D0 | DB backup: daily pg_dump → S3 |
| S131 | DR & Backup | D0 | Restore test: automated weekly DR drill |
| S132 | Feature Flags | All | Feature flag system: gradual rollout nowych flows |
| S133 | AB Testing | D2 | A/B framework: scoring algo, UI decyzja flow |
| S134 | Compliance | D0 | RODO audit + DPA template |
| S135 | Faza 3 Kaizen | All | NPS, time-to-decision, automation_coverage% |

---

### FAZA 4 — SKALOWALNOŚĆ & DOSKONAŁOŚĆ (Sprinty 136–180, ~90 dni)
**Cel:** Platform excellence, marketplace, AI-native, scale-out

| Sprint | Epik | Cel BPMN | Task |
|--------|------|----------|------|
| S136 | Microservices | Arch | Wydzielenie Ingestion Service jako osobny kontener |
| S137 | Microservices | Arch | Wydzielenie AI/Intelligence Service |
| S138 | Microservices | Arch | Event mesh: Kafka/Redpanda między serwisami |
| S139 | Microservices | Arch | Service mesh: mTLS między serwisami |
| S140 | Multi-Region | Arch | Geo-routing: PL tenant → PL region, EU tenant → EU |
| S141 | Multi-Region | Arch | Data residency: GDPR compliance per region |
| S142 | ML Platform | D2 | Feature store: cechy przetargów (365d sliding window) |
| S143 | ML Platform | D2 | Model registry: versioned scoring models per tenant |
| S144 | ML Platform | D2 | Online learning: score updates w real-time po wyniku |
| S145 | NLP Extraction | D4 | NLP pipeline: SWZ → structured data (NER + RE) |
| S146 | NLP Extraction | D4 | Clause extraction: warunki, kary, terminy |
| S147 | NLP Extraction | D4 | Q&A: pytaj o SWZ w języku naturalnym |
| S148 | Marketplace | New | Tender marketplace: wyszukiwanie + subskrypcja publiczna |
| S149 | Marketplace | New | Partner network: biuro rachunkowe → dostęp dla klientów |
| S150 | Marketplace | New | White-label: platforma pod brandem partnera |
| S151 | Data Products | D6 | Data API: agregaty branżowe do sprzedaży |
| S152 | Data Products | D6 | Benchmark SaaS: "jak wypadasz vs branża" subscription |
| S153 | Process Mining | All | Process mining: rzeczywiste vs modelowe BPMN flows |
| S154 | Process Mining | All | Conformance checking: wykrywanie dewiacji od TO-BE |
| S155 | Process Mining | All | Enhancement: proponuj poprawki na bazie event log |
| S156 | Self-Service | D0 | Admin panel: tenant config bez kodu |
| S157 | Self-Service | D0 | No-code workflow builder (non-technical users) |
| S158 | Self-Service | D0 | Self-service onboarding: 0 touchpoint do first value |
| S159 | Voice UI | All | Voice: "Hermes, jakie mam dziś przetargi?" |
| S160 | Predictive | D2 | Predict: które przetargi pojawią się w przyszłym tygodniu |
| S161 | Predictive | D2 | Predict: optymalna data składania oferty |
| S162 | Predictive | D2 | Predict: jaka cena wygrywa dla tego CPV+region |
| S163 | Autonomous | All | Autonomous agent: pełny cycle bid bez interwencji (opcja) |
| S164 | Autonomous | All | Human-in-loop gates: zatwierdzenie przed wysłaniem oferty |
| S165 | Autonomous | All | Audit trail: każda autonomiczna decyzja wyjaśnialna |
| S166 | Ecosystem | All | SDK: Python + JS do integracji zewnętrznych |
| S167 | Ecosystem | All | Plugin system: zewnętrzne moduły CPV-specific |
| S168 | Ecosystem | All | App store: gotowe integracje (Comarch, Symfonia, SAP) |
| S169 | Excellence | All | Zero-downtime deploy pipeline |
| S170 | Excellence | All | Chaos engineering: fault injection tests |
| S171 | Excellence | All | SLA: 99.9% uptime guarantee + monitoring |
| S172 | Excellence | All | Cost optimization: idle resource cleanup |
| S173 | Excellence | All | Green IT: power usage awareness |
| S174 | Compliance | D0 | ISO 27001 przygotowanie |
| S175 | Compliance | D0 | SOC 2 Type I audit |
| S176 | Community | All | Open-source connectors (BZP/TED) jako osobny repo |
| S177 | Community | All | Developer docs: API reference + examples |
| S178 | Community | All | Changelog + release notes automation |
| S179 | Handoff | All | Pełna dokumentacja procesowa BPMN 2.0 finalna |
| S180 | Faza 4 Kaizen | All | OKR review: platforma vs cele biznesowe |

---

## 7. METRYKI JAKOŚCI PROCESÓW (Process KPIs)

| KPI | Faza 1 Target | Faza 2 Target | Faza 3 Target | Faza 4 Target |
|-----|--------------|--------------|--------------|--------------|
| ingest_p95_latency | < 120s (async) | < 60s | < 30s | < 10s |
| alert_delivery_rate | > 95% | > 98% | > 99.5% | > 99.9% |
| doc_fetch_coverage | > 70% | > 85% | > 95% | > 98% |
| scoring_cache_hit | > 80% | > 90% | > 95% | > 99% |
| win_pred_accuracy | baseline | > 0.65 AUC | > 0.75 AUC | > 0.85 AUC |
| time_to_decision | < 5 min | < 3 min | < 2 min | < 1 min |
| automation_coverage | 0% | 30% | 70% | 90% |
| api_p95 | < 500ms | < 200ms | < 100ms | < 50ms |

---

## 8. SPRINT 1 — PIERWSZA AKCJA (Async Ingest)

**Natychmiastowy następny krok:**

```
BPMN TO-BE: P1.3 Async Ingest Run

[Message Start: POST /api/v1/ingest/run]
  → [Service Task: create IngestTask(status=PENDING, task_id=uuid)]
  → [Message End: 202 Accepted {task_id}]  ← ZMIANA: nie blokujemy

[Parallel: Background Worker]
  → [Service Task: execute run_ingest()]  ← osobny thread/ARQ task
      → [Intermediate Message: SSE /ingest/stream/{task_id}]
          → steps: FETCHING → NORMALIZING → SCORING → DONE
      → [Service Task: update IngestTask(status=DONE)]
  → [Signal End: ingest.complete → event bus]

WYMAGANE:
- Tabela: ingest_tasks (id, status, tenant_id, result_json, created_at)
- Endpoint: GET /api/v1/ingest/tasks/{task_id}
- Endpoint: GET /api/v1/ingest/stream/{task_id} (SSE)
- Background: asyncio.create_task() lub ARQ
```

---

*Dokument żywy — aktualizowany po każdym sprincie. Wersja: `git log --oneline docs/bpmn/`*
