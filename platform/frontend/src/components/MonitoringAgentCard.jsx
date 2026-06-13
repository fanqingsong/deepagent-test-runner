/**
 * Monitoring Agent Card Component
 *
 * Displays the current status of the AI Monitoring Agent on the Dashboard.
 * Follows the IBM Carbon design system.
 */

import React from 'react';
import { useAuth } from '../contexts/AuthContext';
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
 * AI Report Display Component
 *
 * Parses and displays AI-generated monitoring reports in a formatted way.
 */
function AIReportDisplay({ content }) {
  // Parse JSON from markdown code blocks
  const parseReport = (text) => {
    try {
      // Remove markdown code blocks
      const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[1]);
      }
      // Try parsing as direct JSON
      return JSON.parse(text);
    } catch (e) {
      // If parsing fails, return raw text
      return { raw: text };
    }
  };

  const report = parseReport(content);

  // If raw text (parsing failed), display as is
  if (report.raw) {
    return <div className="ai-summary-content">{content}</div>;
  }

  // Get status color
  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'critical': return '#da1e28';
      case 'warning': return '#f1c21b';
      case 'normal': return '#24a148';
      default: return '#6f6f6f';
    }
  };

  const getStatusLabel = (status) => {
    switch (status.toLowerCase()) {
      case 'critical': return 'Critical';
      case 'warning': return 'Warning';
      case 'normal': return 'Normal';
      default: return status;
    }
  };

  return (
    <div className="ai-report-formatted">
      {/* Status Badge */}
      {report.status && (
        <div className="ai-status-badge" style={{ backgroundColor: getStatusColor(report.status) }}>
          {getStatusLabel(report.status)}
        </div>
      )}

      {/* Summary */}
      {report.summary && (
        <div className="ai-section">
          <h4>📋 Summary</h4>
          <p>{report.summary}</p>
        </div>
      )}

      {/* Highlights */}
      {report.highlights && report.highlights.length > 0 && (
        <div className="ai-section">
          <h4>🎯 Key Findings</h4>
          <ul className="ai-list">
            {report.highlights.map((highlight, index) => (
              <li key={index} className={highlight.startsWith('✓') ? 'ai-positive' : 'ai-warning'}>
                {highlight}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Trends */}
      {report.trends && (report.trends.improving?.length > 0 || report.trends.concerning?.length > 0) && (
        <div className="ai-section">
          <h4>📈 Trends</h4>
          {report.trends.improving && report.trends.improving.length > 0 && report.trends.improving[0] !== 'None identified' && (
            <div className="ai-trend-group">
              <strong>Improving:</strong>
              <ul className="ai-list">
                {report.trends.improving.map((trend, index) => (
                  <li key={`imp-${index}`} className="ai-positive">{trend}</li>
                ))}
              </ul>
            </div>
          )}
          {report.trends.concerning && report.trends.concerning.length > 0 && report.trends.concerning[0] !== 'None identified' && (
            <div className="ai-trend-group">
              <strong>Concerning:</strong>
              <ul className="ai-list">
                {report.trends.concerning.map((trend, index) => (
                  <li key={`con-${index}`} className="ai-warning">{trend}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations && report.recommendations.length > 0 && (
        <div className="ai-section">
          <h4>💡 Recommendations</h4>
          <ol className="ai-ordered-list">
            {report.recommendations.map((rec, index) => (
              <li key={index}>{rec}</li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

/**
 * MonitoringAgentCard Component
 *
 * Shows:
 * - Agent status with icon
 * - Last check time
 * - Active alerts count
 * - AI-generated analysis summary
 */
function MonitoringAgentCard({ className = '' }) {
  const { isAuthenticated } = useAuth();

  const { status, activeAlertsCount, isLoading, error, lastUpdate } = useMonitoring({
    pollInterval: 30000, // 30 seconds
    enabled: isAuthenticated, // Only poll when authenticated
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
          <AIReportDisplay content={status.report_summary} />
        </div>
      )}
    </div>
  );
}

export default MonitoringAgentCard;
