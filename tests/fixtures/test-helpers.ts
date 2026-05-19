import { test as base, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8080';

export const TEST_USER = {
  email: 'e2e@test.com',
  password: 'TestPass123!',
};

export const ADMIN_USER = {
  email: 'admin@test.com',
  password: 'AdminPass123!',
};

export async function doLogin(
  page: Page,
  email: string = TEST_USER.email,
  password: string = TEST_USER.password
): Promise<{ token: string; user: Record<string, unknown> }> {
  const response = await page.request.post(`${BASE_URL}/api/v1/auth/login`, {
    data: { email, password, remember_me: false },
  });

  if (!response.ok()) {
    throw new Error(`Login failed: ${response.status()} ${await response.text()}`);
  }

  const data = await response.json();
  return { token: data.access_token, user: data.user };
}

type AuthFixture = {
  authedPage: Page;
  authToken: string;
};

export const test = base.extend<AuthFixture>({
  authedPage: async ({ page }, use) => {
    const { token, user } = await doLogin(page);

    await page.goto('/#login');
    await page.evaluate(
      ({ token, user }) => {
        localStorage.setItem('auth_token', token);
        localStorage.setItem('refresh_token', '');
        localStorage.setItem('user', JSON.stringify(user));
      },
      { token, user }
    );

    await use(page);
  },
  authToken: async ({ page }, use) => {
    const { token } = await doLogin(page);
    await use(token);
  },
});

export { expect } from '@playwright/test';

export async function createTestDefinition(
  page: Page,
  token: string,
  overrides: Record<string, unknown> = {}
): Promise<Record<string, unknown>> {
  const defaults = {
    name: `E2E Test ${Date.now()}`,
    description: 'Created by E2E test',
    test_id: `E2E_${Date.now()}`,
    url: 'https://example.com',
    tags: ['e2e'],
    test_goal: 'E2E test goal',
    test_steps: [
      {
        step_number: 1,
        description: 'Navigate to page',
        type: 'navigate',
        params: { url: 'https://example.com' },
        expected_result: 'Page loaded',
      },
    ],
  };

  const response = await page.request.post(`${BASE_URL}/api/v1/test-definitions/`, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    data: { ...defaults, ...overrides },
  });

  if (!response.ok()) {
    throw new Error(`Create test failed: ${response.status()}`);
  }

  return response.json();
}

export async function createSchedule(
  page: Page,
  token: string,
  testDefinitionId: number,
  overrides: Record<string, unknown> = {}
): Promise<Record<string, unknown>> {
  const defaults = {
    name: `E2E Schedule ${Date.now()}`,
    schedule_type: 'single',
    test_definition_id: testDefinitionId,
    cron_expression: '0 2 * * *',
    timezone: 'UTC',
    is_active: true,
  };

  const response = await page.request.post(`${BASE_URL}/api/v1/schedules/`, {
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    data: { ...defaults, ...overrides },
  });

  if (!response.ok()) {
    throw new Error(`Create schedule failed: ${response.status()}`);
  }

  return response.json();
}
