# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: auth.spec.ts >> Auth – login form >> wrong password → error message visible
- Location: e2e/auth.spec.ts:39:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=/Nieprawidłowy|błąd|spróbuj/i, [role="alert"], .error, [class*="error"]').first()
Expected: visible
Error: SyntaxError: Invalid flags supplied to RegExp constructor 'i, [role="alert"], .error, [class*="error"]'
    at new RegExp (<anonymous>)
    at createTextMatcher (<anonymous>:8050:16)
    at Object.queryAll (<anonymous>:6831:33)
    at InjectedScript._queryEngineAll (<anonymous>:6804:49)
    at InjectedScript.querySelectorAll (<anonymous>:6791:30)
    at eval (eval at evaluate (:303:30), <anonymous>:2:46)
    at UtilityScript.evaluate (<anonymous>:305:16)
    at UtilityScript.<anonymous> (<anonymous>:1:44)

Call log:
  - Expect "toBeVisible" with timeout 10000ms
  - waiting for locator('text=/Nieprawidłowy|błąd|spróbuj/i, [role="alert"], .error, [class*="error"]').first()

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e3]:
    - generic [ref=e4]:
      - generic [ref=e6]: b
      - heading "budos" [level=1] [ref=e7]
      - paragraph [ref=e8]: by YU-NA
      - paragraph [ref=e9]: AI dla przetargów budowlanych
    - generic [ref=e10]:
      - generic [ref=e11]:
        - button "Logowanie" [ref=e12]:
          - img [ref=e13]
          - text: Logowanie
        - button "Rejestracja" [ref=e16]:
          - img [ref=e17]
          - text: Rejestracja
      - generic [ref=e20]:
        - generic [ref=e21]:
          - generic [ref=e22]: E-mail
          - generic [ref=e23]:
            - img
            - textbox "twoj@firma.pl" [ref=e24]: e2e_test@terra.os
        - generic [ref=e25]:
          - generic [ref=e26]: Hasło
          - generic [ref=e27]:
            - img
            - textbox "••••••••" [ref=e28]: WrongPassword999!
            - button "Pokaż hasło" [ref=e29]:
              - img [ref=e30]
        - generic [ref=e34]:
          - img [ref=e35]
          - generic [ref=e37]: Nie udało się wykonać operacji. Spróbuj ponownie.
        - button "Zaloguj się" [ref=e38]:
          - img [ref=e39]
          - text: Zaloguj się
        - button "Zapomniałeś hasła?" [ref=e42]
    - paragraph [ref=e43]: budos © 2026
  - alert [ref=e44]
```