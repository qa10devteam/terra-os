# AXON — Brand Bible v1.0

> Intelligence Infrastructure for Procurement

---

## 1. Brand Architecture

```
         ┌─────────────────┐
         │      AXON       │  ← Platform brand (rdzeń)
         │  (Navy + Blue)  │     "Intelligence infrastructure for procurement"
         └────────┬────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┐
    │             │             │             │
┌───┴───┐   ┌───┴───┐   ┌───┴───┐   ┌───┴───┐
│ TERRA │   │ FORGE │   │ NEXUS │   │ ATLAS │
│(Amber)│   │(Violet│   │(Teal) │   │(Silver│
│Budowl.│   │IT/SaaS│   │Health │   │Multi  │
└───────┘   └───────┘   └───────┘   └───────┘
```

### Naming Convention
- Platform: **AXON**
- Verticals: **AXON | TERRA**, **AXON | FORGE**, etc. (pipe separator)
- Subdomains: `terra.axon.ai`, `forge.axon.ai`

### Positioning Statement
AXON is the intelligence infrastructure that transforms public procurement data into decisive action. Unlike legacy procurement tools that digitize paperwork, AXON's AI engine analyzes feasibility, calculates margins, and recommends decisions — turning weeks of manual analysis into seconds of certainty.

**AXON | TERRA** is the first vertical edition — purpose-built for construction firms competing in public tenders (BZP/TED). It adds domain-specific benchmarks (Intercenbud/SEKOCENBUD), logistics optimization, weather risk analysis, and cost estimation with real material prices.

---

## 2. Archetypes & Semantic Core

### Platform (AXON)
| Dimension | Value |
|-----------|-------|
| Primary Archetype | **Sage (Mędrzec)** — 70% |
| Secondary Archetype | **Ruler (Władca)** — 30% |
| Motivation | Truth + Control |
| Shadow (to avoid) | Dogmatism, Tyranny |
| Shadow mitigation | Transparent AI reasoning, simple UX |

### First Product (AXON|TERRA)
| Dimension | Value |
|-----------|-------|
| Primary Archetype | **Sage** — 60% (inherited) |
| Secondary Archetype | **Hero (Bohater)** — 40% |
| Motivation | Mastery of construction procurement |
| Shadow mitigation | "Tool for masters, not a replacement" |

### Semantic Core

**Platform:** `SIGNAL • PRECISION • COMMAND`
- **SIGNAL** — extracting opportunities from noise (BZP/TED/market data feeds)
- **PRECISION** — AI engine calculates, never guesses (benchmarked scores)
- **COMMAND** — user has full control over decisions (go/no-go/pivot)

**Terra extension:** `GROUND • BUILD • CERTAINTY`

---

## 3. Visual Identity

### Color Palette

#### Primary
| Name | Hex | Usage |
|------|-----|-------|
| Axon Navy | `#0A1628` | Backgrounds, sidebar, authority |
| Axon Blue | `#2563EB` | Primary CTA, links, interactive |
| Axon Cyan | `#06B6D4` | Live data, signals, real-time |

#### Secondary
| Name | Hex | Usage |
|------|-----|-------|
| Terra Amber | `#D97706` | Construction edition accent, warnings |
| Terra Ground | `#78716C` | Earth tone, sectoral identity |
| Success Green | `#059669` | Positive scores, go-decisions |
| Risk Red | `#DC2626` | High risk, blockers |

#### Neutral (Slate scale)
| Name | Hex | Usage |
|------|-----|-------|
| Slate 50 | `#F8FAFC` | Card backgrounds (light) |
| Slate 100 | `#F1F5F9` | Body text (dark mode) |
| Slate 400 | `#94A3B8` | Secondary text |
| Slate 800 | `#1E293B` | Card backgrounds (dark mode) |
| Slate 900 | `#0F172A` | Primary text (light mode) |

#### Gradients
- **Hero:** `#0A1628 → #1E3A5F` (dark authority)
- **Signal pulse:** `#2563EB → #06B6D4` (data flow)
- **Score spectrum:** `#DC2626 → #D97706 → #059669` (risk → warning → safe)

### Typography

| Context | Font | Weight | Tracking |
|---------|------|--------|----------|
| Logo/Brand | Inter | 700 Bold | +0.08em |
| Tagline | Inter | 400 Regular | 0 |
| Headings (UI) | Inter | 600 Semi-Bold | -0.01em |
| Body (UI) | Inter | 400 Regular | 0 |
| Data/Scores | JetBrains Mono | 500 Medium | 0 |

**Size scale:** 12 / 14 / 16 / 20 / 24 / 32 / 40 px

### Logo Mark

**AXON:** Abstract neural graph — 3 nodes (solid circles) connected by clean geometric lines forming a triangular constellation. Deep navy. Minimalist, flat, no gradients.

**Variants:**
1. Mark only (favicons, app icon)
2. Mark + wordmark (horizontal, header)
3. Wordmark only (inline, documentation)

**Minimum size:** 24px (mark), 80px (full)

### Iconography
- System: **Lucide Icons** (outline, 1.5px stroke weight)
- Custom extensions for: decision gauge, score bars, pipeline arrows, signal pulse

---

## 4. Tone of Voice

### Principles
1. **CERTAIN, not hopeful** — "Margin wynosi 12.4%" not "Margin może wynosić..."
2. **CONCISE, not verbose** — Max 2 sentences per insight
3. **ACTIONABLE, not descriptive** — "Złóż ofertę do 15.07" not "Termin upływa..."
4. **TRANSPARENT, not magical** — "Score 0.78: CPV match + lokalizacja + zasoby"

### Copy Examples
| Context | Copy |
|---------|------|
| Dashboard | "6 nowych przetargów. 2 z high score." |
| Engine result | "Feasible. Margin: 14.2% przy obecnych stawkach." |
| Alert | "Deadline za 3 dni. Brak wyceny." |
| Decision | "Go. 73% szans. Risk: termin realizacji." |
| Empty state | "Brak danych. Dodaj przetarg lub włącz monitoring." |

### Forbidden Words
- "Rewolucja" / "game-changer" / "innowacyjny"
- "Magiczny" / "automatycznie" (without explanation)
- "Sztuczna inteligencja" → use: "engine" / "analiza"
- Emoji in UI (acceptable in social media only)

---

## 5. UI Design Language

### Layout
- Sidebar: fixed 240px, Axon Navy background
- Content area: max-width 1280px, centered
- Cards: rounded-xl (12px), subtle border, white/slate-800 bg
- Grid: 8px base unit, breakpoints at 16/24/32/48

### Components
| Component | Style |
|-----------|-------|
| Primary button | rounded-lg, solid Axon Blue fill, white text |
| Secondary button | rounded-lg, ghost/outline, Slate 400 border |
| Score badge | colored dot + monospace number |
| Status pill | rounded-full, muted bg + darker text |
| Data table | clean rows, alternating bg, sortable headers |
| Charts | minimal, no gridlines, muted axis, bright data lines |

### Motion
- Micro interactions: 150ms ease-out
- Content transitions: 300ms ease-in-out
- Page transitions: 500ms ease-out
- Principle: motion = feedback, never decoration

### Mode Default
- **Dark mode** = default for power users (Axon Navy bg)
- Light mode = available, Slate 50 bg

---

## 6. Photography & Imagery

### Style: Documentary, not stock
- Real construction sites, aerial drone perspectives
- Clean data visualization overlays
- Infrastructure at dawn/dusk (golden hour authority)
- NO smiling-at-laptop, NO staged diversity

### Image Generation Prompts

**Hero image (landing page):**
```
Documentary style aerial photograph of a large construction site 
at golden hour, concrete structures rising, cranes silhouetted 
against deep blue sky, shot on Fuji GFX 100S, slightly desaturated 
earth tones with deep blue shadows, cinematic wide angle, 
no people visible, clean composition, 8k
```

**Dashboard context image:**
```
Dark premium SaaS dashboard UI, deep navy background #0A1628, 
slate cards #1E293B, KPI metrics at top, pipeline kanban board 
below with colored score badges, Inter font, Lucide outline icons, 
blue #2563EB accents, cyan #06B6D4 data, minimal professional 
fintech-quality interface, no decorative elements
```

**Logo mark:**
```
Minimalist abstract logo mark on pure white background. Three 
interconnected circular nodes forming neural network graph, 
connected by clean geometric lines of equal weight. Deep navy 
#0A1628. Swiss design, flat vector, no gradients, no shadows, 
no text. Ultra clean corporate tech, 8k
```

---

## 7. Audio Identity

### Brand Sound (2-3 sec)
```
Suno: "Minimal electronic audio logo, single clean synth note 
rising to resolution, subtle reverb tail, modern, precise, 
corporate tech, 3 seconds, F major, 80 BPM"
Negative: "Drums, vocals, complex melody, orchestral"
```

### Notification Sounds
| Event | Sound |
|-------|-------|
| New tender alert | Short ascending two-note chime |
| Decision confirmed | Single confident low tone |
| Warning/deadline | Subtle rhythmic pulse |
| Score complete | Brief resolution chord |

---

## 8. Voice Design (ElevenLabs)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Stability | 0.82 | Sage = consistent, authoritative |
| Similarity | 0.85 | Brand recognition |
| Style | 0.02 | Minimal expressiveness |
| Speed | 0.97 | Slightly deliberate (authority) |
| Mode | Robust (v3) | Predictable, corporate |

**Character:** Male or female, 30-45, neutral accent. Think: senior analyst briefing the CEO. Not warm, not cold — precise.

---

## 9. Competitive Positioning Map

```
                    HIGH INTELLIGENCE
                         │
         AXON ●          │
                         │
    ─────────────────────┼─────────────────────
    SIMPLE                                COMPLEX
                         │
                         │         ● Palantir
         ● OpenTender    │    ● Jaggaer
                         │
                    LOW INTELLIGENCE
```

AXON occupies: **High Intelligence + Simple** — the premium quadrant.

---

## 10. Brand Application Rules

### Do
- Always pair AXON mark with sufficient whitespace (min 50% mark width)
- Use Axon Navy as dominant dark tone
- Show real data patterns, never fake screenshots
- Lead with numbers, not adjectives

### Don't
- Never stretch or rotate the mark
- Never use gradients on the logo
- Never place logo on busy/photo backgrounds without dark overlay
- Never use more than 2 accent colors simultaneously
- Never say "AI" without showing the reasoning

---

## 11. Domain & Digital Presence

### Priority domains to secure:
1. `axon.build` (most relevant, likely available)
2. `getaxon.io` (SaaS convention)
3. `axonhq.com` (authority)
4. `terra.axon.build` (first vertical)

### Social handles:
- `@axonbuild` (Twitter/X, LinkedIn, GitHub)
- `AXON | Intelligence Infrastructure` (LinkedIn company page)

---

*Document version: 1.0*
*Created: 2026-07-12*
*Author: QA10 Brand Architecture*
*Next review: before public launch*
