/**
 * LoginPage
 *
 * Login page with local authentication and registration:
 * 1. Local username/password
 * 2. User registration
 * 3. Password reset
 *
 * Note: Casdoor and SSO options have been hidden
 */

import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import LoginForm from './auth/LoginForm';
import RegisterForm from './auth/RegisterForm';
import PasswordResetForm from './auth/PasswordResetForm';
import './LoginPage.css';

function LoginPage() {
  const { login, loginOidc } = useAuth();

  const [activeTab, setActiveTab] = useState('local');
  const [showRegister, setShowRegister] = useState(false);
  const [showPasswordReset, setShowPasswordReset] = useState(false);

  const handleSwitchToRegister = () => {
    setShowRegister(true);
    setShowPasswordReset(false);
  };

  const handleSwitchToLogin = () => {
    setShowRegister(false);
    setShowPasswordReset(false);
  };

  const handleSwitchToPasswordReset = () => {
    setShowPasswordReset(true);
    setShowRegister(false);
  };

  const handleLoginSuccess = (user) => {
    // Redirect to dashboard using hash routing
    window.location.hash = 'dashboard';
  };

  const handleRegistrationSuccess = (user) => {
    // After successful registration, switch back to login
    setShowRegister(false);
  };

  const handlePasswordResetSuccess = () => {
    // After successful password reset request, switch back to login
    setShowPasswordReset(false);
    setShowRegister(false);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        {!showRegister && !showPasswordReset ? (
          <>
            <div className="login-header">
              <h1>Claude Code Test Runner</h1>
              <p>Sign in to your account</p>
            </div>

            <LoginForm
              onLoginSuccess={handleLoginSuccess}
              onSwitchToPasswordReset={handleSwitchToPasswordReset}
            />

            {/* Switch to Register */}
            <div className="login-footer">
              <p>
                Don't have an account?{' '}
                <button
                  type="button"
                  className="link-button"
                  onClick={handleSwitchToRegister}
                >
                  Create account
                </button>
              </p>
              <p className="footer-note">
                Admin users can view all data. Regular users can only view their own data.
              </p>
            </div>
          </>
        ) : showRegister ? (
          <>
            <div className="login-header">
              <h1>Claude Code Test Runner</h1>
              <p>Create a new account</p>
            </div>

            <RegisterForm
              onRegistrationSuccess={handleRegistrationSuccess}
              onSwitchToLogin={handleSwitchToLogin}
            />
          </>
        ) : (
          <>
            <div className="login-header">
              <h1>Claude Code Test Runner</h1>
              <p>Reset Your Password</p>
            </div>

            <PasswordResetForm
              onSuccess={handlePasswordResetSuccess}
              onCancel={handleSwitchToLogin}
            />
          </>
        )}
      </div>
    </div>
  );
}

export default LoginPage;
