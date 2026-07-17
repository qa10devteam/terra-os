# RAPORT CYBERSECURITY - YUNA BUD-OS (Terra.OS)
## Pełny audyt bezpieczeństwa z symulacją ataków

**Data:** 2026-07-17  
**Audytor:** Hermes Agent  
**Klasyfikacja:** POUFNE  
**Werdykt:** 🔴 PLATFORMA NIEZDATNA DO PRODUKCJI — WYMAGA NATYCHMIASTOWEJ NAPRAWY

---

## EXECUTIVE SUMMARY

| Kategoria | 🔴 Krytyczne | 🟠 Wysokie | 🟡 Średnie | 🔵 Niskie |
|-----------|:---:|:---:|:---:|:---:|
| Autentykacja & Autoryzacja | 4 | 6 | 5 | 3 |
| Injection & Input Validation | 3 | 12 | 9 | 0 |
| Infrastruktura & Supply Chain | 5 | 7 | 6 | 4 |
| **RAZEM** | **12** | **25** | **20** | **7** |

**Łącznie: 64 podatności, w tym 12 krytycznych.**

---

## TOP 12 KRYTYCZNYCH PODATNOŚCI

### 🔴 C-01: ~200 endpointów BEZ AUTENTYKACJI (IDOR masowy)
- **Pliki:** `m7_backend.py`, `intelligence.py`, `module3.py`, `estimator.py`, +16 routerów
- **Atak:** `curl https://app.yuna.pl/api/v2/m7/settings/usage?tenant_id=DOWOLNY_UUID` — pełny dostęp do danych dowolnej organizacji
- **Skutek:** Odczyt/zapis przetargów, ofert, kosztorysów, analiz AI KAŻDEGO klienta
- **CVSS:** 10.0

### 🔴 C-02: Hardcoded JWT Secret
- **Plik:** `auth/utils.py:15`
- **Secret:** `terra-dev-secret-change-in-production-xyz`
- **Atak:** Wygenerowanie tokenu JWT z `role=owner` dla dowolnego `org_id`
- **Skutek:** Pełne przejęcie dowolnego konta bez znajomości hasła
- **CVSS:** 9.8

### 🔴 C-03: SQL Injection via model_dump() keys
- **Pliki:** `tender_alerts.py:342`, `competitor_watch.py:195`, `automations.py:127`, `offers.py:275`, `buyer_crm.py:260`
- **Atak:** `{"name; DROP TABLE tender_alert; --": "pwned"}`
- **Skutek:** Pełna kontrola nad bazą danych — odczyt, modyfikacja, usunięcie
- **CVSS:** 9.8

### 🔴 C-04: Stored XSS via dangerouslySetInnerHTML + ts_headline()
- **Plik:** `TenderFTSSearch.tsx:92`
- **Atak:** Wstrzyknięcie `<script>` do tytułu przetargu → wykonanie w przeglądarce ofiary
- **Skutek:** Kradzież sesji, phishing, keylogging u wszystkich użytkowników
- **CVSS:** 8.6

### 🔴 C-05: SSRF via webhook dispatch
- **Plik:** `automations.py:417`
- **Atak:** Ustawienie webhook URL na `http://169.254.169.254/latest/meta-data/` (AWS metadata)
- **Skutek:** Wyciek credentials AWS, dostęp do infrastruktury chmurowej
- **CVSS:** 9.1

### 🔴 C-06: Stripe Webhook bez weryfikacji podpisu
- **Plik:** `billing.py:648`
- **Atak:** `curl -X POST /api/v2/billing/webhook -d '{"type":"checkout.session.completed","data":{"plan":"business"}}'`
- **Skutek:** Darmowy upgrade do najdroższego planu (Business 1499 PLN) bez płatności
- **CVSS:** 9.1

### 🔴 C-07: Demo Reset bez autentykacji
- **Plik:** `demo.py`
- **Atak:** `curl -X POST /api/v2/demo/reset?secret=demo-reset-secret-change-in-prod`
- **Skutek:** Wyczyszczenie WSZYSTKICH danych demo organizacji
- **CVSS:** 8.2

### 🔴 C-08: TUNNEL_URL.txt w repozytorium git
- **Plik:** `TUNNEL_URL.txt`
- **Atak:** Publiczny URL Cloudflare tunnel → bezpośredni dostęp do instancji dev
- **Skutek:** W połączeniu z C-02 — pełny dostęp bez VPN/firewalla
- **CVSS:** 7.5

### 🔴 C-09: Tokeny E2E (JWT + refresh) committed do git
- **Plik:** `apps/ui/e2e/.auth/user.json`
- **Atak:** Użycie tokenu z repo → natychmiastowy dostęp jako `owner`
- **Skutek:** Nieautoryzowany dostęp do konta z pełnymi uprawnieniami
- **CVSS:** 8.0

### 🔴 C-10: Brak tenant isolation w zasobach (cross-tenant IDOR)
- **Plik:** `resources.py:118`
- **Atak:** `GET /api/v2/resources/subcontractors/{UUID_innego_tenanta}`
- **Skutek:** Odczyt danych podwykonawców, sprzętu, kalendarzy INNYCH firm
- **CVSS:** 8.6

### 🔴 C-11: Password reset token plaintext w DB
- **Plik:** `auth/router.py:385`
- **Atak:** SQL injection/DB backup → odczyt tokenów → reset hasła dowolnego użytkownika
- **Skutek:** Account takeover przez chain z C-03
- **CVSS:** 7.5

### 🔴 C-12: Upload dokumentów bez autentykacji
- **Plik:** `multimodal.py`
- **Atak:** Upload malware/webshell bez tokenu
- **Skutek:** Remote Code Execution jeśli pliki servowane statycznie
- **CVSS:** 8.1

---

## SYMULACJA ATAKÓW — KILL CHAIN

### Scenariusz 1: Przejęcie platformy (0 do full admin w 3 krokach)
```
1. Odczytaj JWT secret z publicznego repo (lub użyj domyślnego)
2. Wygeneruj token: jwt.encode({"sub":"admin","org_id":"*","role":"owner"}, "terra-dev-secret-change-in-production-xyz")
3. Wyślij do dowolnego endpointu → pełna kontrola nad platformą
Czas ataku: < 30 sekund
```

### Scenariusz 2: Kradzież danych wszystkich klientów
```
1. Enumeracja tenant_id (brak rate limiting, brak auth na ~200 endpointów)
2. GET /api/v2/m7/tenders?tenant_id={każdy_UUID}
3. Eksfiltracja przetargów, ofert, kosztorysów, analiz konkurencji
Czas ataku: < 5 minut na pełny dump
```

### Scenariusz 3: Financial fraud via Stripe bypass
```
1. POST /api/v2/billing/webhook z fałszywym eventem checkout.session.completed
2. Organizacja upgradowana do Business bez płatności
3. Powtórz dla każdej organizacji
Czas ataku: < 1 minuta
```

### Scenariusz 4: Wiper attack via SQL Injection
```
1. PUT /api/v2/alerts/{id} body: {"name; DROP TABLE ALL; --": "x"}
2. Kaskadowe usunięcie danych przez brak foreign key constraints
Czas ataku: < 10 sekund
```

### Scenariusz 5: Supply chain + lateral movement
```
1. SSRF via automations webhook → AWS metadata (169.254.169.254)
2. Pozyskaj AWS credentials
3. Dostęp do S3, RDS, EC2 — pełna infrastruktura
Czas ataku: < 2 minuty
```

---

## ROADMAPA CYBERSECURITY — PLAN NAPRAWCZY

### 🚨 FAZA 0: HOTFIX (natychmiast, przed jakimkolwiek deployem)
**Czas: 1-2 dni | Blokuje produkcję**

| # | Zadanie | Priorytet | Effort |
|---|---------|-----------|--------|
| 0.1 | Dodaj `Depends(get_current_user)` do WSZYSTKICH ~200 endpointów bez auth | P0 | 4h |
| 0.2 | Zamień `tenant_id` query param na `user.org_id` z tokenu JWT | P0 | 4h |
| 0.3 | Wymuś JWT_SECRET z env (fail-closed: `if not os.getenv("JWT_SECRET"): sys.exit(1)`) | P0 | 30min |
| 0.4 | Usuń `TUNNEL_URL.txt` i `e2e/.auth/user.json` z repo + `.gitignore` | P0 | 15min |
| 0.5 | Wymuś `STRIPE_WEBHOOK_SECRET` — odrzuć webhook bez valid signature | P0 | 1h |
| 0.6 | Wyłącz `DEMO_MODE` domyślnie (opt-in, nie opt-out) | P0 | 30min |
| 0.7 | Dodaj allowlist kolumn do dynamicznych UPDATE (model_dump injection fix) | P0 | 2h |

### 🔴 FAZA 1: CRITICAL FIXES (tydzień 1-2)
**Czas: 5-7 dni roboczych**

| # | Zadanie | Priorytet | Effort |
|---|---------|-----------|--------|
| 1.1 | Tenant isolation: KAŻDE query do DB musi filtrować po `org_id` z tokenu | P1 | 3d |
| 1.2 | Sanitize `dangerouslySetInnerHTML` — użyj DOMPurify na ts_headline() | P1 | 4h |
| 1.3 | SSRF protection: zablokuj prywatne IP w webhook dispatch (allowlist publicznych) | P1 | 4h |
| 1.4 | Hash password reset tokens (bcrypt/argon2 przed zapisem do DB) | P1 | 2h |
| 1.5 | Rate limiting na auth endpoints (login: 5/min, reset: 3/h, refresh: 10/min) | P1 | 4h |
| 1.6 | Invalidate all sessions po password change | P1 | 2h |
| 1.7 | Upload auth + file type validation (magic bytes, nie extension) | P1 | 4h |
| 1.8 | Parametryzuj WSZYSTKIE SQL queries — audit f-stringów z user input | P1 | 2d |
| 1.9 | Redis: dodaj `requirepass` w docker-compose + connection string | P1 | 1h |
| 1.10 | Usuń `unsafe-eval` z CSP, zamień `unsafe-inline` na nonce | P1 | 4h |

### 🟠 FAZA 2: HARDENING (tydzień 3-4)
**Czas: 5-7 dni roboczych**

| # | Zadanie | Priorytet | Effort |
|---|---------|-----------|--------|
| 2.1 | Implementacja 2FA (TOTP) dla owner/admin accounts | P2 | 2d |
| 2.2 | Audit logging: kto, co, kiedy, skąd (immutable log) | P2 | 2d |
| 2.3 | WAF rules: block SQLi/XSS patterns na edge (Cloudflare) | P2 | 4h |
| 2.4 | Secret rotation policy: JWT, DB credentials, API keys (quarterly) | P2 | 1d |
| 2.5 | Dependency pinning + automated vulnerability scanning (Dependabot/Snyk) | P2 | 4h |
| 2.6 | Error sanitization: nigdy nie zwracaj stack trace do klienta | P2 | 4h |
| 2.7 | CSRF: fix bypass (SameSite=Strict cookies, double-submit token) | P2 | 1d |
| 2.8 | Docker: non-root user, read-only filesystem, resource limits | P2 | 4h |
| 2.9 | API versioning + deprecation policy (zabezpieczenie przed breaking changes) | P2 | 1d |
| 2.10 | Pen-test zewnętrzny (OWASP Top 10 validation) | P2 | 1d+ |

### 🟡 FAZA 3: MATURE SECURITY (miesiąc 2-3)
**Czas: ongoing**

| # | Zadanie | Priorytet | Effort |
|---|---------|-----------|--------|
| 3.1 | SOC2 Type II preparation — policies, procedures, evidence collection | P3 | ongoing |
| 3.2 | Data encryption at rest (PG: TDE lub column-level encryption) | P3 | 1w |
| 3.3 | Network segmentation: API/DB/Redis w oddzielnych VPC subnets | P3 | 2d |
| 3.4 | Intrusion Detection System (IDS) — anomaly detection na API calls | P3 | 1w |
| 3.5 | Bug bounty program (po fixach P0-P2) | P3 | setup 1d |
| 3.6 | Disaster Recovery: backup encryption, cross-region, RTO/RPO targets | P3 | 1w |
| 3.7 | Zero-trust architecture: mTLS between services, no implicit trust | P3 | 2w |
| 3.8 | Security training dla devów (OWASP, secure coding practices) | P3 | recurring |

---

## METRYKI SUKCESU

| Metryka | Teraz | Po Fazie 0 | Po Fazie 1 | Po Fazie 2 | Cel |
|---------|-------|-----------|-----------|-----------|-----|
| Endpointy bez auth | ~200 | 0 | 0 | 0 | 0 |
| SQLi vectors | 8+ | 1 | 0 | 0 | 0 |
| XSS vectors | 3+ | 3 | 0 | 0 | 0 |
| Hardcoded secrets | 5+ | 0 | 0 | 0 | 0 |
| OWASP Top 10 compliance | ~20% | 50% | 80% | 95% | 100% |
| Mean Time to Detect (MTD) | ∞ | ∞ | 24h | 1h | <15min |
| Pen-test pass rate | FAIL | FAIL | PARTIAL | PASS | PASS |

---

## WNIOSKI KOŃCOWE

**Stan obecny:** Platforma jest w stanie **pre-alpha pod kątem bezpieczeństwa**. Każdy punkt z OWASP Top 10 ma minimum jedną krytyczną podatność. Atakujący o średnich umiejętnościach może przejąć pełną kontrolę w < 1 minuty.

**Najbardziej destrukcyjny scenariusz:** Chain C-02 + C-01 → pełny dump danych WSZYSTKICH klientów + modyfikacja ofert przetargowych = straty finansowe + RODO + utrata reputacji.

**Rekomendacja:** NIE DEPLOYOWAĆ na produkcję przed ukończeniem Fazy 0 i Fazy 1. Koszt naprawy teraz: ~2-3 tygodnie. Koszt naprawy po breaku: 6-12 miesięcy + kary UODO + utrata klientów.

---

*Szczegółowe raporty techniczne:*
- `/home/ubuntu/terra-os/SECURITY_AUDIT_AUTH.md`
- `/home/ubuntu/terra-os/SECURITY_AUDIT_INJECTION.md`
- `/home/ubuntu/terra-os-security-audit.md`
