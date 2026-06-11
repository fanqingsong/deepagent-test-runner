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
  // httpOnly cookies are sent automatically by the browser
  // No need to manually add Authorization header
  // Only add X-Session-Token if stored in localStorage/sessionStorage (backward compatibility)
  const sessionToken = localStorage.getItem('session_token') || sessionStorage.getItem('session_token');
  if (sessionToken) {
    return {
      'X-Session-Token': sessionToken,
    };
  }
  return {};
};

async function parseApiError(response, fallback) {
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
      credentials: 'include',  // Include httpOnly cookies
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
          credentials: 'include',
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
const getDashboardData = async (days = 30) => {
  const response = await apiFetch(`${DASHBOARD_API}/dashboard?days=${days}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, 'Failed to fetch dashboard data'));
  }
  return response.json();
};

// Suite Dashboard API
export const getSuiteDashboard = async (days = 30) => {
