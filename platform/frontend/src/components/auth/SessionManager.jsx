/**
 * SessionManager Component
 *
 * Displays and manages active user sessions.
 * Allows users to view all active sessions and terminate specific sessions.
 * WCAG 2.1 Level AA compliant with proper ARIA labels and keyboard navigation.
 */

import { useState, useEffect } from 'react';
import authClient from '../../services/auth';
import './SessionManager.css';

function SessionManager() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [terminating, setTerminating] = useState(new Set());

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    setLoading(true);
    setError('');

    try {
      const sessionsData = await authClient.getSessions();
      setSessions(sessionsData);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to load sessions';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleTerminateSession = async (sessionId) => {
    // Prevent double-click
    if (terminating.has(sessionId)) {
      return;
    }

    setTerminating((prev) => new Set(prev).add(sessionId));
    setError('');

    try {
      await authClient.terminateSession(sessionId);

      // Remove the terminated session from the list
      setSessions((prev) => prev.filter((session) => session.id !== sessionId));
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to terminate session';
      setError(errorMessage);
      setTerminating((prev) => {
        const next = new Set(prev);
        next.delete(sessionId);
        return next;
      });
    }
  };

  const handleTerminateAllOthers = async () => {
    if (terminating.has('all')) {
      return;
    }

    if (!confirm('Are you sure you want to terminate all other sessions? This will sign you out of all other devices.')) {
      return;
    }

    setTerminating((prev) => new Set(prev).add('all'));
    setError('');

    try {
      await authClient.terminateAllOtherSessions();

      // Keep only the current session
      setSessions((prev) => prev.filter((session) => session.is_current));
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to terminate sessions';
      setError(errorMessage);
      setTerminating((prev) => {
        const next = new Set(prev);
        next.delete('all');
        return next;
      });
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isCurrentSession = (session) => {
    const currentSessionToken = localStorage.getItem('session_token');
    return session.session_token === currentSessionToken;
  };

  return (
    <div className="session-manager">
      <div className="session-manager-header">
        <h2>Active Sessions</h2>
        <button
          className="terminate-all-button"
          onClick={handleTerminateAllOthers}
          disabled={terminating.has('all') || sessions.length <= 1}
          aria-label="Terminate all other sessions"
        >
          {terminating.has('all') ? 'Terminating...' : 'Terminate All Other Sessions'}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-message" role="alert" aria-live="assertive">
          <svg
            className="error-icon"
            focusable="false"
            aria-hidden="true"
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="loading-state" aria-live="polite">
          <div className="spinner" aria-hidden="true"></div>
          <span>Loading sessions...</span>
        </div>
      ) : sessions.length === 0 ? (
        /* Empty State */
        <div className="empty-state" aria-live="polite">
          <p>No active sessions found.</p>
        </div>
      ) : (
        /* Sessions List */
        <div className="sessions-list" role="list">
          {sessions.map((session) => {
            const isCurrent = isCurrentSession(session);
            const isTerminating = terminating.has(session.id);

            return (
              <div
                key={session.id}
                className={`session-card ${isCurrent ? 'current' : ''}`}
                role="listitem"
              >
                <div className="session-info">
                  <div className="session-header">
                    <h3 className="session-title">
                      {isCurrent && (
                        <span className="current-badge" aria-label="Current session">
                          Current
                        </span>
                      )}
                      {session.user_agent || 'Unknown Device'}
                    </h3>
                  </div>

                  <div className="session-details">
                    <div className="session-detail">
                      <span className="detail-label">IP Address:</span>
                      <span className="detail-value">{session.ip_address || 'Unknown'}</span>
                    </div>
                    <div className="session-detail">
                      <span className="detail-label">Last Active:</span>
                      <span className="detail-value">{formatDate(session.last_active)}</span>
                    </div>
                    <div className="session-detail">
                      <span className="detail-label">Expires:</span>
                      <span className="detail-value">{formatDate(session.expires_at)}</span>
                    </div>
                  </div>
                </div>

                {!isCurrent && (
                  <button
                    className="terminate-button"
                    onClick={() => handleTerminateSession(session.id)}
                    disabled={isTerminating}
                    aria-label={`Terminate session from ${session.ip_address || 'unknown location'}`}
                    aria-busy={isTerminating}
                  >
                    {isTerminating ? (
                      <>
                        <span className="spinner-small" aria-hidden="true"></span>
                        <span>Terminating...</span>
                      </>
                    ) : (
                      'Terminate'
                    )}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default SessionManager;
