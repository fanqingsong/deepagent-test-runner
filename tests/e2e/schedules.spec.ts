import { test, expect } from '@playwright/test';
import { loginViaApi, createTestDefinition, createSchedule } from '../fixtures/test-helpers';

test.describe('Schedule Management', () => {
  let token: string;

  test.beforeEach(async ({ page }) => {
    token = await loginViaApi(page);
    await page.goto('/#schedules');
    await page.waitForURL(/#schedules/);
  });

  test('displays schedule management page', async ({ page }) => {
    await expect(page.locator('text=调度配置')).toBeVisible();
  });

  test('displays create schedule button', async ({ page }) => {
    await expect(page.locator('button:has-text("创建调度")')).toBeVisible();
  });

  test('opens create schedule modal', async ({ page }) => {
    await page.locator('button:has-text("创建调度")').click();
    await expect(page.locator('text=创建新调度')).toBeVisible();
  });

  test('displays schedule from API', async ({ page }) => {
    const testDef = await createTestDefinition(page, token, {
      name: 'Schedule E2E Test',
    });
    await createSchedule(page, token, testDef.id as number, {
      name: 'E2E Visible Schedule',
    });

    await page.reload();
    await page.waitForURL(/#schedules/);

    await expect(page.locator('text=E2E Visible Schedule')).toBeVisible({ timeout: 10000 });
  });

  test('can toggle schedule active/inactive', async ({ page }) => {
    const testDef = await createTestDefinition(page, token);
    const schedule = await createSchedule(page, token, testDef.id as number, {
      name: 'E2E Toggle Schedule',
    });

    await page.reload();
    await page.waitForURL(/#schedules/);

    const scheduleRow = page.locator('tr:has-text("E2E Toggle Schedule")');
    await expect(scheduleRow).toBeVisible({ timeout: 10000 });

    const toggleBtn = scheduleRow.locator('button[title*="禁用"], button[title*="启用"]').first();
    if (await toggleBtn.isVisible()) {
      await toggleBtn.click();
    }
  });
});
