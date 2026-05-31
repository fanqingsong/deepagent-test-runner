/**
 * MFALogin Component
 *
 * MFA verification interface during login.
 * Accepts TOTP code or backup code for two-factor authentication.
 * WCAG 2.1 Level AA compliant.
 */

import { useState } from 'react';
import authClient from '../../services/auth';
import './MFALogin.css';

function MFALogin({ onVerified, onCancel, userEmail }) {
  const [code, setCode] = useState('');
  const [useBackup, setUseBackup] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await authClient.verifyMFA(code, useBackup);

      if (onVerified) {
        onVerified();
      }
    } catch (err) {
      // Extract error message from response or use default
      const errorMessage = err.response?.data?.detail || err.message || 'Verification failed. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mfa-login">
      <div className="mfa-login-header">
        <h2>Two-Factor Authentication</h2>
        <p>Enter the verification code from your authenticator app</p>
      </div>

      {error && (
        <div className="error-message" role="alert" aria-live="assertive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="mfa-input-group">
          <label htmlFor="mfa-code">
            {useBackup ? 'Backup Code' : 'Authentication Code'}
          </label>
          <input
            id="mfa-code"
            type="text"
            inputMode={useBackup ? "text" : "numeric"}
            maxLength={useBackup ? 10 : 6}
            pattern={useBackup ? "[A-Z0-9-]+" : "[0-9]{6}"}
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder={useBackup ? "XXXX-XXXX-XXXX" : "123456"}
            disabled={loading}
            aria-label={useBackup ? "8-character backup code" : "6-digit authentication code"}
            autoComplete={useBackup ? "off" : "one-time-code"}
            required
            autoFocus
          />
        </div>

        <div className="mfa-login-actions">
          <button
            type="button"
            className="btn-link"
            onClick={() => {
              setUseBackup(!useBackup);
              setCode('');
              setError('');
            }}
          >
            {useBackup ? 'Use Authenticator App Instead' : 'Use Backup Code'}
          </button>
        </div>

        <div className="mfa-login-buttons">
          <button
            type="button"
            className="btn-secondary"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !code}
          >
            {loading ? 'Verifying...' : 'Verify'}
          </button>
        </div>

        <div className="mfa-login-info">
          <p><strong>Tip:</strong> Backup codes can only be used once each.</p>
        </div>
      </form>
    </div>
  );
}

export default MFALogin;
