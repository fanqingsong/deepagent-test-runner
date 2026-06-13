// Token Management API
import { BASE_URL, apiFetch, parseApiError } from './api-utils.js';

const TOKEN_API = `${BASE_URL}/api/v1/token`;
const LLM_USAGE_API = `${BASE_URL}/api/v1/llm-usage`;

const periodToDays = (period) =>
  ({ hourly: 1, daily: 30, weekly: 90, monthly: 365 }[period] || 30);

const mapSummary = (data) => ({
  ...data,
  total_cost: data.total_cost ?? 0,
  budget_limit: data.budget_limit ?? 1000000,
});

// Token Usage (dashboard) — backed by working llm-usage endpoints
export const getTokenUsage = async (period = 'daily') => {
  const days = periodToDays(period);
  const response = await apiFetch(`${LLM_USAGE_API}/summary?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch token usage'));
  return mapSummary(await response.json());
};

export const getTokenUsageSummary = async () => {
  const response = await apiFetch(`${LLM_USAGE_API}/summary?days=30`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch usage summary'));
  return mapSummary(await response.json());
};

export const getTokenUsageOverTime = async (period = 'daily') => {
  const days = periodToDays(period);
  const response = await apiFetch(`${LLM_USAGE_API}/by-day?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch usage over time'));
  const rows = await response.json();
  return {
    timeline: (Array.isArray(rows) ? rows : []).map((row) => ({
      date: row.date,
      tokens: row.total_tokens ?? 0,
      calls: row.call_count ?? 0,
    })),
  };
};

export const getTokenUsageByScope = async (period = 'daily') => {
  const days = periodToDays(period);
  const response = await apiFetch(`${LLM_USAGE_API}/by-agent?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch usage by scope'));
  const rows = await response.json();
  return (Array.isArray(rows) ? rows : []).map((row) => ({
    scope: row.agent_type,
    name: row.agent_type,
    tokens: row.total_tokens ?? 0,
    calls: row.call_count ?? 0,
  }));
};

// Budget Management
export const getBudgets = async (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  const response = await apiFetch(`${TOKEN_API}/budgets${queryString ? `?${queryString}` : ''}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch budgets'));
  return response.json();
};

export const getBudget = async (budgetId) => {
  const response = await apiFetch(`${TOKEN_API}/budgets/${budgetId}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch budget'));
  return response.json();
};

export const createBudget = async (budgetData) => {
  const response = await apiFetch(`${TOKEN_API}/budgets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(budgetData),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to create budget'));
  return response.json();
};

export const updateBudget = async (budgetId, budgetData) => {
  const response = await apiFetch(`${TOKEN_API}/budgets/${budgetId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(budgetData),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update budget'));
  return response.json();
};

export const deleteBudget = async (budgetId) => {
  const response = await apiFetch(`${TOKEN_API}/budgets/${budgetId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to delete budget'));
  if (response.status === 204) return null;
  return response.json();
};

export const getBudgetHierarchy = async (budgetId) => {
  if (budgetId) {
    const response = await apiFetch(`${TOKEN_API}/budgets/hierarchy/${budgetId}`);
    if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch budget hierarchy'));
    return response.json();
  }
  return getBudgets();
};

// Quota Management
export const getUserQuota = async (userId) => {
  const response = await apiFetch(`${TOKEN_API}/quotas/user/${userId}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch user quota'));
  return response.json();
};

export const updateUserQuota = async (userId, quotaData) => {
  const response = await apiFetch(`${TOKEN_API}/quotas/user/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(quotaData),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update user quota'));
  return response.json();
};

export const resetUserQuota = async (userId) => {
  const response = await apiFetch(`${TOKEN_API}/quotas/user/${userId}/reset`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to reset user quota'));
  return response.json();
};

export const getQuotaConfig = async () => {
  const response = await apiFetch(`${TOKEN_API}/quotas`);
  if (!response.ok) {
    return { default_limit: 100000, default_period: 'monthly' };
  }
  const data = await response.json();
  return {
    default_limit: 100000,
    default_period: 'monthly',
    quotas: data.quotas || data.items || [],
  };
};

export const updateQuotaConfig = async (configData) => {
  const response = await apiFetch(`${TOKEN_API}/quotas/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(configData),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update quota configuration'));
  return response.json();
};

// Alert Management
export const getAlerts = async (params = {}) => {
  const queryString = new URLSearchParams(params).toString();
  const response = await apiFetch(`${TOKEN_API}/alerts${queryString ? `?${queryString}` : ''}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch alerts'));
  return response.json();
};

export const acknowledgeAlert = async (alertId) => {
  const response = await apiFetch(`${TOKEN_API}/alerts/${alertId}/acknowledge`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to acknowledge alert'));
  return response.json();
};

export const getAlertConfig = async () => ({
  email_enabled: true,
  threshold_warning: 75,
  threshold_critical: 90,
});

export const updateAlertConfig = async (configData) => {
  const response = await apiFetch(`${TOKEN_API}/alerts/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(configData),
  });
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to update alert configuration'));
  return response.json();
};

// Analytics
export const getTokenAnalytics = async (params = {}) => {
  const period = params.period || 'daily';
  const days = periodToDays(period);
  const response = await apiFetch(`${LLM_USAGE_API}/summary?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch token analytics'));
  return mapSummary(await response.json());
};

export const getTokenCostBreakdown = async (period = 'daily') => {
  const response = await apiFetch(`${TOKEN_API}/analytics/costs`);
  if (!response.ok) {
    return { cost_breakdown: { by_model: {}, by_agent_type: {} } };
  }
  return response.json();
};

export const getModelComparison = async (period = 'daily') => {
  const data = await getTokenCostBreakdown(period);
  const byModel = data.cost_breakdown?.by_model || {};
  return Object.entries(byModel).map(([model, cost]) => ({
    model,
    cost,
    total_tokens: 0,
  }));
};

export const getAgentRankings = async (period = 'daily') => {
  const days = periodToDays(period);
  const response = await apiFetch(`${LLM_USAGE_API}/by-agent?days=${days}`);
  if (!response.ok) throw new Error(await parseApiError(response, 'Failed to fetch agent rankings'));
  const rows = await response.json();
  return (Array.isArray(rows) ? rows : [])
    .sort((a, b) => (b.total_tokens || 0) - (a.total_tokens || 0))
    .map((row, index) => ({
      rank: index + 1,
      agent_type: row.agent_type,
      subagent_name: row.agent_type,
      total_tokens: row.total_tokens ?? 0,
      call_count: row.call_count ?? 0,
    }));
};

export const getTokenForecast = async () => ({
  forecast: [],
  message: 'Forecast requires an active token budget',
});
