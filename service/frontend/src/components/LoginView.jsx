/**
 * LoginView Component
 *
 * Login page for email/password authentication using backend service.
 * Provides a clean, focused login experience with remember me functionality.
 */

import { useNavigate } from 'react-router-dom';
import LoginForm from './components/auth/LoginForm';
import './LoginView.css';

function LoginView() {
  const navigate = useNavigate();

  const handleLoginSuccess = (user) => {
    // Redirect to dashboard after successful login
    navigate('/dashboard', { replace: true });
  };

  const handleBackToHome = () => {
    navigate('/');
  };

  return (
    <div className="login-view-container">
      <div className="login-view-card">
        {/* Header */}
        <div className="login-view-header">
          <h1>Claude Code Test Runner</h1>
          <p>Sign in to your account</p>
        </div>

        {/* Login Form */}
        <LoginForm onLoginSuccess={handleLoginSuccess} />

        {/* Footer */}
        <div className="login-view-footer">
          <button
            className="back-button"
            onClick={handleBackToHome}
            type="button"
          >
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}

export default LoginView;
