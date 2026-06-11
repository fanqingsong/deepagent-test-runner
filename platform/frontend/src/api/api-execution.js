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

export const publishVersion = async (versionId) => {
  const response = await apiFetch(`${TEST_API}/reviews/versions/${versionId}/publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to publish version'));
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

export const approveSuiteVersion = async (versionId) => {
  const response = await apiFetch(`${TEST_API}/reviews/suite-versions/${versionId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to approve suite version'));
  return response.json();
};

export const rejectSuiteVersion = async (versionId, reason) => {
  const response = await apiFetch(`${TEST_API}/reviews/suite-versions/${versionId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to reject suite version'));
  return response.json();
};

export const publishSuiteVersion = async (versionId) => {
  const response = await apiFetch(`${TEST_API}/reviews/suite-versions/${versionId}/publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to publish suite version'));
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

// --- Suite Versions ---

export const getSuiteVersions = async (suiteId) => {
  const response = await apiFetch(`${TEST_API}/suite-versions/test-suite/${suiteId}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load suite versions'));
  return response.json();
};

export const restoreSuiteVersion = async (suiteId, versionId) => {
  const response = await apiFetch(`${TEST_API}/suite-versions/test-suite/${suiteId}/restore/${versionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to restore suite version'));
  return response.json();
};

export const submitSuiteVersionForReview = async (versionId) => {
  const response = await apiFetch(`${TEST_API}/suite-versions/${versionId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to submit suite version for review'));
  return response.json();
};

export const createDraftFromSuiteVersion = async (suiteId, fromVersionId) => {
  const qs = fromVersionId ? `?from_version_id=${fromVersionId}` : '';
  const response = await apiFetch(`${TEST_API}/suite-versions/test-suite/${suiteId}/create-draft${qs}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to create draft'));
  return response.json();
};

// --- Suite Permissions ---

export const getSuitePermissions = async (suiteId) => {
  const response = await apiFetch(`${TEST_API}/suite-permissions/${suiteId}/permissions`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load suite permission list'));
  return response.json();
};

export const addSuitePermission = async (suiteId, { userId, permissionType }) => {
  const response = await apiFetch(`${TEST_API}/suite-permissions/${suiteId}/permissions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, permission_type: permissionType }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to add suite permission'));
  return response.json();
};

export const updateSuitePermission = async (suiteId, userId, { permissionType }) => {
  const response = await apiFetch(`${TEST_API}/suite-permissions/${suiteId}/permissions/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ permission_type: permissionType }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update suite permission'));
  return response.json();
};

export const removeSuitePermission = async (suiteId, userId) => {
  const response = await apiFetch(`${TEST_API}/suite-permissions/${suiteId}/permissions/${userId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to remove suite permission'));
};

// --- Marketplace ---

export const listPublishedTestCases = async (params = {}) => {
  const qs = new URLSearchParams();
  if (params.status) qs.set('status', params.status);
  if (params.search) qs.set('search', params.search);
  if (params.skip !== undefined) qs.set('skip', params.skip);
  if (params.limit !== undefined) qs.set('limit', params.limit);
  const response = await apiFetch(`${TEST_API}/test-workspaces/marketplace?${qs.toString()}`);
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
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/copy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to copy test case'));
  return response.json();
};

export const getPublishedVersions = async (testCaseId) => {
  const response = await apiFetch(`${TEST_API}/test-workspaces/${testCaseId}/published-versions`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load published versions'));
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

