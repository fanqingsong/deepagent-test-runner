/**
 * LoginPage
 *
 * Login page with local authentication:
 * 1. Local username/password
 *
 * Note: Casdoor and SSO options have been hidden
 */

import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './LoginPage.css';

function LoginPage() {
  const { login, loginOidc } = useAuth();

  const [activeTab, setActiveTab] = useState('local');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError('');
  };

  const handleLocalLogin = async (e) => {
    e.preventDefault();

    // Prevent rapid double-submit
    if (loading) {
      return;
    }

    // Validate form inputs
    if (!formData.email.trim()) {
      setError('Please enter your email');
      return;
    }

    if (!formData.password.trim()) {
      setError('Please enter your password');
      return;
    }

    setLoading(true);
    setError('');

    const result = await login('local', formData.email, formData.password);

    if (result.success) {
      // Redirect to dashboard using hash routing
      window.location.hash = 'dashboard';
    } else {
      setError(result.error);
      setLoading(false);
    }
  };

  const handleCasdoorLogin = async (e) => {
    e.preventDefault();

    // Prevent rapid double-submit
    if (loading) {
      return;
    }

    setLoading(true);
    setError('');

    const result = await login('casdoor', formData.username, formData.password);

    if (result.success) {
      // Redirect to dashboard using hash routing
      window.location.hash = 'dashboard';
    } else {
      setError(result.error);
      setLoading(false);
    }
  };

  const handleOidcLogin = async () => {
    // Prevent rapid double-submit
    if (loading) {
      return;
    }

    setLoading(true);
    setError('');

    const result = await loginOidc();

    if (!result.success) {
      setError(result.error);
      setLoading(false);
    }
    // If successful, redirect happens automatically
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>Claude Code Test Runner</h1>
          <p>Sign in to your account</p>
        </div>

        {/* Auth Method Tabs */}
        <div className="auth-tabs">
          <button
            className={`tab-button ${activeTab === 'local' ? 'active' : ''}`}
            onClick={() => setActiveTab('local')}
          >
            Local Account
          </button>
          {/* Casdoor and SSO options hidden */}
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {/* Local Login Form */}
        {activeTab === 'local' && (
          <form className="login-form" onSubmit={handleLocalLogin} noValidate>
            <div className="form-group">
              <label htmlFor="local-email">Email</label>
              <input
                id="local-email"
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
                placeholder="Enter your email"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="local-password">Password</label>
              <input
                id="local-password"
                type="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                required
                placeholder="Enter your password"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              className="login-button"
              disabled={loading}
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        )}

        {/* Casdoor and SSO forms hidden */}

        {/* Footer */}
        <div className="login-footer">
          <p>
            Admin users can view all data. Regular users can only view their own data.
          </p>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
