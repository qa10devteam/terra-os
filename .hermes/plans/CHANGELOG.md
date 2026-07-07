# Changelog

All notable changes to Terra.OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- M7: OR-Tools MILP logistics optimizer scaffolding
- Flutter mobile app — device registration, offline plan cache (Drift)
- LangGraph supervisor pipeline wiring M1→M2→M3

---

## [0.3.0] — 2024-Q4 — *M5: Decision Engine L2 (Monte Carlo)*

### Added
- **L2 Stochastic Engine** (`services/engine/l2_stochastic.py`):
  - Constrained Monte Carlo sampler (default 2 000 samples, configurable via `n_samples`)
  - Bayesian priors on cost overrun, volume deviation, and market price uncertainty
  - Sobol sensitivity analysis — returns `drivers[]` with `S1` and `ST` indices
  - `margin_p10 / margin_p50 / margin_p90` distribution output
  - `win_prob_at_price[]` curve (price → win probability)
  - Deterministic under fixed `seed` parameter (reproducibility test added)
- **`POST /api/v1/tenders/{id}/engine/run`** now executes L1 + L2 in a single call, persisting results to `risk_run` table
- **`POST /api/v1/tenders/{id}/risk`** standalone L2 endpoint (does not re-run L1)
- `EngineResultSchema.risk` field added with full `RiskSchema` payload
- `risk_run` DB table (migration `0004_engine_l2.py`): stores samples, p10/p50/p90, win_prob, drivers
- Determinism test: fixed seed reproduces exact p50 value across runs
- Win-probability monotonicity test: higher price → lower win_prob (guard test)
- No L1-violating sample can appear in L2 output (constraint propagation guard test)

### Changed
- `GET /api/v1/tenders/{id}/engine` now returns latest stored `risk_run` alongside discrepancies
- Engine router response model updated to `EngineResultSchema` v2

### Fixed
- L1 axiom A003 false-positive on tenders with implicit dewatering scope
- Cursor pagination edge case when exactly `limit` items exist

---

## [0.2.0] — 2024-Q3 — *M4: Decision Engine L1 (Symbolic)*

### Added
- **L1 Symbolic Engine** (`services/engine/l1_symbolic.py`):
  - clingo ASP solver + Z3 SMT integration for hard constraint checking
  - Earthworks class-C axiom corpus (Phase 0 validation on 3 real tenders):
    - `A001` — Masa bilans: cut volume vs fill volume balance check
    - `A002` — Odwodnienie: dewatering item required when groundwater depth < 1.5 m
    - `A003` — Suma: estimate line totals must reconcile to `total_net_pln` (zero tolerance)
    - `A004` — Cena rażąco niska: price ≥ 30% below buyer estimate triggers `warn`
    - `A005` — Termin: deadline feasibility vs mobilization norm
    - `A006` — Gwarancja: warranty period within statutory bounds
  - Violations emitted with `provenance` (page + section), `severity` (`warn` | `block`), and `axiom_id`
- **`POST /api/v1/tenders/{id}/engine/run`** — L1 only (L2 added in v0.3.0)
- **`POST /api/v1/tenders/{id}/rules/check`** — live axiom check, not persisted (A004/A005/A006 only)
- `discrepancy` DB table (migration `0003_engine_l1.py`): replaces-on-run, stores violations
- Golden fixture tests: broken przedmiar → exact expected violation set; clean fixture → zero violations
- Per-axiom unit tests (`tests/engine/test_axioms.py`)

### Changed
- Tender `status` state machine extended: `analyzing → estimated → decided_go / decided_nogo`
- `VALID_STATUSES` set updated in tenders router
- `analysis` table `key_facts` JSONB column added (stores engine-relevant facts)

### Fixed
- `estimate_line` sum rounding: now uses `NUMERIC(15,4)` throughout, eliminating float drift
- Missing `tenant_id` propagation in document pipeline

### Security
- All engine endpoints require authenticated user (`AuthUser` dependency)
- `explanation_md` is the **only** LLM-authored field in `EngineResult` (guard test added)

---

## [0.1.0] — 2024-Q2 — *M3: Kosztorysant (Estimator MVP)*

### Added
- **Tier 1 complete** — full pre-engine workflow operational end-to-end on fixtures
- **Estimator Variant A (doc)** — simplified calc `Wk = Σ(Lj × Cj)` per Rozp. MRiT 20.12.2021
  - `Cj` sourced from market price base config or KNR priors mapped from `knr_code`
  - Mirrors buyer's methodology for apples-to-apples comparison
- **Estimator Variant B (owner)** — detailed calc `Cj = Σ(n×c) + Kpj + Zj`
  - Uses private `rate_card` (RMS efficiencies) + `calibration_coeff`
  - **Computed entirely in deterministic local code** — owner rates never sent to any cloud LLM
- **`GET /api/v1/estimates/{id}/compare`** — returns `delta_pln` and `margin_headroom_pct`
- Sum-reconciliation tests: line totals == `total_net_pln` (zero tolerance, rounding policy enforced)
- **`PATCH /api/v1/estimates/{id}/params`** — variable sidebar: overhead %, profit %, efficiency multipliers
- **`POST /api/v1/estimates/{id}/chat`** (SSE) — chat-brain edits: LLM proposes `{op, target, value}`, applied by deterministic code
- Audit trail: every param change writes an `audit_log` row
- **M1 (Ingestion):** BZP + TED + BK fixture connectors, CPV/geo filter, deterministic scorer, `match_score`, `match_reason`
- **M2 (Documents):** pymupdf text extraction + Gemma VLM-OCR for scans, `przedmiar_item` parser, chunk+embed into `document_chunk`, Agentic RAG summary with cited red-flags
- M0 scaffold: 32-table DB schema, Alembic migrations, `/health`, shared packages (Provenance, Flag, AuditWriter, TerraError), 14 tests green

### Changed
- N/A (initial release)

### Security
- Owner `rate_card` data isolated in local `rate_card` table — no-egress guard test added
- `TERRA_SECRET_KEY` required for JWT signing; startup fails fast if missing
- Refresh token rotation: old token revoked on each `/refresh` call

---

[Unreleased]: https://github.com/your-org/terra-os/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/your-org/terra-os/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/your-org/terra-os/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/your-org/terra-os/releases/tag/v0.1.0
