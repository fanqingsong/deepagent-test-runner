import { test, expect } from '@playwright/test';
import { loginViaApi } from '../fixtures/test-helpers';

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaApi(page);
    await page.goto('/#dashboard');
    await page.waitForURL(/#dashboard/);
  });

  test('displays dashboard title', async ({ page }) => {
    await expect(page.locator('text=测试仪表板')).toBeVisible();
  });

  test('displays stats cards section', async ({ page }) => {
    const statsContainer = page.locator('.stats-cards, [class*="stats"]').first();
    await expect(statsContainer).toBeVisible({ timeout: 15000 });
  });

  test('displays recent test runs', async ({ page }) => {
    await expect(page.locator('text=最近')).toBeVisible({ timeout: 15000 });
  });

  test('displays role indicator', async ({ page }) => {
    const roleIndicator = page.locator('text=管理员视图').or(page.locator('text=个人视图'));
    await expect(roleIndicator).toBeVisible({ timeout: 10000 });
  });

  test('navigation tabs are visible', async ({ page }) => {
    await expect(page.locator('button:has-text("仪表板")')).toBeVisible();
    await expect(page.locator('button:has-text("测试管理")')).toBeVisible();
    await expect(page.locator('button:has-text("调度配置")')).toBeVisible();
  });
});
