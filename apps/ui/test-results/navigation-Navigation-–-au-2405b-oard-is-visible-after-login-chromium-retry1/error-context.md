# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: navigation.spec.ts >> Navigation – authenticated user >> main dashboard is visible after login
- Location: e2e/navigation.spec.ts:38:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('main, [class*="content"], [class*="page"], h1, h2')
Expected: visible
Error: strict mode violation: locator('main, [class*="content"], [class*="page"], h1, h2') resolved to 5 elements:
    1) <main class="flex-1 overflow-auto bg-earth-950">…</main> aka getByRole('main')
    2) <h1 class="text-[22px] font-semibold text-earth-100 tracking-tight leading-tight">Dashboard</h1> aka getByRole('heading', { name: 'Dashboard' })
    3) <h2 class="text-base font-semibold text-earth-100">Najgorętsze dziś</h2> aka getByRole('heading', { name: 'Najgorętsze dziś' })
    4) <h2 class="text-sm font-semibold text-earth-100">AI Digest</h2> aka getByRole('heading', { name: 'AI Digest' })
    5) <h2 class="text-base font-bold text-earth-100 leading-tight">Twoja firma</h2> aka getByRole('heading', { name: 'Twoja firma' })

Call log:
  - Expect "toBeVisible" with timeout 10000ms
  - waiting for locator('main, [class*="content"], [class*="page"], h1, h2')

```

# Page snapshot

```yaml
- generic [ref=e1]:
  - generic [ref=e2]:
    - generic [ref=e4]:
      - generic [ref=e5]:
        - generic [ref=e7]: b
        - button "Rozwiń menu" [ref=e8]:
          - img [ref=e9]
      - navigation [ref=e11]:
        - generic [ref=e12]:
          - img [ref=e14]
          - generic [ref=e18]:
            - generic [ref=e19]:
              - button [ref=e20]:
                - img [ref=e21]
              - generic:
                - generic: Zwiad
                - generic: Zwiad przetargowy BZP/TED
            - generic [ref=e28]:
              - button [ref=e29]:
                - img [ref=e30]
              - generic:
                - generic: Lejek
                - generic: Kanban przetargów
            - generic [ref=e34]:
              - button [ref=e35]:
                - img [ref=e36]
              - generic:
                - generic: Silnik AI
                - generic: Analiza AHP + Friedman
            - generic [ref=e46]:
              - button [ref=e47]:
                - img [ref=e48]
              - generic:
                - generic: Decyzja
                - generic: Rekomendacje AI
        - generic [ref=e52]:
          - img [ref=e54]
          - generic [ref=e58]:
            - generic [ref=e59]:
              - button [ref=e60]:
                - img [ref=e61]
              - generic:
                - generic: Kosztorys
                - generic: Wycena KNR i materiały
            - generic [ref=e63]:
              - button [ref=e64]:
                - img [ref=e65]
              - generic:
                - generic: Oferta
                - generic: Kreator oferty PDF
            - generic [ref=e68]:
              - button [ref=e69]:
                - img [ref=e70]
              - generic:
                - generic: Kontrakty
                - generic: Tracker + cashflow
            - generic [ref=e73]:
              - button [ref=e74]:
                - img [ref=e75]
              - generic:
                - generic: Logistyka
                - generic: Zasoby, sprzęt, harmonogram
            - generic [ref=e77]:
              - button [ref=e78]:
                - img [ref=e79]
              - generic:
                - generic: Zasoby
                - generic: Pracownicy i maszyny
        - generic [ref=e84]:
          - img [ref=e86]
          - generic [ref=e88]:
            - generic [ref=e89]:
              - button [ref=e90]:
                - img [ref=e91]
              - generic:
                - generic: Dashboard
                - generic: Panel główny
            - generic [ref=e96]:
              - button [ref=e97]:
                - img [ref=e98]
              - generic:
                - generic: Analityka
                - generic: AHP, Friedman, Ryzyko
            - generic [ref=e100]:
              - button [ref=e101]:
                - img [ref=e102]
              - generic:
                - generic: Cennik ICB
                - generic: Baza cen InterCenBud
            - generic [ref=e108]:
              - button [ref=e109]:
                - img [ref=e110]
              - generic:
                - generic: Rynek
                - generic: Trendy i benchmarki CPV
            - generic [ref=e113]:
              - button [ref=e114]:
                - img [ref=e115]
              - generic:
                - generic: Rynek S6
                - generic: Dashboard BZP · TED · GUS
        - generic [ref=e117]:
          - img [ref=e119]
          - generic [ref=e122]:
            - generic [ref=e123]:
              - button [ref=e124]:
                - img [ref=e125]
              - generic:
                - generic: Ustawienia
                - generic: Organizacja i konto
            - generic [ref=e128]:
              - button [ref=e129]:
                - img [ref=e130]
              - generic:
                - generic: System
                - generic: Parametry systemu
      - generic [ref=e133]:
        - generic [ref=e134]: ET
        - button "Wyloguj się" [ref=e135]:
          - img [ref=e136]
    - generic [ref=e139]:
      - generic [ref=e140]:
        - generic [ref=e141]: NBP
        - generic [ref=e143]:
          - generic [ref=e144]:
            - generic [ref=e145]: EUR
            - generic [ref=e146]: "4.2963"
            - generic [ref=e147]: PLN
            - generic [ref=e148]: ↑0.01%
          - generic [ref=e149]:
            - generic [ref=e150]: USD
            - generic [ref=e151]: "3.9412"
            - generic [ref=e152]: PLN
            - generic [ref=e153]: ↓0.23%
          - generic [ref=e154]:
            - generic [ref=e155]: CHF
            - generic [ref=e156]: "4.4521"
            - generic [ref=e157]: PLN
            - generic [ref=e158]: ↑0.08%
        - generic [ref=e159]:
          - generic [ref=e160]: demo
          - generic [ref=e162]: 12:21:24
      - main [ref=e164]:
        - generic [ref=e166]:
          - navigation "Breadcrumb" [ref=e167]:
            - button "YU-NA" [ref=e169]
            - generic [ref=e170]:
              - img [ref=e171]
              - generic [ref=e173]: Dashboard
          - generic [ref=e174]:
            - generic [ref=e175]:
              - heading "Dashboard" [level=1] [ref=e176]
              - paragraph [ref=e177]: Przegląd aktywności przetargowej
            - button "Odśwież" [ref=e179]:
              - img [ref=e181]
              - generic [ref=e186]: Odśwież
          - generic [ref=e187]:
            - generic [ref=e189]:
              - generic [ref=e190]:
                - generic [ref=e191]: Aktywne przetargi
                - img [ref=e193]
              - generic [ref=e195]:
                - paragraph [ref=e196]: "0"
                - generic [ref=e197]:
                  - img [ref=e198]
                  - generic [ref=e201]: +12 vs. poprzedni tydzień
            - generic [ref=e203]:
              - generic [ref=e204]:
                - generic [ref=e205]: Pipeline
                - img [ref=e207]
              - generic [ref=e210]:
                - paragraph [ref=e211]: 0,0 M PLN
                - generic [ref=e212]:
                  - img [ref=e213]
                  - generic [ref=e216]: +8 wzrost wartości
            - generic [ref=e218]:
              - generic [ref=e219]:
                - generic [ref=e220]: Win Rate MTD
                - img [ref=e222]
              - generic [ref=e226]:
                - paragraph [ref=e227]: 0%
                - generic [ref=e228]:
                  - img [ref=e229]
                  - generic [ref=e232]: +0 wobec celu
            - generic [ref=e234]:
              - generic [ref=e235]:
                - generic [ref=e236]: Nowe dziś
                - img [ref=e238]
              - paragraph [ref=e242]: "0"
          - generic [ref=e243]:
            - generic [ref=e245]:
              - generic [ref=e246]:
                - heading "Najgorętsze dziś" [level=2] [ref=e249]
                - button "Wszystkie" [ref=e250]:
                  - text: Wszystkie
                  - img [ref=e251]
              - generic [ref=e253]:
                - img [ref=e255]
                - generic [ref=e258]:
                  - paragraph [ref=e259]: Brak gorących przetargów
                  - paragraph [ref=e260]: Nowe przetargi pojawią się po następnym skanie rynku.
            - generic [ref=e262]:
              - generic [ref=e263]:
                - generic [ref=e264]:
                  - img [ref=e266]
                  - generic [ref=e268]:
                    - heading "AI Digest" [level=2] [ref=e269]
                    - paragraph [ref=e270]: Inteligencja rynkowa YU-NA
                - button "Odśwież" [ref=e271]:
                  - img [ref=e273]
                  - generic [ref=e278]: Odśwież
              - generic [ref=e280]:
                - img [ref=e282]
                - generic [ref=e284]:
                  - paragraph [ref=e285]: Digest zostanie wygenerowany dziś o 8:00
                  - paragraph [ref=e286]: Kliknij „Odśwież" aby wygenerować teraz.
    - button "Otwórz asystenta" [ref=e289]:
      - img [ref=e291]
  - generic:
    - generic [ref=e294]:
      - img [ref=e295]
      - generic [ref=e299]: Błąd API (HTTP 429)
      - button "Zamknij" [ref=e300]:
        - img [ref=e301]
    - generic [ref=e307]:
      - img [ref=e308]
      - generic [ref=e312]: Błąd API (HTTP 429)
      - button "Zamknij" [ref=e313]:
        - img [ref=e314]
    - generic [ref=e320]:
      - img [ref=e321]
      - generic [ref=e325]: Nie udało się pobrać KPI
      - button "Zamknij" [ref=e326]:
        - img [ref=e327]
  - generic [ref=e333]:
    - generic [ref=e334]:
      - generic [ref=e335]:
        - generic [ref=e336]:
          - img [ref=e338]
          - generic [ref=e342]: Twoja firma
        - generic [ref=e343]:
          - img [ref=e345]
          - generic [ref=e349]: Co robicie?
        - generic [ref=e350]:
          - img [ref=e352]
          - generic [ref=e355]: Gdzie działacie?
        - generic [ref=e356]:
          - img [ref=e358]
          - generic [ref=e365]: Start!
      - generic [ref=e366]:
        - generic [ref=e367]:
          - img [ref=e369]
          - generic [ref=e373]:
            - heading "Twoja firma" [level=2] [ref=e374]
            - paragraph [ref=e375]: Na dobry początek — powiemy systemowi, z kim ma do czynienia.
        - generic [ref=e376]:
          - img [ref=e377]
          - generic [ref=e379]: Przetargi dopasowane do Twojej firmy, nie do wszystkich.
      - generic [ref=e382]:
        - generic [ref=e383]:
          - generic [ref=e384]: Nazwa firmy
          - textbox "np. Kowalski Budownictwo Sp. z o.o." [active] [ref=e385]: E2E Tester
        - generic [ref=e386]:
          - generic [ref=e387]: NIP (opcjonalny, do weryfikacji w GUS)
          - textbox "np. 123-456-78-90" [ref=e388]
      - generic [ref=e389]:
        - button "Pomiń konfigurację" [ref=e390]
        - button "Dalej" [ref=e391]:
          - text: Dalej
          - img [ref=e392]
    - paragraph [ref=e394]: Dane konfiguracyjne mozna zmienić w dowolnym momencie w Ustawieniach.
  - alert [ref=e395]
```

# Test source

```ts
  1   | import { test, expect, Page } from '@playwright/test';
  2   | 
  3   | /**
  4   |  * E2E – Navigation tests (Terra-OS / budos)
  5   |  *
  6   |  * Pre-condition: user is authenticated (storageState from auth.setup.ts)
  7   |  *
  8   |  * Tests:
  9   |  *  1. Main dashboard visible after login
  10  |  *  2. Sidebar module navigation: Rynek, Kosztorys, Zwiad
  11  |  *  3. No unhandled JS errors in console across those modules
  12  |  */
  13  | 
  14  | const jsErrors: string[] = [];
  15  | 
  16  | test.describe('Navigation – authenticated user', () => {
  17  |   test.beforeEach(async ({ page }) => {
  18  |     // Collect uncaught JS errors
  19  |     page.on('pageerror', (err) => {
  20  |       // Ignore known benign errors (e.g. network, service worker)
  21  |       const msg = err.message;
  22  |       if (
  23  |         !msg.includes('ChunkLoadError') &&
  24  |         !msg.includes('Loading chunk') &&
  25  |         !msg.includes('serviceWorker')
  26  |       ) {
  27  |         jsErrors.push(msg);
  28  |       }
  29  |     });
  30  | 
  31  |     await page.goto('/');
  32  |     // Wait for authenticated dashboard to load
  33  |     await expect(
  34  |       page.locator('[aria-label="Zwiń menu"], [aria-label="Rozwiń menu"]').first()
  35  |     ).toBeVisible({ timeout: 15_000 });
  36  |   });
  37  | 
  38  |   test('main dashboard is visible after login', async ({ page }) => {
  39  |     // The sidebar must be visible
  40  |     await expect(
  41  |       page.locator('[aria-label="Zwiń menu"], [aria-label="Rozwiń menu"]')
  42  |     ).toBeVisible();
  43  | 
  44  |     // Main content area must exist
> 45  |     await expect(page.locator('main, [class*="content"], [class*="page"], h1, h2')).toBeVisible({ timeout: 10_000 });
      |                                                                                     ^ Error: expect(locator).toBeVisible() failed
  46  | 
  47  |     // Page title should not be an error
  48  |     await expect(page).not.toHaveTitle(/error|404|500/i);
  49  |   });
  50  | 
  51  |   test('navigate to Rynek (market-intel) module', async ({ page }) => {
  52  |     // Expand sidebar if collapsed (click toggle)
  53  |     const expandBtn = page.locator('[aria-label="Rozwiń menu"]');
  54  |     if (await expandBtn.isVisible()) {
  55  |       await expandBtn.click();
  56  |     }
  57  | 
  58  |     // Click "Rynek" in sidebar
  59  |     const rynekBtn = page.getByRole('button', { name: 'Rynek' }).first();
  60  |     await expect(rynekBtn).toBeVisible({ timeout: 5_000 });
  61  |     await rynekBtn.click();
  62  | 
  63  |     // Page content should load
  64  |     await page.waitForTimeout(2_000);
  65  | 
  66  |     // The page should show some content area
  67  |     await expect(page.locator('main, [class*="page"], h1, h2, [class*="Market"], [class*="market"]')).toBeVisible({ timeout: 10_000 });
  68  |   });
  69  | 
  70  |   test('navigate to Kosztorys module', async ({ page }) => {
  71  |     // Expand sidebar if collapsed
  72  |     const expandBtn = page.locator('[aria-label="Rozwiń menu"]');
  73  |     if (await expandBtn.isVisible()) {
  74  |       await expandBtn.click();
  75  |     }
  76  | 
  77  |     const kosztorysBtn = page.getByRole('button', { name: 'Kosztorys' }).first();
  78  |     await expect(kosztorysBtn).toBeVisible({ timeout: 5_000 });
  79  |     await kosztorysBtn.click();
  80  | 
  81  |     await page.waitForTimeout(2_000);
  82  | 
  83  |     await expect(page.locator('main, [class*="page"], h1, h2, [class*="Kosztorys"], [class*="kosztorys"]')).toBeVisible({ timeout: 10_000 });
  84  |   });
  85  | 
  86  |   test('navigate to Zwiad module', async ({ page }) => {
  87  |     // Expand sidebar if collapsed
  88  |     const expandBtn = page.locator('[aria-label="Rozwiń menu"]');
  89  |     if (await expandBtn.isVisible()) {
  90  |       await expandBtn.click();
  91  |     }
  92  | 
  93  |     const zwiadBtn = page.getByRole('button', { name: 'Zwiad' }).first();
  94  |     await expect(zwiadBtn).toBeVisible({ timeout: 5_000 });
  95  |     await zwiadBtn.click();
  96  | 
  97  |     await page.waitForTimeout(2_000);
  98  | 
  99  |     await expect(page.locator('main, [class*="page"], h1, h2, [class*="Zwiad"], [class*="zwiad"]')).toBeVisible({ timeout: 10_000 });
  100 |   });
  101 | 
  102 |   test('no unhandled JS errors across module navigation', async ({ page }) => {
  103 |     // Expand sidebar
  104 |     const expandBtn = page.locator('[aria-label="Rozwiń menu"]');
  105 |     if (await expandBtn.isVisible()) {
  106 |       await expandBtn.click();
  107 |     }
  108 | 
  109 |     const modules = ['Rynek', 'Kosztorys', 'Zwiad'];
  110 |     const collectedErrors: string[] = [];
  111 | 
  112 |     page.on('pageerror', (err) => {
  113 |       const msg = err.message;
  114 |       if (!msg.includes('ChunkLoadError') && !msg.includes('Loading chunk') && !msg.includes('serviceWorker')) {
  115 |         collectedErrors.push(msg);
  116 |       }
  117 |     });
  118 | 
  119 |     for (const moduleName of modules) {
  120 |       const btn = page.getByRole('button', { name: moduleName }).first();
  121 |       if (await btn.isVisible({ timeout: 3_000 }).catch(() => false)) {
  122 |         await btn.click();
  123 |         await page.waitForTimeout(1_500);
  124 |       }
  125 |     }
  126 | 
  127 |     // Assert no critical JS errors occurred
  128 |     expect(collectedErrors, `JS errors found: ${collectedErrors.join('; ')}`).toHaveLength(0);
  129 |   });
  130 | });
  131 | 
```