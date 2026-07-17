import { test, expect } from '@playwright/test';

/**
 * E2E – Authentication tests (Terra-OS / budos)
 *
 * Tests:
 *  1. Valid credentials → dashboard visible
 *  2. Wrong password → error message shown
 *  3. Password visibility toggle
 */

// These tests do NOT use saved storageState — they start fresh
test.use({ storageState: { cookies: [], origins: [] } });

const VALID_EMAIL = 'e2e_test@terra.os';
const VALID_PASS = 'E2eTest123!';

test.describe('Auth – login form', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Make sure we see the login form
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10_000 });
  });

  test('valid credentials → dashboard visible', async ({ page }) => {
    await page.locator('input[type="email"]').fill(VALID_EMAIL);
    await page.locator('input[type="password"]').fill(VALID_PASS);
    await page.locator('button[type="submit"]').click();

    // After login the sidebar navigation should appear
    await expect(
      page.locator('[aria-label="Zwiń menu"], [aria-label="Rozwiń menu"]').first()
    ).toBeVisible({ timeout: 15_000 });

    // The login form should no longer be visible
    await expect(page.locator('button[type="submit"]')).not.toBeVisible({ timeout: 5_000 });
  });

  test('wrong password → error message visible', async ({ page }) => {
    await page.locator('input[type="email"]').fill(VALID_EMAIL);
    await page.locator('input[type="password"]').fill('WrongPassword999!');
    await page.locator('button[type="submit"]').click();

    // Expect an error message to appear
    // The LoginForm shows error text directly in the DOM
    const errorMsg = page.locator('[role="alert"], .error, [class*="error"]');
    const errorText = page.getByText(/Nieprawidłowy|błąd|spróbuj/i);
    const anyError = errorMsg.or(errorText);
    await expect(anyError.first()).toBeVisible({ timeout: 10_000 });

    // Should still be on the login page (form still visible)
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test('wrong password → stays on login page', async ({ page }) => {
    await page.locator('input[type="email"]').fill(VALID_EMAIL);
    await page.locator('input[type="password"]').fill('BadPass123!');
    await page.locator('button[type="submit"]').click();

    // After a moment, the email input must still be visible (not navigated away)
    await page.waitForTimeout(3_000);
    await expect(page.locator('input[type="email"]')).toBeVisible();
  });

  test('password visibility toggle', async ({ page }) => {
    const passwordInput = page.locator('input[type="password"], input[type="text"][placeholder*="••"]').first();
    const toggleButton = page.locator('button[aria-label="Pokaż hasło"], button[aria-label="Ukryj hasło"]').first();

    // Initially password is hidden
    await expect(page.locator('input[type="password"]')).toBeVisible();

    // Click toggle
    await toggleButton.click();

    // After toggle: input type should be text (or password hidden field disappears)
    const visibleInput = page.locator('input[type="text"]');
    await expect(visibleInput).toBeVisible({ timeout: 5_000 });

    // Toggle back
    const hideButton = page.locator('button[aria-label="Ukryj hasło"]').first();
    if (await hideButton.isVisible()) {
      await hideButton.click();
      await expect(page.locator('input[type="password"]')).toBeVisible({ timeout: 5_000 });
    }
  });
});
