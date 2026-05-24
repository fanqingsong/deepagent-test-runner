import { useState, useEffect, useCallback } from 'react';
import {
  getTestSuites,
  deleteTestSuite,
  runTestSuite,
  getSuiteRuns,
  createTestSuite,
  updateTestSuite,
} from '../api';
import Modal from './Modal';
import './SuiteManager.css';

const STATUS_MAP = {
  pending: { label: 'Pending', color: '#8d8d8d' },
  running: { label: 'Running', color: '#0f62fe' },
  completed: { label: 'Completed', color: '#42be65' },
  passed: { label: 'Passed', color: '#42be65' },
  failed: { label: 'Failed', color: '#da1e28' },
  cancelled: { label: 'Cancelled', color: '#8d8d8d' },
  partial: { label: 'Partial', color: '#f1c21b' },
};

function StatusBadge({ status }) {
  const info = STATUS_MAP[status] || { label: status, color: '#8d8d8d' };
  return (
    <span style={{
      padding: '2px 8px',
      fontSize: '12px',
      borderRadius: '24px',
      background: info.color,
      color: '#fff',
    }}>
      {info.label}
    </span>
  );
}

function SuiteForm({ suite, onSuccess, onCancel }) {
  const [form, setForm] = useState({
    name: suite?.name || '',
    description: suite?.description || '',
    execution_mode: suite?.execution_mode || 'sequential',
    max_concurrency: suite?.max_concurrency || 1,
    fail_strategy: suite?.fail_strategy || 'continue',
    test_definition_ids: suite?.test_definition_ids || [],
    is_dynamic: suite?.is_dynamic || false,
  });

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSuccess(form);
  };

  return (
    <form className="suite-form" onSubmit={handleSubmit}>
      <div className="suite-form-group">
        <label>Name *</label>
        <input
          value={form.name}
          onChange={(e) => handleChange('name', e.target.value)}
          required
          placeholder="Test suite name"
        />
      </div>

      <div className="suite-form-group">
        <label>Description</label>
        <textarea
          value={form.description}
          onChange={(e) => handleChange('description', e.target.value)}
          rows={2}
          placeholder="Optional description"
        />
      </div>

      <div className="suite-form-row">
        <div className="suite-form-group">
          <label>Execution Mode</label>
          <select
            value={form.execution_mode}
            onChange={(e) => handleChange('execution_mode', e.target.value)}
          >
            <option value="sequential">Sequential</option>
            <option value="parallel">Parallel</option>
          </select>
        </div>

        <div className="suite-form-group">
          <label>Failure Strategy</label>
          <select
            value={form.fail_strategy}
            onChange={(e) => handleChange('fail_strategy', e.target.value)}
          >
            <option value="continue">Continue</option>
            <option value="fail_fast">Fail fast</option>
          </select>
        </div>
      </div>

      {form.execution_mode === 'parallel' && (
        <div className="suite-form-group">
          <label>Max Concurrency</label>
          <input
            type="number"
            min={1}
            max={10}
            value={form.max_concurrency}
            onChange={(e) => handleChange('max_concurrency', parseInt(e.target.value) || 1)}
          />
        </div>
      )}

      <div className="suite-form-actions">
        <button type="button" className="suite-btn suite-btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="suite-btn suite-btn-primary">
          {suite ? 'Save' : 'Create'}
        </button>
      </div>
    </form>
  );
}

function SuiteRunsSection({ suiteId }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getSuiteRuns(suiteId, 0, 20)
      .then((data) => { if (!cancelled) setRuns(data); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [suiteId]);

  if (loading) return <p style={{ color: 'var(--cds-text-secondary)' }}>Loading run history...</p>;
  if (!runs.length) return <p style={{ color: 'var(--cds-text-secondary)' }}>No run history</p>;

  return (
    <table className="suite-runs-table">
      <thead>
        <tr>
          <th>Run ID</th>
          <th>Status</th>
          <th>Passed/Failed/Skipped</th>
          <th>Triggered By</th>
          <th>Created At</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr key={run.id}>
            <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{run.run_id}</td>
            <td><StatusBadge status={run.status} /></td>
            <td>{run.passed}/{run.failed}/{run.skipped}</td>
            <td>{run.triggered_by}</td>
            <td>{new Date(run.created_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function SuiteManager() {
  const [suites, setSuites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingSuite, setEditingSuite] = useState(null);
  const [expandedSuite, setExpandedSuite] = useState(null);

  const loadSuites = useCallback(async () => {
    try {
      const data = await getTestSuites();
      setSuites(data);
    } catch (err) {
      console.error('Failed to load suites:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSuites(); }, [loadSuites]);

  const handleRun = async (suiteId) => {
    try {
      await runTestSuite(suiteId);
      alert('Suite run triggered');
    } catch (err) {
      alert('Run failed: ' + err.message);
    }
  };

  const handleDelete = async (suiteId) => {
    if (!confirm('Are you sure you want to delete this test suite?')) return;
    try {
      await deleteTestSuite(suiteId);
      setSuites((prev) => prev.filter((s) => s.id !== suiteId));
    } catch (err) {
      alert('Delete failed: ' + err.message);
    }
  };

  const handleFormSuccess = async (formData) => {
    try {
      if (editingSuite) {
        await updateTestSuite(editingSuite.id, formData);
      } else {
        await createTestSuite(formData);
      }
      setShowForm(false);
      setEditingSuite(null);
      loadSuites();
    } catch (err) {
      alert('Save failed: ' + err.message);
    }
  };

  if (loading) {
    return (
      <div className="suite-manager">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="suite-manager">
      {!expandedSuite ? (
        <>
          {suites.length === 0 ? (
            <div className="suite-empty">
              <p>No test suites yet</p>
              <p style={{ fontSize: '14px' }}>Click the "Create Suite" button above to start organizing your test cases</p>
            </div>
          ) : (
            <div className="suite-grid">
              {suites.map((suite) => (
                <div key={suite.id} className="suite-card">
                  <div className="suite-card-header">
                    <h3 className="suite-card-title">{suite.name}</h3>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      {suite.is_dynamic && (
                        <span className="suite-badge dynamic">Dynamic</span>
                      )}
                      <span className="suite-badge mode">
                        {suite.execution_mode === 'parallel' ? 'Parallel' : 'Sequential'}
                      </span>
                    </div>
                  </div>

                  {suite.description && (
                    <p className="suite-card-desc">{suite.description}</p>
                  )}

                  <div className="suite-card-meta">
                    <span>Tests: {(suite.suite_entries?.length || suite.test_definition_ids?.length || 0)}</span>
                    <span>Strategy: {suite.fail_strategy === 'fail_fast' ? 'Fail fast' : 'Continue'}</span>
                  </div>

                  <div className="suite-card-actions">
                    <button
                      className="suite-btn suite-btn-primary"
                      onClick={() => handleRun(suite.id)}
                    >
                      Run
                    </button>
                    <button
                      className="suite-btn suite-btn-secondary"
                      onClick={() => setExpandedSuite(suite)}
                    >
                      Details
                    </button>
                    <button
                      className="suite-btn suite-btn-ghost"
                      onClick={() => {
                        setEditingSuite(suite);
                        setShowForm(true);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      className="suite-btn suite-btn-danger"
                      onClick={() => handleDelete(suite.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="suite-detail">
          <div className="suite-detail-header">
            <h2 className="suite-detail-title">{expandedSuite.name}</h2>
            <button
              className="suite-btn suite-btn-ghost"
              onClick={() => setExpandedSuite(null)}
            >
              Back to List
            </button>
          </div>
          {expandedSuite.description && (
            <p style={{ color: 'var(--cds-text-secondary)', marginBottom: 'var(--cds-layout-md)' }}>
              {expandedSuite.description}
            </p>
          )}
          <div className="suite-runs-section">
            <h3 style={{ fontSize: '16px', fontWeight: 'var(--cds-font-weight-regular)', marginBottom: 'var(--cds-spacing-md)' }}>
              Run History
            </h3>
            <SuiteRunsSection suiteId={expandedSuite.id} />
          </div>
        </div>
      )}

      <Modal
        isOpen={showForm}
        onClose={() => { setShowForm(false); setEditingSuite(null); }}
        title={editingSuite ? `Edit Suite: ${editingSuite.name}` : 'Create Test Suite'}
      >
        <SuiteForm
          suite={editingSuite}
          onSuccess={handleFormSuccess}
          onCancel={() => { setShowForm(false); setEditingSuite(null); }}
        />
      </Modal>
    </div>
  );
}
