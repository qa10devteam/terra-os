# GRUNT — Plan 6 Iteracji (MVP + Production Path)

> Dokument oparty na `BLUEPRINT_GRUNT_technical.md` + `michal_input.yaml`
> Cel: zbudować w pełni działający system dla wykonawcy robót ziemnych

---

## 📋 Kontekst biznesowy

**Klient:** Firma p. Michała — roboty ziemne, Dzierżoniów, 7 osób
**Problem:** Strata czasu/danych przed przetargiem (zwiad → analiza → kosztorys → decyzja)
**Rozwiązanie:** Lokalna aplikacja desktopowa (Tauri + Next.js + FastAPI + LangGraph)
**AI:** Hybrid — Ollama lokalnie (~0 zł) + Claude Bedrock Frankfurt (trudne rozumowanie)
**Warianty:** 65k (GRUNT) → 180k (SILNIK) → 560k (MÓZG)

---

## 🔄 6 Iteracji

### Iteracja 1 — SPIKE + Fundament (Tygodnie 1-3)
**Cel:** De-risk fixed-price, zweryfikować techniczne założenia, zbudować szkielet

- [ ] Architektura Tauri (Rust shell + Next.js UI + FastAPI sidecar)
- [ ] PostgreSQL 16 + pgvector schema (tenant_id, tender, estimate, discrepancy)
- [ ] LangGraph agent runtime (ingest, tracker, analysis, estimator)
- [ ] Ollama integration (Qwen3 14B + Gemma 4 12B vision)
- [ ] Bedrock client (Claude, eu-central-1)
- [ ] MCP tooling + AG-UI (CopilotKit)
- [ ] Audit log (append-only)
- [ ] Backup/DR scaffold
- [ ] **SPIKE:** L1 solver pairing (clingo + Z3) na 2-3 realnych przetargach
- [ ] **SPIKE:** Class-C axiom corpus (earthworks domain) workshop
- [ ] **SPIKE:** Firm-calibration cold-start on historical data

**Deliverables:** Working prototype of Tauri shell + DB + agents + AI routing

---

### Iteracja 2 — ZWIAD (Module 1) (Tygodnie 3-9)
**Cel:** Znajdź i przeanalizuj przetargi

- [ ] BZP API connector (`ezamowienia.gov.pl`)
- [ ] TED connector (EU thresholds)
- [ ] Baza Konkurencyjności connector
- [ ] Municipal BIPs connector (4 voivodeships)
- [ ] CPV filtering + geo matching + owner profile scoring
- [ ] Document pipeline: fetch SWZ/design/przedmiar → OCR → parse → chunk → embed
- [ ] Agentic RAG: summary + red-flags + discrepancy engine (L1 basic)
- [ ] Tracker agent (deadlines, version changes)
- [ ] UI: Tender list + detail view + chat brain

**Deliverables:** Working discovery module with real tender data

---

### Iteracja 3 — KOSZTORYSANT + L1/L2 Engine (Module 2) (Tygodnie 8-16)
**Cel:** Dwa warianty kosztorysu + silnik decyzyjny

- [ ] Variant A: doc-based (Rozp. MRiT 2021, KNR/KNNR/KSNR mapping)
- [ ] Variant B: owner engine (Excel import, real rates, RMS)
- [ ] A↔B delta → margin headroom visualization
- [ ] L1 symbolic engine (ASP/clingo + Z3 SMT)
- [ ] L2 stochastic (Monte Carlo, Sobol sensitivity)
- [ ] Email-broker agent (IMAP/SMTP, RFQ to subcontractors)
- [ ] Interactive kosztorys (chat-brain edits + variable sidebar)
- [ ] Live rule-violation detection (L1)
- [ ] UI: Cost estimator + risk visualization + rule violations

**Deliverables:** Full estimating module with decision engine

---

### Iteracja 4 — Kalibracja + Learning Loop (Tygodnie 15-19)
**Cel:** Dopasowanie pod firmę p. Michała

- [ ] Bayesian update from closed contracts
- [ ] Firm-specific productivity/overhead calibration
- [ ] KNR/market priors → firm priors
- [ ] UAT on real cases
- [ ] Performance optimization
- [ ] Bug fixes from UAT
- [ ] Documentation + user manuals

**Deliverables:** Calibrated system ready for production

---

### Iteracja 5 — Deploy + Training (Tygodnie 19-21)
**Cel:** Wdrożenie na docelowym sprzęcie

- [ ] Tauri installer packaging (Windows/macOS/Linux)
- [ ] Auto-update channel
- [ ] Hardware setup (RTX 5060 Ti 16GB or RTX 3090 24GB)
- [ ] Ollama model download + configuration
- [ ] Automated backup setup (disk/NAS)
- [ ] User training (p. Michał + estimator)
- [ ] Handover documentation
- [ ] RODO compliance (data notice, backup testing)

**Deliverables:** Production-ready installed application

---

### Iteracja 6 — MÓZG (Module 3) (Tygodnie 22-32)
**Cel:** Zarządzanie budową + mobile app

- [ ] Resource registry (equipment: excavators/vans; 7 employees)
- [ ] Contract pipeline (won-tender → delivery)
- [ ] Team calendar + availability
- [ ] MILP logistics (OR-Tools for equipment allocation/routing)
- [ ] Daily-plan dispatch (photos, drawings, Google Maps, cautions)
- [ ] Flutter mobile app (iOS + Android)
- [ ] Messenger integration (WhatsApp/Telegram)
- [ ] Offline cache + sync
- [ ] Push notifications
- [ ] Per-device auth (Tailscale tunnel)

**Deliverables:** Complete earthworks management system with mobile app

---

## 🎯 Kluczowe decyzje (LOCKED)

| Decyzja | Wartość |
|---------|---------|
| Deployment model | Installed local desktop (Tauri) |
| AI topology | Hybrid: Ollama local + Bedrock Frankfurt |
| Decision engine | L1 symbolic + L2 stochastic + L3 neuro-symbolic |
| Mobile app | Flutter (iOS+Android), Tier 3 only |
| Cloud region | eu-central-1 (RODO) |
| Vector store | pgvector in local Postgres |
| Hardware path | B (hybrid, GPU 16-24GB) |

---

## 📊 KPI (z oferty)

| KPI | Baseline | 90 day | 180 day | 365 day |
|-----|----------|--------|---------|---------|
| Czas analizy przetargu | 1-2 dni | 4h | 1h | <30 min |
| Przetargów/miesiąc | 4-6 | 15 | 30 | 40+ |
| Czas kosztorysu | 5-15 dni | 1 dzień | 4h | 2h |
| Pułapki wykryte | 0 (na budowie) | automatycznie | 90% | pełne |
| Czas planu dnia | 30-60 min | 5 min | 2 min | 1 min |

---

## 🏗️ Stack

| Warstwa | Technologia |
|---------|-------------|
| Desktop shell | Tauri (Rust) |
| UI | Next.js 16 + Tailwind v4 + CopilotKit |
| App API | FastAPI (Python) |
| Agents | LangGraph + MCP tools |
| Decision engine | clingo, Z3, NumPy/SciPy, OR-Tools |
| DB | PostgreSQL 16 + pgvector |
| Local LLM | Ollama: Qwen3 14-32B, Gemma 4 12B |
| Cloud LLM | Claude (Bedrock eu-central-1) |
| Mobile (Tier 3) | Flutter |

---

*Blueprint v1.0 → QA10 R&D Division → 2026-06-21*
