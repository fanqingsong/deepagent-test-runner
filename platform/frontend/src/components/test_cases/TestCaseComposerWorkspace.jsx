import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getTestCase, updateTestCase, publishTestCase,
  getTestCaseRunHistory, getTestRunDetails,
  getStepVersions, createDraftFromVersion,
} from '../../api';
import TestCaseConfigTab from './TestCaseConfigTab';
import TestCaseScriptTab from './TestCaseScriptTab';
import TestCaseRunHistoryTab from './TestCaseRunHistoryTab';
import TestCaseVersionTab from './TestCaseVersionTab';
import TestCasePermissionsSection from './TestCasePermissionsSection';
import './TestCaseComposerWorkspace.css';
import './test-cases-shared.css';

const STATUS_LABELS = {
  draft: 'Draft',
  generating: 'Generating',
  testing: 'Testing',
  passed: 'Passed',
  pending_review: 'Pending Review',
  approved: 'Approved',
  published: 'Published',
  rejected: 'Rejected',
};

export default function TestCaseComposerWorkspace({ testCaseId, onTestCaseChanged }) {
  const [testCase, setTestCase] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [savingConfig, setSavingConfig] = useState(false);
  const [publishing, setPublishing] = useState(false);

  // Draft/read-only mode
  const [draftMode, setDraftMode] = useState(false);

  // Form state
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formGoal, setFormGoal] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [configDirty, setConfigDirty] = useState(false);

  // Config collapse
  const [configCollapsed, setConfigCollapsed] = useState(false);
  const [permissionsCollapsed, setPermissionsCollapsed] = useState(false);

  // Run history
  const [runHistory, setRunHistory] = useState([]);
  const [runHistoryLoading, setRunHistoryLoading] = useState(false);
  const [expandedRunId, setExpandedRunId] = useState(null);
  const [expandedRunCases, setExpandedRunCases] = useState([]);
  const [expandedRunLoading, setExpandedRunLoading] = useState(false);

  // Versions for draft creation
  const [versions, setVersions] = useState([]);
  const [versionRefreshKey, setVersionRefreshKey] = useState(0);

  // Draggable divider
  const leftPaneRef = useRef(null);
  const dividerRef = useRef(null);
  const draggingRef = useRef(false);

  const readOnly = !draftMode;

  // ── Data Loading ──────────────────────────────────

  const loadTestCase = useCallback(async () => {
    if (!testCaseId) return;
    try {
      setLoading(true);
      const data = await getTestCase(testCaseId);
      setTestCase(data);
      setError(null);
      setFormName(data.name || '');
      setFormUrl(data.url || '');
      setFormGoal(data.test_goal || '');
      setFormDesc(data.description || '');
      setConfigDirty(false);
      setDraftMode(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [testCaseId]);

  useEffect(() => { loadTestCase(); }, [loadTestCase]);

  const loadRunHistory = useCallback(async () => {
    if (!testCaseId) return;
    try {
      setRunHistoryLoading(true);
      const runs = await getTestCaseRunHistory(testCaseId, { limit: 50 });
      setRunHistory(runs);
    } catch { /* non-critical */ } finally {
      setRunHistoryLoading(false);
    }
  }, [testCaseId]);

  useEffect(() => { loadRunHistory(); }, [loadRunHistory]);

  // ── Handlers ──────────────────────────────────────

  const handleSaveConfig = async () => {
    try {
      setSavingConfig(true);
      setError(null);
      await updateTestCase(testCaseId, {
        name: formName, url: formUrl,
        test_goal: formGoal, description: formDesc || null,
      });
      setConfigDirty(false);
      await loadTestCase();
      onTestCaseChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setSavingConfig(false);
    }
  };

  const handlePublish = async () => {
    try {
      setPublishing(true);
      setError(null);
      await publishTestCase(testCaseId);
      await loadTestCase();
    } catch (e) {
      setError(e.message);
    } finally {
      setPublishing(false);
    }
  };

  const onFormChange = (field) => (e) => {
    const setters = { name: setFormName, url: setFormUrl, goal: setFormGoal, desc: setFormDesc };
    setters[field](e.target.value);
    setConfigDirty(true);
  };

  const handleToggleRunExpand = async (runId) => {
    if (expandedRunId === runId) {
      setExpandedRunId(null);
      setExpandedRunCases([]);
      return;
    }
    setExpandedRunId(runId);
    setExpandedRunLoading(true);
    try {
      const cases = await getTestRunDetails(runId);
      setExpandedRunCases(cases);
    } catch { setExpandedRunCases([]); } finally {
      setExpandedRunLoading(false);
    }
  };

  const handleDraftModeToggle = async () => {
    if (!draftMode) {
      // Switching TO draft mode - create draft if needed
      try {
        setError(null);
        // Load versions to check for existing draft
        const vers = await getStepVersions(testCaseId);
        setVersions(vers);
        const currentVersion = vers.find(v => v.review_status === 'draft');
        if (!currentVersion && vers.length > 0) {
          // Create draft from latest version
          const latest = vers[0]; // versions are sorted desc
          await createDraftFromVersion(testCaseId, latest.id);
          // Trigger version list refresh
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
      divider.classList.add('composer-divider--dragging');
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
      divider.classList.remove('composer-divider--dragging');
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

  if (!testCaseId) {
    return (
      <div className="composer-workspace">
        <div className="composer-empty">
          <div className="composer-empty-icon">&larr;</div>
          <h3>Select or create a test case</h3>
          <p>Select from the list or click "Create Test" to get started</p>
        </div>
      </div>
    );
  }

  if (loading && !testCase) {
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

        <span className="composer-header-name">{testCase?.name || 'Unnamed Test'}</span>

        <div className="composer-header-separator" />

        <span className={`composer-status-badge status-${testCase?.status}`}>
          {STATUS_LABELS[testCase?.status] || testCase?.status}
        </span>

        {testCase?.status === 'pending_review' && (
          <span style={{
            padding: '2px 10px', fontSize: '11px', fontWeight: 600,
            background: '#f1c21b', color: '#1c1c1c',
          }}>
            Pending Admin Review
          </span>
        )}

        <div className="composer-header-actions">
          {testCase?.status !== 'pending_review' && testCase?.status !== 'published' && testCase?.status !== 'approved' && (
            <button
              className="composer-submit-btn"
              onClick={handlePublish}
              disabled={publishing}
            >
              {publishing ? 'Submitting...' : 'Submit for Review'}
            </button>
          )}
        </div>
      </div>

      {error && <div className="composer-error-bar">{error}</div>}

      {/* Split Pane */}
      <div className="composer-split-pane">
        {/* Left Pane: Config + Script */}
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
              <div className="composer-config-row">
                <label className="composer-config-label">Name</label>
                <input
                  className="composer-config-input"
                  value={formName}
                  onChange={onFormChange('name')}
                  disabled={readOnly || savingConfig || publishing}
                />
              </div>
              <div className="composer-config-row">
                <label className="composer-config-label">URL</label>
                <input
                  className="composer-config-input"
                  value={formUrl}
                  onChange={onFormChange('url')}
                  placeholder="https://example.com"
                  disabled={readOnly || savingConfig || publishing}
                />
              </div>
              <div className="composer-config-row">
                <label className="composer-config-label">Goal</label>
                <textarea
                  className="composer-config-textarea"
                  value={formGoal}
                  onChange={onFormChange('goal')}
                  placeholder="Describe what to test..."
                  rows={2}
                  disabled={readOnly || savingConfig || publishing}
                />
              </div>
              <div className="composer-config-row">
                <label className="composer-config-label">Description</label>
                <textarea
                  className="composer-config-textarea"
                  value={formDesc}
                  onChange={onFormChange('desc')}
                  placeholder="Optional description..."
                  rows={1}
                  disabled={readOnly || savingConfig || publishing}
                />
              </div>
              {!readOnly && (
                <div className="composer-config-actions">
                  <button
                    className="composer-config-save-btn"
                    onClick={handleSaveConfig}
                    disabled={!configDirty || savingConfig}
                  >
                    {savingConfig ? 'Saving...' : 'Save'}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Script Section */}
          <div className="composer-script-section">
            <div className="composer-script-section-header">
              <span className="composer-script-section-title">Playwright Script</span>
            </div>
            <div className="composer-script-section-body">
              <TestCaseScriptTab
                testCaseId={testCase?.test_definition_id || testCaseId}
                appId={testCaseId}
                readOnly={readOnly}
                onRunComplete={loadRunHistory}
              />
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="composer-divider" ref={dividerRef} />

        {/* Right Pane: Permissions + Run History + Versions */}
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
              <TestCasePermissionsSection
                workspaceId={testCaseId}
                readOnly={readOnly}
                onPermissionsChange={(perms) => {
                  // Track that permissions changed (for save indicator if needed)
                }}
                initialPermissions={[]}
              />
            </div>
          </div>

          {/* Versions */}
          <div className="composer-version-section">
            <div className="composer-section-header">
              <span className="composer-section-title">Versions</span>
            </div>
            <div className="composer-section-body">
              <TestCaseVersionTab
                testCaseId={testCaseId}
                onVersionRestored={loadTestCase}
                onVersionSubmitted={loadTestCase}
                refreshKey={versionRefreshKey}
              />
            </div>
          </div>

          {/* Run History */}
          <div className="composer-run-history-section">
            <div className="composer-section-header">
              <span className="composer-section-title">
                Run History
                <span className="composer-section-count">({runHistory.length})</span>
              </span>
            </div>
            <div className="composer-section-body">
              <TestCaseRunHistoryTab
                runHistory={runHistory}
                runHistoryLoading={runHistoryLoading}
                expandedRunId={expandedRunId}
                expandedRunCases={expandedRunCases}
                expandedLoading={expandedRunLoading}
                onToggleRunExpand={handleToggleRunExpand}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
