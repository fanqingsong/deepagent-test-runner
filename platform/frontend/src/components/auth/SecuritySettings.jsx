/**
 * SecuritySettings Component
 *
 * User security settings page for MFA and password management.
 * Provides MFA enable/disable controls and password change functionality.
 * WCAG 2.1 Level AA compliant.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import authClient from '../../services/auth';
import MFASetup from './MFASetup';
import './SecuritySettings.css';

function SecuritySettings() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [mfaStatus, setMfaStatus] = useState(null);
  const [showMFASetup, setShowMFASetup] = useState(false);
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [showDisableMFA, setShowDisableMFA] = useState(false);

  // Password change form state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');

  // Disable MFA form state
  const [disablePassword, setDisablePassword] = useState('');
  const [disableTOTP, setDisableTOTP] = useState('');

  useEffect(() => {
    fetchMFAStatus();
  }, []);

  const fetchMFAStatus = async () => {
    setLoading(true);
    setError('');

    try {
      const data = await authClient.getMFAStatus();
      setMfaStatus(data);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch security settings';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleMFAEnabled = () => {
    setShowMFASetup(false);
    setSuccess('MFA has been enabled successfully.');
    setTimeout(() => setSuccess(''), 5000);
    fetchMFAStatus();
  };

  const handleDisableMFA = async (e) => {
    e.preventDefault();

    if (!disablePassword) {
      setPasswordError('Password is required to disable MFA');
      return;
    }

    setSaving(true);
    setError('');
    setPasswordError('');

    try {
      await authClient.disableMFA(disablePassword, disableTOTP || null);

      setShowDisableMFA(false);
      setDisablePassword('');
      setDisableTOTP('');
      setSuccess('MFA has been disabled successfully.');
      setTimeout(() => setSuccess(''), 5000);
      fetchMFAStatus();
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to disable MFA';
      setPasswordError(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters long');
      return;
    }

    setSaving(true);
    setError('');
    setPasswordError('');

    try {
      await authClient.changePassword(currentPassword, newPassword);

      setShowPasswordChange(false);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setSuccess('Password changed successfully. All other sessions have been terminated.');
      setTimeout(() => setSuccess(''), 5000);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to change password';
      setPasswordError(errorMessage);
    } finally {
      setSaving(false);
    }
  };

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

  if (loading) {
    return (
      <div className="security-settings-loading" aria-live="polite">
        <div className="spinner" aria-hidden="true"></div>
        <span>Loading security settings...</span>
      </div>
    );
  }

  if (showMFASetup && !mfaStatus?.mfa_enabled) {
    return (
      <div className="security-settings">
        <MFASetup onMFAEnabled={handleMFAEnabled} onCancel={() => setShowMFASetup(false)} />
      </div>
    );
  }

  return (
    <div className="security-settings">
      <div className="security-settings-header">
        <h1>Security Settings</h1>
        <p>Manage your account security preferences</p>
      </div>

      {error && (
        <div className="error-message" role="alert" aria-live="assertive">
          {error}
        </div>
      )}

      {success && (
        <div className="success-message" role="status" aria-live="polite">
          {success}
        </div>
      )}

      <div className="security-settings-sections">
        {/* MFA Section */}
        <section className="security-section" aria-labelledby="mfa-heading">
          <h2 id="mfa-heading">Two-Factor Authentication</h2>

          {mfaStatus?.mfa_enabled ? (
            <div className="mfa-enabled">
              <div className="status-badge status-enabled">
                <span aria-hidden="true">✓</span>
                <span>Enabled</span>
              </div>

              <div className="mfa-info">
                <p>
                  <strong>Recovery Codes Remaining:</strong> {mfaStatus.remaining_recovery_codes} of 10
                </p>
                {mfaStatus.remaining_recovery_codes <= 3 && (
                  <p className="warning">
                    ⚠️ You have low recovery codes remaining. Consider disabling and re-enabling MFA to generate new codes.
                  </p>
                )}
              </div>

              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowDisableMFA(true)}
                aria-label="Disable two-factor authentication"
              >
                Disable MFA
              </button>
            </div>
          ) : (
            <div className="mfa-disabled">
              <div className="status-badge status-disabled">
                <span aria-hidden="true">○</span>
                <span>Not Enabled</span>
              </div>

              <p className="mfa-description">
                Add an extra layer of security to your account by requiring a verification code when you log in.
              </p>

              <button
                type="button"
                className="btn-primary"
                onClick={() => setShowMFASetup(true)}
                aria-label="Enable two-factor authentication"
              >
                Enable MFA
              </button>
            </div>
          )}
        </section>

        {/* Password Section */}
        <section className="security-section" aria-labelledby="password-heading">
          <h2 id="password-heading">Password</h2>

          <p className="password-description">
            Change your password to maintain account security. You will be logged out of all other devices after changing your password.
          </p>

          <button
            type="button"
            className="btn-secondary"
            onClick={() => setShowPasswordChange(true)}
            aria-label="Change password"
          >
            Change Password
          </button>
        </section>
      </div>

      {/* Disable MFA Modal */}
      {showDisableMFA && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="disable-mfa-title">
          <div className="modal-content">
            <h2 id="disable-mfa-title">Disable Two-Factor Authentication</h2>

            <p>
              Disabling MFA will reduce the security of your account. You can re-enable it at any time.
            </p>

            {passwordError && (
              <div className="error-message" role="alert" aria-live="assertive">
                {passwordError}
              </div>
            )}

            <form onSubmit={handleDisableMFA}>
              <div className="form-group">
                <label htmlFor="disable-password">Current Password</label>
                <input
                  id="disable-password"
                  type="password"
                  value={disablePassword}
                  onChange={(e) => setDisablePassword(e.target.value)}
                  required
                  aria-describedby="disable-password-description"
                />
                <small id="disable-password-description">
                  Enter your current password to confirm
                </small>
              </div>

              <div className="form-group">
                <label htmlFor="disable-totp">TOTP Code (Optional)</label>
                <input
                  id="disable-totp"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  value={disableTOTP}
                  onChange={(e) => setDisableTOTP(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="123456"
                  autoComplete="one-time-code"
                  aria-describedby="disable-totp-description"
                />
                <small id="disable-totp-description">
                  Provide TOTP code for additional verification
                </small>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setShowDisableMFA(false);
                    setDisablePassword('');
                    setDisableTOTP('');
                    setPasswordError('');
                  }}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={saving || !disablePassword}
                >
                  {saving ? 'Disabling...' : 'Disable MFA'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Change Password Modal */}
      {showPasswordChange && (
        <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="change-password-title">
          <div className="modal-content">
            <h2 id="change-password-title">Change Password</h2>

            {passwordError && (
              <div className="error-message" role="alert" aria-live="assertive">
                {passwordError}
              </div>
            )}

            <form onSubmit={handlePasswordChange}>
              <div className="form-group">
                <label htmlFor="current-password">Current Password</label>
                <input
                  id="current-password"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </div>

              <div className="form-group">
                <label htmlFor="new-password">New Password</label>
                <input
                  id="new-password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  aria-describedby="password-strength password-requirements"
                />
                {newPassword && (
                  <div className="password-strength" aria-live="polite">
                    <div
                      className="strength-bar"
                      style={{
                        width: `${(getPasswordStrength(newPassword).strength / 5) * 100}%`,
                        backgroundColor: getPasswordStrength(newPassword).color,
                      }}
                      aria-label={`Password strength: ${getPasswordStrength(newPassword).label}`}
                    />
                    <span>{getPasswordStrength(newPassword).label}</span>
                  </div>
                )}
                <small id="password-requirements">
                  Must be at least 8 characters with mixed case, numbers, and special characters
                </small>
              </div>

              <div className="form-group">
                <label htmlFor="confirm-password">Confirm New Password</label>
                <input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  autoComplete="new-password"
                  aria-invalid={confirmPassword && confirmPassword !== newPassword}
                  aria-describedby="confirm-password-description"
                />
                {confirmPassword && confirmPassword !== newPassword && (
                  <small id="confirm-password-description" className="error">
                    Passwords do not match
                  </small>
                )}
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setShowPasswordChange(false);
                    setCurrentPassword('');
                    setNewPassword('');
                    setConfirmPassword('');
                    setPasswordError('');
                  }}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={saving || !currentPassword || !newPassword || !confirmPassword || newPassword !== confirmPassword}
                >
                  {saving ? 'Changing...' : 'Change Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default SecuritySettings;
