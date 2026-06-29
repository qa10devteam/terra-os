# Specyfikacja: Moduł Kosztorysów Terra.OS — Eksport DOCX

## 1. Cel

Moduł kosztorysów generuje **profesjonalne kosztorysy budowlane w formacie DOCX** — gotowe do wydruku, złożenia w przetargu lub wysyłki do zamawiającego. Dwa warianty (doc / owner) z pełnym formatowaniem, tabelami, nagłówkami i podpisami.

---

## 2. Warianty kosztorysu

| Wariant | Źródło cen | Cel |
|---------|-----------|-----|
| `doc` | Z dokumentacji przetargowej (przedmiar + ceny katalogowe KNR) | Kosztorys inwestorski / ofertowy wg SIWZ |
| `owner` | Własna baza (RateCard + calibration_coeff) | Kosztorys wewnętrzny — realna wycena |

---

## 3. Endpointy API

```
POST /api/v1/tenders/{id}/estimate                     → {estimate_doc_id, estimate_owner_id}
GET  /api/v1/estimates/{id}                            → Estimate (JSON)
GET  /api/v1/tenders/{id}/estimate/compare             → {margin_headroom_pct, ...}
PATCH /api/v1/estimates/{id}/params                    → recompute + sum reconciled

# ─── NOWE (eksport DOCX) ───────────────────────────────────────────────────
POST /api/v1/estimates/{id}/export/docx                → 200 application/vnd.openxmlformats-officedocument.wordprocessingml.document
POST /api/v1/tenders/{id}/estimate/export/docx         → 200 (oba warianty w jednym ZIP)
POST /api/v1/estimates/{id}/export/docx/preview        → 200 {pages, sections[], warnings[]}
```

### 3.1 POST /estimates/{id}/export/docx

**Request body (opcjonalny):**
```json
{
  "template": "kosztorys_ofertowy",         // default | kosztorys_ofertowy | kosztorys_inwestorski | uproszczony
  "company_name": "override",               // null → z owner_profile
  "include_summary": true,                  // tabela podsumowująca na końcu
  "include_cover_page": true,               // strona tytułowa
  "include_kp_breakdown": false,            // rozbicie KP na pozycje
  "watermark": null,                        // "WERSJA ROBOCZA" | null
  "page_format": "A4",                      // A4 | A3
  "orientation": "portrait",                // portrait | landscape (landscape dla >8 kolumn)
  "font_family": "Arial",                   // Arial | Times New Roman | Calibri
  "font_size_pt": 9,                        // 8–12
  "decimal_places": 2,                      // 2–4
  "hide_unit_prices": false,                // true → ukrywa kolumnę cen jednostkowych
  "custom_header_md": null,                 // markdown → render jako nagłówek
  "custom_footer_md": null,                 // markdown → render jako stopka
  "sign_fields": ["Sporządził", "Sprawdził", "Zatwierdził"]
}
```

**Response:** Plik `.docx` (Content-Disposition: attachment)

### 3.2 POST /tenders/{id}/estimate/export/docx

Generuje ZIP z dwoma plikami:
- `kosztorys_doc_{tender_title}.docx` (wariant doc)
- `kosztorys_owner_{tender_title}.docx` (wariant owner)
- `porownanie.docx` (opcjonalnie — tabela porównawcza)

### 3.3 POST /estimates/{id}/export/docx/preview

Dry-run: zwraca metadane bez generowania pliku.
```json
{
  "pages": 12,
  "sections": ["Strona tytułowa", "Tabela kosztorysu", "Podsumowanie", "Podpisy"],
  "warnings": ["Pozycja 14: brak ceny jednostkowej — użyto 0.00"],
  "estimated_file_size_kb": 340
}
```

---

## 4. Struktura dokumentu DOCX

### 4.1 Strona tytułowa (opcjonalna)
```
┌─────────────────────────────────────────────┐
│           [Logo firmy — jeśli w profilu]      │
│                                               │
│        KOSZTORYS OFERTOWY / INWESTORSKI       │
│                                               │
│  Zadanie:  {tender.title}                     │
│  Nr ref.:  {tender.external_id}               │
│  Zamawiający: {tender.buyer}                  │
│  CPV: {tender.cpv[]}                          │
│                                               │
│  Wykonawca: {owner_profile.company_name}      │
│  Data:      {export_date}                     │
│  Wartość netto: {estimate.total_net_pln} PLN  │
│  Wartość brutto: {total * 1.23} PLN           │
│                                               │
│  Sporządził: ____________  Data: ________     │
│  Sprawdził:  ____________  Data: ________     │
└─────────────────────────────────────────────┘
```

### 4.2 Tabela kosztorysu (główna)

| Lp. | Podstawa | Opis robót | Jedn. | Ilość | Cena jedn. | Robocizna | Materiały | Sprzęt | Wartość |
|-----|----------|------------|-------|-------|------------|-----------|-----------|--------|---------|
| 1   | KNR 2-01 0307-01 | Roboty ziemne... | m³ | 450.00 | 28.50 | 4 500.00 | 6 200.00 | 2 125.00 | 12 825.00 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

Kolumny konfigurowalne:
- **Pełny** (9 kol.): Lp, Podstawa, Opis, Jm, Ilość, Cena jdn, R, M, S, Wartość
- **Uproszczony** (6 kol.): Lp, Opis, Jm, Ilość, Cena, Wartość
- **Bez cen** (5 kol.): Lp, Opis, Jm, Ilość, Wartość (ukryte ceny jednostkowe)

### 4.3 Podsumowanie

```
┌─────────────────────────────────────────────┐
│  Wartość robót netto:           87 450,00 PLN │
│  Koszty pośrednie (KP 12%):    10 494,00 PLN │
│  Zysk (Z 8%):                   7 835,52 PLN │
│  ─────────────────────────────────────────    │
│  RAZEM NETTO:                  105 779,52 PLN │
│  VAT 23%:                       24 329,29 PLN │
│  RAZEM BRUTTO:                 130 108,81 PLN │
│                                               │
│  Słownie: sto trzydzieści tysięcy sto osiem   │
│  złotych 81/100                               │
└─────────────────────────────────────────────┘
```

### 4.4 Podpisy

```
Sporządził: _________________    Data: __________

Sprawdził:  _________________    Data: __________

Zatwierdził: ________________    Data: __________
```

---

## 5. Szablony (templates)

| ID | Nazwa | Opis | Kolumny |
|----|-------|------|---------|
| `kosztorys_ofertowy` | Kosztorys ofertowy | Pełny, z cenami, do złożenia w przetargu | 9 |
| `kosztorys_inwestorski` | Kosztorys inwestorski | Jak ofertowy, bez zysku | 9 |
| `uproszczony` | Kosztorys uproszczony | Bez rozbicia R/M/S | 6 |
| `default` | Domyślny | = kosztorys_ofertowy | 9 |

Szablony ładowane z `templates/` w katalogu projektu. Customowe szablony `.docx` (python-docx template) mogą być dodane przez użytkownika.

---

## 6. Implementacja techniczna

### 6.1 Biblioteka
```
python-docx >= 1.1.0
num2words >= 0.5.0  (kwota słownie)
```

### 6.2 Moduł
```
services/estimator/export_docx.py
```

### 6.3 Klasy

```python
@dataclass
class DocxExportConfig:
    template: str = "kosztorys_ofertowy"
    company_name: str | None = None
    include_summary: bool = True
    include_cover_page: bool = True
    include_kp_breakdown: bool = False
    watermark: str | None = None
    page_format: str = "A4"
    orientation: str = "portrait"
    font_family: str = "Arial"
    font_size_pt: int = 9
    decimal_places: int = 2
    hide_unit_prices: bool = False
    custom_header_md: str | None = None
    custom_footer_md: str | None = None
    sign_fields: list[str] = field(default_factory=lambda: ["Sporządził", "Sprawdził", "Zatwierdził"])


def export_estimate_docx(
    estimate: Estimate,
    tender: Tender,
    owner_profile: OwnerProfile,
    config: DocxExportConfig = DocxExportConfig(),
) -> bytes:
    """Generate DOCX bytes from estimate data."""
    ...
```

### 6.4 Formatowanie liczb
- Separator tysięcy: spacja (`12 825,00`)
- Separator dziesiętny: przecinek
- Waluta: `PLN` (nie `zł` — formalny dokument)
- Kwota słownie: `num2words(amount, lang='pl', to='currency')`

### 6.5 Stylowanie DOCX
- Nagłówki: bold, 12pt
- Tabela: border 0.5pt, header row shaded (#E5E7EB), alternating row stripes
- Kolumny liczbowe: wyrównanie prawe
- Stopka: numer strony "Strona X z Y"
- Margines: 2cm (góra/dół), 2.5cm (lewo), 1.5cm (prawo)

---

## 7. Walidacja i guardy

| Reguła | Akcja |
|--------|-------|
| `estimate.lines` puste | → 422 "Kosztorys nie ma pozycji" |
| `sum(lines) ≠ total_net_pln` | → 500 "Sum reconciliation failed" — BLOKUJE eksport |
| Pozycja bez ceny | → warning w preview, 0.00 w DOCX |
| Pozycja bez jednostki | → warning, "kpl" default |
| Brak owner_profile | → użyj "—" w miejscu nazwy firmy |
| Template nieznany | → 404 |

---

## 8. Integracja z Chat-brain

Chat-brain (`POST /estimates/{id}/chat`) po edycji parametru:
1. Rekomputuje kosztorys
2. W SSE event `done` dodaje: `"docx_stale": true`
3. Frontend wyświetla badge "DOCX nieaktualny — eksportuj ponownie"

---

## 9. Testy akceptacyjne

```
T-DOCX-1: POST /estimates/{id}/export/docx → 200 + valid .docx (python-docx opens it)
T-DOCX-2: Generated DOCX has correct total_net_pln in summary table
T-DOCX-3: Kwota słownie matches numeric total
T-DOCX-4: hide_unit_prices=true → kolumna "Cena jedn." nie istnieje
T-DOCX-5: watermark="WERSJA ROBOCZA" → text watermark on every page
T-DOCX-6: Sum reconciliation failure → export blocked (500)
T-DOCX-7: Empty estimate → 422
T-DOCX-8: ZIP export (oba warianty) → valid ZIP with 2+ .docx files
T-DOCX-9: Preview returns correct page estimate and warnings
T-DOCX-10: Custom sign_fields appear at bottom of document
```

---

## 10. Roadmap

| Faza | Zakres |
|------|--------|
| **v1** | Eksport single DOCX, template default, cover page, summary, podpisy |
| **v2** | ZIP dual-variant, porównanie, preview endpoint |
| **v3** | Custom .docx templates (user-uploaded), logo embed, ATH tabela |
| **v4** | PDF export (via LibreOffice headless lub weasyprint) |

---

## 11. Przykład użycia (curl)

```bash
# Eksport kosztorysu do DOCX
curl -X POST http://localhost:8000/api/v1/estimates/{id}/export/docx \
  -H "Content-Type: application/json" \
  -d '{"template": "kosztorys_ofertowy", "include_cover_page": true}' \
  -o kosztorys.docx

# Preview (dry-run)
curl -X POST http://localhost:8000/api/v1/estimates/{id}/export/docx/preview \
  -H "Content-Type: application/json" \
  -d '{"template": "uproszczony"}'
# → {"pages": 8, "sections": [...], "warnings": [...]}

# ZIP obu wariantów
curl -X POST http://localhost:8000/api/v1/tenders/{id}/estimate/export/docx \
  -o kosztorysy.zip
```

---

*Wersja: 1.0 | Data: 2026-06-29 | Terra.OS — Moduł Kosztorysów*
