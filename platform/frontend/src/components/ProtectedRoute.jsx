/**
 * ProtectedRoute
 *
 * Wrapper component that requires authentication.
 * Redirects to login page if user is not authenticated.
 */

import { useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      // Redirect to login using hash routing
      window.location.hash = 'login';
    }
  }, [isAuthenticated, loading]);

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

  if (!isAuthenticated) {
    return null; // Will redirect via useEffect
  }

  return children;
}

export default ProtectedRoute;
