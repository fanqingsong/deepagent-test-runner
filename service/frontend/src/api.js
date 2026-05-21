// API Base URLs — use same origin as the page (nginx proxy in dev/prod)
const BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ||
  window.location.origin;

const TEST_API = `${BASE_URL}/api/v1`;
const DASHBOARD_API = `${BASE_URL}/api/v1/analytics`;
const SCHEDULER_API = `${BASE_URL}/api/v1`;
const USERS_API = `${BASE_URL}/api/v1`;

// Import authService for authentication
import authService from './services/authService';

const getAuthHeaders = () => {
  const token = authService.getAccessToken();
  if (!token) {
    return {};
  }
  return {
    Authorization: `Bearer ${token}`,
  };
};

export async function parseApiError(response, fallback) {
  const status = response?.status;
  const statusText = response?.statusText || '';
  let bodyText = '';
  try {
    bodyText = await response.text();
  } catch {
    bodyText = '';
  }
  let detail = '';
  if (bodyText) {
    try {
      const json = JSON.parse(bodyText);
      detail =
        json?.detail ||
        json?.error ||
        json?.message ||
        (typeof json === 'string' ? json : '') ||
        bodyText;
    } catch {
      detail = bodyText;
    }
  }
  const parts = [
    typeof status === 'number' ? `HTTP ${status}` : null,
    statusText || null,
    (detail || '').toString().trim() || null,
  ].filter(Boolean);
  const base = fallback || '请求失败';
  return parts.length ? `${base}（${parts.join(' - ')}）` : base;
}

async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    mode: 'cors',
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
  });
  if (response.status === 401) {
    window.location.hash = 'login';
    throw new Error('登录已过期，请重新登录');
  }
  return response;
}

export const getTests = async () => {
  const response = await apiFetch(`${TEST_API}/test-definitions/`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, '加载测试列表失败'));
  }
  return response.json();
};

export const createTest = async (testData) => {
  try {
    const { test_steps, ...testInfo } = testData;

    // Create test
    // ROOT CAUSE: Missing trailing slash caused ERR_CONNECTION_REFUSED
    // Nginx routes /api/v1/ with trailing slash, so POST endpoint must match
    const createUrl = `${TEST_API}/test-definitions/`;
    console.log('=== Creating Test ===');
    console.log('Full URL:', createUrl);
    console.log('Request body:', JSON.stringify(testInfo, null, 2));
    console.log('====================');

    const testResponse = await fetch(createUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(testInfo),
      mode: 'cors'
    });

    if (!testResponse.ok) {
      throw new Error(`Failed to create test: ${testResponse.statusText}`);
    }

    const test = await testResponse.json();

    // Replace steps in one request (avoid N+1 calls)
    const replaceStepsResponse = await fetch(`${TEST_API}/test-steps/test-definition/${test.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({
        test_steps: (test_steps || []).map((step, index) => ({
          step_number: index + 1,
          description: step.description,
          type: 'action',
          params: {},
          expected_result: null
        }))
      }),
      mode: 'cors'
    });

    if (!replaceStepsResponse.ok) {
      const errorText = await replaceStepsResponse.text();
      throw new Error(`Failed to replace steps: ${replaceStepsResponse.statusText} - ${errorText}`);
    }

    return test;
  } catch (error) {
    console.error('Error creating test:', error);
    throw new Error('Failed to create test. Please try again.');
  }
};

export const updateTest = async (testId, testData) => {
  try {
    const { test_steps, ...testInfo } = testData;

    // Use test_id instead of numeric ID for PUT request
    const testIdString = testInfo.test_id || testId.toString();

    // Update test basic info
    const testResponse = await fetch(`${TEST_API}/test-definitions/${testIdString}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(testInfo),
      mode: 'cors'
    });

    if (!testResponse.ok) {
      const errorText = await testResponse.text();
      throw new Error(`Failed to update test: ${testResponse.statusText} - ${errorText}`);
    }

    const test = await testResponse.json();

    // Get the internal ID from the response
    const internalId = test.id;

    // Replace steps in one request (avoid N+1 calls)
    const replaceStepsResponse = await fetch(`${TEST_API}/test-steps/test-definition/${internalId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({
        test_steps: (test_steps || []).map((step, index) => ({
          step_number: index + 1,
          description: step.description,
          type: 'action',
          params: {},
          expected_result: null
        }))
      }),
      mode: 'cors'
    });

    if (!replaceStepsResponse.ok) {
      const errorText = await replaceStepsResponse.text();
      throw new Error(`Failed to replace steps: ${replaceStepsResponse.statusText} - ${errorText}`);
    }

    return test;
  } catch (error) {
    console.error('Error updating test:', error);
    throw error;
  }
};

// Dashboard API
export const getDashboardData = async (days = 30) => {
  try {
    const response = await fetch(`${DASHBOARD_API}/dashboard?days=${days}`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch dashboard data: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error('Error fetching dashboard data:', error);
    throw error;
  }
};

export const getTestRuns = async (limit = 20) => {
  try {
    const response = await fetch(`${DASHBOARD_API}/test-runs?limit=${limit}`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch test runs: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error('Error fetching test runs:', error);
    throw error;
  }
};

export const getTestRunDetails = async (runId) => {
  try {
    const response = await fetch(`${DASHBOARD_API}/test-runs/${runId}`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch test run details: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error('Error fetching test run details:', error);
    throw error;
  }
};

// Get test job status
export const getJobStatus = async (jobId) => {
  try {
    const response = await fetch(`${SCHEDULER_API}/jobs/${jobId}`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      mode: 'cors'
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch job status: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error('Error fetching job status:', error);
    throw error;
  }
};

// Get all jobs
export const getJobs = async () => {
  try {
    const response = await fetch(`${SCHEDULER_API}/jobs/`, {
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      mode: 'cors'
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch jobs: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error('Error fetching jobs:', error);
    return [];
  }
};

export const getTestStats = async () => {
  try {
    const response = await fetch(`${DASHBOARD_API}/dashboard`, {
      headers: getAuthHeaders()
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch test stats: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error('Error fetching test stats:', error);
    throw error;
  }
};

export const getSchedules = async () => {
  const response = await apiFetch(`${SCHEDULER_API}/schedules/`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, '加载调度列表失败'));
  }
  return response.json();
};

export const deleteSchedule = async (scheduleId) => {
  const response = await apiFetch(`${SCHEDULER_API}/schedules/${scheduleId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, '删除调度失败'));
  }
};

export const getUsers = async () => {
  const response = await apiFetch(`${USERS_API}/users`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, '加载用户列表失败'));
  }
  return response.json();
};

export const updateUser = async (userId, userData) => {
  const response = await apiFetch(`${USERS_API}/users/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, '更新用户失败'));
  }
  return response.json();
};

export const deleteUser = async (userId) => {
  const response = await apiFetch(`${USERS_API}/users/${userId}`, {
    method: 'DELETE',
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, '删除用户失败'));
  }
};

// Conversations
export const createConversation = async (testDefinitionId, type = 'planning', metadata = {}) => {
  const response = await fetch(`${TEST_API}/conversations/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ test_definition_id: testDefinitionId, thread_type: type, metadata })
  });
  if (!response.ok) throw new Error('Failed to create conversation');
  return response.json();
};

export const getConversation = async (threadId) => {
  const response = await fetch(`${TEST_API}/conversations/${threadId}`, {
    headers: { ...getAuthHeaders() }
  });
  if (!response.ok) throw new Error('Failed to get conversation');
  return response.json();
};

export const sendMessage = async (threadId, content) => {
  const response = await fetch(`${TEST_API}/conversations/${threadId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ content })
  });
  if (!response.ok) throw new Error('Failed to send message');
  return response.json();
};

export const approveConversation = async (threadId, modifications = []) => {
  const response = await fetch(`${TEST_API}/conversations/${threadId}/approve`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ modifications })
  });
  if (!response.ok) throw new Error('Failed to approve conversation');
  return response.json();
};

export const regeneratePlan = async (threadId, feedback) => {
  const response = await fetch(`${TEST_API}/conversations/${threadId}/regenerate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ feedback })
  });
  if (!response.ok) throw new Error('Failed to regenerate plan');
  return response.json();
};

// Failure recovery
export const getFailureConversation = async (runId) => {
  const response = await fetch(`${TEST_API}/conversations/failure/${runId}`, {
    headers: { ...getAuthHeaders() }
  });
  if (!response.ok) throw new Error('Failed to get failure conversation');
  return response.json();
};

export const respondToFailure = async (runId, action, params = {}) => {
  const response = await fetch(`${TEST_API}/conversations/failure/${runId}/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ action, params })
  });
  if (!response.ok) throw new Error('Failed to respond to failure');
  return response.json();
};

// Regression
export const saveAsRegression = async (testId, runId) => {
  const response = await fetch(`${TEST_API}/test-definitions/regression/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ run_id: runId })
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, '保存回归测试失败'));
  }
  return response.json();
};

export const getRegressionTests = async () => {
  const response = await fetch(`${TEST_API}/test-definitions/regression`, {
    headers: { ...getAuthHeaders() }
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, '加载回归测试列表失败'));
  }
  return response.json();
};

// APP Workspace
export const createApp = async (data) => {
  const response = await apiFetch(`${TEST_API}/apps/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, '创建 APP 失败'));
  return response.json();
};

export const listApps = async (params = {}) => {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  if (params.search) qs.set('search', params.search);
  const response = await apiFetch(`${TEST_API}/apps/?${qs.toString()}`);
  if (!response.ok) throw new Error(await parseApiError(response, '加载 APP 列表失败'));
  return response.json();
};

export const getApp = async (appId) => {
  const response = await apiFetch(`${TEST_API}/apps/${appId}`);
  if (!response.ok) throw new Error(await parseApiError(response, '加载 APP 失败'));
  return response.json();
};

export const updateApp = async (appId, data) => {
  const response = await apiFetch(`${TEST_API}/apps/${appId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, '更新 APP 失败'));
  return response.json();
};

export const archiveApp = async (appId) => {
  const response = await apiFetch(`${TEST_API}/apps/${appId}`, { method: 'DELETE' });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, '删除 APP 失败'));
  }
};

export const runApp = async (appId, { forceRegenerate, useExistingPlan } = {}) => {
  const response = await apiFetch(`${TEST_API}/apps/${appId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      force_regenerate: !!forceRegenerate,
      use_existing_plan: !!useExistingPlan,
    }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, '运行 APP 失败'));
  return response.json();
};

export const generateAppPlan = async (appId) => {
  const response = await apiFetch(`${TEST_API}/apps/${appId}/generate-plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, '生成测试计划失败'));
  return response.json();
};

export const saveAppSteps = async (appId) => {
  const response = await apiFetch(`${TEST_API}/apps/${appId}/save-steps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, '保存测试步骤失败'));
  return response.json();
};

export const getAppRunProgress = async (appId) => {
  const response = await apiFetch(`${TEST_API}/apps/${appId}/run-progress`);
  if (!response.ok) throw new Error(await parseApiError(response, '获取进度失败'));
  return response.json();
};

export const refineApp = async (appId, feedback) => {
  const response = await apiFetch(`${TEST_API}/apps/${appId}/refine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, '优化计划失败'));
  return response.json();
};

export const publishApp = async (appId) => {
  const response = await apiFetch(`${TEST_API}/apps/${appId}/publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, '发布 APP 失败'));
  return response.json();
};
