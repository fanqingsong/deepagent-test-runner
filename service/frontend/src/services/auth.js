import axios from 'axios';
import authService from './authService';

// Use current origin (port 8080 with nginx) for API requests
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin;

/**
 * Authentication API client for communicating with backend service
 */
class AuthClient {
  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1/auth`,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to include auth tokens
    this.client.interceptors.request.use(
      (config) => {
        const accessToken = localStorage.getItem('access_token');
        const sessionToken = localStorage.getItem('session_token');

        if (accessToken) {
          config.headers.Authorization = `Bearer ${accessToken}`;
        }
        if (sessionToken) {
          config.headers['X-Session-Token'] = sessionToken;
        }

        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Add response interceptor to handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // If 401 and not retrying yet, try token refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
              const response = await this.refreshAccessToken(refreshToken);

              // Store new tokens
              localStorage.setItem('access_token', response.access_token);

              // Retry original request with new token
              originalRequest.headers.Authorization = `Bearer ${response.access_token}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            // Refresh failed, clear tokens and redirect to login
            this.clearTokens();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  /**
   * Register a new user
   */
  async register(email, password) {
    const response = await this.client.post('/register', {
      email,
      password,
    });

    return response.data;
  }

  /**
   * Verify email with token
   */
  async verifyEmail(token) {
    const response = await this.client.post('/verify-email', { token });
    return response.data;
  }

  /**
   * Login with email and password
   */
  async login(email, password, rememberMe = false) {
    const response = await this.client.post('/login', {
      email,
      password,
      remember_me: rememberMe,
    });

    // Handle MFA requirement (202 Accepted response)
    if (response.status === 202 && response.data.require_mfa) {
      // Don't store tokens yet - MFA verification required first
      // Store temporary email for MFA flow
      sessionStorage.setItem('pending_login_email', email);
      return { require_mfa: true, email };
    }

    // Store tokens and session for successful login (200 OK)
    const { access_token, refresh_token, session_token, user } = response.data;

    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    localStorage.setItem('session_token', session_token);
    localStorage.setItem('user_info', JSON.stringify(user));

    // Notify authService about authentication state change
    authService.notifyAuthChange();

    // Clear pending login data
    sessionStorage.removeItem('pending_login_email');

    return response.data;
  }

  /**
   * Logout current user
   */
  async logout() {
    try {
      await this.client.post('/logout');
    } finally {
      this.clearTokens();
    }
  }

  /**
   * Get all active sessions for current user
   */
  async getSessions() {
    const response = await this.client.get('/sessions');
    return response.data;
  }

  /**
   * Terminate a specific session
   */
  async terminateSession(sessionId) {
    const response = await this.client.delete(`/sessions/${sessionId}`);
    return response.data;
  }

  /**
   * Terminate all other sessions except current
   */
  async terminateAllOtherSessions() {
    const response = await this.client.delete('/sessions');
    return response.data;
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshAccessToken(refreshToken) {
    const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
      refresh_token: refreshToken,
    });

    return response.data;
  }

  /**
   * Clear all auth tokens from storage
   */
  clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('session_token');
    localStorage.removeItem('user');
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    return !!localStorage.getItem('access_token');
  }

  /**
   * Get current user from storage
   */
  getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  /**
   * Fetch current user from API
   */
  async fetchCurrentUser() {
    const response = await this.client.get('/me');
    return response.data;
  }

  /**
   * Setup MFA (get QR code and secret)
   */
  async setupMFA() {
    const response = await this.client.post('/mfa/setup');
    return response.data;
  }

  /**
   * Enable MFA with verification code
   */
  async enableMFA(totpCode) {
    const response = await this.client.post('/mfa/enable', {
      totp_code: totpCode,
    });
    return response.data;
  }

  /**
   * Disable MFA
   */
  async disableMFA(password, totpCode = null) {
    const payload = { password };
    if (totpCode) {
      payload.totp_code = totpCode;
    }
    const response = await this.client.post('/mfa/disable', payload);
    return response.data;
  }

  /**
   * Get MFA status
   */
  async getMFAStatus() {
    const response = await this.client.get('/mfa/status');
    return response.data;
  }

  /**
   * Verify MFA code during login
   */
  async verifyMFA(code, useBackup = false) {
    const payload = useBackup ? { recovery_code: code } : { totp_code: code };
    const response = await this.client.post('/mfa/verify', payload);

    // Store tokens and session after successful MFA verification
    const { access_token, refresh_token, session_token, user } = response.data;

    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    localStorage.setItem('session_token', session_token);
    localStorage.setItem('user_info', JSON.stringify(user));

    // Notify authService about authentication state change
    authService.notifyAuthChange();

    // Clear pending login data
    sessionStorage.removeItem('pending_login_email');

    return response.data;
  }

  /**
   * Change password
   */
  async changePassword(currentPassword, newPassword) {
    const response = await this.client.post('/password/change', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(email) {
    const response = await this.client.post('/password/reset', {
      email,
    });
    return response.data;
  }

  /**
   * Confirm password reset with token
   */
  async confirmPasswordReset(token, newPassword) {
    const response = await this.client.post('/password/reset/confirm', {
      token,
      new_password: newPassword,
    });
    return response.data;
  }
}

// Export singleton instance
export const authClient = new AuthClient();
export default authClient;
