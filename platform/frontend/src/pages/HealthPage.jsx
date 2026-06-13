/**
 * Health Check Page Component
 *
 * System health monitoring dashboard with:
 * - Overall system health status
 * - Individual component health
 * - Health check history
 * - Component status visualization
 *
 * Follows IBM Carbon design system.
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './HealthPage.css';

function HealthPage() {
  const { user } = useAuth();
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [historyData, setHistoryData] = useState([]);

  const fetchHealthData = async (skipCache = false) => {
    try {
      setRefreshing(true);
      setError(null);

      // Fetch detailed health check
      const skipParam = skipCache ? 'skip_cache=true' : '';
      const response = await fetch(`/api/v1/health/detailed?${skipParam}`, {
        headers: {
          'Authorization': `Bearer ${user?.token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch health data');
      }

      const data = await response.json();
      setHealthData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/v1/health/history?limit=20', {
        headers: {
          'Authorization': `Bearer ${user?.token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch health history');
      }

      const data = await response.json();
      setHistoryData(data.entries || []);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  };

  useEffect(() => {
    if (user) {
      fetchHealthData();
      fetchHistory();

      // Refresh every 30 seconds
      const interval = setInterval(() => {
        fetchHealthData();
      }, 30000);

      return () => clearInterval(interval);
    }
  }, [user]);

  const handleRefresh = () => {
    fetchHealthData(true); // Skip cache
    fetchHistory();
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
        return '#198038'; // IBM Green
      case 'degraded':
        return '#f1c21b'; // IBM Yellow
      case 'unhealthy':
        return '#da1e28'; // IBM Red
      default:
        return '#6f6f6f'; // IBM Gray
    }
  };

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
        return '✓';
      case 'degraded':
        return '⚠';
      case 'unhealthy':
        return '✕';
      default:
        return '?';
    }
  };

  if (loading) {
    return (
      <div className="health-page">
        <div className="health-loading">Loading health data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="health-page">
        <div className="health-error">
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={() => fetchHealthData()} className="health-button">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!healthData) {
    return null;
  }

  const { status, components, timestamp, total_components, healthy_components, degraded_components, unhealthy_components } = healthData;

  return (
    <div className="health-page">
      <div className="health-header">
        <h1>System Health</h1>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className={`health-button ${refreshing ? 'refreshing' : ''}`}
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Overall Status */}
      <div className="health-overall-status" style={{ borderColor: getStatusColor(status) }}>
        <div className="health-status-icon" style={{ color: getStatusColor(status) }}>
          {getStatusIcon(status)}
        </div>
        <div className="health-status-info">
          <h2 style={{ color: getStatusColor(status) }}>{status?.toUpperCase()}</h2>
          <p>{healthData.details || 'System health check completed'}</p>
          <p className="health-timestamp">
            Last check: {new Date(timestamp).toLocaleString()}
          </p>
        </div>
      </div>

      {/* Component Summary */}
      <div className="health-summary">
        <div className="health-summary-card">
          <h3>Total Components</h3>
          <p className="health-summary-value">{total_components}</p>
        </div>
        <div className="health-summary-card healthy">
          <h3>Healthy</h3>
          <p className="health-summary-value">{healthy_components}</p>
        </div>
        <div className="health-summary-card degraded">
          <h3>Degraded</h3>
          <p className="health-summary-value">{degraded_components}</p>
        </div>
        <div className="health-summary-card unhealthy">
          <h3>Unhealthy</h3>
          <p className="health-summary-value">{unhealthy_components}</p>
        </div>
      </div>

      {/* Component Details */}
      <div className="health-components">
        <h3>Component Details</h3>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="health-toggle-button"
        >
          {showDetails ? 'Hide Details' : 'Show Details'}
        </button>

        {showDetails && (
          <div className="health-components-list">
            {Object.entries(components).map(([name, component]) => (
              <div
                key={name}
                className="health-component-card"
                style={{ borderLeftColor: getStatusColor(component.status) }}
              >
                <div className="health-component-header">
                  <h4>{name}</h4>
                  <span
                    className="health-component-status"
                    style={{ color: getStatusColor(component.status) }}
                  >
                    {getStatusIcon(component.status)} {component.status?.toUpperCase()}
                    {component.is_critical && ' *'}
                  </span>
                </div>
                <p className="health-component-details">{component.details}</p>
                <div className="health-component-meta">
                  {component.response_time_ms && (
                    <span>Response: {component.response_time_ms?.toFixed(2)}ms</span>
                  )}
                  {component.metadata && Object.keys(component.metadata).length > 0 && (
                    <button
                      onClick={() => console.log(component.metadata)}
                      className="health-metadata-button"
                    >
                      View Metadata
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Health History */}
      {historyData.length > 0 && (
        <div className="health-history">
          <h3>Health History</h3>
          <div className="health-history-list">
            {historyData.map((entry, index) => (
              <div key={index} className="health-history-entry">
                <span className="health-history-time">
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>
                <span
                  className="health-history-status"
                  style={{ color: getStatusColor(entry.status) }}
                >
                  {getStatusIcon(entry.status)} {entry.status?.toUpperCase()}
                </span>
                <span className="health-history-response">
                  {entry.response_time_ms?.toFixed(0)}ms
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="health-footer">* Critical component</p>
    </div>
  );
}

export default HealthPage;
