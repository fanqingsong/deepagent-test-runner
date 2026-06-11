import { DASHBOARD_API, SCHEDULER_API, apiFetch, parseApiError } from './api-utils.js';

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

export const getTestRunDetails = async (runId) => {
  const response = await apiFetch(`${DASHBOARD_API}/test-runs/${runId}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to fetch test run details'));
  }
  return response.json();
};


