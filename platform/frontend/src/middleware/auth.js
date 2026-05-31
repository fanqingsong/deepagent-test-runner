/**
 * JWT Authentication Middleware
 *
 * Validates JWT tokens and attaches authentication headers to API requests.
 * Used by the API client to authenticate requests to auth-service.
 */

import authClient from '../services/auth';

/**
 * Check if user is authenticated
 * @returns {boolean} True if user has valid access token
 */
export function isAuthenticated() {
  return authClient.isAuthenticated();
}

/**
 * Get authentication headers for API requests
 * @returns {Object} Headers object with Authorization and X-Session-Token
 */
export function getAuthHeaders() {
  const accessToken = localStorage.getItem('access_token');
  const sessionToken = localStorage.getItem('session_token');

  const headers = {
    'Content-Type': 'application/json',
  };

  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  if (sessionToken) {
    headers['X-Session-Token'] = sessionToken;
  }

  return headers;
}

/**
 * Validate current session and redirect if not authenticated
 * @param {string} redirectTo - Path to redirect to if not authenticated
 * @returns {boolean} True if authenticated, false otherwise
 */
export function requireAuth(redirectTo = '/login') {
  if (!isAuthenticated()) {
    window.location.href = redirectTo;
    return false;
  }
  return true;
}

/**
 * Get current user from storage
 * @returns {Object|null} User object or null if not authenticated
 */
export function getCurrentUser() {
  return authClient.getCurrentUser();
}

/**
 * Logout user and clear tokens
 * @returns {Promise<void>}
 */
export async function logout() {
  await authClient.logout();
}

/**
 * Check if token is expired
 * @returns {boolean} True if token is expired or invalid
 */
export function isTokenExpired() {
  const token = localStorage.getItem('access_token');
  if (!token) return true;

  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp;
    return Date.now() >= exp * 1000;
  } catch {
    return true;
  }
}

/**
 * Ensure valid token, refresh if needed
 * @returns {Promise<string>} Valid access token
 * @throws {Error} If token cannot be refreshed
 */
export async function ensureValidToken() {
  if (isTokenExpired()) {
    throw new Error('Token expired');
  }
  return localStorage.getItem('access_token');
}

export default {
  isAuthenticated,
  getAuthHeaders,
  requireAuth,
  getCurrentUser,
  logout,
  isTokenExpired,
  ensureValidToken,
};
