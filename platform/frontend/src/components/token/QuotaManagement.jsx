import { useState, useEffect, useCallback } from 'react';
import {
  getUserQuota,
  updateUserQuota,
  resetUserQuota,
  getQuotaConfig,
  updateQuotaConfig,
} from '../../api/api-token';
import AlertBanner from '../AlertBanner';
import Modal from '../Modal';
import './QuotaManagement.css';

function formatNumber(num) {
  if (!num && num !== 0) return '0';
  return num.toLocaleString();
}

function formatPercentage(value, total) {
  if (!total || total === 0) return '0%';
  return `${Math.round((value / total) * 100)}%`;
}

// Quota Usage Bar Component
function QuotaUsageBar({ label, used, total, color = '#0f62fe' }) {
  const percentage = total > 0 ? Math.min(100, (used / total) * 100) : 0;

  return (
    <div className="quota-usage-bar">
      <div className="quota-bar-header">
        <span className="quota-bar-label">{label}</span>
        <span className="quota-bar-value">
          {formatNumber(used)} / {formatNumber(total)}
        </span>
      </div>
      <div className="quota-bar-track">
        <div
          className="quota-bar-fill"
          style={{ width: `${percentage}%`, backgroundColor: color }}
        />
      </div>
      <div className="quota-bar-percentage">{formatPercentage(used, total)}</div>
    </div>
  );
}

// User Quota Card Component
function UserQuotaCard({ quota, onEdit, onReset }) {
  const usagePercentage = quota.used / quota.limit;

  return (
    <div className="user-quota-card">
      <div className="card-header">
        <h3 className="card-title">{quota.user_name || quota.user_id}</h3>
        <span className={`quota-status ${usagePercentage >= 0.9 ? 'critical' : usagePercentage >= 0.75 ? 'warning' : 'normal'}`}>
          {usagePercentage >= 0.9 ? 'Critical' : usagePercentage >= 0.75 ? 'Warning' : 'Normal'}
        </span>
      </div>

      <QuotaUsageBar
        label="Tokens Used"
        used={quota.used}
        total={quota.limit}
      />

      <div className="card-details">
        <div className="detail-item">
          <span className="detail-label">Period</span>
          <span className="detail-value">{quota.period}</span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Resets</span>
          <span className="detail-value">
            {new Date(quota.resets_at).toLocaleDateString()}
          </span>
        </div>
        <div className="detail-item">
          <span className="detail-label">Time Remaining</span>
          <span className="detail-value">
            {Math.ceil((new Date(quota.resets_at) - new Date()) / (1000 * 60 * 60 * 24))} days
          </span>
        </div>
      </div>

      <div className="card-actions">
        <button className="action-button" onClick={() => onEdit(quota)}>
          Edit Quota
        </button>
        <button className="action-button reset" onClick={() => onReset(quota)}>
          Reset Quota
        </button>
      </div>
    </div>
  );
}

// Quota Form Component
function QuotaForm({ quota, onSave, onCancel }) {
  const [formData, setFormData] = useState({
    user_id: quota?.user_id || '',
    limit: quota?.limit || 100000,
    period: quota?.period || 'monthly',
    resets_at: quota?.resets_at || '',
    description: quota?.description || '',
  });

  const [errors, setErrors] = useState({});

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: null }));
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.user_id.trim()) {
      newErrors.user_id = 'User ID is required';
    }
    if (!formData.limit || formData.limit <= 0) {
      newErrors.limit = 'Limit must be greater than 0';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      onSave(formData);
    }
  };

  return (
    <form className="quota-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label className="form-label">User ID *</label>
        <input
          type="text"
          className={`form-input ${errors.user_id ? 'error' : ''}`}
          value={formData.user_id}
          onChange={(e) => handleChange('user_id', e.target.value)}
          placeholder="Enter user ID"
          disabled={!!quota?.user_id}
        />
        {errors.user_id && <span className="form-error">{errors.user_id}</span>}
      </div>

      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Token Limit *</label>
          <input
            type="number"
            className={`form-input ${errors.limit ? 'error' : ''}`}
            value={formData.limit}
            onChange={(e) => handleChange('limit', parseInt(e.target.value) || 0)}
            min="0"
          />
          {errors.limit && <span className="form-error">{errors.limit}</span>}
        </div>

        <div className="form-group">
          <label className="form-label">Period *</label>
          <select
            className="form-select"
            value={formData.period}
            onChange={(e) => handleChange('period', e.target.value)}
          >
            <option value="hourly">Hourly</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Reset Date</label>
        <input
          type="date"
          className="form-input"
          value={formData.resets_at}
          onChange={(e) => handleChange('resets_at', e.target.value)}
        />
      </div>

      <div className="form-group">
        <label className="form-label">Description</label>
        <textarea
          className="form-textarea"
          value={formData.description}
          onChange={(e) => handleChange('description', e.target.value)}
          placeholder="Enter quota description"
          rows={3}
        />
      </div>

      <div className="form-actions">
        <button type="button" className="cancel-button" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="submit-button">
          Save Quota
        </button>
      </div>
    </form>
  );
}

// Quota Configuration Component
function QuotaConfiguration({ config, onSave, onClose }) {
  const [formData, setFormData] = useState({
    default_limit: config?.default_limit || 100000,
    default_period: config?.default_period || 'monthly',
    auto_reset: config?.auto_reset || true,
    reset_day_of_month: config?.reset_day_of_month || 1,
    enforce_hard_limit: config?.enforce_hard_limit || true,
    warning_threshold: config?.warning_threshold || 80,
  });

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="quota-configuration">
      <h3 className="config-title">Global Quota Configuration</h3>
      <form className="config-form" onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Default Limit</label>
            <input
              type="number"
              className="form-input"
              value={formData.default_limit}
              onChange={(e) => handleChange('default_limit', parseInt(e.target.value) || 0)}
              min="0"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Default Period</label>
            <select
              className="form-select"
              value={formData.default_period}
              onChange={(e) => handleChange('default_period', e.target.value)}
            >
              <option value="hourly">Hourly</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
        </div>

        <div className="form-group checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={formData.auto_reset}
              onChange={(e) => handleChange('auto_reset', e.target.checked)}
            />
            <span>Auto-reset quotas</span>
          </label>
        </div>

        {formData.auto_reset && (
          <div className="form-group">
            <label className="form-label">Reset Day of Month</label>
            <input
              type="number"
              className="form-input"
              value={formData.reset_day_of_month}
              onChange={(e) => handleChange('reset_day_of_month', parseInt(e.target.value) || 1)}
              min="1"
              max="28"
            />
          </div>
        )}

        <div className="form-group checkbox-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={formData.enforce_hard_limit}
              onChange={(e) => handleChange('enforce_hard_limit', e.target.checked)}
            />
            <span>Enforce hard limit (block when exceeded)</span>
          </label>
        </div>

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

// Reset Confirmation Component
function ResetConfirmation({ quota, onConfirm, onCancel }) {
  return (
    <div className="reset-confirmation">
      <h3 className="confirmation-title">Reset User Quota</h3>
      <p className="confirmation-message">
        Are you sure you want to reset the quota for "{quota?.user_name || quota?.user_id}"?
        This will set the used tokens back to 0.
      </p>
      <div className="confirmation-actions">
        <button className="cancel-button" onClick={onCancel}>
          Cancel
        </button>
        <button className="danger-button" onClick={onConfirm}>
          Reset Quota
        </button>
      </div>
    </div>
  );
}

// Main Quota Management Component
function QuotaManagement() {
  const [quotas, setQuotas] = useState([]);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showEditForm, setShowEditForm] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [selectedQuota, setSelectedQuota] = useState(null);

  const fetchQuotas = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [quotasData, configData] = await Promise.all([
        // Mock data - in real implementation, this would fetch from API
        Promise.resolve([
          { user_id: 'user1', user_name: 'John Doe', limit: 100000, used: 75000, period: 'monthly', resets_at: '2026-07-01' },
          { user_id: 'user2', user_name: 'Jane Smith', limit: 50000, used: 12000, period: 'monthly', resets_at: '2026-07-01' },
          { user_id: 'user3', user_name: 'Bob Johnson', limit: 200000, used: 180000, period: 'monthly', resets_at: '2026-07-01' },
        ]),
        getQuotaConfig(),
      ]);

      setQuotas(quotasData);
      setConfig(configData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQuotas();
  }, [fetchQuotas]);

  const handleEdit = async (formData) => {
    try {
      await updateUserQuota(selectedQuota.user_id, formData);
      setShowEditForm(false);
      setSelectedQuota(null);
      await fetchQuotas();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleReset = async () => {
    try {
      await resetUserQuota(selectedQuota.user_id);
      setShowResetConfirm(false);
      setSelectedQuota(null);
      await fetchQuotas();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleConfigSave = async (formData) => {
    try {
      await updateQuotaConfig(formData);
      setShowConfig(false);
      await fetchQuotas();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="quota-management">
        <div className="loading-state">Loading quota data...</div>
      </div>
    );
  }

  return (
    <div className="quota-management">
      <div className="page-header">
        <h2 className="page-title">Quota Management</h2>
        <button className="config-button" onClick={() => setShowConfig(true)}>
          Configure Settings
        </button>
      </div>

      {error && (
        <AlertBanner
          message={`Error: ${error}`}
          type="error"
          onDismiss={() => setError(null)}
        />
      )}

      <div className="quota-summary">
        <div className="summary-item">
          <span className="summary-label">Total Users</span>
          <span className="summary-value">{quotas.length}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Total Allocated</span>
          <span className="summary-value">
            {formatNumber(quotas.reduce((sum, q) => sum + q.limit, 0))}
          </span>
        </div>
        <div className="summary-item">
          <span className="summary-label">Total Used</span>
          <span className="summary-value">
            {formatNumber(quotas.reduce((sum, q) => sum + q.used, 0))}
          </span>
        </div>
      </div>

      <div className="quota-cards">
        {quotas.map((quota) => (
          <UserQuotaCard
            key={quota.user_id}
            quota={quota}
            onEdit={(q) => {
              setSelectedQuota(q);
              setShowEditForm(true);
            }}
            onReset={(q) => {
              setSelectedQuota(q);
              setShowResetConfirm(true);
            }}
          />
        ))}
      </div>

      {/* Edit Form Modal */}
      <Modal
        isOpen={showEditForm}
        onClose={() => {
          setShowEditForm(false);
          setSelectedQuota(null);
        }}
        title="Edit User Quota"
      >
        <QuotaForm
          quota={selectedQuota}
          onSubmit={handleEdit}
          onCancel={() => {
            setShowEditForm(false);
            setSelectedQuota(null);
          }}
        />
      </Modal>

      {/* Reset Confirmation Modal */}
      <Modal
        isOpen={showResetConfirm}
        onClose={() => {
          setShowResetConfirm(false);
          setSelectedQuota(null);
        }}
        title="Reset Quota"
      >
        <ResetConfirmation
          quota={selectedQuota}
          onConfirm={handleReset}
          onCancel={() => {
            setShowResetConfirm(false);
            setSelectedQuota(null);
          }}
        />
      </Modal>

      {/* Configuration Modal */}
      <Modal
        isOpen={showConfig}
        onClose={() => setShowConfig(false)}
        title="Quota Configuration"
      >
        <QuotaConfiguration
          config={config}
          onSave={handleConfigSave}
          onClose={() => setShowConfig(false)}
        />
      </Modal>
    </div>
  );
}

export default QuotaManagement;
