/**
 * LoginForm Component
 *
 * Email/password login form with remember me functionality and MFA support.
 * WCAG 2.1 Level AA compliant with proper form labels, error messages, and focus management.
 */

import { useState } from 'react';
import authClient from '../../services/auth';
import MFALogin from './MFALogin';
import './LoginForm.css';

function LoginForm({ onLoginSuccess, onSwitchToPasswordReset }) {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [requireMFA, setRequireMFA] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [isSuspended, setIsSuspended] = useState(false);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    const fieldValue = type === 'checkbox' ? checked : value;

    setFormData((prev) => ({ ...prev, [name]: fieldValue }));
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Prevent rapid double-submit
    if (loading) {
      return;
    }

    // Validate form inputs
    if (!formData.email.trim()) {
      setError('Please enter your email address');
      return;
    }

    if (!formData.password.trim()) {
      setError('Please enter your password');
      return;
    }

    // Basic email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await authClient.login(
        formData.email,
        formData.password,
        formData.rememberMe
      );

      // Check if MFA is required
      if (response.require_mfa) {
        setRequireMFA(true);
        setUserEmail(formData.email);
        setLoading(false);
        return;
      }

      if (onLoginSuccess) {
        onLoginSuccess(response.user);
      }
    } catch (err) {
      // Extract error message from response or use default
      let errorMessage = err.message || 'Login failed. Please try again.';

      // Handle different error response structures
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        // detail can be a string or an object
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (typeof detail === 'object' && detail.message) {
          errorMessage = detail.message;
        }
      }

      // Check if account is suspended
      if (errorMessage.toLowerCase().includes('suspended')) {
        setIsSuspended(true);
      } else {
        setIsSuspended(false);
      }

      setError(errorMessage);
      setLoading(false);
    }
  };

  const handleMFACancel = () => {
    setRequireMFA(false);
    setUserEmail('');
    setError('');
    setLoading(false);
  };

  const handleMFAVerified = () => {
    setRequireMFA(false);
    setUserEmail('');
    setLoading(false);

    // Fetch user data after MFA verification
    authClient.fetchCurrentUser()
      .then(user => {
        if (onLoginSuccess) {
          onLoginSuccess(user);
        }
      })
      .catch(err => {
        setError('Failed to complete login. Please try again.');
        setLoading(false);
      });
  };

  // Show MFA login form if required
  if (requireMFA) {
    return (
      <MFALogin
        onVerified={handleMFAVerified}
        onCancel={handleMFACancel}
        userEmail={userEmail}
      />
    );
  }

  return (
    <div className="login-form-container">
      <form className="login-form" onSubmit={handleSubmit} noValidate>
        {/* Error Message - WCAG 2.1: role="alert" for screen readers */}
        {error && (
          <div className="error-message" role="alert" aria-live="assertive">
            <svg
              className="error-icon"
              focusable="false"
              aria-hidden="true"
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <div>
              <span>{error}</span>
              {isSuspended && (
                <p className="support-contact">Please contact support for assistance: support@example.com</p>
              )}
            </div>
          </div>
        )}

        {/* Email Field - WCAG 2.1: Proper label association with htmlFor */}
        <div className="form-group">
          <label htmlFor="login-email">
            Email Address <span className="required" aria-label="required">*</span>
          </label>
          <input
            id="login-email"
            type="email"
            name="email"
            value={formData.email}
            onChange={handleInputChange}
            required
            autoComplete="email"
            placeholder="you@example.com"
            disabled={loading}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? 'login-error' : undefined}
          />
        </div>

        {/* Password Field - WCAG 2.1: Proper label and autocomplete */}
        <div className="form-group">
          <label htmlFor="login-password">
            Password <span className="required" aria-label="required">*</span>
          </label>
          <input
            id="login-password"
            type="password"
            name="password"
            value={formData.password}
            onChange={handleInputChange}
            required
            autoComplete="current-password"
            placeholder="Enter your password"
            disabled={loading}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? 'login-error' : undefined}
          />
          <div className="forgot-password-link">
            <button
              type="button"
              className="link-button"
              onClick={onSwitchToPasswordReset}
            >
              Forgot password?
            </button>
          </div>
        </div>

        {/* Remember Me Checkbox - WCAG 2.1: Proper label wrapping */}
        <div className="form-group checkbox-group">
          <label className="checkbox-label" htmlFor="login-remember">
            <input
              id="login-remember"
              type="checkbox"
              name="rememberMe"
              checked={formData.rememberMe}
              onChange={handleInputChange}
              disabled={loading}
            />
            <span className="checkbox-text">Remember me for 30 days</span>
          </label>
        </div>

        {/* Submit Button - WCAG 2.1: Clear state indication */}
        <button
          type="submit"
          className="login-button"
          disabled={loading}
          aria-busy={loading}
        >
          {loading ? (
            <>
              <span className="spinner" aria-hidden="true"></span>
              <span>Signing in...</span>
            </>
          ) : (
            'Sign In'
          )}
        </button>
      </form>
    </div>
  );
}

export default LoginForm;
