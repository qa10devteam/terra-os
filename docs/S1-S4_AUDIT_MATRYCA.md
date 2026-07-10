# S1-S4 AUDIT — Matryca Tabela ↔ Endpoint ↔ Frontend

## STATUS: ✅ COMPLETE

### Legenda statusów Frontend
- 🟢 LIVE — endpoint wołany przez frontend, dane wyświetlane
- 🟡 PARTIAL — endpoint istnieje, hook napisany, ale UI niekompletne/broken
- 🔴 DEAD — endpoint gotowy, frontend go NIE woła
- ⚫ MISSING — endpoint nie istnieje, tabela niewykorzystana

---

## MATRYCA GŁÓWNA

| # | Tabela DB | Router backend | Prefix API | Frontend call | Status |
|---|-----------|---------------|------------|---------------|--------|
| 1 | `tenant` | organizations | `/api/v2/organizations` | `organizations/me` | 🟢 |
| 2 | `owner_profile` | estimator, rfq, export | `/api/v1` | via engine | 🟡 |
| 3 | `tender` | zwiad, tenders_v2, bzp, ted | `/api/v1/tenders`, `/api/v2/tenders` | ZwiadPage, PipelinePage | 🟢 |
| 4 | `tender_document` | documents, documents_upload, bzp_documents | `/api/v1`, `/api/v2/documents`, `/api/v1/bzp/documents` | DocumentViewer | 🟢 |
| 5 | `document_chunk` | search, intelligence | `/api/v2/search`, `/api/v2/intelligence` | — | 🔴 |
| 6 | `przedmiar_item` | kosztorys_v2 | `/api/v2/kosztorys` | KosztorysPage | 🟢 |
| 7 | `analysis` | documents, engine, chat | `/api/v1` | SilnikPage | 🟡 |
| 8 | `discrepancy` | engine, analytics_v2 | `/api/v1`, `/api/v2/analytics` | — | 🔴 |
| 9 | `estimate` | estimator, estimates_v2, engine, export | `/api/v1`, `/api/v2/estimates` | KosztorysPage | 🟢 |
| 10 | `estimate_line` | estimates_v2, offers, kosztorys_v2 | `/api/v2/estimates`, `/api/v1/offers` | KosztorysPage, OfertaPage | 🟢 |
| 11 | `rate_card` | kosztorys_v2 (user_rates) | `/api/v2/kosztorys/user-rates` | KosztorysPage | 🟢 |
| 12 | `calibration_coeff` | — | — | — | ⚫ |
| 13 | `rfq` | rfq | `/api/v1/rfq` | RfqPage | 🟡 |
| 14 | `rfq_message` | rfq | `/api/v1/rfq` | RfqPage | 🟡 |
| 15 | `axiom` | engine | `/api/v1/tenders/{id}/engine` | SilnikPage | 🟢 |
| 16 | `risk_run` | engine | `/api/v1/tenders/{id}/engine/run` | SilnikPage | 🟢 |
| 17 | `resource_equipment` | resources, module3 | `/api/v1/equipment` | ImportPage (equipment) | 🟢 |
| 18 | `employee` | module3, resources | `/api/v1/resources/employees` | ImportPage | 🟢 |
| 19 | `competency` | module3 | `/api/v1` | — | 🔴 |
| 20 | `availability` | module3 | `/api/v1` | — | 🔴 |
| 21 | `contract` | module3, system | `/api/v1/contracts` | — | 🔴 |
| 22 | `calendar_event` | resources | `/api/v1/calendar` | — | 🔴 |
| 23 | `daily_plan` | module3 | `/api/v1` | — | 🔴 |
| 24 | `dispatch` | — | — | — | ⚫ |
| 25 | `field_status` | module3 | `/api/v1` | — | 🔴 |
| 26 | `mobile_device` | module3 | `/api/v1` | — | 🔴 |
| 27 | `approval_request` | rfq, decisions_v2, module3 | `/api/v1/rfq`, `/api/v2/decisions` | DecyzjaPage | 🟡 |
| 28 | `agent_run` | system | `/api/v1` | SystemPage | 🟡 |
| 29 | `audit_log` | audit, system, chat, rfq, gdpr | `/api/v2/audit` | — | 🔴 |

---

## ZŁOTE DATASETY — status integracji

| # | Dataset | Tabela/plik | Router | Frontend endpoint | Status |
|---|---------|-------------|--------|-------------------|--------|
| 1 | ICB ceny średnie | `icb_ceny_srednie` (784k) | intelligence, market_intelligence, benchmark | `/api/v2/intelligence/prices/icb` | 🟡 hook istnieje, widgety częściowe |
| 2 | ICB Forecast | `icb_forecast` | intelligence | `/api/v1/intelligence/prices/forecast` | 🟡 endpoint wołany, dane mogą być puste |
| 3 | Intercenbud KoBo | `intercenbud_kobo_full.json` (165MB) | kosztorys_v2 (material_alerts) | `/api/v2/kosztorys/material-alerts` | 🟡 |
| 4 | Atlas Tenders | `historical_tenders` | market_intelligence, buyer_crm, competitor_watch | wiele endpointów | 🔴 frontend nie woła |
| 5 | DDC CWICR | `ddc_cwicr_pl_warsaw_workitems.parquet` (25MB) | — | — | ⚫ nieużywany |
| 6 | Qdrant embeddings | vector store (50MB+) | search, intelligence | `/api/v2/intelligence/fts` | 🟡 |
| 7 | MV rankings | `mv_contractor_ranking`, `mv_buyer_ranking` | market_intelligence | — | 🔴 |
| 8 | Labor inflation | `mv_labor_inflation_index` | market_intelligence | `/api/v2/intelligence/prices/inflation` | 🟡 hook istnieje |

---

## FRONTEND HOOKS vs BACKEND — status

| Hook (api-v2.ts) | Backend endpoint | Tabele | Status |
|------------------|-----------------|--------|--------|
| `useIntelSummary` | `/api/v2/intelligence/summary` | tender, historical_tenders | 🟢 |
| `useIntelTrends` | `/api/v2/intelligence/trends` | tender, historical_tenders | 🟢 |
| `useCompetitorsTop` | `/api/v2/intelligence/competitors/top` | mv_contractor_ranking | 🟢 |
| `useBuyersTop` | `/api/v2/intelligence/buyers/top` | mv_buyer_ranking | 🟢 |
| `useWinRates` | `/api/v2/intelligence/win-rates` | historical_tenders | 🟢 |
| `useTopBuyersCpv` | `/api/v2/intelligence/top-buyers-cpv` | historical_tenders | 🟢 |
| `useSeasonality` | `/api/v2/intelligence/seasonality` | historical_tenders | 🟢 |
| `useFTS` | `/api/v2/intelligence/fts` | document_chunk (Qdrant) | 🟢 |
| `useInflation` | `/api/v2/intelligence/prices/inflation` | mv_labor_inflation_index | 🟢 |
| CompetitorWatch | `/api/v2/competitors` | competitor_watch, atlas_contractors | 🟢 |
| BuyerCRM | `/api/v2/buyer-crm` | buyer_crm, atlas_buyers | 🟢 |
| Alerts | `/api/v2/alerts` | tender_alert | 🟢 |
| Bookmarks | `/api/v2/bookmarks` | tender_bookmark | 🟢 |

### Hooki w UI ale endpoint zwraca błąd/puste:
- `intelligence/summary` → "Invalid or expired token" (auth problem)
- `intelligence/prices/forecast` → potencjalnie puste dane (icb_forecast puste?)
- `buyer-crm` → zależy od atlas_buyers (import needed)
- `competitors` → zależy od atlas_contractors (import needed)

---

## ROUTERY BEZ FRONTENDU (28 endpointów gotowych, UI ich nie woła)

| Router | Endpoint | Potencjalna strona UI |
|--------|----------|----------------------|
| `advanced_analytics` | `/api/v2/analyze-swz`, `/sensitivity`, `/score-decision`, `/recommendation`, `/report`, `/feedback` | DecyzjaPage, AnalyticsPage |
| `module3` | `/resources/*`, `/plans/*`, `/dispatch/*`, `/field-status/*` | Zasoby/Operacje (brak strony) |
| `gus_bdl` | `/api/v1/gus/indicators` | MarketBar |
| `krs_verify` | `/api/v1/verify/krs` | Weryfikacja kontrahenta |
| `comments` | `/api/v1/comments` | Komentarze na tenderze |
| `audit` | `/api/v2/audit` | Admin panel |
| `decisions_v2` | `/api/v2/decisions` | DecyzjaPage (rozszerzone) |
| `monitoring` | `/api/v2/system-status`, `/alerts`, `/sla-metrics` | SystemPage (rozszerzone) |
| `sources_health` | `/api/v2/sources/health` | SystemPage |
| `ted_integration` | `/api/v1/ted/sync` | Admin sync |
| `email_webhooks` | `/api/v1/email/*`, `/api/v1/webhooks/*` | Automation settings |

---

## WNIOSKI AUDITU

### Gap Analysis:
1. **Auth token expiry** — frontend nie refreshuje tokenu (screenshot: "Invalid or expired token")
2. **Atlas data nie zaimportowany** — `historical_tenders`, `atlas_buyers`, `atlas_contractors` mogą być puste
3. **Materialized views** mogą nie istnieć — `mv_*` tabele mogą wymagać CREATE
4. **29 tabel, 8 live w UI** — 72% danych niewidocznych
5. **52 routery, 24 live w UI** — 54% endpointów martwych
6. **6 złotych datasetów, 0-2 live w UI** — ogromny potencjał niewykorzystany

### Priorytety wdrożenia:
1. 🔥 Fix auth (token refresh) — bez tego nic nie działa
2. 🔥 Import atlas data → historical_tenders, atlas_buyers, atlas_contractors
3. 🔥 Create materialized views (mv_*)
4. Quick wins — podpięcie istniejących hooków do widgetów
5. Nowe strony — module3/zasoby, audit, decisions
