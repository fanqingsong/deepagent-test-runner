/**
 * PasswordResetConfirm Component
 *
 * Form for confirming password reset with token and setting new password.
 * WCAG 2.1 Level AA compliant with password strength feedback.
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import authClient from '../../services/auth';
import './PasswordResetConfirm.css';

function PasswordResetConfirm() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [tokenValid, setTokenValid] = useState(true);

  useEffect(() => {
    const resetToken = searchParams.get('token');
    if (!resetToken) {
      setTokenValid(false);
      setError('Invalid or missing reset token');
    } else {
      setToken(resetToken);
    }
  }, [searchParams]);

  const getPasswordStrength = (password) => {
    if (!password) return { strength: 0, label: 'Weak', color: '#da1e28' };
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) strength++;
    if (strength <= 2) return { strength, label: 'Weak', color: '#da1e28' };
    if (strength <= 3) return { strength, label: 'Medium', color: '#f1c21b' };
    return { strength, label: 'Strong', color: '#24a148' };
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    if (!tokenValid) return;
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await authClient.confirmPasswordReset(token, newPassword);
      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to reset password. The token may be expired.';
      setError(errorMessage);
      setLoading(false);
    }
  };

  if (!tokenValid) {
    return (
      <div className="password-reset-confirm-container">
        <div className="error-message" role="alert">
          <svg className="error-icon" focusable="false" aria-hidden="true" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
          </svg>
          <div>
            <p><strong>Invalid Reset Link</strong></p>
            <p>This password reset link is invalid or has expired. Please request a new reset link.</p>
            <button className="btn-link" onClick={() => navigate('/password-reset')}>Request New Reset Link</button>
          </div>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="password-reset-confirm-container">
        <div className="success-message" role="status" aria-live="polite">
          <svg className="success-icon" focusable="false" aria-hidden="true" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
          </svg>
          <div>
            <p><strong>Password Reset Successful</strong></p>
            <p>Your password has been reset. You can now log in with your new password.</p>
            <p>Redirecting to login page...</p>
          </div>
        </div>
      </div>
    );
  }

  const passwordStrength = getPasswordStrength(newPassword);

  return (
    <div className="password-reset-confirm-container">
      <form className="password-reset-confirm-form" onSubmit={handleSubmit} noValidate>
        <div className="form-header">
          <h2>Set New Password</h2>
          <p>Enter your new password below.</p>
        </div>

        {error && (
          <div className="error-message" role="alert" aria-live="assertive">
            <svg className="error-icon" focusable="false" aria-hidden="true" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
            </svg>
            <span>{error}</span>
          </div>
        )}

        <div className="form-group">
          <label htmlFor="new-password">New Password <span className="required" aria-label="required">*</span></label>
          <input
            id="new-password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            autoComplete="new-password"
            placeholder="Enter new password"
            disabled={loading}
            aria-invalid={error ? 'true' : 'false'}
            aria-describedby="password-strength password-requirements"
          />
          {newPassword && (
            <div className="password-strength" aria-live="polite">
              <div className="strength-bar-container">
                <div className="strength-bar" style={{ width: `${(passwordStrength.strength / 5) * 100}%`, backgroundColor: passwordStrength.color }}></div>
              </div>
              <span className="strength-label">{passwordStrength.label}</span>
            </div>
          )}
          <small id="password-requirements">Must be at least 8 characters with mixed case, numbers, and special characters</small>
        </div>

        <div className="form-group">
          <label htmlFor="confirm-password">Confirm New Password <span className="required" aria-label="required">*</span></label>
          <input
            id="confirm-password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
            placeholder="Confirm new password"
            disabled={loading}
            aria-invalid={confirmPassword && confirmPassword !== newPassword}
            aria-describedby="confirm-error"
          />
          {confirmPassword && confirmPassword !== newPassword && (
            <small id="confirm-error" className="error">Passwords do not match</small>
          )}
        </div>

        <button
          type="submit"
          className="submit-button"
          disabled={loading || !newPassword || !confirmPassword || newPassword !== confirmPassword}
          aria-busy={loading}
        >
          {loading ? <><span className="spinner" aria-hidden="true"></span><span>Resetting...</span></> : 'Reset Password'}
        </button>

        <button
          type="button"
          className="cancel-button"
          onClick={() => navigate('/login')}
          disabled={loading}
        >
          Cancel
        </button>
      </form>
    </div>
  );
}

export default PasswordResetConfirm;
