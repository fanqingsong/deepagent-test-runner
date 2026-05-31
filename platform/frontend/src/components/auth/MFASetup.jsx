/**
 * MFASetup Component
 *
 * Multi-factor authentication setup interface.
 * Displays QR code, TOTP secret, and backup codes for MFA enrollment.
 * WCAG 2.1 Level AA compliant with proper focus management and error handling.
 */

import { useState } from 'react';
import authClient from '../../services/auth';
import './MFASetup.css';

function MFASetup({ onMFAEnabled, onCancel }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mfaData, setMFAData] = useState(null);
  const [verificationCode, setVerificationCode] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [showCodes, setShowCodes] = useState(false);
  const [copiedCode, setCopiedCode] = useState(null);

  const handleSetup = async () => {
    setLoading(true);
    setError('');

    try {
      const data = await authClient.setupMFA();
      setMFAData(data);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to setup MFA. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyAndEnable = async (e) => {
    e.preventDefault();

    if (!verificationCode || verificationCode.length !== 6) {
      setError('Please enter the 6-digit verification code from your authenticator app.');
      return;
    }

    setVerifying(true);
    setError('');

    try {
      await authClient.enableMFA(verificationCode);

      if (onMFAEnabled) {
        onMFAEnabled();
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Verification failed. Please try again.';
      setError(errorMessage);
    } finally {
      setVerifying(false);
    }
  };

  const handleCopyCode = (code, index) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(index);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const handleDownloadCodes = () => {
    if (!mfaData) return;

    const codesText = mfaData.recovery_codes.join('\n');
    const blob = new Blob([codesText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mfa-recovery-codes.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="mfa-setup-loading" aria-live="polite">
        <div className="spinner" aria-hidden="true"></div>
        <span>Setting up MFA...</span>
      </div>
    );
  }

  if (!mfaData) {
    return (
      <div className="mfa-setup">
        <div className="mfa-setup-header">
          <h2>Setup Two-Factor Authentication</h2>
          <p>Enhance your account security by requiring a verification code when you log in.</p>
        </div>

        {error && (
          <div className="error-message" role="alert" aria-live="assertive">
            {error}
          </div>
        )}

        <div className="mfa-setup-info">
          <h3>Before you begin</h3>
          <ul>
            <li>You'll need an authenticator app (Google Authenticator, Authy, etc.)</li>
            <li>Scan the QR code or enter the secret manually</li>
            <li>Save your backup codes in a secure location</li>
            <li>Backup codes are required if you lose access to your authenticator</li>
          </ul>
        </div>

        <div className="mfa-setup-actions">
          <button
            className="btn-primary"
            onClick={handleSetup}
            disabled={loading}
          >
            Get Started
          </button>
          <button
            className="btn-secondary"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mfa-setup">
      <div className="mfa-setup-header">
        <h2>Setup Two-Factor Authentication</h2>
        <p>Follow these steps to secure your account</p>
      </div>

      {error && (
        <div className="error-message" role="alert" aria-live="assertive">
          {error}
        </div>
      )}

      <div className="mfa-setup-steps">
        {/* Step 1: Scan QR Code */}
        <div className="mfa-step">
          <div className="mfa-step-number">1</div>
          <div className="mfa-step-content">
            <h3>Scan QR Code</h3>
            <p>Open your authenticator app and scan this QR code:</p>
            <div className="qr-code-container">
              <img src={mfaData.qr_code} alt="QR code for TOTP setup" />
            </div>
            <details>
              <summary>Or enter this code manually</summary>
              <code className="secret-code">{mfaData.secret}</code>
            </details>
          </div>
        </div>

        {/* Step 2: Enter Verification Code */}
        <div className="mfa-step">
          <div className="mfa-step-number">2</div>
          <div className="mfa-step-content">
            <h3>Enter Verification Code</h3>
            <p>Enter the 6-digit code from your authenticator app:</p>
            <form onSubmit={handleVerifyAndEnable}>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                pattern="[0-9]{6}"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="123456"
                disabled={verifying}
                aria-label="Six-digit verification code"
                autoComplete="one-time-code"
                required
              />
              <button
                type="submit"
                className="btn-primary"
                disabled={verificationCode.length !== 6 || verifying}
              >
                {verifying ? 'Verifying...' : 'Verify and Enable'}
              </button>
            </form>
          </div>
        </div>

        {/* Step 3: Save Backup Codes */}
        <div className="mfa-step">
          <div className="mfa-step-number">3</div>
          <div className="mfa-step-content">
            <h3>Save Backup Codes</h3>
            <p>Save these codes in a secure location. You can use each code only once:</p>

            <div className="backup-codes-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowCodes(!showCodes)}
              >
                {showCodes ? 'Hide Codes' : 'Show Codes'}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleDownloadCodes}
              >
                Download Codes
              </button>
            </div>

            {showCodes && (
              <div className="backup-codes-grid" role="list">
                {mfaData.recovery_codes.map((code, index) => (
                  <div key={index} className="backup-code-item" role="listitem">
                    <code>{code}</code>
                    <button
                      type="button"
                      className="btn-copy"
                      onClick={() => handleCopyCode(code, index)}
                      aria-label={`Copy code ${index + 1}`}
                    >
                      {copiedCode === index ? '✓ Copied!' : 'Copy'}
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="backup-codes-warning">
              <strong>⚠️ Important:</strong> These codes are the only way to access your account if you lose your authenticator device.
            </div>
          </div>
        </div>
      </div>

      <div className="mfa-setup-actions">
        <button
          className="btn-secondary"
          onClick={onCancel}
          disabled={verifying}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export default MFASetup;
