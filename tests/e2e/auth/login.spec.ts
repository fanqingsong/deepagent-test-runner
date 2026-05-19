import { test, expect } from '@playwright/test';
import { loginViaApi, TEST_USER } from '../../fixtures/test-helpers';

test.describe('Login', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/#login');
  });

  test('shows login form with email and password fields', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('AI Test Runner');
    await expect(page.locator('#login-email')).toBeVisible();
    await expect(page.locator('#login-password')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText('Sign In');
  });

  test('validates empty email field', async ({ page }) => {
    await page.locator('#login-password').fill('somepassword');
    await page.locator('button[type="submit"]').click();
    await expect(page.locator('.error-message, [role="alert"]')).toBeVisible();
  });

  test('validates empty password field', async ({ page }) => {
    await page.locator('#login-email').fill('test@example.com');
    await page.locator('button[type="submit"]').click();
    await expect(page.locator('.error-message, [role="alert"]')).toBeVisible();
  });

  test('shows error on invalid credentials', async ({ page }) => {
    await page.locator('#login-email').fill('wrong@test.com');
    await page.locator('#login-password').fill('wrongpassword');
    await page.locator('button[type="submit"]').click();
    await expect(page.locator('.error-message, [role="alert"]')).toBeVisible();
  });

  test('successful login redirects to dashboard', async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/#dashboard');
    await page.waitForURL(/#dashboard/);
    await expect(page.locator('text=测试仪表板')).toBeVisible();
  });

  test('logout redirects to login page', async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/#dashboard');
    await page.waitForURL(/#dashboard/);

    await page.locator('button:has-text("退出登录")').click();
    await expect(page).toHaveURL(/#login/);
  });

  test('forgot password link switches to password reset', async ({ page }) => {
    await page.locator('button:has-text("Forgot password")').click();
    await expect(page.locator('text=Reset Your Password')).toBeVisible();
  });
});
