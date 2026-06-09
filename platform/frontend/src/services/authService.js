/**
 * Authentication Service
 *
 * SECURITY: Now uses httpOnly cookies for JWT tokens instead of localStorage.
 * Tokens are automatically sent with requests and cannot be accessed via JavaScript.
 */

// Use the current origin (protocol + hostname + port) to work in all environments
const BASE_URL = window.location.origin;

const API_BASE_URL = `${BASE_URL}/api/v1`;

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
        signal: controller.signal,
        credentials: 'include',  // SECURITY: Include cookies in CORS requests
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
   * SECURITY: Check if user info exists (tokens are in httpOnly cookies)
   */
  isAuthenticated() {
    const userStr = localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY);
    return !!userStr;
  }

  /**
   * Get access token
   * SECURITY: This is no longer accessible - tokens are in httpOnly cookies
   * This method returns null to indicate tokens are handled by browser
   */
  getAccessToken() {
    // Tokens are now in httpOnly cookies - not accessible via JavaScript
    return null;
  }

  /**
   * Get auth headers for API requests
   * SECURITY: No longer needed - cookies are sent automatically
   */
  getAuthHeaders() {
    // Cookies are sent automatically - no manual headers needed
    return {};
  }

  /**
   * Get refresh token
   * SECURITY: This is no longer accessible - tokens are in httpOnly cookies
   */
  getRefreshToken() {
    // Tokens are now in httpOnly cookies - not accessible via JavaScript
    return null;
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
   * Set user info (tokens are handled by httpOnly cookies)
   */
  setAuthData(provider, user, rememberMe = false) {
    const storage = rememberMe ? localStorage : sessionStorage;
    storage.setItem(PROVIDER_KEY, provider);
    storage.setItem(USER_KEY, JSON.stringify(user));
    storage.setItem('remember_me', rememberMe ? '1' : '0');
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
      storage.removeItem(PROVIDER_KEY);
      storage.removeItem(USER_KEY);
      storage.removeItem('remember_me');
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
   * SECURITY: Tokens are set in httpOnly cookies by backend
   */
  async loginLocal(email, password, rememberMe = false) {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',  // SECURITY: Include cookies in response
      body: JSON.stringify({
        email,
        password,
        remember_me: rememberMe,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    // Store user info locally (tokens are in httpOnly cookies)
    this.setAuthData('local', data.user, rememberMe);
    return data;
  }

  /**
   * Logout
   * SECURITY: Backend clears httpOnly cookies
   */
  async logout() {
    try {
      await this.fetchWithTimeout(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        credentials: 'include',  // SECURITY: Include cookies for logout
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearAuthData();
    }
  }

  /**
   * Get current user info
   * SECURITY: Cookies are sent automatically
   */
  async getCurrentUser() {
    const response = await this.fetchWithTimeout(`${API_BASE_URL}/auth/me`, {
      credentials: 'include',  // SECURITY: Include cookies
    });

    if (!response.ok) {
      throw new Error('Failed to get user info');
    }

    const user = await response.json();
    this.updateStoredUser(user);
    return user;
  }

  /**
   * Refresh access token
   * SECURITY: Cookies are handled automatically by browser
   */
  async refreshToken() {
    const provider = this.getProvider();

    const response = await this.fetchWithTimeout(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',  // SECURITY: Include cookies
    });

    if (!response.ok) {
      this.clearAuthData();
      throw new Error('Token refresh failed');
    }

    return response.json();
  }

  /**
   * Check if token is expired
   * SECURITY: We cannot check token expiry directly since tokens are in httpOnly cookies
   * Instead, we'll try a request and handle 401 responses
   */
  isTokenExpired() {
    // Cannot directly check - tokens are in httpOnly cookies
    // This method now returns false (assume valid until API says otherwise)
    return false;
  }

  /**
   * Ensure valid token, refresh if needed
   * SECURITY: Try making a request and handle 401 responses
   */
  async ensureValidToken() {
    // Tokens are in httpOnly cookies - browser handles refresh automatically
    // Just verify we can make authenticated requests
    try {
      const response = await this.fetchWithTimeout(`${API_BASE_URL}/auth/me`, {
        credentials: 'include',
      });
      if (response.status === 401) {
        // Token is invalid - try refresh
        await this.refreshToken();
      }
      return true;
    } catch (error) {
      this.clearAuthData();
      throw error;
    }
  }
}

// Export singleton instance
const authService = new AuthService();
export default authService;
