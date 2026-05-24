import { useState, useEffect, useCallback } from 'react';
import {
  getTestSuite, updateTestSuite, runTestSuite,
  getSuiteRuns, submitSuiteForReview,
} from '../../api';
import SuiteConfigTab from './SuiteConfigTab';
import SuiteEntriesTab from './SuiteEntriesTab';
import SuiteRunHistoryTab from './SuiteRunHistoryTab';
import Toast from '../Toast';
import '../studio/studio-shared.css';
import './SuiteEditorPanel.css';

const TABS = [
  { key: 'config', label: 'Configuration' },
  { key: 'entries', label: 'Test Entries' },
  { key: 'history', label: 'Run History' },
];

export default function SuiteEditorPanel({ suiteId, onSuiteChanged, onDelete }) {
  const [suite, setSuite] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('config');
  const [isRunning, setIsRunning] = useState(false);

  // Toast state
  const [toast, setToast] = useState({ message: null, type: 'success', key: 0 });

  const showToast = (message, type = 'success') => {
    setToast(prev => ({ message, type, key: prev.key + 1 }));
  };

  // Form state
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formMode, setFormMode] = useState('sequential');
  const [formConcurrency, setFormConcurrency] = useState(1);
  const [formFailStrategy, setFormFailStrategy] = useState('continue');
  const [configDirty, setConfigDirty] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);

  // Schedule form state
  const [formScheduleEnabled, setFormScheduleEnabled] = useState(false);
  const [formCronExpression, setFormCronExpression] = useState('0 2 * * *');
  const [formTimezone, setFormTimezone] = useState('Asia/Shanghai');
  const [formScheduleAllowConcurrent, setFormScheduleAllowConcurrent] = useState(false);
  const [formScheduleMaxRetries, setFormScheduleMaxRetries] = useState(0);
  const [formScheduleRetryInterval, setFormScheduleRetryInterval] = useState(60);
  const [nextRunTime, setNextRunTime] = useState(null);
  const [lastRunTime, setLastRunTime] = useState(null);

  // Run history state
  const [runs, setRuns] = useState([]);
  const [runsLoading, setRunsLoading] = useState(false);

  const loadSuite = useCallback(async () => {
    if (!suiteId) return;
    try {
      setLoading(true);
      const data = await getTestSuite(suiteId);
      setSuite(data);
      setFormName(data.name || '');
      setFormDesc(data.description || '');
      setFormMode(data.execution_mode || 'sequential');
      setFormConcurrency(data.max_concurrency || 1);
      setFormFailStrategy(data.fail_strategy || 'continue');
      setFormScheduleEnabled(data.schedule_enabled || false);
      setFormCronExpression(data.cron_expression || '0 2 * * *');
      setFormTimezone(data.timezone || 'Asia/Shanghai');
      setFormScheduleAllowConcurrent(data.schedule_allow_concurrent || false);
      setFormScheduleMaxRetries(data.schedule_max_retries ?? 0);
      setFormScheduleRetryInterval(data.schedule_retry_interval ?? 60);
      setNextRunTime(data.next_run_time || null);
      setLastRunTime(data.last_run_time || null);
      setConfigDirty(false);
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [suiteId]);

  useEffect(() => { loadSuite(); }, [loadSuite]);

  const loadRuns = useCallback(async () => {
    if (!suiteId) return;
    try {
      setRunsLoading(true);
      const data = await getSuiteRuns(suiteId, 0, 50);
      setRuns(data);
    } catch { /* non-critical */ } finally {
      setRunsLoading(false);
    }
  }, [suiteId]);

  useEffect(() => { loadRuns(); }, [loadRuns]);

  const handleSaveConfig = async () => {
    if (!formName.trim()) {
      showToast('Name cannot be empty', 'error');
      return;
    }
    try {
      setSavingConfig(true);
      await updateTestSuite(suiteId, {
        name: formName,
        description: formDesc || null,
        execution_mode: formMode,
        max_concurrency: formMode === 'parallel' ? formConcurrency : 1,
        fail_strategy: formFailStrategy,
        schedule_enabled: formScheduleEnabled,
        cron_expression: formScheduleEnabled ? formCronExpression : null,
        timezone: formTimezone,
        schedule_allow_concurrent: formScheduleAllowConcurrent,
        schedule_max_retries: formScheduleMaxRetries,
        schedule_retry_interval: formScheduleRetryInterval,
      });
      setConfigDirty(false);
      await loadSuite();
      onSuiteChanged?.();
      showToast('Configuration saved');
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      setSavingConfig(false);
    }
  };

  const handleRun = async () => {
    try {
      setIsRunning(true);
      await runTestSuite(suiteId);
      showToast('Run triggered');
      setTimeout(() => loadRuns(), 1500);
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      setIsRunning(false);
    }
  };

  const handleSubmitForReview = async () => {
    try {
      await submitSuiteForReview(suiteId);
      await loadSuite();
      onSuiteChanged?.();
      showToast('Submitted for review');
    } catch (e) {
      showToast(e.message, 'error');
    }
  };

  const handleUpdateEntries = async (entries) => {
    try {
      await updateTestSuite(suiteId, { suite_entries: entries });
      await loadSuite();
      onSuiteChanged?.();
      showToast('Test entries updated');
    } catch (e) {
      showToast(e.message, 'error');
    }
  };

  const markDirty = () => setConfigDirty(true);

  if (!suiteId) {
    return (
      <div className="suite-editor">
        <div className="suite-editor-empty">
          <div className="suite-editor-empty-icon">&#8592;</div>
          <h3>Select or create a suite</h3>
          <p>Select an existing suite from the left list, or click "New Suite" to create one</p>
        </div>
      </div>
    );
  }

  if (loading && !suite) {
    return (
      <div className="suite-editor">
        <div className="suite-editor-empty">Loading...</div>
      </div>
    );
  }

  return (
    <div className="suite-editor">
      {/* Header */}
      <div className="suite-editor-header">
        <div className="suite-editor-header-info">
          <h1 className="suite-editor-name">{suite?.name || 'Unnamed Suite'}</h1>
        </div>
        <div className="suite-editor-header-actions">
          <span className="suite-editor-status-badge" style={{
            borderColor: suite?.is_dynamic ? '#6929c4' : '#0f62fe',
            color: suite?.is_dynamic ? '#6929c4' : '#0f62fe',
          }}>
            {suite?.is_dynamic ? 'Dynamic' : suite?.execution_mode === 'parallel' ? 'Parallel' : 'Sequential'}
          </span>
          {suite?.review_status === 'pending_review' && (
            <span style={{ background: '#f1c21b', color: '#1c1c1c', padding: '2px 10px', fontSize: '12px', borderRadius: '24px' }}>
              Pending Review
            </span>
          )}
          {suite?.review_status === 'approved' && (
            <span style={{ background: '#42be65', color: '#fff', padding: '2px 10px', fontSize: '12px', borderRadius: '24px' }}>
              Approved
            </span>
          )}
          {suite?.review_status === 'rejected' && (
            <span style={{ background: '#da1e28', color: '#fff', padding: '2px 10px', fontSize: '12px', borderRadius: '24px' }}>
              Rejected
            </span>
          )}
          {(suite?.review_status === 'draft' || suite?.review_status === 'rejected') && (
            <button
              className="suite-editor-run-btn"
              style={{ background: '#0f62fe' }}
              onClick={handleSubmitForReview}
            >
              Submit for Review
            </button>
          )}
          <button
            className="suite-editor-run-btn"
            onClick={handleRun}
            disabled={isRunning || suite?.review_status !== 'approved'}
            title={suite?.review_status !== 'approved' ? 'Suite must be approved before running' : ''}
          >
            {isRunning ? 'Running...' : 'Run'}
          </button>
          <button
            className="suite-editor-delete-btn"
            onClick={() => onDelete(suiteId)}
          >
            Delete
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="suite-editor-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`suite-editor-tab ${activeTab === tab.key ? 'suite-editor-tab--active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="suite-editor-content">
        {activeTab === 'config' && (
          <SuiteConfigTab
            formName={formName}
            formDesc={formDesc}
            formMode={formMode}
            formConcurrency={formConcurrency}
            formFailStrategy={formFailStrategy}
            configDirty={configDirty}
            savingConfig={savingConfig}
            onChangeName={(e) => { setFormName(e.target.value); markDirty(); }}
            onChangeDesc={(e) => { setFormDesc(e.target.value); markDirty(); }}
            onChangeMode={(e) => { setFormMode(e.target.value); markDirty(); }}
            onChangeConcurrency={(e) => { setFormConcurrency(parseInt(e.target.value) || 1); markDirty(); }}
            onChangeFailStrategy={(e) => { setFormFailStrategy(e.target.value); markDirty(); }}
            onSaveConfig={handleSaveConfig}
            formScheduleEnabled={formScheduleEnabled}
            formCronExpression={formCronExpression}
            formTimezone={formTimezone}
            formScheduleAllowConcurrent={formScheduleAllowConcurrent}
            formScheduleMaxRetries={formScheduleMaxRetries}
            formScheduleRetryInterval={formScheduleRetryInterval}
            nextRunTime={nextRunTime}
            lastRunTime={lastRunTime}
            onChangeScheduleEnabled={(v) => { setFormScheduleEnabled(v); markDirty(); }}
            onChangeCronExpression={(v) => { setFormCronExpression(v); markDirty(); }}
            onChangeTimezone={(v) => { setFormTimezone(v); markDirty(); }}
            onChangeScheduleAllowConcurrent={(v) => { setFormScheduleAllowConcurrent(v); markDirty(); }}
            onChangeScheduleMaxRetries={(v) => { setFormScheduleMaxRetries(v); markDirty(); }}
            onChangeScheduleRetryInterval={(v) => { setFormScheduleRetryInterval(v); markDirty(); }}
          />
        )}
        {activeTab === 'entries' && (
          <SuiteEntriesTab
            suite={suite}
            onUpdateEntries={handleUpdateEntries}
          />
        )}
        {activeTab === 'history' && (
          <SuiteRunHistoryTab
            runs={runs}
            loading={runsLoading}
          />
        )}
      </div>
      <Toast key={toast.key} message={toast.message} type={toast.type} onDone={() => setToast(prev => ({ ...prev, message: null }))} />
    </div>
  );
}
