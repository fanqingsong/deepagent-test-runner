import { BASE_URL, apiFetch, parseApiError } from './api-utils.js';

const ROOT_CAUSE_API = `${BASE_URL}/api/v1/analysis/root-cause`;

// (Re)build the Neo4j knowledge graph from PostgreSQL execution data.
export const buildRootCauseGraph = async (days = 90) => {
  const response = await apiFetch(`${ROOT_CAUSE_API}/build?days=${days}`, {
    method: 'POST',
    timeout: 180000,
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to build root cause graph'));
  return response.json();
};

// Local search: root cause + causal analysis for one run.
export const analyzeRunRootCause = async (runId) => {
  const response = await apiFetch(`${ROOT_CAUSE_API}/run/${encodeURIComponent(runId)}`, {
    timeout: 120000,
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to analyze run'));
  return response.json();
};

// Global search: failure communities over a time window.
export const analyzeGlobalRootCause = async (days = 7) => {
  const response = await apiFetch(`${ROOT_CAUSE_API}/global?days=${days}`, {
    timeout: 120000,
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load global analysis'));
  return response.json();
};

