# TERRA.OS — KONTYNUACJA PRAC

## Status: Plan gotowy, do implementacji
## Data: 30.06.2026

---

## CO TO JEST

Terra.OS — platforma SaaS do zarządzania przetargami budowlanymi w Polsce.
Dark theme, po polsku, z silnikiem analitycznym (Game Theory, ML, NLP).

## CO JUŻ JEST ZROBIONE

### Infrastruktura (działa)
- **Backend:** FastAPI (Python 3.12) na porcie 8000
- **Frontend:** Next.js na porcie 3000
- **Proxy:** Caddy na porcie 80 (proxy /api/* → 8000)
- **DB:** PostgreSQL 16
- **Systemd:** terra-api, terra-ui, caddy, terra-tunnel (HA x4)
- **Tunel:** Cloudflare (losowy URL, zmienia się po restarcie)

### Aplikacja (działa)
- BZP sync (e-Zamówienia API) — pobieranie przetargów
- Seed DB z przykładowymi danymi
- Lista przetargów + detail view
- Chat AI (Claude)
- Kursy walut (NBP API)
- Pogoda (Open-Meteo)
- Statusy pipeline: new→matched→analyzing→estimated→decided_go→decided_nogo→archived
- PATCH /tenders/{id} — zmiana statusu
- Tailwind v4, dark theme, glass-card, earth-* colors
- motion/react (NIE framer-motion)
- lucide-react ikony

### Pliki kluczowe
- `/home/ubuntu/terra-os/apps/ui/` — frontend Next.js
- `/home/ubuntu/terra-os/services/api/` — backend FastAPI
- `/home/ubuntu/terra-os/PLAN_140.md` — pełny 140-fazowy plan (referencia)
- `/home/ubuntu/terra-os/SPEC.md` — specyfikacja do implementacji (CZYTAJ TO)
- `/home/ubuntu/terra-os/RESEARCH.md` — research konkurencji i datasety
- `/home/ubuntu/terra-os/apps/ui/src/lib/constants.ts` — STATUS_LABELS, STATUS_COLORS
- `/home/ubuntu/terra-os/apps/ui/src/lib/utils.ts` — fmtPLN, fmtDate, matchColor

---

## ZASADY TECHNICZNE (KRYTYCZNE)

1. **Tailwind v4** — nowa składnia
2. **motion/react** — NIE framer-motion
3. **AnimatePresence** — zawsze ternary `? : null` (NIE `&&`)
4. **API paths:** relative `/api/v1/...` (Caddy proxy)
5. **BZP route:** `{bzp_number:path}` (bo slash w numerze)
6. **Odpowiedzi API list:** `{items: [], total: N}`
7. **Max limit:** 100
8. **PLN format:** `1 200 000 zł`
9. **Daty:** `DD.MM.YYYY`
10. **Język UI:** polski
11. **Dark theme:** zinc/slate palette, earth-* accents

---

## CO ROBIĆ DALEJ

Przeczytaj `/home/ubuntu/terra-os/SPEC.md` — tam jest specyfikacja ~100 faz do implementacji.
Zacznij od **Fazy 1** (blok A — Fundament).

Priorytet: funkcjonalność > akademia. Silnik analityczny ma dawać REALNĄ wartość firmom budowlanym, nie być showcase PhD.

---

## KOMENDY

```bash
# Status serwisów
sudo systemctl status terra-api terra-ui caddy

# Restart po zmianach
sudo systemctl restart terra-ui  # po zmianach frontend
sudo systemctl restart terra-api  # po zmianach backend

# Build frontend
cd /home/ubuntu/terra-os/apps/ui && npm run build

# Logi
journalctl -u terra-api -f
journalctl -u terra-ui -f

# Tunel URL (losowy)
journalctl -u terra-tunnel -n 5 | grep "https://"
```
