import { useState, useEffect, useCallback } from 'react';
import {
  getAlerts,
  acknowledgeAlert,
  getAlertConfig,
  updateAlertConfig,
} from '../../api/api-token';
import AlertBanner from '../AlertBanner';
import Modal from '../Modal';
import './AlertManagement.css';

const SEVERITY_LABELS = {
  info: 'Info',
  warning: 'Warning',
  critical: 'Critical',
  emergency: 'Emergency',
};

const SEVERITY_COLORS = {
  info: '#0f62fe',
  warning: '#f1c21b',
  critical: '#da1e28',
  emergency: '#da1e28',
};

const STATUS_LABELS = {
  active: 'Active',
  acknowledged: 'Acknowledged',
  resolved: 'Resolved',
};

function formatTime(isoStr) {
  if (!isoStr) return '-';
  const d = new Date(isoStr);
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// Severity Badge Component
function SeverityBadge({ severity }) {
  return (
    <span className="severity-badge" style={{ backgroundColor: `${SEVERITY_COLORS[severity]}20`, color: SEVERITY_COLORS[severity] }}>
      {SEVERITY_LABELS[severity] || severity}
    </span>
  );
}

// Status Badge Component
function StatusBadge({ status }) {
  return <span className={`status-badge ${status}`}>{STATUS_LABELS[status] || status}</span>;
}

// Alert Card Component
function AlertCard({ alert, onAcknowledge, onView }) {
  const severity = alert.severity || 'info';

  return (
    <div className={`alert-card severity-${severity}`}>
      <div className="alert-header">
        <div className="alert-title-row">
          <SeverityBadge severity={severity} />
          <h3 className="alert-title">{alert.title}</h3>
        </div>
        <StatusBadge status={alert.status} />
      </div>

      <p className="alert-message">{alert.message}</p>

      {alert.metadata && (
        <div className="alert-metadata">
          {alert.metadata.usage && (
            <div className="metadata-item">
              <span className="metadata-label">Usage</span>
              <span className="metadata-value">{alert.metadata.usage}</span>
            </div>
          )}
          {alert.metadata.threshold && (
            <div className="metadata-item">
              <span className="metadata-label">Threshold</span>
              <span className="metadata-value">{alert.metadata.threshold}%</span>
            </div>
          )}
          {alert.metadata.budget && (
            <div className="metadata-item">
              <span className="metadata-label">Budget</span>
              <span className="metadata-value">{alert.metadata.budget}</span>
            </div>
          )}
        </div>
      )}

      <div className="alert-footer">
        <span className="alert-time">{formatTime(alert.created_at)}</span>
        <div className="alert-actions">
          <button className="action-button" onClick={() => onView(alert)}>
            View Details
          </button>
          {alert.status === 'active' && (
            <button className="action-button acknowledge" onClick={() => onAcknowledge(alert)}>
              Acknowledge
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Alert History Component
function AlertHistory({ alerts, onSelect }) {
  const [filter, setFilter] = useState('all');

  const filteredAlerts = alerts.filter((alert) => {
    if (filter === 'all') return true;
    if (filter === 'active') return alert.status === 'active';
    if (filter === 'acknowledged') return alert.status === 'acknowledged';
    if (filter === 'resolved') return alert.status === 'resolved';
    return true;
  });

  return (
    <div className="alert-history">
      <div className="history-header">
        <h3 className="history-title">Alert History</h3>
        <select
          className="filter-select"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="all">All Alerts</option>
          <option value="active">Active</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      <div className="history-list">
        {filteredAlerts.map((alert) => (
          <div
            key={alert.id}
            className="history-item"
            onClick={() => onSelect(alert)}
          >
            <SeverityBadge severity={alert.severity} />
            <span className="history-message">{alert.title}</span>
            <span className="history-time">{formatTime(alert.created_at)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Alert Configuration Component
function AlertConfiguration({ config, onSave, onClose }) {
  const [formData, setFormData] = useState({
    enabled: config?.enabled ?? true,
    warning_threshold: config?.warning_threshold || 75,
    critical_threshold: config?.critical_threshold || 90,
    notification_channels: config?.notification_channels || ['email'],
    email_recipients: config?.email_recipients || '',
    webhook_url: config?.webhook_url || '',
    cooldown_minutes: config?.cooldown_minutes || 30,
  });

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleToggleChannel = (channel) => {
    setFormData((prev) => ({
      ...prev,
      notification_channels: prev.notification_channels.includes(channel)
        ? prev.notification_channels.filter((c) => c !== channel)
        : [...prev.notification_channels, channel],
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="alert-configuration">
      <h3 className="config-title">Alert Configuration</h3>
      <form className="config-form" onSubmit={handleSubmit}>
        <div className="form-group checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={formData.enabled}
              onChange={(e) => handleChange('enabled', e.target.checked)}
            />
            <span>Enable alerts</span>
          </label>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Warning Threshold (%)</label>
            <input
              type="number"
              className="form-input"
              value={formData.warning_threshold}
              onChange={(e) => handleChange('warning_threshold', parseInt(e.target.value) || 0)}
              min="0"
              max="100"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Critical Threshold (%)</label>
            <input
              type="number"
              className="form-input"
              value={formData.critical_threshold}
              onChange={(e) => handleChange('critical_threshold', parseInt(e.target.value) || 0)}
              min="0"
              max="100"
            />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Notification Channels</label>
          <div className="channel-toggles">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={formData.notification_channels.includes('email')}
                onChange={() => handleToggleChannel('email')}
              />
              <span>Email</span>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={formData.notification_channels.includes('webhook')}
                onChange={() => handleToggleChannel('webhook')}
              />
              <span>Webhook</span>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={formData.notification_channels.includes('sms')}
                onChange={() => handleToggleChannel('sms')}
              />
              <span>SMS</span>
            </label>
          </div>
        </div>

        {formData.notification_channels.includes('email') && (
          <div className="form-group">
            <label className="form-label">Email Recipients</label>
            <textarea
              className="form-textarea"
              value={formData.email_recipients}
              onChange={(e) => handleChange('email_recipients', e.target.value)}
              placeholder="Enter email addresses, comma-separated"
              rows={3}
            />
          </div>
        )}

        {formData.notification_channels.includes('webhook') && (
          <div className="form-group">
            <label className="form-label">Webhook URL</label>
            <input
              type="url"
              className="form-input"
              value={formData.webhook_url}
              onChange={(e) => handleChange('webhook_url', e.target.value)}
              placeholder="https://your-webhook-url.com"
            />
          </div>
        )}

        <div className="form-group">
          <label className="form-label">Cooldown Period (minutes)</label>
          <input
            type="number"
            className="form-input"
            value={formData.cooldown_minutes}
            onChange={(e) => handleChange('cooldown_minutes', parseInt(e.target.value) || 0)}
            min="0"
          />
          <span className="form-helper">Minimum time between similar alerts</span>
        </div>

        <div className="form-actions">
          <button type="button" className="cancel-button" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="submit-button">
            Save Configuration
          </button>
        </div>
      </form>
    </div>
  );
}

// Alert Details Component
function AlertDetails({ alert, onClose }) {
  if (!alert) return null;

  return (
    <div className="alert-details">
      <div className="details-header">
        <SeverityBadge severity={alert.severity} />
        <StatusBadge status={alert.status} />
      </div>

      <h2 className="details-title">{alert.title}</h2>
      <p className="details-message">{alert.message}</p>

      {alert.metadata && (
        <div className="details-metadata">
          <h4 className="metadata-title">Additional Information</h4>
          <div className="metadata-grid">
            {Object.entries(alert.metadata).map(([key, value]) => (
              <div key={key} className="metadata-item">
                <span className="metadata-label">{key}</span>
                <span className="metadata-value">{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="details-timeline">
        <h4 className="timeline-title">Timeline</h4>
        <div className="timeline-item">
          <span className="timeline-label">Created</span>
          <span className="timeline-time">{formatTime(alert.created_at)}</span>
        </div>
        {alert.acknowledged_at && (
          <div className="timeline-item">
            <span className="timeline-label">Acknowledged</span>
            <span className="timeline-time">{formatTime(alert.acknowledged_at)}</span>
          </div>
        )}
        {alert.resolved_at && (
          <div className="timeline-item">
            <span className="timeline-label">Resolved</span>
            <span className="timeline-time">{formatTime(alert.resolved_at)}</span>
          </div>
        )}
      </div>

      <div className="details-actions">
        <button className="close-button" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}

// Main Alert Management Component
function AlertManagement() {
  const [alerts, setAlerts] = useState([]);
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showConfig, setShowConfig] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [alertsData, configData] = await Promise.all([
        getAlerts({ status: 'active' }),
        getAlertConfig(),
      ]);

      setAlerts(alertsData.alerts || []);
      setActiveAlerts(alertsData.alerts?.filter((a) => a.status === 'active') || []);
      setConfig(configData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  const handleAcknowledge = async (alert) => {
    try {
      await acknowledgeAlert(alert.id);
      await fetchAlerts();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleConfigSave = async (formData) => {
    try {
      await updateAlertConfig(formData);
      setShowConfig(false);
      await fetchAlerts();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="alert-management">
        <div className="loading-state">Loading alerts...</div>
      </div>
    );
  }

  return (
    <div className="alert-management">
      <div className="page-header">
        <h2 className="page-title">Alert Management</h2>
        <button className="config-button" onClick={() => setShowConfig(true)}>
          Configure Alerts
        </button>
      </div>

      {error && (
        <AlertBanner
          message={`Error: ${error}`}
          type="error"
          onDismiss={() => setError(null)}
        />
      )}

      <div className="alerts-section">
        <h3 className="section-title">
          Active Alerts ({activeAlerts.length})
        </h3>

        {activeAlerts.length === 0 ? (
          <div className="empty-state">
            <p>No active alerts</p>
          </div>
        ) : (
          <div className="alerts-grid">
            {activeAlerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onAcknowledge={handleAcknowledge}
                onView={(a) => {
                  setSelectedAlert(a);
                  setShowDetails(true);
                }}
              />
            ))}
          </div>
        )}
      </div>

      <div className="history-section">
        <AlertHistory
          alerts={alerts}
          onSelect={(alert) => {
            setSelectedAlert(alert);
            setShowDetails(true);
          }}
        />
      </div>

      {/* Configuration Modal */}
      <Modal
        isOpen={showConfig}
        onClose={() => setShowConfig(false)}
        title="Alert Configuration"
      >
        <AlertConfiguration
          config={config}
          onSave={handleConfigSave}
          onClose={() => setShowConfig(false)}
        />
      </Modal>

      {/* Details Modal */}
      <Modal
        isOpen={showDetails}
        onClose={() => {
          setShowDetails(false);
          setSelectedAlert(null);
        }}
        title="Alert Details"
      >
        <AlertDetails
          alert={selectedAlert}
          onClose={() => {
            setShowDetails(false);
            setSelectedAlert(null);
          }}
        />
      </Modal>
    </div>
  );
}

export default AlertManagement;
