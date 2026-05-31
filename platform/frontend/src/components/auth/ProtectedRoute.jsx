/**
 * ProtectedRoute Component (auth-service version)
 *
 * Wrapper component that requires JWT authentication.
 * Redirects to login page if user is not authenticated.
 * Uses the new auth-service JWT + session token authentication.
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { isAuthenticated } from '../../middleware/auth';

function ProtectedRoute({ children }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check authentication status
    if (!isAuthenticated()) {
      // Redirect to login page
      navigate('/login', { replace: true });
    } else {
      setLoading(false);
    }
  }, [navigate]);

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '18px',
        color: '#666'
      }}>
        Loading...
      </div>
    );
  }

  return children;
}

export default ProtectedRoute;
