/**
 * RegisterForm Component
 *
 * User registration form with email, password, and confirm password fields.
 * WCAG 2.1 Level AA compliant with proper form labels, error messages, and focus management.
 * Follows IBM Carbon Design System.
 */

import { useState } from 'react';
import authClient from '../../services/auth';
import './RegisterForm.css';

function RegisterForm({ onRegistrationSuccess, onSwitchToLogin }) {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
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
      setError('Please enter a password');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // Password strength validation
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long');
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
      const response = await authClient.register(
        formData.email,
        formData.password
      );

      setSuccess(true);

      // Auto-switch to login after 2 seconds
      setTimeout(() => {
        if (onSwitchToLogin) {
          onSwitchToLogin();
        }
      }, 2000);
    } catch (err) {
      // Extract error message from response or use default
      const errorMessage = err.response?.data?.detail || err.message || 'Registration failed. Please try again.';
      setError(errorMessage);
      setLoading(false);
    }
  };

  // Show success message
  if (success) {
    return (
      <div className="register-form-container">
        <div className="success-message" role="status" aria-live="polite">
          <svg
            className="success-icon"
            focusable="false"
            aria-hidden="true"
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <div>
            <span className="success-title">Registration successful!</span>
            <p className="success-description">
              Please check your email to verify your account. You can now log in.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="register-form-container">
      <h2 className="form-title">Create an account</h2>

      <form className="register-form" onSubmit={handleSubmit} noValidate>
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
            <span>{error}</span>
          </div>
        )}

        {/* Email Field */}
        <div className="form-group">
          <label htmlFor="register-email">
            Email Address <span className="required" aria-label="required">*</span>
          </label>
          <input
            id="register-email"
            type="email"
            name="email"
            value={formData.email}
            onChange={handleInputChange}
            required
            autoComplete="email"
            placeholder="you@example.com"
            disabled={loading}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? 'register-error' : undefined}
          />
        </div>

        {/* Password Field */}
        <div className="form-group">
          <label htmlFor="register-password">
            Password <span className="required" aria-label="required">*</span>
          </label>
          <input
            id="register-password"
            type="password"
            name="password"
            value={formData.password}
            onChange={handleInputChange}
            required
            autoComplete="new-password"
            placeholder="Create a password (min. 8 characters)"
            disabled={loading}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? 'register-error' : undefined}
          />
        </div>

        {/* Confirm Password Field */}
        <div className="form-group">
          <label htmlFor="register-confirm-password">
            Confirm Password <span className="required" aria-label="required">*</span>
          </label>
          <input
            id="register-confirm-password"
            type="password"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleInputChange}
            required
            autoComplete="new-password"
            placeholder="Confirm your password"
            disabled={loading}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby={error ? 'register-error' : undefined}
          />
        </div>

        {/* Submit Button - WCAG 2.1: Clear state indication */}
        <button
          type="submit"
          className="primary-button"
          disabled={loading}
          aria-busy={loading}
        >
          {loading ? (
            <>
              <span className="spinner" aria-hidden="true"></span>
              <span>Creating account...</span>
            </>
          ) : (
            'Create account'
          )}
        </button>
      </form>

      {/* Switch to Login */}
      <div className="form-footer">
        <p>
          Already have an account?{' '}
          <button
            type="button"
            className="link-button"
            onClick={onSwitchToLogin}
            disabled={loading}
          >
            Sign in
          </button>
        </p>
      </div>
    </div>
  );
}

export default RegisterForm;
