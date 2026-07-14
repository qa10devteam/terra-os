import { test, expect } from '@playwright/test';

test.describe('Smoke tests – Terra.OS top pages', () => {
  test('/ (dashboard) loads successfully', async ({ page }) => {
    await page.goto('/');
    // Verify page rendered with some heading or main content area
    await expect(page.locator('h1, h2, [data-testid="dashboard"], main')).toBeVisible();
    // No uncaught errors – page title should be set
    await expect(page).not.toHaveTitle(/error|500|404/i);
  });

  test('/tenders – table or list renders', async ({ page }) => {
    await page.goto('/tenders');
    // Verify a table, list, or grid of tenders is visible
    const content = page.locator(
      'table, [role="grid"], [data-testid="tenders-list"], ul, [class*="tender"]'
    );
    await expect(content.first()).toBeVisible({ timeout: 10_000 });
  });

  test('/alerts – page loads', async ({ page }) => {
    await page.goto('/alerts');
    await expect(
      page.locator('h1, h2, [data-testid="alerts"], main')
    ).toBeVisible();
    await expect(page).not.toHaveTitle(/error|500|404/i);
  });

  test('/settings – page loads', async ({ page }) => {
    await page.goto('/settings');
    await expect(
      page.locator('h1, h2, [data-testid="settings"], main')
    ).toBeVisible();
    await expect(page).not.toHaveTitle(/error|500|404/i);
  });

  test('/billing – plan name is shown', async ({ page }) => {
    await page.goto('/billing');
    // Expect some plan indicator (text like "Pro", "Free", "Enterprise" or a plan element)
    const planIndicator = page.locator(
      '[data-testid="plan-name"], [class*="plan"], text=/Pro|Free|Starter|Enterprise|Basic/i'
    );
    await expect(planIndicator.first()).toBeVisible({ timeout: 10_000 });
  });

  test('/login – form renders, submit redirects', async ({ page }) => {
    // Clear auth state for this test
    await page.context().clearCookies();

    await page.goto('/login');

    // Verify login form elements
    const emailInput = page.getByLabel(/email/i);
    const passwordInput = page.getByLabel(/hasło|password/i);
    const submitBtn = page.getByRole('button', { name: /zaloguj|login|sign in/i });

    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(submitBtn).toBeVisible();

    // Fill and submit
    await emailInput.fill('test@terra.os');
    await passwordInput.fill('TestPassword123!');
    await submitBtn.click();

    // Verify redirect away from /login
    await expect(page).not.toHaveURL(/\/login/, { timeout: 10_000 });
  });
});
