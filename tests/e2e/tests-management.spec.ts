import { test, expect } from '@playwright/test';
import { loginViaApi, createTestDefinition } from '../fixtures/test-helpers';

test.describe('Test Management', () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    token = await loginViaApi(page);
    await page.goto('/#tests');
    await page.waitForURL(/#tests/);
  });

  test('displays test management page', async ({ page }) => {
    await expect(page.locator('text=测试管理')).toBeVisible();
  });

  test('displays create test button', async ({ page }) => {
    await expect(page.locator('button:has-text("创建测试")')).toBeVisible();
  });

  test('opens create test modal', async ({ page }) => {
    await page.locator('button:has-text("创建测试")').click();
    await expect(page.locator('text=创建新测试')).toBeVisible();
  });

  test('displays test list from API', async ({ page }) => {
    await createTestDefinition(page, token, {
      name: 'E2E Visible Test',
      description: 'Should appear in list',
    });

    await page.reload();
    await page.waitForURL(/#tests/);

    await expect(page.locator('text=E2E Visible Test')).toBeVisible({ timeout: 10000 });
  });

  test('search filters tests by name', async ({ page }) => {
    await createTestDefinition(page, token, { name: 'Searchable Alpha Test' });
    await createTestDefinition(page, token, { name: 'Searchable Beta Test' });

    await page.reload();
    await page.waitForURL(/#tests/);

    await expect(page.locator('text=Searchable Alpha')).toBeVisible({ timeout: 10000 });

    await page.locator('.search-input, input[placeholder*="搜索"]').fill('Alpha');
    await expect(page.locator('text=Searchable Alpha')).toBeVisible();
    await expect(page.locator('text=Searchable Beta')).not.toBeVisible();
  });

  test('shows empty state when no tests match filter', async ({ page }) => {
    await page.locator('.search-input, input[placeholder*="搜索"]').fill('zzz_no_match_xyz');
    await expect(page.locator('text=没有找到测试用例')).toBeVisible({ timeout: 10000 });
  });
});
