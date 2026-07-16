# Terra.OS — Master Plan Finalizacji
**Data:** 2026-07-16  
**Metodyka:** NEXUS 6-Agent Audit (2 batche × 3 agentów)  
**Agenci:** Backend Architect, Security Architect, Sprint Prioritizer, CFO, DPO, Senior Developer

---

## EXECUTIVE SUMMARY

Terra.OS to dojrzała platforma SaaS (432 endpointy, 112 tabel DB, 4137 testów, 35 stron UI) działająca na drastycznie przewymiarowanej infrastrukturze (g6.24xlarge, ~28k PLN/mies) z **zerowym przychodem**. System jest funkcjonalnie kompletny na poziomie ~75%, ale ma **krytyczne luki** w izolacji tenantów, brakujący Stripe live, i problemy z routingiem UI.

**Estymata do production launch: 8-12 tygodni z 2-3 devami.**  
**Break-even po optymalizacji infra: 4-8 klientów.**

---

## STAN AKTUALNY — METRYKI

| Metryka | Wartość | Ocena |
|---------|---------|-------|
| API endpoints | 432 | ✅ Kompletne |
| DB tabele | 112 + 15 materialized views | ✅ Bogate |
| Unit testy | 4137 | ✅ Solidne |
| Przetargi w DB | 3716 (BZP+TED+BIP) | ✅ Live data |
| Strony UI | 35 komponentów | ✅ Zaimplementowane |
| Integracje | BZP, TED, BIP, GUS, NBP, Open-Meteo, Bedrock AI | ✅ Działające |
| GPU utilization | 0% | 🔴 Zmarnowane |
| Przychód | 0 PLN | 🔴 Zero |
| Burn rate | ~28-32k PLN/mies | 🔴 Krytyczny |
| Bezpieczeństwo | 6.5/10 | 🟡 Wymaga pracy |
| RODO | Częściowa zgodność | 🟡 P0 przed launchen |

---

## 🔴 P0 — NAPRAWIONE DZIŚ (16.07.2026)

| # | Problem | Fix | Status |
|---|---------|-----|--------|
| 1 | Pogoda nie działa | `NEXT_PUBLIC_API_URL` wskazywał na betatp (8765) zamiast terra-os (8000) | ✅ DONE |
| 2 | Demo user widzi 0 przetargów | `org_id` mismatch — user w innym tenancie niż dane | ✅ DONE |
| 3 | Scrapery BZP/TED/BIP | Platform document scraper + BIPScraper class | ✅ DONE (wcześniej) |

---

## 🔴 P0 — DO NATYCHMIASTOWEJ NAPRAWY

### Infra & Koszty (CFO)
| # | Problem | Impact | Rozwiązanie | Oszczędność |
|---|---------|--------|-------------|-------------|
| 1 | GPU g6.24xlarge z 0% utilization | ~21k PLN/mies zmarnowane | Downgrade → m7i.4xlarge (16 vCPU, 64GB) | **18 700 PLN/mies** |
| 2 | Stripe nie live | 0 przychodu | Aktywacja test→live, webhook prod URL | Revenue start |

### Bezpieczeństwo (Security Architect)
| # | Problem | Impact | Rozwiązanie |
|---|---------|--------|-------------|
| 3 | 74 tabele z tenant_id BEZ RLS | Cross-tenant data leakage | Script: `ALTER TABLE X ENABLE ROW LEVEL SECURITY; CREATE POLICY...` |
| 4 | `/api/v1/subcontractors` + `/equipment` zwraca WSZYSTKIE org | IDOR confirmed | Dodać `WHERE org_id = current_user_org()` |
| 5 | JWT fallback secret w kodzie | Token forgery possible | Env-only secret, rotate |

### Architektura (Backend Architect)
| # | Problem | Impact | Rozwiązanie |
|---|---------|--------|-------------|
| 6 | N+1 w module3.py (1920+ queries/req) | Timeout na większych danych | Refactor → joinedload / subquery |
| 7 | `competency` — 210k seq_scans, 0 indeksów | Slow queries | CREATE INDEX |
| 8 | Duplikaty tabel (employee/employees, calendar_event/calendar_events) | Fragmentacja danych | Migracja → merge do jednej |

### RODO (DPO)
| # | Problem | Impact | Rozwiązanie |
|---|---------|--------|-------------|
| 9 | Brak automatycznej retencji/purge | Dane narastają bezterminowo | Cron job cleanup >24 mies |
| 10 | Niepełna kaskada right to erasure | Dane w employee, buyer_crm, email_logs zostają | Rozszerzenie cascade delete |

---

## 🟡 P1 — SPRINT 1-2

| # | Problem | Agent | Sprint |
|---|---------|-------|--------|
| 1 | Rate limiting na auth (brute-force) | Security | S1 |
| 2 | Stripe sandbox → live checkout | Sprint Prioritizer | S2 |
| 3 | CI/CD prod deployment (auto-deploy) | Senior Dev | S2 |
| 4 | Email transakcyjny (welcome, reset, alert) | Senior Dev | S2 |
| 5 | CORS wildcard methods fix | Security | S1 |
| 6 | Password policy (min 12 chars, complexity) | Security | S1 |
| 7 | DPA podpisany + flow akceptacji w UI | DPO | S2 |
| 8 | Sub-processors lista (Bedrock, Stripe, Open-Meteo) | DPO | S2 |
| 9 | Backup automation + tested restore | Senior Dev | S2 |
| 10 | Export PDF kosztorysu | Sprint Prioritizer | S2 |

---

## 🔵 P2 — SPRINT 3-4

| # | Problem | Sprint |
|---|---------|--------|
| 1 | GDPR full export + delete flow | S3 |
| 2 | JWT refresh + secure cookie | S3 |
| 3 | MFA (TOTP) | S3 |
| 4 | Observability (Prometheus/Grafana) | S4 |
| 5 | Module3 OR-Tools logistics | S4-5 |
| 6 | IMAP email poller (RFQ broker) | S3 |
| 7 | Structured logging | S4 |
| 8 | Dependency audit (Trivy/Snyk) | S3 |
| 9 | Column-level encryption (hourly_rate, PESEL) | S4 |
| 10 | AI profilowanie disclosure (Art. 22 GDPR) | S3 |

---

## PLAN SPRINTOWY — 6 SPRINTÓW (12 TYGODNI)

### Sprint 1 (Tydzień 1-2): HARDENING
**Cel:** Security P0 + infra optimization  
**Agenci:** Security Architect, Backend Architect, DevOps

- [ ] Downgrade EC2 → m7i.4xlarge
- [ ] RLS na wszystkich 74 tabelach z tenant_id
- [ ] Fix IDOR w subcontractors/equipment/calendar
- [ ] Rate limiting na auth (10/min)
- [ ] Fix N+1 w module3.py
- [ ] Indeksy na competency, historical_tenders
- [ ] Merge duplicate tables (employee → employees)
- [ ] JWT secret → env only
- [ ] Password policy upgrade

**DoD:** Zero P0 security, <500ms avg response, <5k PLN/mies infra

---

### Sprint 2 (Tydzień 3-4): REVENUE
**Cel:** Stripe live + email + deploy pipeline  
**Agenci:** Backend Architect, Frontend Dev, DevOps

- [ ] Stripe live keys + webhook prod
- [ ] Checkout flow (Pro/Business/Enterprise)
- [ ] Email transakcyjny (SES/Resend)
- [ ] staging.terra-os.pl z auto-deploy
- [ ] DPA template + acceptance flow
- [ ] Export kosztorys PDF/DOCX
- [ ] UI routing fix (33 stron → proper Next.js routes)

**DoD:** Stripe sandbox checkout → subscription OK, staging online

---

### Sprint 3 (Tydzień 5-6): COMPLIANCE
**Cel:** RODO pełne + backup + JWT refresh  
**Agenci:** DPO, Security Architect, Senior Dev

- [ ] GDPR export/delete endpoints
- [ ] Data retention cron (>24 mies → archive)
- [ ] Consent tracking z IP/UA
- [ ] Sub-processors register
- [ ] JWT refresh + HttpOnly cookies
- [ ] Backup daily + tested restore
- [ ] MFA (TOTP)
- [ ] Privacy Policy update (Art. 22)
- [ ] Test coverage ≥ 85%

**DoD:** OWASP clean, GDPR checklist OK, backup tested

---

### Sprint 4 (Tydzień 7-8): POLISH
**Cel:** Performance + monitoring + UX  
**Agenci:** Backend Architect, Frontend Dev, DevOps

- [ ] Prometheus + Grafana dashboards
- [ ] Structured logging (JSON)
- [ ] Module3 OR-Tools integration
- [ ] Column encryption (sensitive data)
- [ ] UI performance (lazy loading, code splitting)
- [ ] Onboarding wizard for new tenants
- [ ] API docs (Swagger UI polish)

**DoD:** P95 < 200ms, monitoring live, onboarding flow complete

---

### Sprint 5 (Tydzień 9-10): SCALE
**Cel:** Multi-tenant production + mobile  
**Agenci:** Backend Architect, Flutter Dev, AI Engineer

- [ ] Multi-tenant onboarding (self-service signup)
- [ ] Flutter mobile MVP (tender list + detail + push)
- [ ] LangGraph agent orchestration
- [ ] AI-powered tender matching improvements
- [ ] Load testing (100 concurrent users)
- [ ] CDN for static assets

**DoD:** 100 concurrent users OK, mobile app in TestFlight

---

### Sprint 6 (Tydzień 11-12): LAUNCH
**Cel:** GTM + first customers + operate  
**Agenci:** Growth Hacker, Senior Dev, PM

- [ ] Landing page SEO-optimized
- [ ] 3 pilot klientów onboarded
- [ ] Helpdesk/support system
- [ ] SLA definition + uptime monitoring
- [ ] Post-launch learning loop
- [ ] Marketing automation (Lemlist campaigns)

**DoD:** 3 płacących klientów, SLA 99.5%, monitoring 24/7

---

## FINANSE — AFTER OPTIMIZATION

| Scenariusz | TCO/mies | Break-even | Klienci |
|-----------|----------|------------|---------|
| Obecny (g6.24xlarge) | ~28-32k PLN | 56-64 Pro lub 19-21 Business | 🔴 Nierealne |
| Po downgrade (m7i.4xlarge) | ~3.5-5k PLN | **4-8 Pro** lub **3-4 Business** | ✅ Realne |
| Reserved Instance (1yr) | ~2.5-3.5k PLN | 3-5 Pro lub 2-3 Business | ✅ Optymalne |

**Pricing model:** Free (0) → Pro (499 PLN/mies) → Business (1499 PLN/mies) → Enterprise (custom)

---

## PEŁNE RAPORTY (szczegóły)

| Raport | Plik | Słowa |
|--------|------|-------|
| Architektura | `/tmp/terra_audit_architecture.md` | 3200 |
| Bezpieczeństwo | `/tmp/terra_audit_security.md` | 2500 |
| Roadmap sprintowy | `/tmp/terra_roadmap.md` | 3000 |
| Finanse / TCO | `/tmp/terra_audit_finance.md` | 3300 |
| RODO / GDPR | `/tmp/terra_audit_rodo.md` | 4065 |
| Integracje / Frontend | `/tmp/terra_audit_integration.md` | 3000 |

---

## CO JEST GOTOWE (nie wymaga pracy)

- ✅ Auth JWT (login, register, refresh, /me)
- ✅ Pełny pipeline ingestion (BZP + TED + BIP) — 3716 przetargów live
- ✅ Platform document scraper (16+ plików per przetarg)
- ✅ Silnik wycen (Monte Carlo, L1 symbolic, L2 stochastic)
- ✅ AI chat (Bedrock Claude Sonnet)
- ✅ Pogoda budowlana (Open-Meteo, construction_risk)
- ✅ GUS indicators + NBP currencies
- ✅ Health endpoints (live, ready, detailed)
- ✅ 33 stron UI (React, Framer Motion, Recharts, Leaflet)
- ✅ Docker configs (API + UI + compose.prod)
- ✅ CI/CD workflows (4 GitHub Actions)
- ✅ Security headers + CSP
- ✅ Parametrized SQL (no injection risk)
- ✅ Pydantic input validation
- ✅ Export XLSX/DOCX kosztorysu
- ✅ Alerts + email dispatcher
- ✅ Calendar sync from tenders
- ✅ Gantt tasks per tender
- ✅ BZP document download + PDF parsing

---

*Generated by NEXUS Orchestrator — 6 parallel audit agents, 2 batches, ~6 min total execution time.*
