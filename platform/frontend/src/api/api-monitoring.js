import { BASE_URL, apiFetch, parseApiError } from './api-utils.js';

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

// --- Admin Chat Monitoring ---

const ADMIN_CHAT_API = `${BASE_URL}/api/v1/admin/chat`;

export const getChatSessions = async (params = {}) => {
  const qs = new URLSearchParams();
  if (params.userId) qs.set('user_id', params.userId);
  if (params.status) qs.set('status', params.status);
  if (params.offset !== undefined) qs.set('offset', params.offset);
  if (params.limit) qs.set('limit', params.limit);
  const response = await apiFetch(`${ADMIN_CHAT_API}/sessions?${qs.toString()}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load chat sessions'));
  return response.json();
};

export const getChatSessionMessages = async (threadId) => {
  const response = await apiFetch(`${ADMIN_CHAT_API}/sessions/${threadId}/messages`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load chat messages'));
  return response.json();
};

export const getChatMetrics = async (days = 30) => {
  const response = await apiFetch(`${ADMIN_CHAT_API}/metrics?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load chat metrics'));
  return response.json();
};

export const getChatSubagentUsage = async (days = 30) => {
  const response = await apiFetch(`${ADMIN_CHAT_API}/subagent-usage?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load subagent usage'));
  return response.json();
};

// --- Script Generation ---

const SCRIPT_API = `${BASE_URL}/api/v1/scripts`;

export const generateScriptStream = async (testId, opts = {}) => {
  const response = await apiFetch(`${SCRIPT_API}/test-definitions/${testId}/generate-script/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force_regenerate: !!opts.force_regenerate }),
    timeout: 600000,
  });
  if (!response.ok) {
    const errMsg = await parseApiError(response, 'Failed to generate script');
    throw new Error(errMsg);
  }
  return response;
};

export const getScript = async (testId) => {
  const response = await apiFetch(`${SCRIPT_API}/test-definitions/${testId}/script`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to load script'));
  return response.json();
};

export const updateScript = async (testId, script) => {
  const response = await apiFetch(`${SCRIPT_API}/test-definitions/${testId}/script`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ playwright_script: script }),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to save script'));
  return response.json();
};

export const validateScript = async (testId) => {
  const response = await apiFetch(`${SCRIPT_API}/test-definitions/${testId}/validate-script`, {
    method: 'POST',
    timeout: 180000, // 3 minutes for script validation
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to validate script'));
  return response.json();
};

export const approveScript = async (testId) => {
  const response = await apiFetch(`${SCRIPT_API}/test-definitions/${testId}/approve-script`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to approve script'));
  return response.json();
};

export const generateDescription = async (testId) => {
  const response = await apiFetch(`${SCRIPT_API}/test-definitions/${testId}/generate-description`, {
    method: 'POST',
    timeout: 30000, // 30 seconds for LLM generation
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to generate description'));
  return response.json();
};


// Monitoring API
const MONITORING_API = `${BASE_URL}/api/v1/monitoring`;

export const getMonitoringStatus = async () => {
  const response = await apiFetch(`${MONITORING_API}/status`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch monitoring status'));
  return response.json();
};


export const getAlerts = async (options = {}) => {
  const params = new URLSearchParams();
  if (options.active_only) params.append('active_only', 'true');
  if (options.alert_type) params.append('alert_type', options.alert_type);
  if (options.severity) params.append('severity', options.severity);
  if (options.limit) params.append('limit', options.limit);

  const response = await apiFetch(`${MONITORING_API}/alerts?${params.toString()}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch alerts'));
  return response.json();
};

export const acknowledgeAlert = async (alertId) => {
  const response = await apiFetch(`${MONITORING_API}/alerts/${alertId}/acknowledge`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to acknowledge alert'));
  return response.json();
};

export const resolveAlert = async (alertId) => {
  const response = await apiFetch(`${MONITORING_API}/alerts/${alertId}/resolve`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to resolve alert'));
  return response.json();
};

export const getMonitoringReports = async (hours = 24, limit = 50) => {
  const response = await apiFetch(`${MONITORING_API}/reports?hours=${hours}&limit=${limit}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch monitoring reports'));
  return response.json();
};
