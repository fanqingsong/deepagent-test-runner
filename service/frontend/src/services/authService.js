/**
 * Authentication Service
 *
 * Handles authentication with both local JWT and Casdoor SSO.
 */

// Use the current origin (protocol + hostname + port) to work in all environments
const BASE_URL = window.location.origin;

const API_BASE_URL = `${BASE_URL}/api/v1`;

const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const PROVIDER_KEY = 'auth_provider'; // 'local' or 'casdoor'
const USER_KEY = 'user_info';

class AuthService {
  constructor() {
    this.authCallbacks = new Set();
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    const token = localStorage.getItem(TOKEN_KEY);
    return !!token;
  }

  /**
   * Get access token
   */
  getAccessToken() {
    return localStorage.getItem(TOKEN_KEY);
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
    return localStorage.getItem(REFRESH_TOKEN_KEY);
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
    const userStr = localStorage.getItem(USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
  }

  /**
   * Set tokens and user info
   */
  setAuthData(token, refreshToken, provider, user) {
    localStorage.setItem(TOKEN_KEY, token);
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
    localStorage.setItem(PROVIDER_KEY, provider);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    this.notifyAuthChange();
  }

  /**
   * Clear auth data
   */
  clearAuthData() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(PROVIDER_KEY);
    localStorage.removeItem(USER_KEY);
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
  async register(username, email, password) {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, email, password }),
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
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
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
   * Casdoor password login
   */
  async loginCasdoor(username, password) {
    const response = await fetch(`${API_BASE_URL}/auth/login/casdoor`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Casdoor login failed');
    }

    const data = await response.json();
    this.setAuthData(data.access_token, data.refresh_token, 'casdoor', data.user);
    return data;
  }

  /**
   * OIDC login - Get authorization URL
   */
  async oidcLogin() {
    const response = await fetch(`${API_BASE_URL}/auth/oidc/login`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'OIDC login failed');
    }

    const data = await response.json();

    // Save state for callback verification
    sessionStorage.setItem('oidc_state', data.state);
    sessionStorage.setItem('auth_provider', 'casdoor');

    // Redirect to Casdoor login page
    window.location.href = data.auth_url;

    return data;
  }

  /**
   * OIDC callback handling
   */
  async handleOidcCallback(code, state) {
    // Verify state
    const savedState = sessionStorage.getItem('oidc_state');
    if (state !== savedState) {
      throw new Error('Invalid state parameter');
    }

    const response = await fetch(
      `${API_BASE_URL}/auth/oidc/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'OIDC callback failed');
    }

    const data = await response.json();
    this.setAuthData(data.access_token, data.refresh_token, 'casdoor', data.user);

    // Clean up session storage
    sessionStorage.removeItem('oidc_state');
    sessionStorage.removeItem('auth_provider');

    return data;
  }

  /**
   * Logout
   */
  async logout() {
    try {
      const token = this.getAccessToken();
      if (token) {
        await fetch(`${API_BASE_URL}/auth/logout`, {
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

    const response = await fetch(`${API_BASE_URL}/auth/me`, {
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
    const refreshToken = this.getRefreshToken();
    const provider = this.getProvider();

    if (!refreshToken || provider !== 'casdoor') {
      throw new Error('Token refresh not supported');
    }

    const response = await fetch(`${API_BASE_URL}/auth/refresh?provider=casdoor`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      this.clearAuthData();
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    const user = this.getUser();
    this.setAuthData(data.access_token, data.refresh_token, 'casdoor', user);

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

    // For local auth, just check if token exists and is not expired
    if (provider === 'local') {
      if (this.isTokenExpired()) {
        this.clearAuthData();
        throw new Error('Token expired');
      }
      return this.getAccessToken();
    }

    // For Casdoor, try to refresh
    if (this.isTokenExpired()) {
      try {
        await this.refreshToken();
      } catch (error) {
        this.clearAuthData();
        throw error;
      }
    }
    return this.getAccessToken();
  }
}

// Export singleton instance
const authService = new AuthService();
export default authService;
