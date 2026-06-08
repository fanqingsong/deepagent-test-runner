import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getTestSuite, updateTestSuite, runTestSuite,
  getSuiteRuns, submitSuiteForReview,
  getSuiteVersions, createDraftFromSuiteVersion,
} from '../../api';
import SuiteConfigTab from './SuiteConfigTab';
import SuiteEntriesTab from './SuiteEntriesTab';
import SuiteRunHistoryTab from './SuiteRunHistoryTab';
import SuiteVersionTab from './SuiteVersionTab';
import SuitePermissionTab from './SuitePermissionTab';
import Toast from '../Toast';
import './SuiteComposerWorkspace.css';

const STATUS_LABELS = {
  draft: 'Draft',
  pending_review: 'Pending Review',
  approved: 'Approved',
  rejected: 'Rejected',
};

export default function SuiteComposerWorkspace({ suiteId, onSuiteChanged, onDelete }) {
  const [suite, setSuite] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [savingConfig, setSavingConfig] = useState(false);
  const [running, setRunning] = useState(false);

  // Draft/read-only mode
  const [draftMode, setDraftMode] = useState(false);

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

  // Version and permission state
  const [versionRefreshKey, setVersionRefreshKey] = useState(0);
  const [versions, setVersions] = useState([]);

  // Config collapse
  const [configCollapsed, setConfigCollapsed] = useState(false);
  const [permissionsCollapsed, setPermissionsCollapsed] = useState(false);
  const [entriesCollapsed, setEntriesCollapsed] = useState(false);
  const [versionsCollapsed, setVersionsCollapsed] = useState(false);
  const [runHistoryCollapsed, setRunHistoryCollapsed] = useState(false);

  // Draggable divider
  const leftPaneRef = useRef(null);
  const dividerRef = useRef(null);
  const draggingRef = useRef(false);

  const readOnly = !draftMode;

  // ── Data Loading ──────────────────────────────────

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
      setError(null);
    } catch (e) {
      setError(e.message);
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

  // ── Handlers ──────────────────────────────────────

  const handleSaveConfig = async () => {
    if (!formName.trim()) {
      showToast('Name cannot be empty', 'error');
      return;
    }
    try {
      setSavingConfig(true);
      setError(null);
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
      setError(e.message);
      showToast(e.message, 'error');
    } finally {
      setSavingConfig(false);
    }
  };

  const handleRun = async () => {
    try {
      setRunning(true);
      setError(null);
      await runTestSuite(suiteId);
      showToast('Run triggered');
      setTimeout(() => loadRuns(), 1500);
    } catch (e) {
      setError(e.message);
      showToast(e.message, 'error');
    } finally {
      setRunning(false);
    }
  };

  const handleSubmitForReview = async () => {
    try {
      setError(null);
      await submitSuiteForReview(suiteId);
      await loadSuite();
      onSuiteChanged?.();
      showToast('Submitted for review');
    } catch (e) {
      setError(e.message);
      showToast(e.message, 'error');
    }
  };

  const handleUpdateEntries = async (entries) => {
    try {
      setError(null);
      await updateTestSuite(suiteId, { suite_entries: entries });
      await loadSuite();
      onSuiteChanged?.();
      showToast('Test entries updated');
    } catch (e) {
      setError(e.message);
      showToast(e.message, 'error');
    }
  };

  const onFormChange = (field) => (e) => {
    const setters = {
      name: setFormName,
      desc: setFormDesc,
      mode: setFormMode,
      concurrency: setFormConcurrency,
      failStrategy: setFormFailStrategy,
    };
    if (field === 'concurrency') {
      setFormConcurrency(parseInt(e.target.value) || 1);
    } else {
      setters[field](e.target.value);
    }
    setConfigDirty(true);
  };

  const handleDraftModeToggle = async () => {
    if (!draftMode) {
      // Switching TO draft mode - check for existing draft
      try {
        setError(null);
        const vers = await getSuiteVersions(suiteId);
        setVersions(vers);
        const currentVersion = vers.find(v => v.review_status === 'draft');
        if (!currentVersion && vers.length > 0) {
          // Create draft from latest version if no draft exists
          const latest = vers[0];
          await createDraftFromSuiteVersion(suiteId, latest.id);
          setVersionRefreshKey(prev => prev + 1);
        }
        setDraftMode(true);
      } catch (e) {
        setError(e.message);
      }
    } else {
      // Switching to read-only - just toggle
      setDraftMode(false);
    }
  };

  // ── Divider Drag ──────────────────────────────────

  useEffect(() => {
    const divider = dividerRef.current;
    if (!divider) return;

    const onMouseDown = (e) => {
      e.preventDefault();
      draggingRef.current = true;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      divider.classList.add('suite-composer-divider--dragging');
    };

    const onMouseMove = (e) => {
      if (!draggingRef.current || !leftPaneRef.current) return;
      const parent = leftPaneRef.current.parentElement;
      const parentRect = parent.getBoundingClientRect();
      const newWidth = ((e.clientX - parentRect.left) / parentRect.width) * 100;
      const clamped = Math.max(25, Math.min(75, newWidth));
      leftPaneRef.current.style.width = `${clamped}%`;
    };

    const onMouseUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      divider.classList.remove('suite-composer-divider--dragging');
    };

    divider.addEventListener('mousedown', onMouseDown);
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);

    return () => {
      divider.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  // ── Empty States ──────────────────────────────────

  if (!suiteId) {
    return (
      <div className="composer-workspace">
        <div className="composer-empty">
          <div className="composer-empty-icon">&larr;</div>
          <h3>Select or create a suite</h3>
          <p>Select an existing suite from the left list, or click "New Suite" to create one</p>
        </div>
      </div>
    );
  }

  if (loading && !suite) {
    return (
      <div className="composer-workspace">
        <div className="composer-empty">Loading...</div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────

  return (
    <div className="composer-workspace">
      {/* Header Bar */}
      <div className="composer-header">
        <button
          className={`composer-draft-toggle ${draftMode ? 'composer-draft-toggle--active' : ''}`}
          onClick={handleDraftModeToggle}
        >
          <span className="composer-draft-toggle-dot" />
          {draftMode ? 'Draft Mode' : 'Read-only'}
        </button>

        <div className="composer-header-separator" />

        <span className="composer-header-name">{suite?.name || 'Unnamed Suite'}</span>

        <div className="composer-header-separator" />

        <span className={`composer-status-badge status-${suite?.review_status}`}>
          {STATUS_LABELS[suite?.review_status] || suite?.review_status}
        </span>

        {suite?.is_dynamic && (
          <span style={{
            padding: '2px 10px',
            fontSize: '11px',
            fontWeight: 600,
            background: '#ddd7ff',
            color: '#6929c4',
          }}>
            Dynamic
          </span>
        )}

        {!suite?.is_dynamic && suite?.execution_mode === 'parallel' && (
          <span style={{
            padding: '2px 10px',
            fontSize: '11px',
            fontWeight: 600,
            background: '#edf5ff',
            color: '#0f62fe',
          }}>
            Parallel
          </span>
        )}

        <div className="composer-header-actions">
          {(suite?.review_status === 'draft' || suite?.review_status === 'rejected') && (
            <button
              className="composer-submit-btn"
              onClick={handleSubmitForReview}
            >
              Submit for Review
            </button>
          )}

          <button
            className="composer-run-btn"
            onClick={handleRun}
            disabled={running || suite?.review_status !== 'approved'}
            title={suite?.review_status !== 'approved' ? 'Suite must be approved before running' : ''}
          >
            {running ? 'Running...' : 'Run'}
          </button>

          <button
            className="composer-delete-btn"
            onClick={() => onDelete(suiteId)}
          >
            Delete
          </button>
        </div>
      </div>

      {error && <div className="composer-error-bar">{error}</div>}

      {/* Split Pane */}
      <div className="composer-split-pane">
        {/* Left Pane: Config + Test Entries */}
        <div className="composer-left-pane" ref={leftPaneRef}>
          {/* Config Section (collapsible) */}
          <div className="composer-config-section">
            <div
              className="composer-config-section-header"
              onClick={() => setConfigCollapsed(!configCollapsed)}
            >
              <span className="composer-config-section-title">Configuration</span>
              <span className={`composer-config-collapse-icon ${configCollapsed ? 'composer-config-collapse-icon--collapsed' : ''}`}>
                &#9660;
              </span>
            </div>
            <div className={`composer-config-body ${configCollapsed ? 'composer-config-body--collapsed' : ''}`}>
              <SuiteConfigTab
                formName={formName}
                formDesc={formDesc}
                formMode={formMode}
                formConcurrency={formConcurrency}
                formFailStrategy={formFailStrategy}
                configDirty={configDirty}
                savingConfig={savingConfig}
                readOnly={readOnly}
                onChangeName={onFormChange('name')}
                onChangeDesc={onFormChange('desc')}
                onChangeMode={onFormChange('mode')}
                onChangeConcurrency={onFormChange('concurrency')}
                onChangeFailStrategy={onFormChange('failStrategy')}
                onSaveConfig={handleSaveConfig}
                formScheduleEnabled={formScheduleEnabled}
                formCronExpression={formCronExpression}
                formTimezone={formTimezone}
                formScheduleAllowConcurrent={formScheduleAllowConcurrent}
                formScheduleMaxRetries={formScheduleMaxRetries}
                formScheduleRetryInterval={formScheduleRetryInterval}
                nextRunTime={nextRunTime}
                lastRunTime={lastRunTime}
                onChangeScheduleEnabled={(v) => { setFormScheduleEnabled(v); setConfigDirty(true); }}
                onChangeCronExpression={(v) => { setFormCronExpression(v); setConfigDirty(true); }}
                onChangeTimezone={(v) => { setFormTimezone(v); setConfigDirty(true); }}
                onChangeScheduleAllowConcurrent={(v) => { setFormScheduleAllowConcurrent(v); setConfigDirty(true); }}
                onChangeScheduleMaxRetries={(v) => { setFormScheduleMaxRetries(v); setConfigDirty(true); }}
                onChangeScheduleRetryInterval={(v) => { setFormScheduleRetryInterval(v); setConfigDirty(true); }}
              />
            </div>
          </div>

          {/* Test Entries Section */}
          <div className="composer-script-section">
            <div
              className="composer-script-section-header"
              onClick={() => setEntriesCollapsed(!entriesCollapsed)}
              style={{ cursor: 'pointer' }}
            >
              <span className="composer-script-section-title">Test Entries</span>
              <span className={`composer-config-collapse-icon ${entriesCollapsed ? 'composer-config-collapse-icon--collapsed' : ''}`}>
                &#9660;
              </span>
            </div>
            <div className={`composer-script-section-body ${entriesCollapsed ? 'composer-section-body--collapsed' : ''}`}>
              <SuiteEntriesTab
                suite={suite}
                onUpdateEntries={handleUpdateEntries}
              />
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="composer-divider" ref={dividerRef} />

        {/* Right Pane: Permissions + Versions + Run History */}
        <div className="composer-right-pane">
          {/* Permissions Section (collapsible) */}
          <div className="composer-permissions-wrapper">
            <div
              className="composer-config-section-header"
              onClick={() => setPermissionsCollapsed(!permissionsCollapsed)}
            >
              <span className="composer-config-section-title">Permissions</span>
              <span className={`composer-config-collapse-icon ${permissionsCollapsed ? 'composer-config-collapse-icon--collapsed' : ''}`}>
                &#9660;
              </span>
            </div>
            <div className={`composer-permissions-body ${permissionsCollapsed ? 'composer-permissions-body--collapsed' : ''}`}>
              <SuitePermissionTab suiteId={suiteId} />
            </div>
          </div>

          {/* Versions */}
          <div className="composer-version-section">
            <div
              className="composer-section-header"
              onClick={() => setVersionsCollapsed(!versionsCollapsed)}
              style={{ cursor: 'pointer' }}
            >
              <span className="composer-section-title">Versions</span>
              <span className={`composer-config-collapse-icon ${versionsCollapsed ? 'composer-config-collapse-icon--collapsed' : ''}`}>
                &#9660;
              </span>
            </div>
            <div className={`composer-section-body ${versionsCollapsed ? 'composer-section-body--collapsed' : ''}`}>
              <SuiteVersionTab
                suiteId={suiteId}
                onVersionRestored={() => {
                  loadSuite();
                  setVersionRefreshKey(prev => prev + 1);
                }}
                onVersionSubmitted={() => {
                  loadSuite();
                  setVersionRefreshKey(prev => prev + 1);
                }}
                refreshKey={versionRefreshKey}
              />
            </div>
          </div>

          {/* Run History */}
          <div className="composer-run-history-section">
            <div
              className="composer-section-header"
              onClick={() => setRunHistoryCollapsed(!runHistoryCollapsed)}
              style={{ cursor: 'pointer' }}
            >
              <span className="composer-section-title">
                Run History
                <span className="composer-section-count">({runs.length})</span>
              </span>
              <span className={`composer-config-collapse-icon ${runHistoryCollapsed ? 'composer-config-collapse-icon--collapsed' : ''}`}>
                &#9660;
              </span>
            </div>
            <div className={`composer-section-body ${runHistoryCollapsed ? 'composer-section-body--collapsed' : ''}`}>
              <SuiteRunHistoryTab
                runs={runs}
                loading={runsLoading}
              />
            </div>
          </div>
        </div>
      </div>

      <Toast key={toast.key} message={toast.message} type={toast.type} onDone={() => setToast(prev => ({ ...prev, message: null }))} />
    </div>
  );
}
