import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '.auth/user.json');

setup('authenticate', async ({ page }) => {
  await page.goto('/login');

  await page.getByLabel(/email/i).fill('test@terra.os');
  await page.getByLabel(/hasło|password/i).fill('TestPassword123!');
  await page.getByRole('button', { name: /zaloguj|login|sign in/i }).click();

  // Wait for redirect away from login
  await expect(page).not.toHaveURL(/\/login/);

  // Save signed-in state
  await page.context().storageState({ path: authFile });
});
