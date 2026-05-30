// API Base URLs — use relative paths so the browser preserves the port
const BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ||
  '';

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
  const base = fallback || 'Request failed';
  return parts.length ? `${base} (${parts.join(' - ')})` : base;
}

async function apiFetch(url, options = {}) {
  const controller = new AbortController();
  const { timeout: timeoutMs = 15000, ...fetchOptions } = options;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      mode: 'cors',
      signal: controller.signal,
      ...fetchOptions,
      headers: {
        ...getAuthHeaders(),
        ...(fetchOptions.headers || {}),
      },
    });
    clearTimeout(timeoutId);

    if (response.status === 401) {
      // Try refreshing the token once before redirecting to login
      try {
        await authService.refreshToken();
        const retryResponse = await fetch(url, {
          mode: 'cors',
          ...fetchOptions,
          headers: {
            ...getAuthHeaders(),
            ...(fetchOptions.headers || {}),
          },
        });
        if (retryResponse.status !== 401) return retryResponse;
      } catch {
        // refresh failed, fall through to redirect
      }
      window.location.hash = 'login';
      throw new Error('Session expired, please log in again');
    }
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Request timeout - server took too long to respond');
    }
    throw error;
  }
}




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

// Suite Dashboard API
export const getSuiteDashboard = async (days = 30) => {
  const response = await fetch(`${DASHBOARD_API}/suite-dashboard?days=${days}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error(`Failed to fetch suite dashboard: ${response.statusText}`);
  return response.json();
};

export const getSuiteRunTimeline = async (suiteId, limit = 10) => {
  const response = await fetch(
    `${DASHBOARD_API}/suite-runs/timeline/${suiteId}?limit=${limit}`,
    { headers: getAuthHeaders() }
  );
  if (!response.ok) throw new Error(`Failed to fetch suite timeline: ${response.statusText}`);
  return response.json();
};

export const getSuiteRunEntries = async (runId) => {
  const response = await fetch(`${DASHBOARD_API}/suite-runs/${runId}/entries`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error(`Failed to fetch suite run entries: ${response.statusText}`);
  return response.json();
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
    throw new Error(await parseApiError(response, 'Failed to load schedule list'));
  }
  return response.json();
};

export const deleteSchedule = async (scheduleId) => {
  const response = await apiFetch(`${SCHEDULER_API}/schedules/${scheduleId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to delete schedule'));
  }
};

export const getUsers = async () => {
  const response = await apiFetch(`${USERS_API}/users`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to load user list'));
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
    throw new Error(await parseApiError(response, 'Failed to update user'));
  }
  return response.json();
};

export const deleteUser = async (userId) => {
  const response = await apiFetch(`${USERS_API}/users/${userId}`, {
    method: 'DELETE',
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, 'Failed to delete user'));
  }
};

// Regression
export const saveAsRegression = async (testId, runId) => {
  const response = await fetch(`${TEST_API}/test-definitions/regression/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ run_id: runId })
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to save regression test'));
  }
  return response.json();
};

export const getRegressionTests = async () => {
  const response = await fetch(`${TEST_API}/test-definitions/regression`, {
    headers: { ...getAuthHeaders() }
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to load regression test list'));
  }
  return response.json();
};

// Test Cases Workspace
export const createTestCase = async (data) => {
  const response = await apiFetch(`${TEST_API}/apps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to create Test Case'));
  return response.json();
};

export const listTestCases = async (params = {}) => {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  if (params.search) qs.set('search', params.search);
  const response = await apiFetch(`${TEST_API}/apps/?${qs.toString()}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load Test Case list'));
  return response.json();
};

export const getTestCase = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load Test Case'));
  return response.json();
};

export const updateTestCase = async (testCaseId, data) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update Test Case'));
  return response.json();
};

export const archiveTestCase = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}`, { method: 'DELETE' });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, 'Failed to delete Test Case'));
  }
};

export const runTestCase = async (testCaseId, { forceRegenerate, useExistingPlan } = {}) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      force_regenerate: !!forceRegenerate,
      use_existing_plan: !!useExistingPlan,
    }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to run Test Case'));
  return response.json();
};

export const generateTestCasePlan = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/generate-plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to generate test plan'));
  return response.json();
};

export const saveTestCasesSteps = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/save-steps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to save test steps'));
  return response.json();
};

export const getTestCaseRunProgress = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/run-progress`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to get progress'));
  return response.json();
};

export const getTestCaseRunHistory = async (testCaseId, { limit = 50, offset = 0 } = {}) => {
  const response = await apiFetch(
    `${TEST_API}/apps/${testCaseId}/runs?limit=${limit}&offset=${offset}`
  );
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load run history'));
  return response.json();
};

export const getTestCaseStepVersions = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/step-versions`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load version history'));
  return response.json();
};

export const restoreTestCaseStepVersion = async (testCaseId, versionId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/step-versions/${versionId}/restore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to restore version'));
  return response.json();
};

export const submitVersionForReview = async (testCaseId, versionId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/step-versions/${versionId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to submit version for review'));
  return response.json();
};

export const refineTestCase = async (testCaseId, feedback) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/refine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to refine plan'));
  return response.json();
};

export const publishTestCase = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to publish Test Case'));
  return response.json();
};

// User Search
export const searchUsers = async (query) => {
  const response = await apiFetch(`${USERS_API}/users/search?q=${encodeURIComponent(query)}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to search users'));
  return response.json();
};

// Test Case Permissions
export const getTestCasePermissions = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/permissions`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load permission list'));
  return response.json();
};

export const addTestCasePermission = async (testCaseId, { userId, permissionType }) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/permissions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, permission_type: permissionType }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to add permission'));
  return response.json();
};

export const updateTestCasePermission = async (testCaseId, userId, { permissionType }) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/permissions/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ permission_type: permissionType }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update permission'));
  return response.json();
};

export const removeTestCasePermission = async (testCaseId, userId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/permissions/${userId}`, {
    method: 'DELETE',
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, 'Failed to remove permission'));
  }
};

// --- Test Suites ---

export const getTestSuites = async (skip = 0, limit = 100) => {
  const response = await apiFetch(`${TEST_API}/test-suites/?skip=${skip}&limit=${limit}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load test suite'));
  return response.json();
};

export const getTestSuite = async (suiteId) => {
  const response = await apiFetch(`${TEST_API}/test-suites/${suiteId}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load test suite'));
  return response.json();
};

export const createTestSuite = async (data) => {
  const response = await apiFetch(`${TEST_API}/test-suites`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to create test suite'));
  return response.json();
};

export const updateTestSuite = async (suiteId, data) => {
  const response = await apiFetch(`${TEST_API}/test-suites/${suiteId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update test suite'));
  return response.json();
};

export const deleteTestSuite = async (suiteId) => {
  const response = await apiFetch(`${TEST_API}/test-suites/${suiteId}`, { method: 'DELETE' });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, 'Failed to delete test suite'));
  }
};

export const runTestSuite = async (suiteId, environment = {}) => {
  const response = await apiFetch(`${TEST_API}/test-suites/${suiteId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ environment }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to run test suite'));
  return response.json();
};

export const getSuiteRuns = async (suiteId, skip = 0, limit = 50) => {
  const response = await apiFetch(`${TEST_API}/test-suites/${suiteId}/runs?skip=${skip}&limit=${limit}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load suite run records'));
  return response.json();
};

export const getSuiteRunDetail = async (runId) => {
  const response = await apiFetch(`${TEST_API}/test-suites/runs/${runId}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load suite run details'));
  return response.json();
};

export const cancelSuiteRun = async (runId) => {
  const response = await apiFetch(`${TEST_API}/test-suites/runs/${runId}/cancel`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to cancel suite run'));
  return response.json();
};

export const resolveSuite = async (suiteId) => {
  const response = await apiFetch(`${TEST_API}/test-suites/${suiteId}/resolve`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to resolve suite'));
  return response.json();
};

// --- Run Configs ---

export const getRunConfigs = async (skip = 0, limit = 100) => {
  const response = await apiFetch(`${TEST_API}/run-configs/?skip=${skip}&limit=${limit}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load run config'));
  return response.json();
};

export const createRunConfig = async (data) => {
  const response = await apiFetch(`${TEST_API}/run-configs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to create run config'));
  return response.json();
};

export const updateRunConfig = async (configId, data) => {
  const response = await apiFetch(`${TEST_API}/run-configs/${configId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update run config'));
  return response.json();
};

export const deleteRunConfig = async (configId) => {
  const response = await apiFetch(`${TEST_API}/run-configs/${configId}`, { method: 'DELETE' });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, 'Failed to delete run config'));
  }
};

// --- Tags ---

export const getTags = async () => {
  const response = await apiFetch(`${TEST_API}/tags`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load tag list'));
  return response.json();
};

export const getTestsByTag = async (tag) => {
  const response = await apiFetch(`${TEST_API}/tags/${encodeURIComponent(tag)}/tests`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load tag tests'));
  return response.json();
};

export const bulkApplyTags = async (testDefinitionIds, tags, mode = 'add') => {
  const response = await apiFetch(`${TEST_API}/tags/bulk-apply`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ test_definition_ids: testDefinitionIds, tags, mode }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to bulk apply tags'));
  return response.json();
};

// --- RBAC: Roles & Permissions ---

export const getRoles = async () => {
  const response = await apiFetch(`${TEST_API}/roles`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load role list'));
  return response.json();
};

export const getPermissions = async () => {
  const response = await apiFetch(`${TEST_API}/roles/permissions`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load permission list'));
  return response.json();
};

export const createRole = async (data) => {
  const response = await apiFetch(`${TEST_API}/roles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to create role'));
  return response.json();
};

export const updateRole = async (roleId, data) => {
  const response = await apiFetch(`${TEST_API}/roles/${roleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update role'));
  return response.json();
};

export const deleteRole = async (roleId) => {
  const response = await apiFetch(`${TEST_API}/roles/${roleId}`, { method: 'DELETE' });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, 'Failed to delete role'));
  }
};

export const assignUserRole = async (userId, roleId) => {
  const response = await apiFetch(`${USERS_API}/users/${userId}/roles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role_id: roleId }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to assign role'));
  return response.json();
};

export const removeUserRole = async (userId, roleId) => {
  const response = await apiFetch(`${USERS_API}/users/${userId}/roles/${roleId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to remove role'));
  return response.json();
};

// --- Test Definitions (for suite builder) ---

export const getTestDefinitions = async (skip = 0, limit = 200) => {
  const response = await apiFetch(`${TEST_API}/apps/?skip=${skip}&limit=${limit}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load test definitions'));
  return response.json();
};

// --- Review/Approval ---

export const getPendingReviews = async () => {
  const response = await apiFetch(`${TEST_API}/reviews/pending`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load review list'));
  return response.json();
};

export const getPendingTestReviews = async () => {
  const response = await apiFetch(`${TEST_API}/reviews/pending/tests`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load pending test reviews'));
  return response.json();
};

export const getPendingSuiteReviews = async () => {
  const response = await apiFetch(`${TEST_API}/reviews/pending/suites`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load pending suite reviews'));
  return response.json();
};

export const approveTest = async (testDefId) => {
  const response = await apiFetch(`${TEST_API}/reviews/tests/${testDefId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to approve test'));
  return response.json();
};

export const rejectTest = async (testDefId, reason) => {
  const response = await apiFetch(`${TEST_API}/reviews/tests/${testDefId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to reject test'));
  return response.json();
};

export const approveVersion = async (versionId) => {
  const response = await apiFetch(`${TEST_API}/reviews/versions/${versionId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to approve version'));
  return response.json();
};

export const rejectVersion = async (versionId, reason) => {
  const response = await apiFetch(`${TEST_API}/reviews/versions/${versionId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to reject version'));
  return response.json();
};

export const approveSuite = async (suiteId) => {
  const response = await apiFetch(`${TEST_API}/reviews/suites/${suiteId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to approve suite'));
  return response.json();
};

export const rejectSuite = async (suiteId, reason) => {
  const response = await apiFetch(`${TEST_API}/reviews/suites/${suiteId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to reject suite'));
  return response.json();
};

export const submitSuiteForReview = async (suiteId) => {
  const response = await apiFetch(`${TEST_API}/test-suites/${suiteId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to submit for review'));
  return response.json();
};

// --- Marketplace ---

export const listPublishedTestCases = async (params = {}) => {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  if (params.search) qs.set('search', params.search);
  if (params.skip !== undefined) qs.set('skip', params.skip);
  if (params.limit !== undefined) qs.set('limit', params.limit);
  const response = await apiFetch(`${TEST_API}/apps/marketplace?${qs.toString()}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load published test cases'));
  return response.json();
};

export const listPublishedSuites = async (params = {}) => {
  const qs = new URLSearchParams();
  if (params.search) qs.set('search', params.search);
  if (params.skip !== undefined) qs.set('skip', params.skip);
  if (params.limit !== undefined) qs.set('limit', params.limit);
  const response = await apiFetch(`${TEST_API}/test-suites/marketplace?${qs.toString()}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load published suites'));
  return response.json();
};

export const copyTestCaseToWorkspace = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/apps/${testCaseId}/copy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to copy test case'));
  return response.json();
};

export const copySuiteToWorkspace = async (suiteId) => {
  const response = await apiFetch(`${TEST_API}/test-suites/${suiteId}/copy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to copy suite'));
  return response.json();
};

// --- LLM Usage API ---

const LLM_USAGE_API = `${BASE_URL}/api/v1/llm-usage`;

export const getLlmUsageSummary = async (days = 30) => {
  const response = await apiFetch(`${LLM_USAGE_API}/summary?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load LLM usage summary'));
  return response.json();
};

export const getLlmUsageByAgent = async (days = 30) => {
  const response = await apiFetch(`${LLM_USAGE_API}/by-agent?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load LLM usage by agent'));
  return response.json();
};

export const getLlmUsageByDay = async (days = 30) => {
  const response = await apiFetch(`${LLM_USAGE_API}/by-day?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load LLM usage by day'));
  return response.json();
};
