# Terra.OS — Research & Competitive Discovery
**Data: czerwiec 2026 | Zakres: 30+ produktów, 8 obszarów, 30+ źródeł danych**

---

## CZĘŚĆ 1 — BAZY DANYCH KOSZTORYSOWYCH

### Ranking datasety (najlepsze dla Terra.OS)

| # | Źródło | Pozycji | Format | Cena | API | Ocena |
|---|--------|---------|--------|------|-----|-------|
| 1 | **INTERCENBUD** (Athenasoft) | 45 000+ KNR | online+plik | sub. kwart. | ❌ (negocjuj) | ⭐⭐⭐⭐⭐ |
| 2 | **DDC CWICR PL_WARSAW** | 55 719 | CSV/Parquet/Qdrant | **FREE CC BY** | ✅ Qdrant REST | ⭐⭐⭐ |
| 3 | **SEKOCENBUD RMS** | 50 000+ | MDB/DBF | sub. kwart. | ❌ | ⭐⭐⭐⭐⭐ |
| 4 | **Atlas Przetargów** | 1,4M umów | Parquet/CSV | **FREE CC BY** | ✅ pandas | ⭐⭐⭐ |
| 5 | **GUS BDL API** | wskaźniki | JSON/XML | **FREE** | ✅ REST | ⭐⭐⭐ |
| 6 | eKosztorysowanie.pl | SEKOC+ORGBUD | SaaS | 749 PLN/mies | ✅ Business | ⭐⭐⭐⭐ |

### Kluczowe odkrycie: żadne polskie źródło (SEKOCENBUD, INTERCENBUD) nie ma publicznego API
→ Wszystkie wymagają licencji lub partnerstwa. Jedyna droga: negocjacja z Athenasoft (właściciel Intercenbud + Norma PRO).

### Rekomendowana architektura hybrydowa:
```
WARSTWA 1 — Ceny rynkowe (Intercenbud/SEKOCENBUD — płatne, polskie normatywy)
WARSTWA 2 — AI search (DDC CWICR PL_WARSAW — FREE, Qdrant semantic search)
WARSTWA 3 — Benchmarki (Atlas Przetargów — FREE, 1,4M rekordów BZP)
```

---

## CZĘŚĆ 2 — MAPA KONKURENCJI (Polska)

```
THREAT MATRIX:
Firma             │ PL │ Budownictwo │ Kosztorys AI │ Kanban │ MC Risk │ Threat
──────────────────┼────┼─────────────┼──────────────┼────────┼─────────┼────────
Przetargi.io      │ ✅ │ ✅          │ ✅ Excel 5min│ ❌     │ ❌      │ 🔴 HIGH
Minerva           │ ✅ │ ✅ 200+ firm│ ❌           │ ❌     │ ❌      │ 🟠 HIGH
TenderPro         │ ✅ │ ✅          │ ❌           │ ❌     │ ❌      │ 🟡 MED
Mimira            │ ✅ │ ✅          │ ❌           │ ❌     │ ❌      │ 🟡 MED
eKosztorysowanie  │ ✅ │ ✅          │ ✅ KNR       │ ❌     │ ❌      │ 🟢 LOW
Altura (NL/€8M)   │ ❌*│ ✅ BAM/EY   │ ❌           │ ❌     │ ❌      │ 🟡 MED*
Tendium (SE)      │ ❌ │ ❌ generic  │ ❌           │ ✅     │ ❌      │ 🟢 LOW
──────────────────┼────┼─────────────┼──────────────┼────────┼─────────┼────────
TERRA.OS          │ ✅ │ ✅          │ ✅ KNR+MC   │ ✅     │ ✅ P10/50/90 │ 💎 USP
```

### Kluczowi gracze:
- **Przetargi.io** — AI wycena w 5 min z SWZ, 121 obszarów analizy, edytowalny Excel. Brak Kanban/Monte Carlo.
- **Minerva** — $3M USD (Open Ocean VC), 450+ klientów, 370-460% YoY growth, 0% churn. Discovery tool, zero kosztorysowania.
- **Altura** (€8M Series A 2025) — globalny wzorzec: connected AI workflows, sentence-level traceability. Brak PL, brak kosztorysowania.
- **Tendium** (Sweden) — BidFlow Kanban dla przetargów. Brak PL, brak kosztorysowania.

---

## CZĘŚĆ 3 — LUKI RYNKOWE (gdzie Terra.OS może być #1)

1. **Full Execution OS** — BZP discovery → go/no-bid → Kanban → SWZ parse → kosztorys → Monte Carlo → submission. Nikt tego nie robi w jednym narzędziu.
2. **Monte Carlo Risk** — Zero probabilistycznych risk engines w całym PL ecosystem. Terra.OS może być PIERWSZYM w CEE.
3. **Competitor Intelligence** — atlasprzetargow 1,4M rekordów (FREE CC BY). "Kto wygrywa w CPV 45xxx w Mazowszu?" — nikt tego nie oferuje.
4. **KNR/RMS Integration** — Zero AI startupów łączy polskie normatywy z AI tender management.
5. **Dark SaaS Aesthetic** — Wszystkie PL narzędzia: jasny korporacyjny design z 2015. Terra.OS definiuje nową estetykę.
6. **BZP MCP Server** — Wzorzec: vergabe-mcp (Niemcy, MIT). Nikt nie zrobił polskiego odpowiednika.
7. **Ukraina/ProZorro** — Polskie firmy budujące Ukrainę + brak narzędzi dla wykonawców w ProZorro. Future expansion.

---

## CZĘŚĆ 4 — TOP 5 FEATURE IDEAS

### 💡 #1 — "SWZ Autopilot" (ContextGem-powered)
```
SWZ ZIP (do 2GB) → Unstructured.io → Reducto AI → ContextGem declarative extraction
→ Claude 3.5 Sonnet → risk analysis → go/no-bid score

Output <5 minut:
- Compliance checklist (czy firma spełnia wymagania formalne)
- Risk flags z sentence-level cytatami ze SWZ (nie hallucynacje!)
- Top 10 pytań do zamawiającego (AI generuje)
- Go/no-bid score 0-100 z uzasadnieniem
```
Differentiator vs Przetargi.io: sentence-level traceability — każde ryzyko z dokładnym cytatem.

### 💡 #2 — "Monte Carlo Margin Defender"
```python
# PERT distribution (standard w project risk)
from scipy.stats import triang
import numpy as np

def monte_carlo_margin(cost_items, contract_value, iterations=10_000):
    total_costs = np.zeros(iterations)
    for item in cost_items:
        c = (item['likely'] - item['low']) / (item['high'] - item['low'])
        price_samples = triang(c, loc=item['low'], scale=item['high']-item['low']).rvs(iterations)
        total_costs += price_samples * item['quantity']
    margins = (contract_value - total_costs) / contract_value * 100
    return {
        'P10': np.percentile(margins, 10),
        'P50': np.percentile(margins, 50),
        'P90': np.percentile(margins, 90),
        'loss_probability': (margins < 0).mean() * 100,
    }
```
Output: histogram marży, Tornado chart wrażliwości, "Przy tej cenie ryzyko straty = 23%"

### 💡 #3 — "Bid Intelligence Dashboard" (Competitor Intel)
DuckDB + atlasprzetargow parquet (1,4M rekordów, FREE) + nightly BZP API sync:
- "Kto wygrywa przetargi CPV 45xxx w woj. mazowieckim?"
- "Jaka była cena wygrywająca w ostatnich 10 przetargach na termomodernizację?"
- "Firma ABC wygrała 15 przetargów drogowych — Twój main competitor"
- Win/loss: "Twoje oferty były X% wyżej od wygrywających"

### 💡 #4 — "Construction Kanban Pro" z AI swim lanes
Stages: `MONITORING → GO/NO-GO → SWZ ANALYSIS → KOSZTORYS → WERYFIKACJA → ZŁOŻENIE → WYNIK`
AI proactive: "Deadline za 3 dni, nikt nie zaczął kosztorysu", "Ryzyko straty 45% — rozważ no-bid"
Keyboard shortcuts (Linear-style): N=nowy, G=go/no-bid, K=kosztorys, Cmd+K=palette

### 💡 #5 — "BZP MCP Server" (open source)
Wzorzec: vergabe-mcp dla Niemiec (GitHub MIT). Polski odpowiednik:
```typescript
bzp_search_notices({ cpv_codes: ["45000000"], region: "PL91", value_min: 2_000_000 })
bzp_get_notice_detail({ notice_id: "...", include_documents: true })
bzp_list_buyer_history({ buyer_nip: "...", years_back: 3 })
bzp_get_contractor_history({ contractor_nip: "..." })
```
Dystrybucja: embedded Terra.OS + open source GitHub (community goodwill + SEO)

---

## CZĘŚĆ 5 — UX WZORCE (implementuj w Terra.OS)

Z analizy Linear, Vercel, Grafana, Hex.tech, Retool:
1. **North Star First** — top-left = jeden KPI (wartość pipeline / win rate)
2. **Color = Function** — Red = problem, Green = OK; zero dekoracji
3. **AI Summary First** — AI podsumowuje → user drilluje
4. **Personal Default** — "Moje przetargi" przed "Wszystkie przetargi"
5. **Keyboard shortcuts** — każda akcja <100ms, Cmd+K command palette
6. **Progressive Disclosure** — 5-9 elementów default, reszta za kliknięciem

---

## CZĘŚĆ 6 — OPEN SOURCE TOOLS DO INTEGRACJI

| Tool | Stars | Zastosowanie w Terra.OS |
|------|-------|-------------------------|
| **ContextGem** | ⭐1.9k | Deklaratywny parser SWZ z sentence-level traceability |
| **DDC CWICR** | ⭐178 | Baza 55K pozycji kosztorysowych PL_WARSAW (FREE) |
| **atlasprzetargow** | ⭐3 | 1,4M rekordów BZP (FREE CC BY) — competitor intel |
| **vergabe-mcp** | ⭐3 | Wzorzec MCP server dla przetargów (replika dla PL) |
| **Unstructured.io** | ⭐10k+ | Pre-processing SWZ PDF/ZIP |
| **Reducto AI** (YC S24) | - | Complex PDF parsing — startup credits dostępne |

---

## CZĘŚĆ 7 — REKOMENDOWANY PIPELINE SWZ

```
SWZ ZIP/PDF (do 2GB)
  → Unstructured.io (file type handling, OCR, table extraction)
  → Reducto AI (complex layouts, scanned pages)
  → ContextGem (declarative: aspects=sekcje SWZ + concepts=wymagania/ryzyka/kary/terminy)
  → Claude 3.5 Sonnet (reasoning, risk analysis, go/no-bid)
  → Structured JSON → PostgreSQL
  → Kanban card auto-created + kosztorys scaffold + risk score
```

---

## ROADMAP PRIORYTETÓW (na podstawie research)

| Priorytet | Feature | Impact | Effort | Differentiator |
|-----------|---------|--------|--------|----------------|
| P0 | SWZ Autopilot (ContextGem) | 🔴 HIGH | 🟡 MED | vs Przetargi.io: traceability |
| P0 | Monte Carlo Margin | 🔴 HIGH | 🟡 MED | Jedyny w PL ecosystem |
| P1 | Competitor Intelligence | 🟠 HIGH | 🟢 LOW | FREE data (atlasprzetargow) |
| P1 | Kanban Pro (dnd-kit) | 🟠 HIGH | 🟡 MED | Jak Tendium ale z kosztorysem |
| P2 | DDC CWICR integration | 🟡 MED | 🟢 LOW | FREE, Qdrant semantic search |
| P2 | BZP MCP Server | 🟡 MED | 🟡 MED | Community + SEO |
| P3 | Intercenbud partnership | 🔴 HIGH | 🔴 HIGH | Polskie normatywy KNR |
