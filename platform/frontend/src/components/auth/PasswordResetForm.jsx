/**
 * PasswordResetForm Component
 *
 * Form for requesting password reset email.
 * WCAG 2.1 Level AA compliant.
 */

import { useState } from 'react';
import authClient from '../../services/auth';
import './PasswordResetForm.css';

function PasswordResetForm({ onSuccess, onCancel }) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    if (!email.trim()) {
      setError('Please enter your email address');
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('Please enter a valid email address');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authClient.requestPasswordReset(email);
      setSuccess(true);
      setTimeout(() => {
        if (onSuccess) onSuccess(email);
      }, 2000);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to send reset email. Please try again.';
      setError(errorMessage);
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="password-reset-form-container">
        <div className="success-message" role="status" aria-live="polite">
          <svg className="success-icon" focusable="false" aria-hidden="true" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
          </svg>
          <div>
            <p><strong>Check your email</strong></p>
            <p>If an account exists for {email}, a password reset link has been sent.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="password-reset-form-container">
      <form className="password-reset-form" onSubmit={handleSubmit} noValidate>
        {error && (
          <div className="error-message" role="alert" aria-live="assertive">
            <svg className="error-icon" focusable="false" aria-hidden="true" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
            </svg>
            <span>{error}</span>
          </div>
        )}
        <div className="form-header">
          <h2>Reset Your Password</h2>
          <p>Enter your email address and we'll send you a link to reset your password.</p>
        </div>
        <div className="form-group">
          <label htmlFor="reset-email">Email Address <span className="required" aria-label="required">*</span></label>
          <input id="reset-email" type="email" name="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" placeholder="you@example.com" disabled={loading} aria-invalid={error ? 'true' : 'false'} />
        </div>
        <button type="submit" className="reset-button" disabled={loading} aria-busy={loading}>
          {loading ? <><span className="spinner" aria-hidden="true"></span><span>Sending...</span></> : 'Send Reset Link'}
        </button>
        {onCancel && (
          <button type="button" className="cancel-button" onClick={onCancel} disabled={loading}>Back to Login</button>
        )}
      </form>
    </div>
  );
}

export default PasswordResetForm;
