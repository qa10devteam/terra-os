import { test as setup, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const authFile = path.join(__dirname, '.auth/user.json');

setup('authenticate', async ({ page }) => {
  // Ensure .auth directory exists
  const authDir = path.dirname(authFile);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  await page.goto('/');

  // Fill login form
  await page.locator('input[type="email"]').fill('e2e_test@terra.os');
  await page.locator('input[type="password"]').fill('E2eTest123!');
  await page.locator('button[type="submit"]').click();

  // Wait for the sidebar (dashboard) to appear — means login was successful
  // Use first() to avoid strict mode violation (multiple nav/button elements may exist)
  await expect(page.locator('[aria-label="Zwiń menu"], [aria-label="Rozwiń menu"]').first()).toBeVisible({ timeout: 15_000 });

  // Save signed-in state
  await page.context().storageState({ path: authFile });
});
