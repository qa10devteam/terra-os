# TERRA.OS — Plan integracji SQL z Frontendem (120 sprintów)

## Stan obecny — Audit

### Bazy danych (PostgreSQL 16 + pgvector)
**29 tabel** w spec/01_data_model.sql:

| Grupa | Tabele | Dane |
|-------|--------|------|
| Tenancy | `tenant`, `owner_profile` | Multi-tenant, profil firmy, CPV, województwa |
| Przetargi | `tender`, `tender_document`, `document_chunk`, `przedmiar_item` | BZP/TED/BIP, dokumenty, chunki wektorowe, przedmiary |
| Kosztorysy | `estimate`, `estimate_line`, `rate_card`, `calibration_coeff` | Wyceny doc/owner, pozycje, stawki |
| Intelligence | `analysis`, `discrepancy`, `axiom`, `risk_run` | Analiza SWZ, anomalie, silnik aksjomatyczny |
| CRM/RFQ | `rfq`, `rfq_message` | Zapytania ofertowe, korespondencja |
| Zasoby | `resource_equipment`, `employee`, `competency`, `availability` | Sprzęt, ludzie, kompetencje, dostępność |
| Operacje | `contract`, `calendar_event`, `daily_plan`, `dispatch`, `field_status`, `mobile_device` | Kontrakty, plany dzienne, dyspozycje |
| System | `approval_request`, `agent_run`, `audit_log` | Akceptacje, AI agenty, logi |

### Złote datasety (NIEWYKORZYSTANE przez frontend)
| Dataset | Format | Rozmiar | Potencjał |
|---------|--------|---------|-----------|
| `icb_ceny_srednie` | Tabela PG | 784k rekordów | Benchmarking cen R/M/S real-time |
| `intercenbud_kobo_full.json` | JSON | 165MB | Pełna baza KNR/KNNR z narzutami |
| `intercenbud_narzuty_full.json` | JSON | 59KB | Współczynniki narzutów |
| `ddc_cwicr_pl_warsaw_workitems.parquet` | Parquet | 25MB | DDC/CWICR pozycje robót |
| `icb_forecast` | Tabela PG | prognoza | Prognoza cen ICB na przyszłe kwartały |
| `kosztorys_pozycja` | Tabela PG | pozycje | Pozycje z z-score'ami anomalii |
| Qdrant vector store | Binary | ~50MB | Embeddingi dokumentów przetargowych |
| `data/atlas/tenders_*.csv.gz` | CSV GZ | 240MB+ | Pełna historia przetargów 2024-2025 |

### Frontend (Next.js 15 / apps/ui)
**5 stron + 20 komponentów page**, ale:
- `api-v2.ts` = 958 linii — **główny klient API**
- Hooki: `useIntelSummary`, `useIntelTrends`, `useCompetitorsTop`, `useBuyersTop`, `useWinRates`, itd.
- Faktycznie wykorzystywane: **~40% endpointów** z 52 routerów backend

### API Backend (FastAPI)
**52 routery**, ale frontend woła tylko ~20 z nich. Niewykorzystane złoto:
- `market_intelligence.py` — trendy, inflacja, predykcje
- `benchmark.py` — porównanie z ICB
- `competitor_watch.py` — monitoring konkurencji
- `buyer_crm.py` — CRM zamawiających
- `advanced_analytics.py` — analiza wrażliwości, scoring, rekomendacje
- `monitoring.py` — SLA, alerting
- `decisions_v2.py` — moduł decyzyjny go/no-go

---

## Framework 120 sprintów

### FAZA 1: AUDIT (Sprint 1-10)
> Mapowanie co mamy vs co używamy

| Sprint | Cel | Deliverable |
|--------|-----|-------------|
| S1 | Audit tabel DB vs frontend calls | Matryca: tabela ↔ endpoint ↔ komponent UI |
| S2 | Audit danychICB/atlas vs wyświetlane | Gap analysis: dane dostępne vs widoczne |
| S3 | Audit endpointów backend | Lista 52 routerów + status: live/dead/partial |
| S4 | Audit frontend hooks | Mapa: hook → endpoint → stan (działa/broken/stub) |
| S5 | Audit wektorów/embeddingów | Qdrant collections, coverage dokumentów |
| S6 | Performance baseline | Czasy odpowiedzi per endpoint, size payloadów |
| S7 | Auth/security audit | JWT flow, token refresh, RBAC gaps |
| S8 | Audit UX flows | Screeny każdego ekranu + broken states |
| S9 | Audit data freshness | Kiedy dane się aktualizują, stale data risk |
| S10 | **Raport auditu** | Dokument: co działa, co nie, priorytety |

### FAZA 2: DISCOVERY (Sprint 11-30)
> Jak to powinno działać — use cases, user stories, architektura

| Sprint | Cel | Deliverable |
|--------|-----|-------------|
| S11-12 | User stories — Zwiad/Pipeline | Epic: "Widzę przetargi z scoring + trend cen" |
| S13-14 | User stories — Kosztorys | Epic: "Wyceniam z ICB real-time, anomalie widoczne" |
| S15-16 | User stories — Decyzja go/no-go | Epic: "Dashboard decyzyjny z silnikiem aksjomatycznym" |
| S17-18 | User stories — Market Intelligence | Epic: "Trendy, inflacja, prognozy CPV na dashboardzie" |
| S19-20 | User stories — CRM Zamawiających | Epic: "Historia, win-rate per buyer, follow-up" |
| S21-22 | User stories — Konkurencja | Epic: "Monitoring konkurentów, ich wygranych, cen" |
| S23-24 | User stories — Zasoby/Plany | Epic: "Kalendarz zasobów, dispatch, mobile" |
| S25-26 | Schema design — nowe tabele/migracje | ERD v2 + Alembic migracje |
| S27-28 | API contract design | OpenAPI spec v2 + TypeScript types |
| S29-30 | **Architektura docelowa** | ADR: real-time vs batch, cache strategy, WebSocket |

### FAZA 3: PLAN (Sprint 31-50)
> Roadmapa wdrożenia — co, w jakiej kolejności, dependencies

| Sprint | Cel | Deliverable |
|--------|-----|-------------|
| S31-32 | Priorytetyzacja RICE | Ranked backlog 50+ features |
| S33-34 | Plan danych — ETL/pipeline | Schemat: ICB→PG, Atlas→PG, BZP sync cadence |
| S35-36 | Plan frontend — component tree | Design system + component dependencies |
| S37-38 | Plan backend — service layer | Service boundaries, shared vs dedicated DB |
| S39-40 | Plan infra — deploy/scale | AWS ECS task definitions, Neon PG scaling |
| S41-42 | Plan testów — E2E + integration | Test strategy per moduł, coverage targets |
| S43-44 | Plan migracji danych | Zero-downtime migration steps |
| S45-46 | Plan rollout — feature flags | Canary/progressive rollout per feature |
| S47-48 | Dependencies + risk | Critical path, blockers, fallback plans |
| S49-50 | **Master Roadmap** | Gantt z milestone'ami, team allocation |

### FAZA 4: WDROŻENIE (Sprint 51-120)
> Budujemy — iteracyjnie, feature po feature

#### Warstwa 1: Data Pipeline (S51-60)
| Sprint | Cel |
|--------|-----|
| S51-52 | ICB seed live — 784k rekordów w PG, cron refresh |
| S53-54 | Atlas import — history 2024-2025 w tender table |
| S55-56 | BZP/TED real-time sync — webhook + polling |
| S57-58 | Embedding pipeline — nowe dokumenty → Qdrant auto |
| S59-60 | Forecast model deploy — icb_forecast tabela live |

#### Warstwa 2: Core Intelligence Frontend (S61-80)
| Sprint | Cel |
|--------|-----|
| S61-62 | ZwiadPage v2 — live scoring + trend mini-chart per tender |
| S63-64 | KosztorysPage v2 — ICB benchmark inline, anomaly markers |
| S65-66 | DecyzjaPage — go/no-go wizard z aksjomatami |
| S67-68 | Market Intelligence dashboard — trends, inflation, CPV heatmap |
| S69-70 | Competitor Watch page — ranking, wygranych, overlap |
| S71-72 | Buyer CRM page — historia, win-rate, notes |
| S73-74 | AnalyticsPage v2 — sensitivity analysis, cost trends |
| S75-76 | RFQ flow — end-to-end z template'ami |
| S77-78 | Alerting — real-time notifications per scoring threshold |
| S79-80 | Bookmarks + saved searches — personalizacja widoku |

#### Warstwa 3: Operacje & Zasoby (S81-100)
| Sprint | Cel |
|--------|-----|
| S81-82 | Zasoby — equipment CRUD + availability calendar |
| S83-84 | Pracownicy — competency matrix + scheduling |
| S85-86 | Daily Plan — dispatch view + mobile PWA |
| S87-88 | Field Status — reporting z terenu |
| S89-90 | Kontrakty — lifecycle tracking, SLA |
| S91-92 | Document Viewer — inline PDF + chunk highlight |
| S93-94 | Import Excel/PDF — batch przedmiary |
| S95-96 | Export — PDF/XLSX kosztorys + oferta |
| S97-98 | Automation rules — n8n/zapier integration UI |
| S99-100 | Mobile PWA — offline-first, GPS dispatch |

#### Warstwa 4: AI & Polish (S101-120)
| Sprint | Cel |
|--------|-----|
| S101-102 | AI Chat v2 — context-aware per aktywny tender |
| S103-104 | AI rekomendacje — auto-scoring + przyczyny |
| S105-106 | AI wycena — predictive pricing z ICB + history |
| S107-108 | RAG search — semantic search po dokumentach |
| S109-110 | Dashboardy executive — KPI, portfolio health |
| S111-112 | Multi-tenant admin — user management, RBAC |
| S113-114 | Performance — lazy loading, virtualization, caching |
| S115-116 | Integration tests E2E — Playwright full suite |
| S117-118 | Security hardening — OWASP, pen-test fixes |
| S119-120 | **Go-live readiness** — monitoring, runbook, SLA |

---

## Quick Wins (natychmiastowe)

Endpointy backend gotowe, frontend ich nie woła:

| # | Feature | Backend endpoint | Frontend component | Effort |
|---|---------|------------------|--------------------|--------|
| 1 | Trendy cenowe CPV | `/intel/trends` | AnalyticsPage | 2h |
| 2 | Top konkurenci | `/intel/competitors-top` | PipelinePage | 2h |
| 3 | Win-rate per buyer | `/intel/win-rates` | CRM widget | 3h |
| 4 | ICB benchmark w kosztorysie | `/benchmark/compare` | KosztorysPage | 4h |
| 5 | Anomalie z-score | `/analytics/anomalies` | KosztorysPage red flags | 3h |
| 6 | Prognoza ICB | `/forecast/icb` | MarketBar widget | 2h |
| 7 | Sensitivity analysis | `/advanced-analytics/sensitivity` | DecyzjaPage | 4h |
| 8 | Competitor watch | `/competitors/watch` | Nowa strona | 1d |
| 9 | Buyer CRM notes | `/buyer-crm/` | Nowa strona | 1d |
| 10 | Alert rules | `/alerts/rules` | NotificationsPage | 4h |

**Razem quick wins: ~5 dni** → +10 widocznych feature'ów na froncie bez pisania nowego backendu.

---

## Metryki sukcesu

| Metryka | Teraz | Cel S60 | Cel S120 |
|---------|-------|---------|----------|
| Endpointy połączone z UI | ~20/52 (38%) | 40/52 (77%) | 52/52 (100%) |
| Datasety live w UI | 0/6 | 4/6 | 6/6 |
| Coverage tabel w UI | ~8/29 (28%) | 20/29 (69%) | 29/29 (100%) |
| Testy E2E | 0 | 30 | 120+ |
| Response time p95 | ? | <500ms | <200ms |
| User satisfaction (NPS) | — | 30+ | 50+ |
