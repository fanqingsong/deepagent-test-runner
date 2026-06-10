/**
 * Monitoring Page Component
 *
 * Comprehensive system monitoring dashboard with:
 * - Current system status display
 * - AI-generated summary
 * - Metric cards with trend indicators
 * - Alert center
 * - Historical data visualization
 *
 * Follows IBM Carbon design system.
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getAlerts, getMonitoringStatus, getMonitoringReports, acknowledgeAlert, resolveAlert } from '../api';
import SystemStatusRadar from '../components/SystemStatusRadar';
import './MonitoringPage.css';

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
 * Format timestamp for display
 */
function formatTimestamp(isoStr) {
  if (!isoStr) return 'N/A';
  const d = new Date(isoStr);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Format relative time
 */
function formatRelativeTime(isoStr) {
  if (!isoStr) return 'N/A';
  const d = new Date(isoStr);
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 360000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.floor(diffHours / 24)}d ago`;
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
 * MonitoringPage Component
 */
function MonitoringPage() {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [reports, setReports] = useState([]);
  const [historyDays, setHistoryDays] = useState(7);
  const [showAlerts, setShowAlerts] = useState(true);

  // Fetch monitoring status
  const fetchStatus = async () => {
    try {
      const response = await getMonitoringStatus();
      console.log('Status response:', response);
      setStatus(response || {});
    } catch (error) {
      console.error('Failed to fetch monitoring status:', error);
      setStatus({});
    }
  };

  // Fetch alerts
  const fetchAlerts = async () => {
    try {
      const response = await getAlerts({ limit: 20 });
      console.log('Alerts response:', response);
      // Handle both possible response formats
      const alerts = response.alerts || response || [];
      setAlerts(Array.isArray(alerts) ? alerts : []);
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
      setAlerts([]);
    }
  };

  // Fetch reports
  const fetchReports = async () => {
    try {
      const hours = historyDays * 24;
      const response = await getMonitoringReports(hours, 50);
      console.log('Reports response:', response);
      // Handle both possible response formats
      const reports = response.reports || response || [];
      setReports(Array.isArray(reports) ? reports : []);
    } catch (error) {
      console.error('Failed to fetch reports:', error);
      setReports([]);
    }
  };

  // Acknowledge alert
  const handleAcknowledgeAlert = async (alertId) => {
    try {
      await acknowledgeAlert(alertId);
      // Refresh alerts
      await fetchAlerts();
      await fetchStatus();
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  };

  // Resolve alert
  const handleResolveAlert = async (alertId) => {
    try {
      await resolveAlert(alertId);
      // Refresh alerts
      await fetchAlerts();
      await fetchStatus();
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  // Initial data load
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      await Promise.all([
        fetchStatus(),
        fetchAlerts(),
        fetchReports(),
      ]);
      setIsLoading(false);
    };

    loadData();
  }, [historyDays]);

  if (isLoading) {
    return (
      <div className="monitoring-page loading">
        <div className="monitoring-header">
          <h1>System Monitoring</h1>
        </div>
        <div className="monitoring-loading">
          <div className="spinner"></div>
          <p>Loading monitoring data...</p>
        </div>
      </div>
    );
  }

  const currentStatus = status?.status || 'unknown';
  const activeAlertsCount = alerts.filter(a => !a.acknowledged).length;

  // Extract metrics
  const metrics = status?.metrics || {};
  const testMetrics = metrics.test_execution?.test_runs_24h || {};
  const llmMetrics = metrics.llm_performance?.token_usage_24h || {};
  const resourceMetrics = metrics.resources || {};

  return (
    <div className="monitoring-page">
      {/* Header */}
      <div className="monitoring-header">
        <h1>System Monitoring</h1>
        <div className="monitoring-controls">
          <select
            value={historyDays}
            onChange={(e) => setHistoryDays(Number(e.target.value))}
            className="monitoring-select"
          >
            <option value={1}>Last 24 hours</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
          </select>
        </div>
      </div>

      {/* System Status Radar Chart */}
      <SystemStatusRadar metrics={status?.metrics} size="medium" />

      {/* Status Summary Banner */}
      <div className={`status-summary-banner ${getStatusColor(currentStatus)}`}>
        <div className="status-summary-content">
          <div className="status-summary-text">
            <strong>Overall Status: {currentStatus.charAt(0).toUpperCase() + currentStatus.slice(1)}</strong>
            <span className="status-updated">
              Last checked: {formatRelativeTime(status?.last_check)}
            </span>
          </div>
          {activeAlertsCount > 0 && (
            <div className="status-alerts-count">
              {activeAlertsCount} active alert{activeAlertsCount !== 1 ? 's' : ''}
            </div>
          )}
        </div>
      </div>

      {/* AI Summary */}
      {status?.report_summary && (
        <div className="ai-summary-card">
          <div className="card-header">
            <h2>🤖 AI Analysis</h2>
            <span className="ai-badge">Generated by DeepAgent</span>
          </div>
          <AIReportDisplay content={status.report_summary} />
        </div>
      )}

      {/* Metrics Grid */}
      <div className="metrics-grid">
        {/* Test Execution Card */}
        <div className="metric-card">
          <div className="metric-header">
            <h3>Test Execution</h3>
            <span className="metric-icon">🧪</span>
          </div>
          <div className="metric-value">
            {testMetrics.total || 0}
          </div>
          <div className="metric-label">Test runs (24h)</div>
          <div className="metric-details">
            <div className="metric-detail">
              <span className="detail-label">Passed:</span>
              <span className="detail-value green">
                {testMetrics.passed || 0} ({Math.round(testMetrics.pass_rate * 100)}%)
              </span>
            </div>
            <div className="metric-detail">
              <span className="detail-label">Failed:</span>
              <span className="detail-value red">
                {testMetrics.failed || 0}
              </span>
            </div>
            <div className="metric-detail">
              <span className="detail-label">Avg duration:</span>
              <span className="detail-value">
                {testMetrics.avg_duration_ms || 0}ms
              </span>
            </div>
          </div>
        </div>

        {/* LLM Performance Card */}
        <div className="metric-card">
          <div className="metric-header">
            <h3>LLM Performance</h3>
            <span className="metric-icon">🤖</span>
          </div>
          <div className="metric-value">
            {Math.round((llmMetrics.total_tokens || 0) / 1000)}K
          </div>
          <div className="metric-label">Tokens used (24h)</div>
          <div className="metric-details">
            <div className="metric-detail">
              <span className="detail-label">Est. cost:</span>
              <span className="detail-value">
                ${llmMetrics.estimated_cost_usd || 0}
              </span>
            </div>
            <div className="metric-detail">
              <span className="detail-label">Avg response:</span>
              <span className="detail-value">
                {metrics.llm_performance?.avg_response_time_ms || 0}ms
              </span>
            </div>
            <div className="metric-detail">
              <span className="detail-label">Calls:</span>
              <span className="detail-value">
                {Object.values(llmMetrics.by_agent || {}).reduce((sum, agent) => sum + (agent.tokens || 0), 0)}
              </span>
            </div>
          </div>
        </div>

        {/* Resources Card */}
        <div className="metric-card">
          <div className="metric-header">
            <h3>System Resources</h3>
            <span className="metric-icon">💻</span>
          </div>
          <div className="metric-value green">
            Healthy
          </div>
          <div className="metric-label">Overall status</div>
          <div className="metric-details">
            <div className="metric-detail">
              <span className="detail-label">Database:</span>
              <span className={`detail-value ${resourceMetrics.database?.status === 'healthy' ? 'green' : 'red'}`}>
                {resourceMetrics.database?.status || 'unknown'}
              </span>
            </div>
            <div className="metric-detail">
              <span className="detail-label">Temporal:</span>
              <span className="detail-value">
                {resourceMetrics.temporal?.status || 'unknown'}
              </span>
            </div>
            <div className="metric-detail">
              <span className="detail-label">Redis:</span>
              <span className="detail-value">
                {resourceMetrics.redis?.status || 'unknown'}
              </span>
            </div>
          </div>
        </div>

        {/* User Activity Card */}
        <div className="metric-card">
          <div className="metric-header">
            <h3>User Activity</h3>
            <span className="metric-icon">👥</span>
          </div>
          <div className="metric-value">
            {metrics.user_activity?.active_users_24h || 0}
          </div>
          <div className="metric-label">Active users (24h)</div>
          <div className="metric-details">
            <div className="metric-detail">
              <span className="detail-label">Total users:</span>
              <span className="detail-value">
                {metrics.user_activity?.total_users || 0}
              </span>
            </div>
            <div className="metric-detail">
              <span className="detail-label">Top features:</span>
              <span className="detail-value">
                {(metrics.user_activity?.top_features || []).slice(0, 2).join(', ')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Alerts Section */}
      <div className="alerts-section">
        <div className="section-header">
          <h2>Alerts</h2>
          <button
            className="btn-tertiary"
            onClick={() => setShowAlerts(!showAlerts)}
          >
            {showAlerts ? 'Hide' : 'Show'}
          </button>
        </div>

        {showAlerts && (
          <div className="alerts-list">
            {alerts.length === 0 ? (
              <div className="alerts-empty">No alerts</div>
            ) : (
              alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`alert-card ${alert.severity} ${alert.acknowledged ? 'acknowledged' : ''}`}
                >
                  <div className="alert-header">
                    <span className={`alert-severity ${alert.severity}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className="alert-type">{alert.alert_type}</span>
                    <span className="alert-time">
                      {formatRelativeTime(alert.created_at)}
                    </span>
                  </div>
                  <div className="alert-title">{alert.title}</div>
                  <div className="alert-description">{alert.description}</div>
                  {!alert.acknowledged && (
                    <div className="alert-actions">
                      <button
                        className="btn-primary"
                        onClick={() => handleAcknowledgeAlert(alert.id)}
                      >
                        Acknowledge
                      </button>
                      <button
                        className="btn-secondary"
                        onClick={() => handleResolveAlert(alert.id)}
                      >
                        Resolve
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Historical Reports Section */}
      <div className="reports-section">
        <div className="section-header">
          <h2>Historical Reports</h2>
          <span className="section-count">{reports.length} reports</span>
        </div>

        <div className="reports-list">
          {reports.map((report) => (
            <div key={report.id} className="report-card">
              <div className="report-header">
                <span className={`report-status ${getStatusColor(report.status)}`}>
                  {report.status.charAt(0).toUpperCase() + report.status.slice(1)}
                </span>
                <span className="report-time">
                  {formatTimestamp(report.check_time)}
                </span>
              </div>
              {report.report_summary && (
                <div className="report-summary">{report.report_summary}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default MonitoringPage;
