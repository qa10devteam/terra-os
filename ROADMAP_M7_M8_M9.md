# YU-NA / budos — ROADMAP M7 → M9
## 3 Milestony × 40 Faz × 5 Sprintów = 600 tasków (120 faz total z M5+M6)
*Wygenerowano: 2026-07-12 | Stack: PostgreSQL 107 tabel, vLLM/Qwen2.5-7B LoRA, Next.js 15, FastAPI*

---

## FILOZOFIA ROADMAPU

> **State-of-Art AI w przetargach budowlanych** oznacza:
> - SQL nie jako storage — jako *silnik wiedzy* (window functions, materialized views, recursive CTE, pg_vector)
> - LLM nie jako chatbot — jako *operator* (RAG nad dokumentami SWZ, agent pętli decyzyjnej, scoring predykcyjny)
> - LangGraph nie jako eksperyment — jako *szkielet orkiestracji* (wieloagentowy pipeline: Zwiad→Analiza→Decyzja→Oferta)
> - Każda strona UI = okno na żywy graf wiedzy, nie tabela danych

---

## LEGENDA
- **Sprint** = 1 dzień pracy (1 commit, weryfikowalny output)
- **Faza** = 5 sprintów (1 strona lub podsystem)
- **Milestone** = 40 faz (8 tygodni) — 1 blok produktowy
- Status: `⬜ TODO` / `🔄 IN_PROGRESS` / `✅ DONE`

---

# MILESTONE 7 — INTELLIGENCE LAYER
*Cel: YU-NA staje się inteligentnym asystentem — SQL jako silnik wiedzy, RAG nad dokumentami, LangGraph agent pipeline*

---

## FAZA 7.01 — SQL Knowledge Engine: pg_vector + embeddingi
*Backend: packages/db + services/ai*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.01.1 | Dodaj kolumnę `embedding vector(768)` do tabel `tender`, `analysis`, `bzp_documents` — pgvector extension | ⬜ |
| S2 | 7.01.2 | Worker: embeduj tytuły+opisy przetargów (Qwen2.5 encoder lub sentence-transformers) — batch 50/min | ⬜ |
| S3 | 7.01.3 | HNSW index na `tender.embedding` — `CREATE INDEX CONCURRENTLY` | ⬜ |
| S4 | 7.01.4 | Endpoint `POST /api/v2/tenders/semantic-search` — cosine similarity top-20 | ⬜ |
| S5 | 7.01.5 | UI: ZwiadPage — zakładka "Szukaj semantycznie" obok FTS | ⬜ |

## FAZA 7.02 — RAG nad dokumentami SWZ
*Backend: services/ai/rag.py + nowy RAG pipeline*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.02.1 | Chunking SWZ: `bzp_documents.content` → chunki 512 tokenów z overlap 64, zapisz do `doc_chunks(id, tender_id, chunk_idx, text, embedding)` | ⬜ |
| S2 | 7.02.2 | Worker: embeduj chunki asynchronicznie (Celery lub BackgroundTask) — progress w `agent_run` | ⬜ |
| S3 | 7.02.3 | RAG retriever: `POST /api/v2/rag/query` — top-k chunks → rerank (cross-encoder) → context window | ⬜ |
| S4 | 7.02.4 | Generator: context + pytanie → vLLM Qwen2.5 budos → strumieniowana odpowiedź SSE | ⬜ |
| S5 | 7.02.5 | UI: ChatWidget — tryb "Pytaj o SWZ" z wyborem przetargu → RAG odpowiedź z cytowaniem stron | ⬜ |

## FAZA 7.03 — LangGraph: Agent Pipeline v1 (Zwiad → Analiza)
*Backend: services/agents/langgraph_pipeline.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.03.1 | Zainstaluj `langgraph`, `langchain-community` w .venv — stwórz `AgentState(TypedDict)` | ⬜ |
| S2 | 7.03.2 | Node `fetch_tender`: pobierz dane przetargu + dokumenty z DB | ⬜ |
| S3 | 7.03.3 | Node `analyze_swz`: RAG retriever → extract key_facts, red_flags, deadlines — zapis do `analysis` | ⬜ |
| S4 | 7.03.4 | Node `score_tender`: scoring_config + CPV benchmark + deadline bonus → match_score | ⬜ |
| S5 | 7.03.5 | Endpoint `POST /api/v2/agent/analyze/{tender_id}` — uruchamia graph, zwraca `agent_run.id`, SSE progress | ⬜ |

## FAZA 7.04 — LangGraph: Agent Pipeline v2 (Decyzja → GO/NO-GO)
*Backend: services/agents/langgraph_pipeline.py (rozbudowa)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.04.1 | Node `ahp_eval`: macierz AHP z scoring_config → GO/CONSIDER/NO-GO | ⬜ |
| S2 | 7.04.2 | Node `competitor_check`: atlas_contractors → kto wygrywał to CPV, po ile | ⬜ |
| S3 | 7.04.3 | Node `bid_strategy`: bid_intelligence history → optymalny markup (bidding model) | ⬜ |
| S4 | 7.04.4 | Node `generate_brief`: wszystkie dane → LLM → `decision_brief` markdown (pros/cons/rekomendacja) | ⬜ |
| S5 | 7.04.5 | UI: DecyzjaPage — "Uruchom AI Analizę" → SSE progress → brief z cytowaniami | ⬜ |

## FAZA 7.05 — SQL: Materialized Views jako silnik dashboardu
*Backend: migrations + api/dashboard.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.05.1 | MV `mv_pipeline_kpi`: win_rate MTD, pipeline_value, avg_deal_size, active_count — REFRESH CONCURRENTLY co 5min | ⬜ |
| S2 | 7.05.2 | MV `mv_cpv_heatmap`: CPV-4 × voivodeship × avg_value × win_rate — zasilona z bid_intelligence + bzp_results | ⬜ |
| S3 | 7.05.3 | MV `mv_competitor_radar`: top-20 konkurentów per CPV z win_rate, avg_price, territory | ⬜ |
| S4 | 7.05.4 | MV `mv_market_forecast`: autoregressive 30/60/90d forecast — window avg last 12 miesięcy per CPV | ⬜ |
| S5 | 7.05.5 | DashboardPage: podłącz wszystkie 4 MV — sub-second response, zero ORM overhead | ⬜ |

## FAZA 7.06 — SQL: Window Functions — scoring predykcyjny
*Backend: services/scoring/scorer_v3.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.06.1 | `RANK() OVER (PARTITION BY cpv5 ORDER BY match_score DESC)` — percentyl tendera w kategorii | ⬜ |
| S2 | 7.06.2 | `LAG/LEAD` na deadline → wykryj przetargi "gorące" (deadline < 14d, brak naszej oferty) | ⬜ |
| S3 | 7.06.3 | `PERCENTILE_CONT(0.5)` na historical_bids per CPV → median cena rynkowa jako kotwica | ⬜ |
| S4 | 7.06.4 | `RECURSIVE CTE` — graph zależności kontraktów (kontrakt → podwykonawcy → zasoby) | ⬜ |
| S5 | 7.06.5 | SilnikPage: nowa zakładka "Score Analytics" — percentyl, hot/cold, median rynkowa | ⬜ |

## FAZA 7.07 — ChatWidget: budos AI Operator (wieloturowy)
*Frontend: ChatWidget.tsx + backend: services/ai/chat_session.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.07.1 | Sesja czatu: `chat_session(id, tenant_id, messages jsonb, context jsonb, created_at)` — persistuj historię | ⬜ |
| S2 | 7.07.2 | Context injection: aktywna strona + wybrany przetarg → automatyczny kontekst w system prompt | ⬜ |
| S3 | 7.07.3 | Tool calls: budos może woła API (`search_tenders`, `get_analysis`, `run_ahp`) — function calling w vLLM | ⬜ |
| S4 | 7.07.4 | Memory: ostatnie 10 tur w kontekście + summary starszych (rolling compression) | ⬜ |
| S5 | 7.07.5 | UI: ChatWidget — "Zapytaj o ten przetarg", "Porównaj z konkurencją", "Wygeneruj brief" — quick actions | �œ |

## FAZA 7.08 — ZwiadPage: pełny live + semantic search
*Frontend: ZwiadPage.tsx (1720 linii)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.08.1 | Tabela live: `GET /api/v2/tenders` cursor-based paginacja, 25/strona, skeleton | ⬜ |
| S2 | 7.08.2 | Filtry: CPV prefix, voivodeship, min/max value, source, deadline range | ⬜ |
| S3 | 7.08.3 | Sortowanie: deadline / wartość / match_score / published_at — klikalne nagłówki | ⬜ |
| S4 | 7.08.4 | Semantic search tab: POST `/api/v2/tenders/semantic-search` — wyniki z similarity score | ⬜ |
| S5 | 7.08.5 | TenderDetail drawer: tytuł, zamawiający, CPV, wartość, deadline + "Uruchom AI Analizę" button | ⬜ |

## FAZA 7.09 — PipelinePage: Kanban live + drag & drop
*Frontend: PipelinePage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.09.1 | Kanban: kolumny OBSERWOWANY / ANALIZOWANY / DECYZJA / OFERTA / ZŁOŻONY / WON / LOST | ⬜ |
| S2 | 7.09.2 | Drag & drop (dnd-kit): PATCH `pipeline_status` + optimistic update | ⬜ |
| S3 | 7.09.3 | Karta: tytuł, zamawiający, deadline countdown, wartość, match_score badge, AI brief snippet | ⬜ |
| S4 | 7.09.4 | Header KPI z MV `mv_pipeline_kpi` — win_rate, pipeline_value, active count | ⬜ |
| S5 | 7.09.5 | Timeline view: SVG oś czasu deadline dla aktywnych + velocity chart (30d) | ⬜ |

## FAZA 7.10 — SilnikPage: AI scoring konfigurowalny
*Frontend: SilnikPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.10.1 | Formularz wag: GET/PUT `/api/v2/scoring/config` — sliders + live preview top-10 | ⬜ |
| S2 | 7.10.2 | Score breakdown waterfall: contribution per kryterium dla wybranego przetargu | ⬜ |
| S3 | 7.10.3 | Deadline bonus chart: boost% vs dni_do_deadline (custom SVG) | ⬜ |
| S4 | 7.10.4 | CPV win-rate heatmap: CPV-4 × win_rate (z MV `mv_cpv_heatmap`) | ⬜ |
| S5 | 7.10.5 | Historia wag: audit_log entries per scoring_config change | ⬜ |

## FAZA 7.11 — DecyzjaPage: AI Decision Brief pełny
*Frontend: DecyzjaPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.11.1 | Lista przetargów high-score (>0.7) wymagających decyzji — "Oczekuje na decyzję" | ⬜ |
| S2 | 7.11.2 | "Uruchom AI Analizę" → LangGraph pipeline SSE progress → brief | ⬜ |
| S3 | 7.11.3 | Brief rendering: pros/cons, WinProbGauge, estimated margin, competitor risk | ⬜ |
| S4 | 7.11.4 | GO/NO-GO button → PATCH pipeline_status + zapis do `approval_request` | ⬜ |
| S5 | 7.11.5 | Historia decyzji: tabela GO/NO-GO z uzasadnieniami AI + ludzką adnotacją | ⬜ |

## FAZA 7.12 — BuyerCRMPage: zamawiający intelligence
*Frontend: BuyerCRMPage.tsx (1212 linii)*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.12.1 | Tabela zamawiających z `atlas_buyers` — sortuj po total_value, win_rate naszej firmy | ⬜ |
| S2 | 7.12.2 | Profil: historia przetargów, CPV mix, average value, sezonowość (MV `mv_cpv_heatmap`) | ⬜ |
| S3 | 7.12.3 | AI summary: "Scharakteryzuj zamawiającego" → RAG po historycznych dokumentach SWZ | ⬜ |
| S4 | 7.12.4 | CRM actions: notatki, kontakty, next follow-up — `buyer_crm` table | ⬜ |
| S5 | 7.12.5 | PolandHeatmap: zamawiający per województwo — kolory wg wartości | ⬜ |

## FAZA 7.13 — CompetitorPage: analiza konkurencji deep
*Frontend: CompetitorPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.13.1 | Lista konkurentów z `atlas_contractors` + `bid_intelligence` — win_rate, avg_price | ⬜ |
| S2 | 7.13.2 | Profil konkurenta: CPV mix, territory, cena vs nasza (head-to-head tabela) | ⬜ |
| S3 | 7.13.3 | AI brief konkurenta: "Oceń strategię X" → RAG po bid_intelligence | ⬜ |
| S4 | 7.13.4 | Trendy: win_rate MoM (recharts LineChart z `mv_competitor_radar`) | ⬜ |
| S5 | 7.13.5 | Alert: śledź konkurenta — notify gdy wygra > X w miesiącu | ⬜ |

## FAZA 7.14 — MarketIntelPage: market intelligence pełny
*Frontend: MarketIntelPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.14.1 | Market summary z `mv_cpv_heatmap` — total value, count, avg CPV (sub-second) | ⬜ |
| S2 | 7.14.2 | Prognoza 30/60/90d z `mv_market_forecast` — wykres z confidence interval | ⬜ |
| S3 | 7.14.3 | SeasonalityChart: przetargi per miesiąc — 3 lata historii (recharts AreaChart) | ⬜ |
| S4 | 7.14.4 | CPV treemap: top-30 per wartość — klikalne drill-down | ⬜ |
| S5 | 7.14.5 | ICBPriceExplorer: real KNR rates z `cpv_regional_benchmark` — per CPV per region | ⬜ |

## FAZA 7.15 — NotificationsPage + real-time bell
*Frontend: NotificationsPage.tsx + Sidebar*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.15.1 | Lista powiadomień: GET `/api/v2/notifications` z paginacją | ⬜ |
| S2 | 7.15.2 | Mark as read — PATCH `/api/v2/notifications/{id}` + optimistic update | ⬜ |
| S3 | 7.15.3 | Filtry: typ (alert/system/tender), przeczytane/nie | ⬜ |
| S4 | 7.15.4 | NotificationsBell: badge z polling 30s — unread count z SQL `COUNT` | ⬜ |
| S5 | 7.15.5 | Ustawienia: email/in-app toggle per event type | ⬜ |

## FAZA 7.16 — CommandMenu: Cmd+K power user
*Frontend: CommandMenu.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.16.1 | FTS search podpięty: `GET /api/v2/tenders/search?q=` — top-5 wyników instant | ⬜ |
| S2 | 7.16.2 | AI search: `GET /api/v2/tenders/semantic-search?q=` — semantyczne wyniki | ⬜ |
| S3 | 7.16.3 | Nawigacja: goto strony, `G Z` → Zwiad, `G P` → Pipeline, `G D` → Decyzja | ⬜ |
| S4 | 7.16.4 | Actions w menu: "Uruchom analizę", "Dodaj do pipeline", "Wygeneruj brief" | ⬜ |
| S5 | 7.16.5 | Historia wyszukiwań: localStorage + "Ostatnie 10" sekcja | ⬜ |

## FAZA 7.17 — DashboardPage: live intelligence hub
*Frontend: DashboardPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.17.1 | KPI cards z MV `mv_pipeline_kpi` — sub-second, zero N+1 | ⬜ |
| S2 | 7.17.2 | "Najgorętsze dziś": top-5 tenderów high-score z deadline < 14d | ⬜ |
| S3 | 7.17.3 | Activity feed: audit_log ostatnie 20 zdarzeń — live polling 60s | ⬜ |
| S4 | 7.17.4 | AI Insight widget: codziennie o 8:00 LangGraph generuje "Digest dnia" | ⬜ |
| S5 | 7.17.5 | Quick actions: "Nowy alert", "Otwórz Pipeline", "Uruchom Zwiad" | ⬜ |

## FAZA 7.18 — SettingsPage: konfiguracja live
*Frontend: SettingsPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.18.1 | Profil org: GET/PATCH `/api/v2/org` — NIP, adres, logo upload | ⬜ |
| S2 | 7.18.2 | Profil usera: email, hasło (change password flow) | ⬜ |
| S3 | 7.18.3 | CPV preferowane: multi-select → zapisz do `scoring_config.preferred_cpv` | ⬜ |
| S4 | 7.18.4 | API keys: BZP, TED, email SMTP — masked inputs + test connection | ⬜ |
| S5 | 7.18.5 | Subscription badge + usage stats (ile tenderów, ile AI analiz w tym miesiącu) | ⬜ |

## FAZA 7.19 — ExportPage + ReportsPage: raporty AI
*Frontend: ExportPage.tsx, ReportsPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.19.1 | Export CSV/XLSX: tendery z filtrami (zakres dat, CPV, pipeline_status) | ⬜ |
| S2 | 7.19.2 | Raport miesięczny: pipeline summary + win/loss + top CPV | ⬜ |
| S3 | 7.19.3 | AI Executive Summary: LangGraph → "Podsumuj miesiąc" → markdown → PDF | ⬜ |
| S4 | 7.19.4 | Scheduled reports: cron export do email (co miesiąc, co tydzień) | ⬜ |
| S5 | 7.19.5 | Report templates: Zarząd / Handlowiec / Techniczny — różne sekcje | ⬜ |

## FAZA 7.20 — MarketKPIBar + OnboardingWizard
*Frontend: MarketKPIBar.tsx, OnboardingWizard.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.20.1 | MarketKPIBar: nowe przetargi dziś + wartość + unread alerts — polling 300s | ⬜ |
| S2 | 7.20.2 | MarketKPIBar: ticker animation — smooth scroll nowych przetargów | ⬜ |
| S3 | 7.20.3 | OnboardingWizard: krok 1 — NIP + CPV preferowane + scoring config | ⬜ |
| S4 | 7.20.4 | OnboardingWizard: krok 2 — pierwszy alert email + test send | ⬜ |
| S5 | 7.20.5 | OnboardingWizard: krok 3 — guided DemoTour (Zwiad→Pipeline→Decyzja) | ⬜ |

## FAZA 7.21 — BookmarksBoardPage + Alert Engine
*Frontend + Backend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.21.1 | Zakładki: kanban OBSERWUJ / PRIORYTET / ARCHIWUM — drag & drop | ⬜ |
| S2 | 7.21.2 | Alert config: dodaj/edytuj/usuń — CPV, słowa kluczowe, wartość min/max | ⬜ |
| S3 | 7.21.3 | Alert matching: background job — SQL matching z `tender` co 15min | ⬜ |
| S4 | 7.21.4 | Alert test: "Testuj teraz" → symulacja matchingu → preview wyników | ⬜ |
| S5 | 7.21.5 | AI alert: "Znajdź przetargi podobne do tych, które wygrałem" — semantic + SQL | ⬜ |

## FAZA 7.22 — AutomationPage: webhooks + n8n
*Frontend: AutomationPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.22.1 | Lista webhooków: GET `/api/v2/webhooks` + create/edit/delete | ⬜ |
| S2 | 7.22.2 | Event mapping: zdarzenie → webhook URL (nowy przetarg / zmiana statusu / alert) | ⬜ |
| S3 | 7.22.3 | Webhook log: ostatnie 50 wykonań z status + payload preview + retry | ⬜ |
| S4 | 7.22.4 | Pre-built templates: "Nowy przetarg → Slack", "GO-decision → email" | ⬜ |
| S5 | 7.22.5 | n8n iframe (jeśli dostępny) lub deep-link do n8n z pre-filled config | ⬜ |

## FAZA 7.23 — TeamPage: zarządzanie zespołem
*Frontend: TeamPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.23.1 | Lista członków: GET `/api/v2/team/members` — avatar, rola, ostatnia aktywność | ⬜ |
| S2 | 7.23.2 | Zaproszenie: POST `/api/v2/team/invite` — email + rola | ⬜ |
| S3 | 7.23.3 | Zmiana roli: PATCH — admin/user/viewer, z potwierdzeniem | ⬜ |
| S4 | 7.23.4 | Activity per member: ile analiz, ile decyzji, win_rate — z audit_log | ⬜ |
| S5 | 7.23.5 | Pending invitations: lista + resend + revoke | ⬜ |

## FAZA 7.24 — Auth: JWT refresh + role guard + idle timeout
*Frontend + Backend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.24.1 | JWT auto-refresh: 14min/15min window — background interval w useStore | ⬜ |
| S2 | 7.24.2 | Role guard: viewer nie edytuje — disabled buttons + 403 handler | ⬜ |
| S3 | 7.24.3 | Session persistence: refresh token httpOnly cookie | ⬜ |
| S4 | 7.24.4 | Idle timeout: 30min → toast ostrzeżenie → auto-logout po 2min | ⬜ |
| S5 | 7.24.5 | Forgot/Reset password flow: POST forgot → email → token → reset | ⬜ |

## FAZA 7.25 — Error handling + Sentry + 404/500
*Frontend + Backend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.25.1 | Custom 404: not-found.tsx z animacją + link do Dashboard | ⬜ |
| S2 | 7.25.2 | Custom 500: error.tsx z "Zgłoś błąd" + retry | ⬜ |
| S3 | 7.25.3 | API error interceptor: 401 → auto-logout, 429 → toast "Za dużo żądań", 500 → Sentry | ⬜ |
| S4 | 7.25.4 | Sentry frontend: `@sentry/nextjs` — capture exceptions + performance traces | ⬜ |
| S5 | 7.25.5 | Sentry backend: FastAPI middleware — capture 500s z request context | ⬜ |

## FAZA 7.26 — Performance: SWR cache + lazy loading + bundle
*Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.26.1 | SWR wrapper dla authFetch: stale-while-revalidate na wszystkich listach | ⬜ |
| S2 | 7.26.2 | Dynamic imports: lazy load stron (Kosztorys, Logistyka, Analytics) — zmniejsz initial JS | ⬜ |
| S3 | 7.26.3 | Bundle analysis: `next build --analyze` — identyfikuj top-5 bloatów | ⬜ |
| S4 | 7.26.4 | Virtual list: ZwiadPage tabela > 100 wierszy → `react-virtual` | ⬜ |
| S5 | 7.26.5 | Lighthouse CI: score ≥ 85 performance, 90 accessibility | ⬜ |

## FAZA 7.27 — E2E Playwright tests
*Tests*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.27.1 | Playwright setup: install + config na port 3001 | ⬜ |
| S2 | 7.27.2 | Test: login → dashboard → zwiad → klik tender → drawer otwarty | ⬜ |
| S3 | 7.27.3 | Test: Pipeline — dodaj tender, drag do DECYZJA, verify PATCH | ⬜ |
| S4 | 7.27.4 | Test: AI chat — wyślij pytanie, odbierz SSE odpowiedź | ⬜ |
| S5 | 7.27.5 | GitHub Actions: CI na PR — playwright headless | ⬜ |

## FAZA 7.28 — Learning Loop: calibration + feedback
*Backend: services/agents/learning_loop.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.28.1 | Feedback endpoint: `POST /api/v2/feedback` — ocena AI analizy (1-5 + komentarz) | ⬜ |
| S2 | 7.28.2 | Calibration: jeśli wygrany przetarg → wstecz zaktualizuj `calibration_coeff` per CPV | ⬜ |
| S3 | 7.28.3 | Retraining trigger: co 50 nowych feedbacków → trigger fine-tuning dataset refresh | ⬜ |
| S4 | 7.28.4 | UI: AnalyticsPage — zakładka "Uczenie" — historia kalibracji, drift metrics | ⬜ |
| S5 | 7.28.5 | A/B test harness: `ab_experiments` → split scoring_config v1 vs v2 — track win_rate | ⬜ |

## FAZA 7.29 — Fine-tuning v2: dataset z produkcji
*Backend: services/ai/finetune/*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.29.1 | Dataset miner: pobierz `analysis` + `decision` + `feedback` z DB → format SFT | ⬜ |
| S2 | 7.29.2 | Filtrowanie: tylko feedback ≥ 4/5, tylko wygrane przetargi → high-quality pairs | ⬜ |
| S3 | 7.29.3 | Fine-tuning v2: LoRA round 2 na dataset_v2.jsonl (~200+ par) — checkpoint-70 | ⬜ |
| S4 | 7.29.4 | Eval: porównaj checkpoint-35 vs checkpoint-70 na validation set (ROUGE + human) | ⬜ |
| S5 | 7.29.5 | Hot-swap: vLLM reload nowego adaptera bez downtime (--lora-modules hot update) | ⬜ |

## FAZA 7.30 — Axiom Engine: reguły biznesowe w SQL
*Backend: `axiom` table + services/axiom.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.30.1 | Axiom loader: wczytaj aktywne reguły z `axiom` table — klasy: SCORING / ALERT / BLOCK | ⬜ |
| S2 | 7.30.2 | Axiom evaluator: dla każdego tendera eval reguł (DSL → Python → wynik) | ⬜ |
| S3 | 7.30.3 | BLOCK axiom: jeśli spełniony → pipeline_status = NO-GO automatycznie | ⬜ |
| S4 | 7.30.4 | UI: SystemPage — zakładka "Aksjomaty" — CRUD reguł z live test | ⬜ |
| S5 | 7.30.5 | Audit: każde uruchomienie aksjomatu → `audit_log` entry | ⬜ |

## FAZA 7.31 — BidIntelligence: historia ofert + ML
*Backend + Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.31.1 | Import wyniku przetargu: POST `/api/v2/bid-intelligence` — nasza cena, wygrywająca, rank | ⬜ |
| S2 | 7.31.2 | Bidding model v2: logistic regression na `bid_intelligence` → win_prob(markup) | ⬜ |
| S3 | 7.31.3 | Optimal markup calculator: sweep 0%→30% → max expected_profit per CPV | ⬜ |
| S4 | 7.31.4 | UI: AnalyticsPage Bidding — nowy chart "Markup vs Win Probability" per CPV | ⬜ |
| S5 | 7.31.5 | Atlas sync: import z `bzp_results` → auto-fill bid_intelligence | ⬜ |

## FAZA 7.32 — Kosztorys v2: ICB/KNR real prices
*Frontend: KosztorysPage.tsx + Backend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.32.1 | `cpv_regional_benchmark` → API `GET /api/v2/icb/rates?cpv=&nuts2=` — real KNR rates | ⬜ |
| S2 | 7.32.2 | ICBPriceExplorer podpięty: wybierz kod KNR → widok cen R+M+S per region | ⬜ |
| S3 | 7.32.3 | AI Wycena v2: RAG po `cpv_regional_benchmark` + historycznych kosztorysach | ⬜ |
| S4 | 7.32.4 | Porównaj warianty: kosztorys A vs B — diff tabela inline | ⬜ |
| S5 | 7.32.5 | Export: sformatowany kosztorys ofertowy do PDF (puppeteer endpoint) | ⬜ |

## FAZA 7.33 — OfertaPage: kreator PDF state-of-art
*Frontend: OfertaPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.33.1 | Formularz: wybierz tender + kosztorys → auto-fill z org settings (NIP, adres, KRS) | ⬜ |
| S2 | 7.33.2 | AI fill: "Wypełnij ofertę AI" → LLM na bazie SWZ + kosztorysu | ⬜ |
| S3 | 7.33.3 | Live preview: HTML oferta renderowana po prawej w real-time | ⬜ |
| S4 | 7.33.4 | Generuj PDF: POST `/api/v2/offers/generate-pdf` — puppeteer → pobierz | ⬜ |
| S5 | 7.33.5 | Szablony: 3 typy (Budowlany / Usługowy / Dostawy) + custom template upload | ⬜ |

## FAZA 7.34 — RfqPage v2: podwykonawcy + porównanie
*Frontend: RfqPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.34.1 | Nowe RFQ: formularz — tytuł, opis, termin, pozycje materiałowe | ⬜ |
| S2 | 7.34.2 | Lista podwykonawców: `subcontractors` table — send email (SMTP) | ⬜ |
| S3 | 7.34.3 | Odpowiedzi: tabela ofert od podwykonawców — import CSV / manual entry | ⬜ |
| S4 | 7.34.4 | Ranking automatyczny: cena + termin + rating → wyróżnij best offer | ⬜ |
| S5 | 7.34.5 | AI porównanie: "Oceń oferty" → LLM summary pros/cons każdej | ⬜ |

## FAZA 7.35 — ContractsPage v2: cashflow + alerty
*Frontend: ContractsPage.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.35.1 | Nowy kontrakt z przetargu WON: wartość, termin, nr umowy — POST `/api/v2/contracts` | ⬜ |
| S2 | 7.35.2 | Cashflow: płatności etapowe — harmonogram fakturowania (timeline chart) | ⬜ |
| S3 | 7.35.3 | Status realizacji: PRZED / W_TRAKCIE / ZAKOŃCZONY / SPORNY — Kanban mini | ⬜ |
| S4 | 7.35.4 | Alerty: deadline milestone + przeterminowane płatności — cron check | ⬜ |
| S5 | 7.35.5 | AI risk monitor: "Oceń ryzyko kontraktu" → analiza klauzul z dokumentów | ⬜ |

## FAZA 7.36 — ResourcesPage + LogistykaPage v2
*Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.36.1 | Pracownicy: profil — specjalizacje, certyfikaty, stawka, availability | ⬜ |
| S2 | 7.36.2 | Sprzęt: harmonogram — calendar view zajętości | ⬜ |
| S3 | 7.36.3 | Konflikt zasobów: alert gdy 2 kontrakty chcą tego samego sprzętu | ⬜ |
| S4 | 7.36.4 | Koszty sprzętu: stawka/dzień → auto-feed do kosztorysu | ⬜ |
| S5 | 7.36.5 | AI optymalizacja: "Przydziel zasoby do kontraktu" → LP optimizer | ⬜ |

## FAZA 7.37 — Landing page YU-NA / budos produkcja
*Frontend: /landing/page.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.37.1 | Hero section: YU-NA brand, headline "Wygrywaj więcej przetargów z AI", CTA | ⬜ |
| S2 | 7.37.2 | Features: 3 bloki (Zwiad AI / Pipeline / budos Operator) z micro-animacjami | ⬜ |
| S3 | 7.37.3 | Social proof: statystyki z DB ("X tenderów", "Y firm", "Z mln PLN w pipeline") | ⬜ |
| S4 | 7.37.4 | Demo CTA: auto-login demo → guided tour 3 kroków | ⬜ |
| S5 | 7.37.5 | SEO: meta, OG image, schema.org SoftwareApplication, sitemap.xml | ⬜ |

## FAZA 7.38 — Pricing + Stripe
*Frontend: /pricing/page.tsx + Backend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.38.1 | Tabela planów: FREE / PRO 499 PLN/mies. / ENTERPRISE — feature comparison | ⬜ |
| S2 | 7.38.2 | Toggle miesięcznie/rocznie (-20%) z animacją | ⬜ |
| S3 | 7.38.3 | Stripe Checkout: `stripe.checkout.sessions.create` → redirect | ⬜ |
| S4 | 7.38.4 | Webhook Stripe: `customer.subscription.created` → update `org.plan` | ⬜ |
| S5 | 7.38.5 | Usage limits + upgrade modal: FREE → blokada po 50 tenderach | ⬜ |

## FAZA 7.39 — Demo page + DemoTour
*Frontend: /demo/page.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.39.1 | Auto-login: GET /demo → token demo org → redirect do dashboard | ⬜ |
| S2 | 7.39.2 | Demo banner sticky + "Przywróć dane demo" button | ⬜ |
| S3 | 7.39.3 | DemoTour: 5-krokowy guided highlight (Shepherd.js lub custom) | ⬜ |
| S4 | 7.39.4 | Demo reset: POST `/api/v2/demo/reset` → przywróć seed data | ⬜ |
| S5 | 7.39.5 | Conversion CTA: po tour → "Zarejestruj się" z pre-filled email | ⬜ |

## FAZA 7.40 — Docs page
*Frontend: /docs/page.tsx*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 7.40.1 | Struktura: sidebar nav (Pierwsze kroki / Zwiad / Pipeline / API / AI) | ⬜ |
| S2 | 7.40.2 | Quick start: 5-min guide rejestracja → pierwszy alert → pierwsza analiza | ⬜ |
| S3 | 7.40.3 | API docs: Swagger embed `/api/v2/docs` + przykłady curl | ⬜ |
| S4 | 7.40.4 | budos AI docs: jak działa RAG, jak fine-tuning, jak LangGraph pipeline | ⬜ |
| S5 | 7.40.5 | Search docs: FTS po treści (Fuse.js client-side) | ⬜ |

---

# MILESTONE 8 — SCALE & PRODUCTION
*Cel: Multi-tenant SaaS, deploy AWS/Vercel, monitoring, BZP auto-sync, pełna autonomia budos AI*

---

## FAZA 8.01 — Multi-tenancy: row-level security
*Backend: DB + API*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.01.1 | Verify RLS: wszystkie 107 tabel mają `tenant_id` i policy `tenant_id = current_setting` | ⬜ |
| S2 | 8.01.2 | Middleware: `SET LOCAL app.tenant_id` na początku każdego żądania | ⬜ |
| S3 | 8.01.3 | Tenant isolation test: user A nie widzi danych user B (automated Playwright) | ⬜ |
| S4 | 8.01.4 | Shared data: `atlas_buyers`, `atlas_contractors`, `bzp_results` — bez RLS (shared read-only) | ⬜ |
| S5 | 8.01.5 | Tenant provisioning: POST `/api/v2/tenants` → create org + user + seed scoring_config | ⬜ |

## FAZA 8.02 — BZP Auto-sync: background worker
*Backend: services/bzp_sync/*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.02.1 | BZP poller: cron co 15min → GET BZP API → parse XML → upsert `tender` | ⬜ |
| S2 | 8.02.2 | Deduplication: `notice_number` UNIQUE constraint + upsert ON CONFLICT | ⬜ |
| S3 | 8.02.3 | Document fetcher: pobierz SIWZ/SWZ dla nowych tenderów → `bzp_documents` | ⬜ |
| S4 | 8.02.4 | Embedding trigger: po fetchu dokumentu → enqueue embedding job | ⬜ |
| S5 | 8.02.5 | UI: SystemPage — "BZP Sync Status" — last_sync, count_today, errors | ⬜ |

## FAZA 8.03 — AWS ECS deploy: backend + PostgreSQL
*Infrastruktura: Terraform*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.03.1 | Terraform: VPC + subnets + security groups (port 8765, 5432) | ⬜ |
| S2 | 8.03.2 | ECS Fargate: task def dla FastAPI — CPU 1vCPU, 2GB RAM, ECR image | ⬜ |
| S3 | 8.03.3 | RDS PostgreSQL: `db.t3.medium`, Multi-AZ, daily backups, pgvector extension | ⬜ |
| S4 | 8.03.4 | Secrets Manager: DATABASE_URL, JWT_SECRET, VLLM_API_KEY | ⬜ |
| S5 | 8.03.5 | ALB: HTTPS cert (ACM), health check `/api/v2/health`, auto-scaling 1→4 tasks | ⬜ |

## FAZA 8.04 — vLLM deploy: dedykowany GPU server
*Infrastruktura*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.04.1 | GPU instance: g5.xlarge (A10G 24GB) w AWS — Spot dla dev, On-Demand dla prod | ⬜ |
| S2 | 8.04.2 | Docker: vLLM container z LoRA adapter — `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1` | ⬜ |
| S3 | 8.04.3 | Auto-scaling: CloudWatch alarm na queue_depth → scale vLLM replicas | ⬜ |
| S4 | 8.04.4 | Failover: jeśli vLLM down → fallback do OpenAI GPT-4o-mini (transparentnie) | ⬜ |
| S5 | 8.04.5 | Cost control: idle shutdown po 30min bez requestów + Lambda wake-up | ⬜ |

## FAZA 8.05 — Vercel deploy: frontend
*Infrastruktura*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.05.1 | `vercel link` → project yu-na-app | ⬜ |
| S2 | 8.05.2 | Env vars: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_VLLM_URL w Vercel dashboard | ⬜ |
| S3 | 8.05.3 | Preview deploys: GitHub integration → comment z URL na każdym PR | ⬜ |
| S4 | 8.05.4 | Custom domain: yu-na.pl + www + SSL (Vercel auto-cert) | ⬜ |
| S5 | 8.05.5 | Edge config: feature flags per tenant (Vercel Edge Config) | ⬜ |

## FAZA 8.06 — Monitoring: Prometheus + Grafana
*Infrastruktura*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.06.1 | FastAPI metrics: `prometheus-fastapi-instrumentator` → `/metrics` endpoint | ⬜ |
| S2 | 8.06.2 | vLLM metrics: token/s, queue_depth, latency p50/p99 | ⬜ |
| S3 | 8.06.3 | PostgreSQL metrics: pg_stat_user_tables, slow query log | ⬜ |
| S4 | 8.06.4 | Grafana dashboard: 4 panele (API latency / DB queries / vLLM tps / Error rate) | ⬜ |
| S5 | 8.06.5 | Alerty PagerDuty/Slack: error_rate > 5% → natychmiastowe powiadomienie | ⬜ |

## FAZA 8.07 — LangGraph v2: autonomiczny agent budos
*Backend: services/agents/langgraph_v2.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.07.1 | ReAct loop: budos może iterować (plan → act → observe → plan) bez limitu kroków | ⬜ |
| S2 | 8.07.2 | Tool registry: 15 narzędzi (search_tenders, run_rag, calc_ahp, send_alert, ...) | ⬜ |
| S3 | 8.07.3 | Long-term memory: `agent_run.state` jsonb → przywróć kontekst po restart | ⬜ |
| S4 | 8.07.4 | Multi-agent: Supervisor → Analyst + Bidder + Drafter — parallel execution | ⬜ |
| S5 | 8.07.5 | Approval gate: akcje z flag `requires_approval=True` → `approval_request` → human confirm | ⬜ |

## FAZA 8.08 — SQL: OLAP na bazie przetargowej
*Backend: analytics/*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.08.1 | TimescaleDB lub partycjonowanie: `tender` partitioned by `published_at` per year | ⬜ |
| S2 | 8.08.2 | OLAP query: "Ewolucja rynku budowlanego 2018-2026" — CPV × wartość × count per kwartał | ⬜ |
| S3 | 8.08.3 | Cohort analysis: firmy które zaczęły wygrywać w X → tracking trajectories | ⬜ |
| S4 | 8.08.4 | Price index: `cpv_regional_benchmark` → indeks inflacji cen budowlanych | ⬜ |
| S5 | 8.08.5 | UI: MarketIntelPage — zakładka "OLAP Explorer" — ad-hoc pivot table | ⬜ |

## FAZA 8.09 — Fine-tuning v3: domain specialization
*Backend: services/ai/finetune/*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.09.1 | Dataset v3: 500+ par z produkcji — SWZ analizy + wygrane oferty + calibration | ⬜ |
| S2 | 8.09.2 | Instruction tuning: dodaj specjalistyczne tagi (`<SWZ_ANALYSIS>`, `<BID_STRATEGY>`) | ⬜ |
| S3 | 8.09.3 | DPO (Direct Preference Optimization): pozytywne vs negatywne przykłady z feedbacku | ⬜ |
| S4 | 8.09.4 | Eval benchmark: custom test set 50 par — ROUGE + BERTScore + human eval | ⬜ |
| S5 | 8.09.5 | Model merge: LoRA checkpoint merge → GGUF export → llama.cpp fallback | ⬜ |

## FAZA 8.10 — API: rate limiting + API keys + billing
*Backend: services/api/*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.10.1 | Rate limiting: `slowapi` middleware — 100 req/min per API key | ⬜ |
| S2 | 8.10.2 | API keys: `api_keys` table — create/revoke z UI (SettingsPage) | ⬜ |
| S3 | 8.10.3 | Usage tracking: per request log → monthly aggregation dla billing | ⬜ |
| S4 | 8.10.4 | Metered billing: AI analiz count per tenant → Stripe metered subscription | ⬜ |
| S5 | 8.10.5 | Admin panel: super-admin view tenants, usage, revenue (osobna strona /admin) | ⬜ |

## FAZA 8.11 — WebSocket: real-time updates
*Backend + Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.11.1 | WebSocket endpoint: `ws://api/v2/ws/{tenant_id}` — FastAPI WebSocket | ⬜ |
| S2 | 8.11.2 | Events: `tender.new`, `pipeline.status_changed`, `analysis.complete`, `alert.fired` | ⬜ |
| S3 | 8.11.3 | Frontend hook: `useWebSocket` — reconnect on drop, exponential backoff | ⬜ |
| S4 | 8.11.4 | Live bell: NotificationsBell animuje się bez pollingu | ⬜ |
| S5 | 8.11.5 | Collaborative: wielu userów widzi zmiany pipeline w real-time | ⬜ |

## FAZA 8.12 — TED/TED+ integracja: EU przetargi
*Backend: services/ted_sync/*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.12.1 | TED API: GET `/api/v2/ted/search?cpv=&country=PL` — parse JSON | ⬜ |
| S2 | 8.12.2 | TED import: upsert do `tender` z `source='TED'` — deduplicate po notice_number | ⬜ |
| S3 | 8.12.3 | Multi-language SWZ: detect language → translate PL jeśli EN/DE (vLLM translate node) | ⬜ |
| S4 | 8.12.4 | EU filter: ZwiadPage — checkbox "Pokaż EU" → filtruj po source | ⬜ |
| S5 | 8.12.5 | EU alert: notyfikuj gdy TED tender matchuje CPV preferowane org | ⬜ |

## FAZA 8.13 — Mobile PWA: offline + push notifications
*Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.13.1 | Service Worker: cache dashboard + pipeline dla offline read | ⬜ |
| S2 | 8.13.2 | Push notifications: Web Push API — subscribe → store endpoint w DB | ⬜ |
| S3 | 8.13.3 | Push trigger: alert fired → send push do subskrybentów | ⬜ |
| S4 | 8.13.4 | Mobile UI audit: wszystkie strony używalne na 375px | ⬜ |
| S5 | 8.13.5 | Install prompt: A2HS banner po 3 wizycie | ⬜ |

## FAZA 8.14 — Knowledge Graph: graf zależności
*Backend: Neo4j lub pg_graph*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.14.1 | Graf w PostgreSQL: `kg_nodes(id, type, props)` + `kg_edges(src, dst, rel, weight)` | ⬜ |
| S2 | 8.14.2 | Populate: buyer → tender → contractor → CPV → region — z istniejących tabel | ⬜ |
| S3 | 8.14.3 | Recursive CTE query: "Znajdź wszystkich kontrahentów zamawiającego X z lat 2020-2024" | ⬜ |
| S4 | 8.14.4 | RAG extension: knowledge graph jako dodatkowy context dla LangGraph nodes | ⬜ |
| S5 | 8.14.5 | UI: NetworkGraph visualization (force-directed, D3.js) na MarketIntelPage | ⬜ |

## FAZA 8.15 — SQL: advanced analytics functions
*Backend: analytics/advanced.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.15.1 | Survival analysis: jak długo firma utrzymuje win streak — `LEAD/LAG` per NIP | ⬜ |
| S2 | 8.15.2 | Market concentration: HHI index per CPV-4 per rok (Herfindahl–Hirschman) | ⬜ |
| S3 | 8.15.3 | Price clustering: k-means na bid prices per CPV → identify outliers | ⬜ |
| S4 | 8.15.4 | Seasonality decomposition: STL (trend + seasonal + residual) na przetargach per miesiąc | ⬜ |
| S5 | 8.15.5 | UI: AnalyticsPage — zakładka "Advanced" — HHI, survival, price clusters | ⬜ |

## FAZA 8.16 — Platformowe: multi-model AI routing
*Backend: services/ai/router.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.16.1 | AI Router: dla każdego request_type → wybierz model (budos LoRA / GPT-4o-mini / Claude) | ⬜ |
| S2 | 8.16.2 | Routing rules: krótkie pytania → budos (szybko, tanio), złożone analizy → GPT-4o | ⬜ |
| S3 | 8.16.3 | Fallback chain: budos → OpenAI → error — transparentnie dla UI | ⬜ |
| S4 | 8.16.4 | Cost tracking: per request cost_pln w `agent_run` — per tenant billing | ⬜ |
| S5 | 8.16.5 | UI: SystemPage — "AI Usage" — model distribution, cost per dzień | ⬜ |

## FAZA 8.17 — Reliability: backup + restore + DR
*Infrastruktura*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.17.1 | RDS automated backup: retention 7 dni + snapshot przed migracją | ⬜ |
| S2 | 8.17.2 | Point-in-time recovery test: restore do konkretnej minuty — verify data | ⬜ |
| S3 | 8.17.3 | Cross-region backup: S3 bucket replication eu-central-1 → eu-west-1 | ⬜ |
| S4 | 8.17.4 | DR playbook: dokumentacja "jak przywrócić prod w 30min" | ⬜ |
| S5 | 8.17.5 | Chaos test: kill RDS primary → verify failover < 60s | ⬜ |

## FAZA 8.18 — Security: pentest + OWASP hardening
*Backend + Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.18.1 | OWASP Top 10 audit: SQL injection (wszystkie ORM queries), XSS (all user inputs) | ⬜ |
| S2 | 8.18.2 | CSP headers: Content-Security-Policy + HSTS + X-Frame-Options | ⬜ |
| S3 | 8.18.3 | Input validation: Pydantic strict mode na wszystkich POST endpoints | ⬜ |
| S4 | 8.18.4 | Secrets rotation: JWT_SECRET rotation script + zero-downtime | ⬜ |
| S5 | 8.18.5 | Penetration test: ZAP scan → fix top-5 findings | ⬜ |

## FAZA 8.19 — CI/CD: GitHub Actions full pipeline
*DevOps*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.19.1 | Backend CI: pytest (822 tests) + ruff lint + mypy na PR | ⬜ |
| S2 | 8.19.2 | Frontend CI: tsc --noEmit + next build na PR | ⬜ |
| S3 | 8.19.3 | E2E CI: Playwright headless na staging URL po merge | ⬜ |
| S4 | 8.19.4 | CD: auto-deploy do staging na merge main → manual promote do prod | ⬜ |
| S5 | 8.19.5 | Dependabot: auto PR dla outdated deps — auto-merge minor versions | ⬜ |

## FAZA 8.20 — Compliance: GDPR + RODO + audit trail
*Backend + Legal*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.20.1 | Data export: POST `/api/v2/gdpr/export` → ZIP ze wszystkimi danymi usera | ⬜ |
| S2 | 8.20.2 | Right to deletion: POST `/api/v2/gdpr/delete` → cascade delete per tenant | ⬜ |
| S3 | 8.20.3 | Consent management: cookies banner + toggle analytics/marketing | ⬜ |
| S4 | 8.20.4 | Audit trail: immutable `audit_log` — append-only, no UPDATE/DELETE | ⬜ |
| S5 | 8.20.5 | Privacy policy + Terms of Service pages (markdown) | ⬜ |

## FAZA 8.21 — budos Agent: autonomiczne działania
*Backend: services/agents/*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.21.1 | Scheduled agent: co 24h → przeskanuj nowe przetargi → auto-analiza top-10 | ⬜ |
| S2 | 8.21.2 | Proactive alerts: agent wykrywa "deadline w 7d bez decyzji" → push do usera | ⬜ |
| S3 | 8.21.3 | Portfolio optimization: "Jakie przetargi mamy wziąć żeby max profit w Q3?" — LP | ⬜ |
| S4 | 8.21.4 | Competitive intelligence: nowa wygrana konkurenta → instant brief | ⬜ |
| S5 | 8.21.5 | UI: "budos AI jest aktywny" indicator + log akcji agenta w ChatWidget | ⬜ |

## FAZA 8.22 — SQL: time-series + forecasting
*Backend: analytics/forecasting.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.22.1 | `date_trunc('month', published_at)` aggregation → time series per CPV | ⬜ |
| S2 | 8.22.2 | ARIMA forecast w SQL (pg_cron + Python UDF) lub Python Prophet | ⬜ |
| S3 | 8.22.3 | Confidence intervals: bootstrap 1000 samples per CPV per miesiąc | ⬜ |
| S4 | 8.22.4 | Seasonality: wykryj sezonowe wzorce (budowlanka: peak wiosna/jesień) | ⬜ |
| S5 | 8.22.5 | UI: MarketIntelPage — 90d forecast chart z CI bands (recharts ReferenceArea) | ⬜ |

## FAZA 8.23 — Platforma: whitelabel + custom domains
*Backend + Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.23.1 | Whitelabel config: per tenant `brand_name`, `logo_url`, `primary_color` | ⬜ |
| S2 | 8.23.2 | Custom domain: tenant → custom_domain → Vercel Edge Config routing | ⬜ |
| S3 | 8.23.3 | CSS variables: `--accent-primary` z tenant config → real-time theme | ⬜ |
| S4 | 8.23.4 | Email branding: Himalaya templates per tenant brand | ⬜ |
| S5 | 8.23.5 | Admin: super-admin zarządza tenant branding z /admin | ⬜ |

## FAZA 8.24 — Integration: GUS + CEIDG data enrichment
*Backend: services/enrichment/*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.24.1 | GUS API: pobierz dane firmy po NIP → `atlas_buyers/contractors` enrichment | ⬜ |
| S2 | 8.24.2 | CEIDG: weryfikacja statusu firmy (aktywna/zawieszona/wykreślona) | ⬜ |
| S3 | 8.24.3 | KRS: pobierz zarząd, kapitał, forma prawna — cache w `org_enrichment` table | ⬜ |
| S4 | 8.24.4 | Risk score: na podstawie GUS/CEIDG/KRS → "ryzyko kontrahenta" badge | ⬜ |
| S5 | 8.24.5 | UI: BuyerCRMPage + CompetitorPage — "Dane z rejestrów" sekcja | ⬜ |

## FAZA 8.25 — SQL: full-text search optimization
*Backend: DB*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.25.1 | `tsvector` column na `tender.title + tender.description` — GIN index | ⬜ |
| S2 | 8.25.2 | Polish stemming: `pg_catalog.polish` dictionary — właściwa fleksja | ⬜ |
| S3 | 8.25.3 | Hybrid search: FTS rank + semantic similarity → `0.7 * fts + 0.3 * cosine` | ⬜ |
| S4 | 8.25.4 | Search autocomplete: `GET /api/v2/tenders/autocomplete?q=` — top-5 < 50ms | ⬜ |
| S5 | 8.25.5 | Search analytics: log search queries → "Popularne wyszukiwania" w CommandMenu | ⬜ |

## FAZA 8.26 — Platforma: invite-only beta + waitlist
*Frontend + Backend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.26.1 | Waitlist: landing CTA → email → POST `/api/v2/waitlist` → zapisz | ⬜ |
| S2 | 8.26.2 | Invite codes: generate 100 kodów → email batch (Himalaya) | ⬜ |
| S3 | 8.26.3 | Registration: wymaga invite code → verify → create org | ⬜ |
| S4 | 8.26.4 | Admin waitlist: /admin → lista emaili + "Wyślij zaproszenie" button | ⬜ |
| S5 | 8.26.5 | Analytics: conversion rate waitlist → registered → active | ⬜ |

## FAZA 8.27 — Platforma: mobile app (React Native / Flutter)
*Mobile*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.27.1 | Expo/Flutter project setup: auth screen + dashboard | ⬜ |
| S2 | 8.27.2 | Pipeline view: lista kart, swipe do zmiany statusu | ⬜ |
| S3 | 8.27.3 | Push notifications native: FCM integration | ⬜ |
| S4 | 8.27.4 | Offline: SQLite cache ostatnich 50 tenderów | ⬜ |
| S5 | 8.27.5 | App Store / Google Play submit: TestFlight beta | ⬜ |

## FAZA 8.28 — Platforma: public API v3
*Backend: API*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.28.1 | API v3 design: REST + WebSocket + GraphQL (strawberry) | ⬜ |
| S2 | 8.28.2 | GraphQL: queries dla `tenders`, `analysis`, `pipeline` | ⬜ |
| S3 | 8.28.3 | Subscriptions: GraphQL subscription na `tender.new` via WebSocket | ⬜ |
| S4 | 8.28.4 | SDK Python: `pip install yu-na-client` — wrapper nad API v3 | ⬜ |
| S5 | 8.28.5 | SDK TypeScript: `npm install @yu-na/client` — typed client | ⬜ |

## FAZA 8.29 — Performance: DB tuning
*Backend: DB*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.29.1 | EXPLAIN ANALYZE top-10 slow queries — identyfikuj missing indexes | ⬜ |
| S2 | 8.29.2 | Partial indexes: `WHERE pipeline_status IS NOT NULL`, `WHERE embedding IS NULL` | ⬜ |
| S3 | 8.29.3 | Connection pooling: PgBouncer transaction mode — max 20 conn do RDS | ⬜ |
| S4 | 8.29.4 | Query cache: Redis dla `mv_pipeline_kpi` → TTL 5min | ⬜ |
| S5 | 8.29.5 | Vacuum tuning: `autovacuum_vacuum_scale_factor = 0.01` na dużych tabelach | ⬜ |

## FAZA 8.30 — Content: blog + SEO + PR
*Marketing*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.30.1 | Blog MDX: `/blog/[slug]` — NextJS MDX rendering | ⬜ |
| S2 | 8.30.2 | Pierwszy post: "Jak AI zmienia przetargi budowlane w Polsce" | ⬜ |
| S3 | 8.30.3 | SEO: schema.org BlogPosting, canonical, sitemap per post | ⬜ |
| S4 | 8.30.4 | PR outreach: 5 branżowych portali (Inżynier Budownictwa, Builder) | ⬜ |
| S5 | 8.30.5 | Case study: anonimowa firma — "20% wzrost win rate po 3 miesiącach" | ⬜ |

## FAZA 8.31 — Integracja: Microsoft Teams / Slack
*Backend: services/integrations/*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.31.1 | Slack App: OAuth flow → save webhook per workspace | ⬜ |
| S2 | 8.31.2 | Slack notifications: nowy alert → rich message z linkiem do przetargu | ⬜ |
| S3 | 8.31.3 | Teams webhook: POST do Teams channel na GO-decision | ⬜ |
| S4 | 8.31.4 | Slack slash command: `/budos analiza <tender_id>` → trigger LangGraph | ⬜ |
| S5 | 8.31.5 | UI: SettingsPage — zakładka "Integracje" — connect/disconnect Slack/Teams | ⬜ |

## FAZA 8.32 — Integracja: e-Zamówienia / ePUAP
*Backend: services/ezam/*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.32.1 | e-Zamówienia API: GET ogłoszenia → upsert `tender` z source='EZ' | ⬜ |
| S2 | 8.32.2 | ePUAP auth: certyfikat kwalifikowany flow (jeśli dostępny) | ⬜ |
| S3 | 8.32.3 | Dokumenty z e-Zamówień: pobierz SIWZ → `bzp_documents` | ⬜ |
| S4 | 8.32.4 | Deduplication cross-source: BZP ↔ e-Zamówienia — match po notice_number | ⬜ |
| S5 | 8.32.5 | Coverage: 95% polskich przetargów publicznych w bazie | ⬜ |

## FAZA 8.33 — Analytics: cohort + LTV
*Backend + Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.33.1 | Cohort analysis: tenants per signup_month → retention over 6 miesięcy | ⬜ |
| S2 | 8.33.2 | LTV calculation: revenue per tenant × avg lifetime | ⬜ |
| S3 | 8.33.3 | Feature usage: która strona używana najczęściej (Mixpanel-like w DB) | ⬜ |
| S4 | 8.33.4 | Churn prediction: ML na usage patterns → identify at-risk tenants | ⬜ |
| S5 | 8.33.5 | Admin dashboard /admin: KPI biznesowe (MRR, churn, DAU, feature adoption) | ⬜ |

## FAZA 8.34 — Platforma: open source core
*Community*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.34.1 | Open source: BZP scraper + atlas builder → osobne repo `yu-na/bzp-crawler` | ⬜ |
| S2 | 8.34.2 | README: setup guide, docker-compose, seed data | ⬜ |
| S3 | 8.34.3 | GitHub: issues, discussions, contributing guide | ⬜ |
| S4 | 8.34.4 | License: AGPL v3 (core) + Commercial (platform) | ⬜ |
| S5 | 8.34.5 | Community: Discord server + newsletter | ⬜ |

## FAZA 8.35 — AI: multimodal — analiza rysunków budowlanych
*Backend: services/ai/multimodal.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.35.1 | PDF rendering: `pdf2image` → strony do JPG | ⬜ |
| S2 | 8.35.2 | Vision model: Qwen2-VL lub GPT-4o Vision → parse rysunek → extract quantities | ⬜ |
| S3 | 8.35.3 | Przedmiar z rysunku: detect rooms → area calculation → kosztorys lines | ⬜ |
| S4 | 8.35.4 | UI: KosztorysPage — "Importuj z rysunku" → upload PDF → auto przedmiar | ⬜ |
| S5 | 8.35.5 | Accuracy eval: 10 testowych rysunków → % poprawnych pozycji | ⬜ |

## FAZA 8.36 — AI: voice interface
*Frontend + Backend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.36.1 | STT: Whisper via `/api/v2/ai/transcribe` — prześlij audio → tekst | ⬜ |
| S2 | 8.36.2 | TTS: budos odpowiada głosem — `edge-tts` lub OpenAI TTS | ⬜ |
| S3 | 8.36.3 | Voice chat: ChatWidget — przycisk mikrofonu → hold to speak → release → send | ⬜ |
| S4 | 8.36.4 | Voice commands: "Pokaż pipeline" → nawigacja głosem | ⬜ |
| S5 | 8.36.5 | Mobile: voice input na Safari iOS (MediaRecorder API) | ⬜ |

## FAZA 8.37 — AI: document generation
*Backend: services/ai/docgen.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.37.1 | Oferta template engine: Jinja2 → wypełnij danymi tendera + kosztorysu | ⬜ |
| S2 | 8.37.2 | AI fill: LangGraph → wczytaj SWZ → wygeneruj treść oferty per sekcja | ⬜ |
| S3 | 8.37.3 | Umowa o podwykonawstwo: template → AI wypełnienie z danych RFQ | ⬜ |
| S4 | 8.37.4 | Pismo odwoławcze KIO: template + AI → 90% gotowy dokument | ⬜ |
| S5 | 8.37.5 | Document library: `/api/v2/documents/templates` — CRUD templates | ⬜ |

## FAZA 8.38 — Platforma: reseller / partner program
*Business*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.38.1 | Partner portal: /partner — rejestracja, dashboard komisy | ⬜ |
| S2 | 8.38.2 | Referral tracking: `utm_partner` → przypisz do partnera | ⬜ |
| S3 | 8.38.3 | Commission: 20% MRR per zaproszony tenant przez 12 miesięcy | ⬜ |
| S4 | 8.38.4 | Partner materials: logo, pitch deck, one-pager (auto-generated z DB stats) | ⬜ |
| S5 | 8.38.5 | White-label deal: partner może oferować jako własny produkt (custom domain) | ⬜ |

## FAZA 8.39 — Platforma: ENTERPRISE features
*Backend + Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.39.1 | SSO: SAML 2.0 / OAuth OIDC — integracja z AD Azure | ⬜ |
| S2 | 8.39.2 | Audit export: `/api/v2/audit/export` → CSV dla audytorów | ⬜ |
| S3 | 8.39.3 | On-premise option: docker-compose self-hosted guide | ⬜ |
| S4 | 8.39.4 | SLA: 99.9% uptime guarantee + status page (statuspage.io) | ⬜ |
| S5 | 8.39.5 | Dedicated support: Slack channel per ENTERPRISE tenant | ⬜ |

## FAZA 8.40 — Launch: public beta
*Go-to-Market*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 8.40.1 | Beta checklist: security ✓, monitoring ✓, backup ✓, DR ✓ | ⬜ |
| S2 | 8.40.2 | Launch email: 500 firm budowlanych z rejestrów — outreach batch | ⬜ |
| S3 | 8.40.3 | LinkedIn campaign: 3 posty launch week — demo video + case study | ⬜ |
| S4 | 8.40.4 | Product Hunt: post na PH z demo video + 50 upvotes target | ⬜ |
| S5 | 8.40.5 | KPI target: 50 firm aktywnych w 30 dni po launch | ⬜ |

---

# MILESTONE 9 — MARKET DOMINANCE
*Cel: #1 platforma AI dla przetargów budowlanych w Polsce — pełna autonomia, network effects, data moat*

---

## FAZA 9.01 — Data Moat: największa baza przetargów w Polsce
*Backend: data*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.01.1 | Historia: zaimportuj BZP od 2010 roku — 500k+ przetargów | ⬜ |
| S2 | 9.01.2 | TED: import EU przetargów z polskim zamawiającym od 2014 | ⬜ |
| S3 | 9.01.3 | e-Zamówienia: full coverage od 2021 | ⬜ |
| S4 | 9.01.4 | Normalizacja: ujednolicenie nazw firm, CPV, województw cross-source | ⬜ |
| S5 | 9.01.5 | Data quality score: per rekord → confidence% → UI badge | ⬜ |

## FAZA 9.02 — AI: budos v2 — specjalistyczny model budowlany
*Backend: AI*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.02.1 | Dataset v4: 2000+ par z produkcji (12 miesięcy danych realnych) | ⬜ |
| S2 | 9.02.2 | Full fine-tune: Qwen2.5-14B (większy model) na 4x L4 — 3 doby | ⬜ |
| S3 | 9.02.3 | Specialized heads: SWZ_ANALYZER / BID_STRATEGIST / CONTRACT_REVIEWER | ⬜ |
| S4 | 9.02.4 | Benchmark: budos v2 vs GPT-4o na testach branżowych — target: parzyść | ⬜ |
| S5 | 9.02.5 | Quantization: AWQ 4-bit → szybszy inference, mniejszy GPU | ⬜ |

## FAZA 9.03 — Network Effects: collaborative intelligence
*Backend + Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.03.1 | Anonymized benchmarks: "Inne firmy w tym CPV wygrywają przy markup 12-15%" | ⬜ |
| S2 | 9.03.2 | Win/loss signals: anonimowe dane ze wszystkich tenantów → lepsze bidding model | ⬜ |
| S3 | 9.03.3 | Collective intelligence: "3 z 5 firm podobnych do Twojej wzięły ten przetarg" | ⬜ |
| S4 | 9.03.4 | Privacy: differential privacy na zbiorczych statystykach | ⬜ |
| S5 | 9.03.5 | UI: "Benchmark" badge na przetargach — co robią firmy podobne do Ciebie | ⬜ |

## FAZA 9.04 — Platformowe: marketplace podwykonawców
*Backend + Frontend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.04.1 | Subcontractor profiles: rejestracja firmy podwykonawczej w platformie | ⬜ |
| S2 | 9.04.2 | Matching: RFQ → AI dopasowanie do podwykonawców per CPV per region | ⬜ |
| S3 | 9.04.3 | Ratings: oceny podwykonawców po wykonaniu → aggregated score | ⬜ |
| S4 | 9.04.4 | Direct messaging: in-platform chat generalny ↔ podwykonawca | ⬜ |
| S5 | 9.04.5 | Transaction: prowizja 1% od wartości umowy podwykonawczej | ⬜ |

## FAZA 9.05 — AI: predykcja wyników przetargów
*Backend: ML*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.05.1 | Features: CPV, region, wartość, liczba ofert, sezon, zamawiający, typ | ⬜ |
| S2 | 9.05.2 | Model: XGBoost na 50k historycznych wyników → `win_probability(features)` | ⬜ |
| S3 | 9.05.3 | Calibration: Platt scaling → prawdziwe prawdopodobieństwa (nie tylko ranking) | ⬜ |
| S4 | 9.05.4 | SHAP: explanation per prediction → "Dlaczego 67% szans wygrania?" | ⬜ |
| S5 | 9.05.5 | UI: DecyzjaPage — "Szacowane szanse: 67%" z SHAP waterfall | ⬜ |

## FAZA 9.06 — Platforma: vertical expansion — drogi, mosty, instalacje
*Data + AI*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.06.1 | CPV taxonomy: specjalizacja dla infrastruktury drogowej (45200000-9) | ⬜ |
| S2 | 9.06.2 | KNR dla dróg: import stawek GDDKiA → `cpv_regional_benchmark` | ⬜ |
| S3 | 9.06.3 | Specjalne formularze kosztorysu: drogi (m2/km), mosty (mb), instalacje (pkt) | ⬜ |
| S4 | 9.06.4 | Regulatory: prawo budowlane dla dróg — RAG knowledge base | ⬜ |
| S5 | 9.06.5 | Marketing: "YU-NA dla firm drogowych" landing subpage | ⬜ |

## FAZA 9.07 — SQL: graph analytics na przetargach
*Backend: analytics*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.07.1 | Powiązania firm: który zamawiający preferuje których wykonawców — bipartite graph | ⬜ |
| S2 | 9.07.2 | Kartele: wykryj skupiska firm wygrywających razem — community detection | ⬜ |
| S3 | 9.07.3 | PageRank: najważniejsze firmy w ekosystemie zamówień publicznych | ⬜ |
| S4 | 9.07.4 | Anomaly detection: przetarg bez konkurencji → flag jako "podejrzany" | ⬜ |
| S5 | 9.07.5 | UI: NetworkGraph viz — D3.js force-directed, klikalne węzły | ⬜ |

## FAZA 9.08 — Platforma: API marketplace
*Business*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.08.1 | Marketplace: inne firmy mogą sprzedawać dane/modele przez YU-NA API | ⬜ |
| S2 | 9.08.2 | Plugin SDK: `yu-na-plugin-sdk` — third-party integration API | ⬜ |
| S3 | 9.08.3 | Review process: QA + security review każdego pluginu | ⬜ |
| S4 | 9.08.4 | Revenue share: 70/30 dla twórców pluginów | ⬜ |
| S5 | 9.08.5 | Launch plugins: "Wycena SEKOCENBUD", "Integracja ERP Symfonia" | ⬜ |

## FAZA 9.09 — AI: contract risk engine
*Backend: services/ai/contract_risk.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.09.1 | Upload umowy: POST `/api/v2/contracts/{id}/upload-doc` → parse PDF | ⬜ |
| S2 | 9.09.2 | Clause extractor: LangGraph → extract kary, terminy, waloryzacja, gwarancja | ⬜ |
| S3 | 9.09.3 | Risk scoring: każda klauzula → severity (HIGH/MED/LOW) + uzasadnienie | ⬜ |
| S4 | 9.09.4 | Benchmark: czy ta kara jest typowa dla tego CPV? (z historycznych wzorców) | ⬜ |
| S5 | 9.09.5 | UI: ContractsPage — "Analiza Ryzyka Umowy" → report PDF | ⬜ |

## FAZA 9.10 — Platforma: internationale — Czech + Slovakia
*Expansion*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.10.1 | Czech ISZUS: parse XML → `tender` z source='CZ' | ⬜ |
| S2 | 9.10.2 | Slovak EKS: API integration | ⬜ |
| S3 | 9.10.3 | Multilingual UI: i18n (next-intl) PL/EN/CZ/SK | ⬜ |
| S4 | 9.10.4 | Currency: CZK/EUR support w kosztorysach | ⬜ |
| S5 | 9.10.5 | Landing: yu-na.cz + yu-na.sk sub-sites | ⬜ |

## FAZA 9.11 — AI: negocjacje i eskalacja
*Backend: services/ai/negotiation.py*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.11.1 | Negotiation playbook: na podstawie CPV + zamawiający → strategie negocjacyjne | ⬜ |
| S2 | 9.11.2 | Odwołanie KIO: template + AI fill → gotowe pismo w 15 min | ⬜ |
| S3 | 9.11.3 | Wyjaśnienia SWZ: AI draft pytań do zamawiającego per niejasna klauzula | ⬜ |
| S4 | 9.11.4 | Warunki umowy: AI negocjuje klauzule — "Zaproponuj zmiany do § 12" | ⬜ |
| S5 | 9.11.5 | Legal RAG: prawo zamówień publicznych 2019 + nowelizacje w knowledge base | ⬜ |

## FAZA 9.12 — Platforma: YU-NA pro mobile app
*Mobile*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.12.1 | Full mobile parity: wszystkie strony dostępne na mobile | ⬜ |
| S2 | 9.12.2 | Offline-first: background sync, conflict resolution | ⬜ |
| S3 | 9.12.3 | Camera: scan faktur/dokumentów → OCR → import do kontraktu | ⬜ |
| S4 | 9.12.4 | Location: budowę na mapie → GPS tracking zespołu (opt-in) | ⬜ |
| S5 | 9.12.5 | App Store v1.0 launch: iOS + Android | ⬜ |

## FAZA 9.13 — Analytics: BI dashboard enterprise
*Frontend + Backend*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.13.1 | Embedded BI: Metabase lub Superset self-hosted → embed iframe | ⬜ |
| S2 | 9.13.2 | Custom dashboards: drag-drop KPI builder per user | ⬜ |
| S3 | 9.13.3 | Scheduled reports: PDF raport zarządczy co tydzień email | ⬜ |
| S4 | 9.13.4 | Alerting: threshold-based alerts z wykresów (np. win_rate < 20%) | ⬜ |
| S5 | 9.13.5 | Export: każdy dashboard → PNG / PDF / data CSV | ⬜ |

## FAZA 9.14 — Platforma: YU-NA dla inwestorów publicznych
*New vertical*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.14.1 | Zamawiający view: oddzielna rola "Zamawiający" — widzi swoje przetargi | ⬜ |
| S2 | 9.14.2 | Analiza ofert: AI ocena złożonych ofert — rażąco niska cena detection | ⬜ |
| S3 | 9.14.3 | Komisja oceny: workflow wieloosobowy — każdy ocenia swoje kryteria | ⬜ |
| S4 | 9.14.4 | Protokół: auto-generuj protokół z postępowania z AI | ⬜ |
| S5 | 9.14.5 | Pricing: osobny plan "Zamawiający" 299 PLN/mies. | ⬜ |

## FAZA 9.15 — AI: fine-tuning infrastructure
*MLOps*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.15.1 | MLflow: experiment tracking — każdy fine-tune run logowany | ⬜ |
| S2 | 9.15.2 | Auto fine-tune: jeśli dataset > 500 nowych par → auto-trigger overnight | ⬜ |
| S3 | 9.15.3 | Model registry: checkpoints wersjonowane — rollback w 1 komendzie | ⬜ |
| S4 | 9.15.4 | Eval pipeline: auto-eval na 100 testowych par po każdym fine-tune | ⬜ |
| S5 | 9.15.5 | Canary deployment: 10% ruchu na nowy model → monitor quality → promuj | ⬜ |

## FAZA 9.16 — Platforma: community features
*Product*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.16.1 | Forum: per-CPV dyskusje — "Jak wygrać 45000000 Roboty budowlane?" | ⬜ |
| S2 | 9.16.2 | Shared templates: publiczne szablony kosztorysów + ofert | ⬜ |
| S3 | 9.16.3 | Expert network: certyfikowani eksperci prawa zamówień — Q&A | ⬜ |
| S4 | 9.16.4 | Events: webinaria "YU-NA Academy" — szkolenia z obsługi | ⬜ |
| S5 | 9.16.5 | Gamification: punkty za wypełnienie profilu, first GO-decision, first win | ⬜ |

## FAZA 9.17 — SQL: self-healing + anomaly detection
*Backend: DB*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.17.1 | Anomaly detection na bid_intelligence: price outliers → flag do review | ⬜ |
| S2 | 9.17.2 | Data quality checks: pg_cron co 1h → sprawdź NULL ratios → alert jeśli > 5% | ⬜ |
| S3 | 9.17.3 | Auto-heal: missing embeddings → auto-enqueue embedding job | ⬜ |
| S4 | 9.17.4 | Consistency checks: tender bez analysis po 24h → trigger LangGraph | ⬜ |
| S5 | 9.17.5 | Dashboard: "Data Health Score" — procent bazy z pełnymi danymi | ⬜ |

## FAZA 9.18 — AI: continual learning loop
*Backend: ML*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.18.1 | Online learning: embedding model update co tydzień na nowych dokumentach | ⬜ |
| S2 | 9.18.2 | Reward model: RLHF-like — feedback pozytywny/negatywny → reward signal | ⬜ |
| S3 | 9.18.3 | PPO fine-tune: quarterly — optimize na reward model | ⬜ |
| S4 | 9.18.4 | Drift detection: wykryj gdy distribution shift w przetargach (COVID, nowe regulacje) | ⬜ |
| S5 | 9.18.5 | Adaptive calibration: co miesiąc recalibruj `calibration_coeff` per CPV per tenant | ⬜ |

## FAZA 9.19 — Exit / Series A readiness
*Business*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.19.1 | Data room: metryki produktowe, cohort retention, MRR growth | ⬜ |
| S2 | 9.19.2 | Technical due diligence package: architektura, security, skalowanie | ⬜ |
| S3 | 9.19.3 | Pitch deck v3: traction, market size (25 mld PLN/rok PL public procurement) | ⬜ |
| S4 | 9.19.4 | Investor demo: live demo z real danymi — "Szukam przetargów na mosty w Śląskiem" | ⬜ |
| S5 | 9.19.5 | Term sheet simulation: poznaj dilution math, key terms | ⬜ |

## FAZA 9.20 — Platforma: #1 w Polsce
*Vision*

| # | Sprint | Zakres | Status |
|---|--------|--------|--------|
| S1 | 9.20.1 | 500 aktywnych firm w platformie | ⬜ |
| S2 | 9.20.2 | 1 mld PLN pipeline value zarządzany przez YU-NA | ⬜ |
| S3 | 9.20.3 | 30% win rate improvement średnio dla użytkowników vs baseline | ⬜ |
| S4 | 9.20.4 | budos AI — najlepszy model do przetargów budowlanych w Polsce | ⬜ |
| S5 | 9.20.5 | Market position: cytowany w branżowych mediach, konferencjach, uczelniach | ⬜ |

---

## PODSUMOWANIE

| Milestone | Fazy | Sprinty | Fokus |
|-----------|------|---------|-------|
| M5 (done) | 20 | 100 | Frontend live — zdobywanie kontraktów |
| M6 (done) | 20 | 100 | Frontend live — realizacja |
| **M7** | **40** | **200** | Intelligence Layer — SQL/RAG/LangGraph/AI |
| **M8** | **40** | **200** | Scale & Production — AWS/Multi-tenant/vLLM prod |
| **M9** | **40** | **200** | Market Dominance — data moat/network effects |
| **TOTAL** | **160** | **800** | **State-of-Art AI platforma przetargowa** |

### Priorytety M7 (zacznij tu):
1. **7.01-7.02** — pgvector + RAG — to fundament wszystkiego
2. **7.03-7.04** — LangGraph pipeline — operator AI
3. **7.05-7.06** — Materialized Views — wydajność dashboardu
4. **7.07** — ChatWidget wieloturowy z tool calls
5. **7.08-7.11** — Strony UI z AI (Zwiad, Pipeline, Decyzja)
