/**
 * Monitoring Hook
 *
 * Custom hook for fetching monitoring status and alerts from the API.
 */
import { useState, useEffect, useCallback } from 'react';

const API_BASE = '/api/v1/monitoring';

/**
 * Fetch monitoring status from the API
 */
async function fetchMonitoringStatus() {
  const response = await fetch(`${API_BASE}/status`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch monitoring status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch active alerts from the API
 */
async function fetchActiveAlerts(limit = 50) {
  const response = await fetch(`${API_BASE}/alerts?active_only=true&limit=${limit}`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch alerts: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Acknowledge an alert
 */
async function acknowledgeAlert(alertId) {
  const response = await fetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to acknowledge alert: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Resolve an alert
 */
async function resolveAlert(alertId) {
  const response = await fetch(`${API_BASE}/alerts/${alertId}/resolve`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to resolve alert: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Custom hook for monitoring data
 *
 * @param {Object} options - Hook options
 * @param {number} options.pollInterval - Polling interval in milliseconds (default: 30000)
 * @param {boolean} options.enabled - Whether to enable polling (default: true)
 */
function useMonitoring(options = {}) {
  const {
    pollInterval = 30000, // 30 seconds default
    enabled = true,
  } = options;

  const [status, setStatus] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Fetch monitoring data
  const fetchMonitoringData = useCallback(async () => {
    if (!enabled) return;

    try {
      setIsLoading(true);
      setError(null);

      // Fetch status and alerts in parallel
      const [statusData, alertsData] = await Promise.all([
        fetchMonitoringStatus().catch(err => {
          console.error('Failed to fetch status:', err);
          return null;
        }),
        fetchActiveAlerts(50).catch(err => {
          console.error('Failed to fetch alerts:', err);
          return { alerts: [] };
        }),
      ]);

      if (statusData) {
        setStatus(statusData);
      }

      if (alertsData && alertsData.alerts) {
        setAlerts(alertsData.alerts);
      }

      setLastUpdate(new Date());
    } catch (err) {
      console.error('Error fetching monitoring data:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [enabled]);

  // Acknowledge an alert
  const acknowledgeAlertById = useCallback(async (alertId) => {
    try {
      const result = await acknowledgeAlert(alertId);
      // Refresh data after acknowledging
      await fetchMonitoringData();
      return result;
    } catch (err) {
      console.error('Error acknowledging alert:', err);
      throw err;
    }
  }, [fetchMonitoringData]);

  // Resolve an alert
  const resolveAlertById = useCallback(async (alertId) => {
    try {
      const result = await resolveAlert(alertId);
      // Refresh data after resolving
      await fetchMonitoringData();
      return result;
    } catch (err) {
      console.error('Error resolving alert:', err);
      throw err;
    }
  }, [fetchMonitoringData]);

  // Initial fetch and polling
  useEffect(() => {
    if (!enabled) return;

    fetchMonitoringData();

    const interval = setInterval(fetchMonitoringData, pollInterval);

    return () => clearInterval(interval);
  }, [fetchMonitoringData, pollInterval, enabled]);

  // Refresh function for manual refresh
  const refresh = useCallback(() => {
    return fetchMonitoringData();
  }, [fetchMonitoringData]);

  return {
    status,
    alerts,
    activeAlertsCount: alerts.length,
    isLoading,
    error,
    lastUpdate,
    acknowledgeAlert: acknowledgeAlertById,
    resolveAlert: resolveAlertById,
    refresh,
  };
}

export default useMonitoring;
