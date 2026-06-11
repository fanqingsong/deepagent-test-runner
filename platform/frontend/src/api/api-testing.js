// Test Cases Workspace
export const createTestCase = async (data) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces`, {
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
  const response = await apiFetch(`${TEST_API}/test-workspaces/?${qs.toString()}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load Test Case list'));
  return response.json();
};

export const getTestCase = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load Test Case'));
  return response.json();
};

export const updateTestCase = async (testCaseId, data) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update Test Case'));
  return response.json();
};

export const archiveTestCase = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}`, { method: 'DELETE' });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, 'Failed to delete Test Case'));
  }
};

export const runTestCase = async (testCaseId, { forceRegenerate, useExistingPlan } = {}) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/run`, {
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

export const getTestCaseRunHistory = async (testCaseId, { limit = 50, offset = 0 } = {}) => {
  const response = await apiFetch(
    `${TEST_API}/test-workspaces/${testCaseId}/runs?limit=${limit}&offset=${offset}`
  );
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load run history'));
  return response.json();
};

export const getStepVersions = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/step-versions`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load versions'));
  return response.json();
};

export const restoreTestCaseVersion = async (testCaseId, versionId) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/step-versions/${versionId}/restore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to restore version'));
  return response.json();
};

export const submitVersionForReview = async (testCaseId, versionId) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/step-versions/${versionId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to submit version for review'));
  return response.json();
};

export const createDraftFromVersion = async (workspaceId, fromVersionId) => {
  const qs = fromVersionId ? `?from_version_id=${fromVersionId}` : '';
  const response = await apiFetch(`${TEST_API}/test-workspaces/${workspaceId}/create-draft${qs}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to create draft'));
  return response.json();
};

export const publishTestCase = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/publish`, {
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
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/permissions`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load permission list'));
  return response.json();
};

export const addTestCasePermission = async (testCaseId, { userId, permissionType }) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/permissions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, permission_type: permissionType }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to add permission'));
  return response.json();
};

export const updateTestCasePermission = async (testCaseId, userId, { permissionType }) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/permissions/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ permission_type: permissionType }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update permission'));
  return response.json();
};

export const removeTestCasePermission = async (testCaseId, userId) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/permissions/${userId}`, {
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

const cancelSuiteRun = async (runId) => {
  const response = await apiFetch(`${TEST_API}/test-suites/runs/${runId}/cancel`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to cancel suite run'));
  return response.json();
};

const resolveSuite = async (suiteId) => {
  const response = await apiFetch(`${TEST_API}/test-suites/${suiteId}/resolve`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to resolve suite'));
  return response.json();
};

// --- Run Configs ---

const getRunConfigs = async (skip = 0, limit = 100) => {
  const response = await apiFetch(`${TEST_API}/run-configs/?skip=${skip}&limit=${limit}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load run config'));
  return response.json();
};

const createRunConfig = async (data) => {
  const response = await apiFetch(`${TEST_API}/run-configs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to create run config'));
  return response.json();
};

const updateRunConfig = async (configId, data) => {
  const response = await apiFetch(`${TEST_API}/run-configs/${configId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update run config'));
  return response.json();
};

const deleteRunConfig = async (configId) => {
  const response = await apiFetch(`${TEST_API}/run-configs/${configId}`, { method: 'DELETE' });
  if (!response.ok && response.status !== 204) {
    throw new Error(await parseApiError(response, 'Failed to delete run config'));
  }
};

// --- Tags ---

const getTags = async () => {
  const response = await apiFetch(`${TEST_API}/tags`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load tag list'));
  return response.json();
};

const getTestsByTag = async (tag) => {
  const response = await apiFetch(`${TEST_API}/tags/${encodeURIComponent(tag)}/tests`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load tag tests'));
  return response.json();
};

const bulkApplyTags = async (testDefinitionIds, tags, mode = 'add') => {
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

const getTestDefinitions = async (skip = 0, limit = 200) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/?skip=${skip}&limit=${limit}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load test definitions'));
  return response.json();
};

// --- Review/Approval ---

export const getPendingReviews = async () => {
  const response = await apiFetch(`${TEST_API}/reviews/pending`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load review list'));
  return response.json();
};

export const getReviewDetail = async (type, id) => {
  let endpoint;
  if (type === 'suite') {
    endpoint = `${TEST_API}/reviews/suites/${id}/detail`;
  } else if (type === 'suite_version') {
    endpoint = `${TEST_API}/reviews/suite-versions/${id}/detail`;
  } else {
    endpoint = `${TEST_API}/reviews/versions/${id}/detail`;
  }
  const response = await apiFetch(endpoint);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load review details'));
  return response.json();
};

const getPendingTestReviews = async () => {
  const response = await apiFetch(`${TEST_API}/reviews/pending/tests`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load pending test reviews'));
  return response.json();
};

const getPendingSuiteReviews = async () => {
  const response = await apiFetch(`${TEST_API}/reviews/pending/suites`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load pending suite reviews'));
  return response.json();
};

export const approveVersion = async (versionId) => {
