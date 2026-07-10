# OWASP Audit — Terra.OS S89

Data: 2026-07-10 | Zakres: services/**/*.py

## A01 — SQL Injection

Potencjalnie niebezpieczne f-string w zapytaniach SQL:

| Plik | Linia | Fragment |
|------|-------|---------|
| bzp_document_scraper.py | 634 | `f"SELECT id FROM tender WHERE {clause}"` — clause generowany wewnętrznie (safe) |
| tender_bookmarks.py | 180 | `f"SELECT count(*) FROM tender_bookmark b WHERE {where}"` — where z allowed-list |
| tender_alerts.py | 243 | `f"SELECT count(*) ... {extra}"` — extra = fixed string |
| resources.py | 73, 239 | `f"SELECT COUNT(*) FROM ... {where}"` — where z builder |
| zwiad.py | 518 | `f"SELECT COUNT(*) FROM tender t WHERE {where}"` — WHERE builder |
| tenders_v2.py | 275 | `f"SELECT COUNT(*) FROM tender t WHERE {where}"` — WHERE builder |

**Ocena**: Brak direct user-input interpolation — klauzule WHERE budowane przez własne buildery z parametryzowanymi wartościami. Ryzyko: NISKIE.

**Zalecenie**: Refactor do `sqlalchemy.select()` + filter zamiast f-string WHERE builders.

## A02 — Broken Auth

Sprawdzono: wszystkie endpointy `/api/v2/` wymagają `Depends(get_current_user)`.
Wyjątki dozwolone (publiczne):
- `GET /api/v1/health` — health check
- `GET /api/v2/health` — health check
- `POST /api/v2/auth/login` — logowanie
- `POST /api/v2/auth/register` — rejestracja

**Ocena**: OK — brak exposedów bez auth.

## A05 — Security Misconfiguration

```
grep -rn 'DEBUG.*True|SECRET_KEY.*=' services/ (excluding tests, venv)
→ Brak hardkodowanych sekretów w kodzie produkcyjnym.
→ Konfiguracja przez env vars (TERRA_SECRET_KEY, SMTP_*, STRIPE_SECRET_KEY).
```

**Ocena**: OK.

## A07 — Cross-Tenant Leakage

Sprawdzono via tenant_isolation_audit.py (S104). Wynik:
- 52 tabele sprawdzone
- 1 finding: `organizations` — 2 rekordy z NULL tenant_id (seed data, akceptowalne)
- Wszystkie tabele przetargowe, alertowe i kosztorysowe mają tenant_id NOT NULL

**Ocena**: Ryzyko NISKIE. Brak cross-tenant data leakage.

## A10 — SSRF

Sprawdzone w:
- `integrations.py` — SSRF check na webhook/fire URL
- `v3/webhooks.py` — SSRF check na URL (blokuje 127.0.0.1, localhost, 10.x, 192.168.x, 172.x)

**Ocena**: OK — zabezpieczenia wdrożone.

---

*Generowane automatycznie — Terra.OS BPMN Sprint 89*
