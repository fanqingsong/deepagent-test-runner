// Dashboard API
const getDashboardData = async (days = 30) => {
  const response = await apiFetch(`${DASHBOARD_API}/dashboard?days=${days}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to fetch dashboard data'));
  }
  return response.json();
};

// Suite Dashboard API
export const getSuiteDashboard = async (days = 30) => {
  const response = await apiFetch(`${DASHBOARD_API}/suite-dashboard?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch suite dashboard'));
  return response.json();
};

export const getSuiteRunTimeline = async (suiteId, limit = 10) => {
  const response = await apiFetch(
    `${DASHBOARD_API}/suite-runs/timeline/${suiteId}?limit=${limit}`
  );
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch suite timeline'));
  return response.json();
};

export const getSuiteRunEntries = async (runId) => {
  const response = await apiFetch(`${DASHBOARD_API}/suite-runs/${runId}/entries`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch suite run entries'));
  return response.json();
};

const getTestRuns = async (limit = 20) => {
  const response = await apiFetch(`${DASHBOARD_API}/test-runs?limit=${limit}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to fetch test runs'));
  }
  return response.json();
};

export const getTestRunDetails = async (runId) => {
  const response = await apiFetch(`${DASHBOARD_API}/test-runs/${runId}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to fetch test run details'));
  }
  return response.json();
};

// Get all jobs
const getJobs = async () => {
  const response = await apiFetch(`${SCHEDULER_API}/jobs/`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to fetch jobs'));
  }
  return response.json();
};

const getTestStats = async () => {
  const response = await apiFetch(`${DASHBOARD_API}/dashboard`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to fetch test stats'));
  }
  return response.json();
};

