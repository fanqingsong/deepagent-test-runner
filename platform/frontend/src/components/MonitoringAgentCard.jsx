/**
 * Monitoring Agent Card Component
 *
 * Displays the current status of the AI Monitoring Agent on the Dashboard.
 * Follows the IBM Carbon design system.
 */

import React from 'react';
import useMonitoring from '../hooks/useMonitoring';
import './MonitoringAgentCard.css';

/**
 * Format a timestamp for display
 */
function formatTime(isoStr) {
  if (!isoStr) return '-';
  const d = new Date(isoStr);
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

/**
 * Get status color class
 */
function getStatusColor(status) {
  switch (status) {
    case 'critical':
      return 'red';
    case 'warning':
      return 'yellow';
    case 'normal':
    default:
      return 'green';
  }
}

/**
 * Get status icon
 */
function getStatusIcon(status) {
  switch (status) {
    case 'critical':
      return '🔴';
    case 'warning':
      return '⚠️';
    case 'normal':
    default:
      return '✅';
  }
}

/**
 * MonitoringAgentCard Component
 *
 * Shows:
 * - Agent status with icon
 * - Last check time
 * - Active alerts count
 * - Recent activity summary
 */
function MonitoringAgentCard({ className = '' }) {
  const { status, activeAlertsCount, isLoading, error, lastUpdate } = useMonitoring({
    pollInterval: 30000, // 30 seconds
    enabled: true,
  });

  const currentStatus = status?.status || 'unknown';
  const lastCheck = status?.last_check || null;

  if (error) {
    return (
      <div className={`stat-card monitoring-card error ${className}`}>
        <div className="stat-card-label">🤖 AI Monitoring Agent</div>
        <div className="stat-card-value red">
          ⚠️ Error
        </div>
        <div className="stat-card-sub">Failed to load status</div>
      </div>
    );
  }

  if (isLoading && !status) {
    return (
      <div className={`stat-card monitoring-card loading ${className}`}>
        <div className="stat-card-label">🤖 AI Monitoring Agent</div>
        <div className="stat-card-value">
          <span className="spinner" />
        </div>
        <div className="stat-card-sub">Loading...</div>
      </div>
    );
  }

  return (
    <div className={`stat-card monitoring-card ${className}`}>
      <div className="stat-card-label">
        🤖 AI Monitoring Agent
        {lastUpdate && (
          <span className="monitoring-last-update">
            Updated {formatTime(lastUpdate.toISOString())}
          </span>
        )}
      </div>

      <div className={`stat-card-value ${getStatusColor(currentStatus)}`}>
        {getStatusIcon(currentStatus)} {currentStatus.charAt(0).toUpperCase() + currentStatus.slice(1)}
      </div>

      <div className="stat-card-sub">
        Last check: {formatTime(lastCheck)}
      </div>

      {activeAlertsCount > 0 && (
        <div className="monitoring-alerts-badge">
          {activeAlertsCount} active alert{activeAlertsCount !== 1 ? 's' : ''}
        </div>
      )}

      {status?.report_summary && (
        <div className="monitoring-summary">
          {status.report_summary}
        </div>
      )}
    </div>
  );
}

export default MonitoringAgentCard;
