import { test, expect } from '@playwright/test';

test.describe('Registration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/#login');
  });

  test('switches to register form', async ({ page }) => {
    await page.locator('button:has-text("Create account")').click();
    await expect(page.locator('text=Create a new account')).toBeVisible();
  });

  test('switches back to login from register', async ({ page }) => {
    await page.locator('button:has-text("Create account")').click();
    await expect(page.locator('text=Create a new account')).toBeVisible();

    await page.locator('button:has-text("Sign in")').click();
    await expect(page.locator('text=Sign in to your account')).toBeVisible();
  });
});
