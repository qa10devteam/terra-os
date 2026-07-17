# 🔴 AUDYT BEZPIECZEŃSTWA — Autentykacja i Autoryzacja
## Projekt: Yuna Bud-OS (terra-os)
### Data: 2026-07-17

---

## PODSUMOWANIE KRYTYCZNE

| Poziom | Ilość |
|--------|-------|
| 🔴 Critical | 4 |
| 🟠 High | 6 |
| 🟡 Medium | 5 |
| 🔵 Low | 3 |

---

## 🔴 CRITICAL — Natychmiastowe zagrożenie

### C1. Masowe endpointy bez autentykacji — pełny dostęp do danych tenantów

**Plik:** `services/api/services/api/routers/m7_backend.py:30-31`  
**Wektor ataku:** ~200 endpointów nie wymaga tokenu JWT. Atakujący może podać dowolny `tenant_id` jako query parameter i odczytać/modyfikować dane dowolnej organizacji.

**Dowód:**
```python
# m7_backend.py:30-31
@router.get("/settings/usage")
def get_usage(tenant_id: str) -> dict:  # ← BEZ AuthUser!
    # Bezpośrednie zapytanie do DB z tenant_id z URL
```

Dotyczy minimum: `m7_backend.py` (25 endpointów), `intelligence.py` (16), `module3.py` (14), `estimator.py` (5), `engine.py` (5), `export.py` (4), `scoring.py` (5), `system.py` (11), `mv_scoring.py` (7), `olap.py` (5), `events.py` (4), `m7_phase2.py` (12), `m7_advanced.py` (5), `proactive.py` (5), `icb_advanced.py` (12), `documents.py` (2), `multimodal.py` (4), `semantic_search.py` (5), `zwiad.py` (4) — łącznie **~200 endpointów**.

**Skutek:** Pełny Insecure Direct Object Reference (IDOR) — dowolny użytkownik internetu może odczytać przetargi, oferty, raporty, koszty, analizy AI dowolnej organizacji bez żadnej autentykacji.

---

### C2. Hardcoded JWT Secret w kodzie źródłowym

**Plik:** `services/api/services/api/auth/utils.py:15`  
**Wektor ataku:** Domyślny sekret `terra-dev-secret-change-in-production-xyz` jest zapisany w repozytorium. Ochrona `ENVIRONMENT not in ("dev", "test", None)` jest łatwa do obejścia (env nie ustawiony = None = dozwolone).

**Dowód:**
```python
SECRET_KEY: str = os.getenv("JWT_SECRET", "terra-dev-secret-change-in-production-xyz")
if os.getenv("ENVIRONMENT") not in ("dev", "test", None) and SECRET_KEY == "...":
    raise RuntimeError(...)
# Gdy ENVIRONMENT nie jest ustawiony (None) → domyślny sekret akceptowany!
```

**Skutek:** Atakujący znający kod (open source / leak) może generować dowolne tokeny JWT z dowolnym `user_id`, `org_id`, `role="owner"`. Pełne przejęcie dowolnego konta.

---

### C3. Tenant isolation bypass w m7_backend — IDOR przez query parameter

**Plik:** `services/api/services/api/routers/m7_backend.py:30-600`  
**Wektor ataku:** Endpointy przyjmują `tenant_id` jako parametr zapytania HTTP zamiast wyciągać go z tokenu JWT. Brak jakiejkolwiek weryfikacji.

**Dowód:**
```python
# m7_backend.py:162
@router.post("/bookmarks/{tender_id}")
def add_bookmark(tender_id: str, tenant_id: str, body: ...):
    # tenant_id comes from query param - ANYONE can write to any org!
```

**Skutek:** Atakujący może dodawać/usuwać/odczytywać zakładki, raporty, alertów, webhooków, członków zespołu DOWOLNEJ organizacji. Read+Write IDOR.

---

### C4. Test fixture `autouse=True` nadpisuje autentykację globalnie

**Plik:** `tests/conftest.py:112-140`  
**Wektor ataku:** Fixture `_override_auth_for_tests` jest `scope="session"` i `autouse=True`. Nadpisuje `get_current_user` na aplikacji produkcyjnej (ten sam obiekt `app`). Jeśli testy uruchomione w tym samym procesie co serwer (np. hot-reload/dev), AUTH JEST WYŁĄCZONE.

**Dowód:**
```python
@pytest.fixture(scope="session", autouse=True)
def _override_auth_for_tests() -> None:
    app.dependency_overrides[get_current_user] = lambda: _demo  # ROLE: owner!
```

**Skutek:** W środowisku deweloperskim/staging, gdy testy i serwer współdzielą proces, wszystkie requesty są automatycznie autentykowane jako `owner` bez tokenu.

---

## 🟠 HIGH — Poważne zagrożenie

### H1. Password reset token przechowywany jako plaintext w bazie danych

**Plik:** `services/api/services/api/auth/router.py:385-388`  
**Wektor ataku:** Token resetu hasła jest zapisywany w bazie danych BEZ haszowania. SQL injection lub backup leak ujawnia tokeny.

**Dowód:**
```python
# router.py:385-388
conn.execute(text(
    "INSERT INTO password_reset_tokens (user_id, token, expires_at) "
    "VALUES (:uid, :token, :exp)"
), {"uid": str(user.id), "token": token, ...})  # ← plaintext!
```

**Porównanie:** Refresh tokeny SĄ haszowane (SHA-256) — `hash_refresh_token()`. Reset tokeny — NIE.

**Skutek:** Każdy z dostępem do bazy (admin DB, SQL injection, backup) może natychmiast przejąć dowolne konto.

---

### H2. Brak walidacji `token_type` w refresh flow — Token confusion

**Plik:** `services/api/services/api/auth/utils.py:51-56`  
**Wektor ataku:** `decode_access_token()` sprawdza `type == "access"`, ale nie istnieje odpowiednik dla refresh tokenów. Refresh token to UUID (nie JWT) — ale access token w cookie może być mylony.

Prawdziwy problem: **session cookie (`session`) zawiera access token** → jeśli CSRF bypass, access token wystarczy do impersonacji.

---

### H3. CSRF middleware pomija requesty bez cookies — bypass

**Plik:** `services/api/services/api/middleware/csrf.py:56-58`  
**Wektor ataku:** Gdy brak `csrf_cookie` → request jest przepuszczany. Atakujący może usunąć cookie `csrf_token` (lub po prostu go nie wysyłać) i ominąć ochronę CSRF.

**Dowód:**
```python
# csrf.py:56-58
if not csrf_cookie:
    # No session cookie — allow (Bearer-less API clients, curl, etc.)
    return await call_next(request)
```

**Skutek:** Atakujący może wykonać cross-origin request z cookie `session` (auto-attached) ale bez `csrf_token` i request przejdzie walidację.

**UWAGA:** Ten bypass jest złagodzony przez fakt, że session cookie ma `SameSite=Strict` — ale SameSite nie chroni przed top-level navigation (form GET → POST redirect).

---

### H4. Brak invalidacji access tokenów po zmianie hasła

**Plik:** `services/api/services/api/auth/router.py:396-441`  
**Wektor ataku:** Po `reset-password` stare access tokeny (15 min TTL) pozostają ważne. Brak blacklisty/wersjonowania tokenów.

**Dowód:** Endpoint `reset_password` aktualizuje hasło i oznacza token resetu jako użyty, ale NIE:
- Nie rewokuje istniejących refresh tokenów użytkownika
- Nie invaliduje istniejących access tokenów (brak blacklisty)

**Skutek:** Atakujący, który wcześniej ukradł token, ma jeszcze do 15 minut dostępu po zmianie hasła przez ofiarę.

---

### H5. Demo reset endpoint z hardcoded secretem w kodzie

**Plik:** `services/api/services/api/routers/demo.py:126, 142-150`  
**Wektor ataku:** `DEMO_RESET_SECRET` ma wartość domyślną `demo-reset-secret-change-in-prod`. Endpoint `/api/v2/demo/reset` przyjmuje secret jako query parameter.

**Dowód:**
```python
DEMO_RESET_SECRET: str = os.getenv("DEMO_RESET_SECRET", "demo-reset-secret-change-in-prod")

@router.post("/reset")
def demo_reset(secret: str = ""):  # BEZ AUTH!
    if secret != DEMO_RESET_SECRET: raise 403
    # WIPE ALL DATA for demo org
```

**Skutek:** Atakujący z domyślnym secretem może wyczyścić dane demo organizacji. W środowisku dev (env nie ustawiony) → destrukcja danych.

---

### H6. Brak allow_credentials w CORS — cookies nie będą wysyłane cross-origin

**Plik:** `services/api/services/api/main.py:382-387`  
**Wektor ataku:** Brak `allow_credentials=True` w konfiguracji CORS. To DOBRZE z perspektywy security (cookies nie lecą cross-origin), ale oznacza że cookie-based auth (`session` cookie) NIE DZIAŁA z domeny frontendu, chyba że same-origin.

**Problem architektoniczny:** System ustawia cookie `session` (router.py:145-153) ale CORS blokuje ich użycie. To sugeruje incomplete implementation.

---

## 🟡 MEDIUM — Umiarkowane zagrożenie

### M1. Plan gate bypass — brak org_id = "free" plan

**Plik:** `services/api/services/api/auth/plan_gate.py:58`  
**Wektor ataku:** Gdy `user.org_id` jest `None`, plan ustawiany jest na `"free"`. Ale token JWT pozwala na ustawienie dowolnego `org_id` → atakujący z forged tokenem (C2) może ustawić org_id na organizację z planem "enterprise".

**Dowód:**
```python
def _check(user: AuthUser) -> None:
    plan_str = _get_org_plan(str(user.org_id)) if user.org_id else "free"
    # Jeśli atakujący kontroluje org_id w JWT → dostęp do dowolnego planu
```

---

### M2. `HTTPBearer(auto_error=False)` — ciche przepuszczanie bez tokenu

**Plik:** `services/api/services/api/auth/deps.py:12`  
**Wektor ataku:** `auto_error=False` oznacza, że FastAPI nie zwróci automatycznie 401 gdy brak headera Authorization. Zależy to całkowicie od kodu `get_current_user`. Kod sprawdza `credentials is None` → poprawne. Ale gdyby ktoś refaktoryzował bez uwagi...

**Status:** Aktualnie bezpieczne, ale architekturalnie ryzykowne (defense-in-depth violation).

---

### M3. Brak rate limitu na endpoint `/api/v2/auth/refresh`

**Plik:** `services/api/services/api/auth/router.py:290`  
**Wektor ataku:** Endpoint refresh nie ma dekoratora `@limiter.limit()`. Atakujący z listą skradzionych refresh tokenów może masowo generować access tokeny.

**Dowód:** `/register` ma `@limiter.limit("5/minute")`, `/login` — tak samo, `/forgot-password` — tak. Ale `/refresh` — NIE MA.

---

### M4. Refresh token jako UUID4 — niska entropia w porównaniu do best practice

**Plik:** `services/api/services/api/auth/utils.py:62`  
**Wektor ataku:** `uuid.uuid4()` generuje 122 bity entropii. Standard bezpieczeństwa zaleca ≥256 bitów dla tokenów sesyjnych.

**Dowód:**
```python
def create_refresh_token():
    raw = str(uuid.uuid4())  # 122 bits vs recommended 256 bits
```

---

### M5. Brak 2FA/MFA — brak implementacji

**Wyszukiwanie:** `grep -r "2FA\|totp\|two_factor\|mfa\|authenticator"` → 0 wyników.

**Skutek:** Konta z dostępem do przetargów wartych miliony PLN nie mają opcji drugiego faktora uwierzytelniania.

---

## 🔵 LOW — Niskie zagrożenie

### L1. Exception handling w `_get_org_plan` zwraca "free" przy błędzie DB

**Plik:** `services/api/services/api/auth/plan_gate.py:51-52`  
**Wektor ataku:** Jeśli baza danych jest niedostępna, plan gate degrades to "free" → użytkownicy z plan "free" mogą momentalnie mieć dostęp jak "free" (brak eskalacji). ALE użytkownicy enterprise też będą traktowani jako "free" → denial of service.

---

### L2. Logout nie invaliduje access tokenów

**Plik:** `services/api/services/api/auth/router.py:332-339`  
**Wektor ataku:** Logout rewokuje tylko refresh token. Access token (15 min) pozostaje ważny. Standard branżowy — akceptowalne z krótkim TTL.

---

### L3. Conftest ujawnia credentiale demo tenanta

**Plik:** `tests/conftest.py:52, 99-103`  
**Wektor ataku:** Hardcoded `DB_PASSWORD=terra_dev_2026`, `user_id`, `org_id` w testach. Jeśli repo jest publiczne, te wartości mogą być użyte do ataku na dev/staging.

---

## BRAKUJĄCE KONTROLE BEZPIECZEŃSTWA

| Kontrola | Status |
|----------|--------|
| 2FA/TOTP | ❌ Brak |
| Account lockout po X nieudanych logowań | ❌ Brak (tylko rate limit 5/min) |
| Password breach check (HaveIBeenPwned) | ❌ Brak |
| JWT blacklist (logout/password change) | ❌ Brak |
| Session binding do IP/fingerprint | ❌ Brak |
| Audit log prób logowania | ❌ Brak |
| Refresh token rotation detection (reuse) | ❌ Brak |
| RBAC granularny (per-endpoint) | ⚠️ Częściowy (tylko komentarze, system, org) |
| Content Security Policy header | ❌ Brak |
| HSTS header | ❌ Brak |

---

## REKOMENDACJE (priorytet)

1. **NATYCHMIAST:** Dodać `AuthUser` dependency do WSZYSTKICH 200 niezabezpieczonych endpointów
2. **NATYCHMIAST:** Usunąć `tenant_id` jako query parameter — wyciągać WYŁĄCZNIE z tokenu JWT
3. **NATYCHMIAST:** Ustawić JWT_SECRET w production i usunąć fallback na None ENVIRONMENT
4. **W CIĄGU 24H:** Haszować password reset tokeny (SHA-256 jak refresh tokeny)
5. **W CIĄGU 7 DNI:** Implementować 2FA dla kont admin/owner
6. **W CIĄGU 7 DNI:** Dodać rate limit na `/refresh` endpoint
7. **W CIĄGU 7 DNI:** Invalidować wszystkie refresh tokeny po zmianie hasła
8. **W CIĄGU 30 DNI:** Implementować JWT blacklist (Redis) dla logout/password-change
