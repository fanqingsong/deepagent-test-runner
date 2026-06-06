import { useState, useEffect, useRef, useCallback } from 'react';
import {
  getTestCase, updateTestCase, runTestCase, publishTestCase, getJobStatus,
  getTestCaseRunProgress,
  getTestCaseRunHistory, getTestRunDetails,
} from '../../api';
import PermissionGate from '../PermissionGate';
import TestCaseConfigTab from './TestCaseConfigTab';
import TestCaseRunHistoryTab from './TestCaseRunHistoryTab';
import TestCaseVersionTab from './TestCaseVersionTab';
import TestCasePermissionTab from './TestCasePermissionTab';
import TestCaseScriptTab from './TestCaseScriptTab';
import ScreenshotLightbox from './ScreenshotLightbox';
import './TestCaseEditorPanel.css';
import './test-cases-shared.css';

const STATUS_LABELS = {
  draft: 'Draft',
  generating: 'Generating',
  testing: 'Testing',
  passed: 'Passed',
  pending_review: 'Pending Review',
  published: 'Published',
};

const TABS = [
  { key: 'config', label: 'Configuration' },
  { key: 'script', label: 'Playwright Script' },
  { key: 'history', label: 'Run History' },
  { key: 'versions', label: 'Version Management' },
  { key: 'permissions', label: 'Permissions' },
];

export default function TestCaseEditorPanel({ testCaseId, onTestCaseChanged }) {
  const [testCase, setTestCase] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('config');

  // Execution state
  const [isRunning, setIsRunning] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const pollingRef = useRef(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formGoal, setFormGoal] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [configDirty, setConfigDirty] = useState(false);

  // Streaming progress
  const [progressSteps, setProgressSteps] = useState([]);
  const [progressCurrent, setProgressCurrent] = useState(0);
  const [progressTotal, setProgressTotal] = useState(0);
  const [browserUrl, setBrowserUrl] = useState('');
  const [browserTitle, setBrowserTitle] = useState('');
  const [selectedScreenshot, setSelectedScreenshot] = useState(null);
  const [runningJobId, setRunningJobId] = useState(null);

  // Run history
  const [runHistory, setRunHistory] = useState([]);
  const [runHistoryLoading, setRunHistoryLoading] = useState(false);
  const [expandedRunId, setExpandedRunId] = useState(null);
  const [expandedRunCases, setExpandedRunCases] = useState([]);
  const [expandedRunLoading, setExpandedRunLoading] = useState(false);

  // Version viewing
  const [viewingVersionId, setViewingVersionId] = useState(null);
  const [viewedSteps, setViewedSteps] = useState(null);

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

  const pollJobStatus = async (jobId) => {
    let attempts = 0;
    const maxAttempts = 120;
    const poll = async () => {
      try {
        const job = await getJobStatus(jobId);
        try {
          const progress = await getTestCaseRunProgress(testCaseId);
          if (progress.completed_steps?.length > 0) {
            setProgressSteps(progress.completed_steps);
            setProgressCurrent(progress.current_step || 0);
            setProgressTotal(progress.total_steps || 0);
            setBrowserUrl(progress.browser_url || '');
            setBrowserTitle(progress.browser_title || '');
          }
        } catch { /* best-effort */ }
        if (job.status === 'completed' || attempts >= maxAttempts) {
          setIsRunning(false);
          setRunningJobId(null);
          setProgressSteps([]);
          setProgressCurrent(0);
          setProgressTotal(0);
          setBrowserUrl('');
          setBrowserTitle('');
          setSelectedScreenshot(null);
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = null;
          await loadTestCase();
          loadRunHistory();
          return;
        }
        attempts++;
      } catch { attempts++; }
    };
    pollingRef.current = setInterval(poll, 2000);
  };

  const handleRun = async (opts = {}) => {
    try {
      setIsRunning(true);
      setError(null);
      const result = await runTestCase(testCaseId, {
        forceRegenerate: !!opts.forceRegenerate,
        useExistingPlan: !!opts.useExistingPlan,
      });
      setRunningJobId(result.job_id);
      pollJobStatus(result.job_id);
    } catch (e) {
      setError(e.message);
      setIsRunning(false);
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

  const handleViewVersion = (version) => {
    if (viewingVersionId === version.id) {
      setViewingVersionId(null);
      setViewedSteps(null);
      return;
    }
    setViewingVersionId(version.id);
    setViewedSteps((version.snapshot?.steps || []).map(s => ({ ...s })));
  };

  const handleRestoreVersion = async (versionId) => {
    try {
      setError(null);
      const { restoreTestCaseVersion } = await import('../../api');
      await restoreTestCaseVersion(testCaseId, versionId);
      setViewingVersionId(null);
      setViewedSteps(null);
      await loadTestCase();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleBackToCurrent = () => {
    setViewingVersionId(null);
    setViewedSteps(null);
  };

  const isBusy = isRunning;

  if (!testCaseId) {
    return (
      <div className="studio-editor">
        <div className="studio-editor-empty">
          <div className="studio-editor-empty-icon">&#8592;</div>
          <h3>Select or create a test case</h3>
          <p>Select an existing test from the left list, or click "Create Test" to create a new one</p>
        </div>
      </div>
    );
  }

  if (loading && !testCase) {
    return (
      <div className="studio-editor">
        <div className="studio-editor-empty">Loading...</div>
      </div>
    );
  }

  return (
    <div className="studio-editor">
      <div className="studio-editor-header">
        <div className="studio-editor-header-info">
          <h1 className="studio-editor-name">{testCase?.name || 'Unnamed Test'}</h1>
        </div>
        <div className="studio-editor-header-actions">
          {error && <span style={{ color: '#da1e28', fontSize: '13px' }}>{error}</span>}
          <span className={`studio-editor-status-badge status-${testCase?.status}`}>
            {STATUS_LABELS[testCase?.status] || testCase?.status}
          </span>
          {testCase?.status === 'pending_review' && (
            <span className="studio-editor-published-tag" style={{ background: '#f1c21b', color: '#1c1c1c' }}>Pending Admin Review</span>
          )}
          {testCase?.status === 'published' && (
            <span className="studio-editor-published-tag">Published</span>
          )}
          {testCase?.status !== 'pending_review' && testCase?.status !== 'published' && !publishing && (
            <button
              className="studio-editor-publish-btn"
              onClick={handlePublish}
              disabled={publishing}
            >
              {publishing ? 'Submitting...' : 'Submit for Review'}
            </button>
          )}
        </div>
      </div>

      <div className="studio-editor-tabs">
        {TABS.map(tab => (
          <button
            key={tab.key}
            className={`studio-editor-tab ${activeTab === tab.key ? 'studio-editor-tab--active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="studio-editor-content">
        {activeTab === 'config' && (
          <TestCaseConfigTab
            testCaseId={testCaseId}
            formName={formName}
            formUrl={formUrl}
            formGoal={formGoal}
            formDesc={formDesc}
            configDirty={configDirty}
            isBusy={isBusy}
            savingConfig={savingConfig}
            onFormChange={onFormChange}
            onSaveConfig={handleSaveConfig}
          />
        )}
        {activeTab === 'script' && (
          <TestCaseScriptTab testCaseId={testCaseId} />
        )}
        {activeTab === 'history' && (
          <TestCaseRunHistoryTab
            runHistory={runHistory}
            runHistoryLoading={runHistoryLoading}
            expandedRunId={expandedRunId}
            expandedRunCases={expandedRunCases}
            expandedLoading={expandedRunLoading}
            onToggleRunExpand={handleToggleRunExpand}
            onSelectScreenshot={setSelectedScreenshot}
          />
        )}
        {activeTab === 'versions' && (
          <TestCaseVersionTab
            testCaseId={testCaseId}
            viewingVersionId={viewingVersionId}
            viewedSteps={viewedSteps}
            onViewVersion={handleViewVersion}
            onRestoreVersion={handleRestoreVersion}
            onBackToCurrent={handleBackToCurrent}
            onVersionSubmitted={loadTestCase}
          />
        )}
        {activeTab === 'permissions' && (
          <TestCasePermissionTab testCaseId={testCaseId} />
        )}
      </div>

      {selectedScreenshot && (
        <ScreenshotLightbox
          src={selectedScreenshot}
          onClose={() => setSelectedScreenshot(null)}
        />
      )}
    </div>
  );
}
