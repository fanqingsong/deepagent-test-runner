/**
 * Authentication Service
 *
 * Handles authentication with local JWT tokens.
 */

// Use the current origin (protocol + hostname + port) to work in all environments
const BASE_URL = window.location.origin;

const API_BASE_URL = `${BASE_URL}/api/v1`;

const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const PROVIDER_KEY = 'auth_provider';
const USER_KEY = 'user_info';

class AuthService {
  constructor() {
    this.authCallbacks = new Set();
    this.fetchTimeout = 10000; // 10 second timeout for all fetch calls
  }

  /**
   * Fetch with timeout
   */
  async fetchWithTimeout(url, options = {}, timeout = this.fetchTimeout) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    const token = localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
    return !!token;
  }

  /**
   * Get access token
   */
  getAccessToken() {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
  }

  /**
   * Get auth headers for API requests
   */
  getAuthHeaders() {
    const token = this.getAccessToken();
    if (!token) {
      return {};
    }
    return {
      'Authorization': `Bearer ${token}`
    };
  }

  /**
   * Get refresh token
   */
  getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY) || sessionStorage.getItem(REFRESH_TOKEN_KEY);
  }

  /**
   * Get auth provider
   */
  getProvider() {
    return localStorage.getItem(PROVIDER_KEY);
  }

  /**
   * Get user info
   */
  getUser() {
    const userStr = localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
  }

  /**
   * Set tokens and user info
   */
  setAuthData(token, refreshToken, provider, user) {
    const rememberMe = localStorage.getItem('remember_me') === '1' || sessionStorage.getItem('remember_me') === '1';
    const storage = rememberMe ? localStorage : sessionStorage;
    storage.setItem(TOKEN_KEY, token);
    if (refreshToken) {
      storage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
    storage.setItem(PROVIDER_KEY, provider);
    storage.setItem(USER_KEY, JSON.stringify(user));
    this.notifyAuthChange();
  }

  /**
   * Update stored user info (e.g., after fetching /auth/me)
   */
  updateStoredUser(user) {
    const rememberMe = localStorage.getItem('remember_me') === '1' || sessionStorage.getItem('remember_me') === '1';
    const storage = rememberMe ? localStorage : sessionStorage;
    storage.setItem(USER_KEY, JSON.stringify(user));
    this.notifyAuthChange();
  }

  /**
   * Clear auth data
   */
  clearAuthData() {
    [localStorage, sessionStorage].forEach(storage => {
      storage.removeItem(TOKEN_KEY);
      storage.removeItem(REFRESH_TOKEN_KEY);
      storage.removeItem(PROVIDER_KEY);
      storage.removeItem(USER_KEY);
      storage.removeItem('remember_me');
      storage.removeItem('session_token');
    });
    this.notifyAuthChange();
  }

  /**
   * Register auth change callback
   */
  onAuthChange(callback) {
    this.authCallbacks.add(callback);
    return () => this.authCallbacks.delete(callback);
  }

  /**
   * Notify all auth callbacks
   */
  notifyAuthChange() {
    this.authCallbacks.forEach(callback => callback());
  }

  /**
   * Local user registration
   */
  async register(email, password) {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    return response.json();
  }

  /**
   * Local password login
   */
  async loginLocal(email, password) {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    this.setAuthData(data.access_token, null, 'local', data.user);
    return data;
  }

  /**
   * Logout
   */
  async logout() {
    try {
      const token = this.getAccessToken();
      if (token) {
        await this.fetchWithTimeout(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearAuthData();
    }
  }

  /**
   * Get current user info
   */
  async getCurrentUser() {
    const token = this.getAccessToken();
    if (!token) {
      throw new Error('No token found');
    }

    const response = await this.fetchWithTimeout(`${API_BASE_URL}/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to get user info');
    }

    return response.json();
  }

  /**
   * Refresh access token
   */
  async refreshToken() {
    const refreshTokenValue = this.getRefreshToken();
    const provider = this.getProvider();

    if (!refreshTokenValue) {
      throw new Error('No refresh token');
    }

    const url = `${API_BASE_URL}/auth/refresh`;

    const headers = { 'Content-Type': 'application/json' };

    // Include session token if available
    const sessionToken = localStorage.getItem('session_token') || sessionStorage.getItem('session_token');
    if (sessionToken) {
      headers['X-Session-Token'] = sessionToken;
    }

    const response = await this.fetchWithTimeout(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ refresh_token: refreshTokenValue }),
    });

    if (!response.ok) {
      this.clearAuthData();
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    const user = this.getUser();
    this.setAuthData(data.access_token, data.refresh_token, provider, user);

    return data;
  }

  /**
   * Check if token is expired
   */
  isTokenExpired() {
    const token = this.getAccessToken();
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
   */
  async ensureValidToken() {
    const provider = this.getProvider();

    if (!this.isTokenExpired()) {
      return this.getAccessToken();
    }

    // Token expired - try to refresh
    try {
      await this.refreshToken();
      return this.getAccessToken();
    } catch (error) {
      this.clearAuthData();
      throw error;
    }
  }
}

// Export singleton instance
const authService = new AuthService();
export default authService;
