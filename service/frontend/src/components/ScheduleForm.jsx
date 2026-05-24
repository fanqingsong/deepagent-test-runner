import { useState, useEffect } from 'react';
import authService from '../services/authService';
import { getTestSuites } from '../api';
import './ScheduleForm.css';

export default function ScheduleForm({ onScheduleCreated, editingSchedule, onCancel }) {
  const [tests, setTests] = useState([]);
  const [suites, setSuites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const buildHttpErrorMessage = async (response, fallback) => {
    const status = response?.status;
    const statusText = response?.statusText || '';

    let bodyText = '';
    try {
      bodyText = await response.text();
    } catch {
      bodyText = '';
    }

    let detail = '';
    if (bodyText) {
      try {
        const json = JSON.parse(bodyText);
        detail =
          json?.detail ||
          json?.error ||
          json?.message ||
          (typeof json === 'string' ? json : '') ||
          bodyText;
      } catch {
        detail = bodyText;
      }
    }

    const normalized = (detail || '').toString().trim();
    const base = fallback || 'Request failed';
    const suffixParts = [
      typeof status === 'number' ? `HTTP ${status}` : null,
      statusText ? statusText : null,
      normalized ? normalized : null,
    ].filter(Boolean);

    return suffixParts.length ? `${base} (${suffixParts.join(' - ')})` : base;
  };

  const getSafeAuthHeaders = () => {
    const token = typeof authService?.getAccessToken === 'function' ? authService.getAccessToken() : null;
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
    return typeof authService?.getAuthHeaders === 'function' ? authService.getAuthHeaders() : {};
  };

  const ensureAuthOrRedirect = async () => {
    if (!authService?.isAuthenticated?.()) {
      window.location.hash = 'login';
      throw new Error('Not logged in or session expired, please log in again');
    }
    try {
      await authService.ensureValidToken();
    } catch {
      window.location.hash = 'login';
      throw new Error('Session expired, please log in again');
    }
  };

  const [formData, setFormData] = useState({
    name: '',
    schedule_type: 'single',
    test_definition_id: null,
    test_suite_id: null,
    tag_filter: null,
    cron_expression: '0 * * * *',
    timezone: 'Asia/Shanghai',
    environment_overrides: {},
    is_active: true,
    allow_concurrent: false,
    max_retries: 3,
    retry_interval_seconds: 60
  });
  const [successMessage, setSuccessMessage] = useState(null);

  // Get validation message
  const getValidationMessage = () => {
    switch (formData.schedule_type) {
      case 'single':
        return 'Please select a test case';
      case 'suite':
        return 'Please enter test suite ID';
      case 'tag_filter':
        return 'Please enter tag filter condition';
      default:
        return 'Please complete required fields';
    }
  };

  // Validate form
  const isFormValid = () => {
    switch (formData.schedule_type) {
      case 'single':
        return formData.test_definition_id !== null;
      case 'suite':
        return formData.test_suite_id !== null;
      case 'tag_filter':
        return formData.tag_filter && formData.tag_filter.trim() !== '';
      default:
        return false;
    }
  };

  useEffect(() => {
    console.log('ScheduleForm - Component mounted/updated');
    loadTests();
    loadSuites();
    if (editingSchedule) {
      setFormData({
        name: editingSchedule.name || '',
        schedule_type: editingSchedule.schedule_type || 'single',
        test_definition_id: editingSchedule.test_definition_id || null,
        test_suite_id: editingSchedule.test_suite_id || null,
        tag_filter: editingSchedule.tag_filter || null,
        cron_expression: editingSchedule.cron_expression || '0 * * * *',
        timezone: editingSchedule.timezone || 'Asia/Shanghai',
        environment_overrides: editingSchedule.environment_overrides || {},
        is_active: editingSchedule.is_active !== undefined ? editingSchedule.is_active : true,
        allow_concurrent: editingSchedule.allow_concurrent || false,
        max_retries: editingSchedule.max_retries || 3,
        retry_interval_seconds: editingSchedule.retry_interval_seconds || 60
      });
    }
  }, [editingSchedule]);

  const loadTests = async () => {
    try {
      await ensureAuthOrRedirect();
      const response = await fetch(`${window.location.origin}/api/v1/test-definitions/`, {
        headers: getSafeAuthHeaders()
      });
      if (response.status === 401) {
        window.location.hash = 'login';
        throw new Error('Session expired, please log in again');
      }
      if (!response.ok) {
        const msg = await buildHttpErrorMessage(response, 'Failed to load test cases');
        if (response.status === 403) {
          throw new Error(`${msg}\n(Request missing Authorization header, or token validation failed/invalid format)`);
        }
        throw new Error(msg);
      }
      const data = await response.json();
      setTests(data.items || data);
    } catch (err) {
      setError(err.message);
    }
  };

  const loadSuites = async () => {
    try {
      const data = await getTestSuites();
      setSuites(data);
    } catch (err) {
      // Non-critical — suites list is optional
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Add debug logs
    console.log('ScheduleForm - handleSubmit called');
    console.log('ScheduleForm - formData:', formData);
    console.log('ScheduleForm - isFormValid:', isFormValid());

    if (!isFormValid()) {
      console.error('ScheduleForm - Form validation failed');
      setError(getValidationMessage());
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await ensureAuthOrRedirect();
      const url = editingSchedule
        ? `${window.location.origin}/api/v1/schedules/${editingSchedule.id}`
        : `${window.location.origin}/api/v1/schedules/`;

      const method = editingSchedule ? 'PUT' : 'POST';

      console.log('ScheduleForm - Sending request:', { method, url, formData });

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...getSafeAuthHeaders()
        },
        body: JSON.stringify(formData)
      });
      if (response.status === 401) {
        window.location.hash = 'login';
        throw new Error('Session expired, please log in again');
      }

      if (!response.ok) {
        const msg = await buildHttpErrorMessage(response, 'Failed to save schedule');
        if (response.status === 403) {
          throw new Error(`${msg}\n(Request missing Authorization header, or token validation failed/invalid format)`);
        }
        throw new Error(msg);
      }

      console.log('ScheduleForm - Request successful');

      // Notify parent component to refresh list and close modal
      onScheduleCreated();
    } catch (err) {
      console.error('ScheduleForm - Error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTestToggle = (testId) => {
    // For single schedule type, only one test can be selected
    setFormData(prev => ({
      ...prev,
      test_definition_id: prev.test_definition_id === testId ? null : testId
    }));
  };

  const cronPresets = [
    { label: 'Every minute', value: '* * * * *' },
    { label: 'Every hour', value: '0 * * * *' },
    { label: 'Daily at 2 AM', value: '0 2 * * *' },
    { label: 'Every Monday at 9 AM', value: '0 9 * * 1' },
    { label: 'First day of month at 3 AM', value: '0 3 1 * *' },
    { label: 'Weekdays at 9 AM', value: '0 9 * * 1-5' }
  ];

  return (
    <form onSubmit={handleSubmit} className="schedule-form">
      {error && (
        <div className="form-alert error">
          <span className="form-alert-icon">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {successMessage && (
        <div className="form-alert success">
          <span className="form-alert-icon">✓</span>
          <span>{successMessage}</span>
        </div>
      )}

      <div className="form-group">
        <label className="form-label required">Schedule Name</label>
        <input
          type="text"
          required
          className="form-input"
          value={formData.name}
          onChange={(e) => setFormData({...formData, name: e.target.value})}
          placeholder="e.g., Daily regression test"
        />
      </div>

      <div className="form-group">
        <label className="form-label">Schedule Type</label>
        <select
          className="form-select"
          value={formData.schedule_type}
          onChange={(e) => {
            const newType = e.target.value;
            setFormData(prev => ({
              ...prev,
              schedule_type: newType,
              test_definition_id: newType === 'single' ? prev.test_definition_id : null,
              test_suite_id: newType === 'suite' ? prev.test_suite_id : null,
              tag_filter: newType === 'tag_filter' ? prev.tag_filter : null
            }));
          }}
        >
          <option value="single">Single Test</option>
          <option value="suite">Test Suite</option>
          <option value="tag_filter">Tag Filter</option>
        </select>
      </div>

      <div className="form-group">
        <label className="form-label required">Cron Expression</label>
        <select
          className="form-select"
          value={formData.cron_expression}
          onChange={(e) => setFormData({...formData, cron_expression: e.target.value})}
        >
          <option value="">Select preset...</option>
          {cronPresets.map(preset => (
            <option key={preset.value} value={preset.value}>
              {preset.label} ({preset.value})
            </option>
          ))}
        </select>
        <input
          type="text"
          required
          className="form-input"
          value={formData.cron_expression}
          onChange={(e) => setFormData({...formData, cron_expression: e.target.value})}
          placeholder="* * * * * (min hour day month weekday)"
        />
        <div className="form-helper">
          <span>Format: min hour day month weekday (e.g., 0 2 * * * = daily at 2 AM)</span>
        </div>
      </div>

      <div className="form-group">
        <label className="form-label">Timezone</label>
        <select
          className="form-select"
          value={formData.timezone}
          onChange={(e) => setFormData({...formData, timezone: e.target.value})}
        >
          <option value="UTC">UTC</option>
          <option value="Asia/Shanghai">Asia/Shanghai (China Standard Time)</option>
          <option value="America/New_York">America/New_York</option>
          <option value="Europe/London">Europe/London</option>
        </select>
      </div>

      {formData.schedule_type === 'single' && (
        <div className="form-group">
          <label className="form-label required">Select Test Case</label>
          <div className="test-selection-list">
            {tests.length === 0 ? (
              <div className="test-empty">No test cases available</div>
            ) : (
              tests.map(test => (
                <label
                  key={test.id}
                  className={`test-selection-item ${formData.test_definition_id === test.id ? 'selected' : ''}`}
                >
                  <input
                    type="radio"
                    name="test_selection"
                    className="test-selection-radio"
                    checked={formData.test_definition_id === test.id}
                    onChange={() => handleTestToggle(test.id)}
                  />
                  <span className="test-selection-name">{test.name}</span>
                </label>
              ))
            )}
          </div>
          <div className="form-helper">
            {formData.test_definition_id ? '✓ 1 test case selected' : 'Please select 1 test case'}
          </div>
        </div>
      )}

      {formData.schedule_type === 'suite' && (
        <div className="form-group">
          <label className="form-label required">Select Test Suite</label>
          <select
            className="form-select"
            value={formData.test_suite_id || ''}
            onChange={(e) => setFormData({...formData, test_suite_id: parseInt(e.target.value) || null})}
          >
            <option value="">Select suite...</option>
            {suites.map(suite => (
              <option key={suite.id} value={suite.id}>
                {suite.name} ({suite.test_definition_ids?.length || 0} tests)
              </option>
            ))}
          </select>
          <div className="form-helper">
            {suites.length === 0 ? 'No test suites available, please create one in the Test Suites page first' : `${suites.length} suites available`}
          </div>
        </div>
      )}

      {formData.schedule_type === 'tag_filter' && (
        <div className="form-group">
          <label className="form-label required">Tag Filter</label>
          <input
            type="text"
            required
            className="form-input"
            value={formData.tag_filter || ''}
            onChange={(e) => setFormData({...formData, tag_filter: e.target.value})}
            placeholder="e.g., smoke,regression"
          />
          <div className="form-helper">
            <span>Enter tag names (e.g., smoke, regression, app-generated). The system will automatically match all published tests containing these tags.</span>
          </div>
        </div>
      )}

      <div className="form-actions">
        <button
          type="submit"
          className="form-btn form-btn-primary"
          disabled={loading || !isFormValid()}
          title={!isFormValid() ? getValidationMessage() : ''}
        >
          {loading ? (
            <>
              <div className="btn-spinner"></div>
              <span>Saving...</span>
            </>
          ) : (
            <span>{editingSchedule ? '💾 Update Schedule' : '✨ Create Schedule'}</span>
          )}
        </button>
        {!isFormValid() && !loading && (
          <div className="form-validation-hint">
            <span className="hint-icon">⚠️</span>
            <span>{getValidationMessage()}</span>
          </div>
        )}
        <button
          type="button"
          className="form-btn form-btn-secondary"
          onClick={onCancel}
        >
          <span>✕ Done</span>
        </button>
      </div>
    </form>
  );
}
