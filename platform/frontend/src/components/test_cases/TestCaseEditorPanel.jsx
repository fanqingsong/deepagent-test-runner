import { useState, useEffect, useRef, useCallback } from 'react';
import {
  getTestCase, updateTestCase, runTestCase, publishTestCase, getJobStatus,
  getTestCaseRunProgress, generateTestCasePlan, saveTestCasesSteps,
  getTestCaseRunHistory, getTestRunDetails, getTestCaseStepVersions,
  restoreTestCaseStepVersion,
} from '../../api';
import PermissionGate from '../PermissionGate';
import TestCaseConfigTab from './TestCaseConfigTab';
import TestCasePlanTab from './TestCasePlanTab';
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

const REVIEW_STATUS_LABELS = {
  draft: 'Draft',
  pending_review: 'Pending Review',
  approved: 'Approved',
  rejected: 'Rejected',
};

const TABS = [
  { key: 'config', label: 'Configuration' },
  { key: 'plan', label: 'Test Steps' },
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
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSavingSteps, setIsSavingSteps] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [stepsSaved, setStepsSaved] = useState(false);
  const pollingRef = useRef(null);

  // Form state
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formGoal, setFormGoal] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [configDirty, setConfigDirty] = useState(false);

  // Plan editing state
  const [editedSteps, setEditedSteps] = useState([]);
  const [editingCell, setEditingCell] = useState(null);
  const [editDraft, setEditDraft] = useState('');
  const [planEdited, setPlanEdited] = useState(false);

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

  // Step versions
  const [stepVersions, setStepVersions] = useState([]);
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
      const steps = data.current_plan?.steps || [];
      setEditedSteps(steps.map(s => ({ ...s })));
      setPlanEdited(false);
      setStepsSaved(false);
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

  const loadStepVersions = useCallback(async () => {
    if (!testCaseId) return;
    try {
      const versions = await getTestCaseStepVersions(testCaseId);
      setStepVersions(versions);
    } catch { /* non-critical */ }
  }, [testCaseId]);

  useEffect(() => { loadStepVersions(); }, [loadStepVersions]);

  // Handlers
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

  const handleGeneratePlan = async () => {
    try {
      setIsGenerating(true);
      setError(null);
      if (configDirty) {
        await updateTestCase(testCaseId, {
          name: formName, url: formUrl,
          test_goal: formGoal, description: formDesc || null,
        });
        setConfigDirty(false);
      }
      await generateTestCasePlan(testCaseId);
      await loadTestCase();
      setActiveTab('plan');
    } catch (e) {
      setError(e.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveSteps = async () => {
    try {
      setIsSavingSteps(true);
      setError(null);
      if (planEdited) {
        await updateTestCase(testCaseId, {
          current_plan: { ...testCase.current_plan, steps: editedSteps },
        });
        setPlanEdited(false);
      }
      await saveTestCasesSteps(testCaseId);
      setStepsSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsSavingSteps(false);
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
          loadStepVersions();
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
      if (planEdited) {
        await updateTestCase(testCaseId, {
          current_plan: { ...testCase.current_plan, steps: editedSteps },
        });
        setPlanEdited(false);
      }
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

  // Inline editing
  const startEdit = (stepIdx, field, currentValue) => {
    setEditingCell({ stepIdx, field });
    setEditDraft(currentValue || '');
  };

  const commitEdit = () => {
    if (!editingCell) return;
    const { stepIdx, field } = editingCell;
    setEditedSteps(prev => {
      const next = [...prev];
      next[stepIdx] = { ...next[stepIdx], [field]: editDraft };
      return next;
    });
    setPlanEdited(true);
    setStepsSaved(false);
    setEditingCell(null);
    setEditDraft('');
  };

  const handleEditKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commitEdit(); }
    else if (e.key === 'Escape') { setEditingCell(null); setEditDraft(''); }
  };

  const onFormChange = (field) => (e) => {
    const setters = { name: setFormName, url: setFormUrl, goal: setFormGoal, desc: setFormDesc };
    setters[field](e.target.value);
    setConfigDirty(true);
  };

  // Run history expand
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

  // Version handlers
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
      await restoreTestCaseStepVersion(testCaseId, versionId);
      setViewingVersionId(null);
      setViewedSteps(null);
      await loadTestCase();
      loadStepVersions();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleBackToCurrent = () => {
    setViewingVersionId(null);
    setViewedSteps(null);
  };

  const isBusy = isRunning || isGenerating || isSavingSteps;
  const hasPlan = editedSteps.length > 0;
  const hasResult = testCase?.latest_result && testCase.latest_result.status;
  const canPublish = !['pending_review', 'published'].includes(testCase?.status) && !publishing;
  const latestResult = testCase?.latest_result || {};
  const resultSteps = latestResult.steps || [];

  // Empty state
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
      {/* Header */}
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
          {canPublish && (
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

      {/* Tabs */}
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

      {/* Content */}
      <div className="studio-editor-content">
        {activeTab === 'config' && (
          <TestCaseConfigTab
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
        {activeTab === 'plan' && (
          <TestCasePlanTab
            editedSteps={editedSteps}
            viewedSteps={viewedSteps}
            hasPlan={hasPlan}
            planEdited={planEdited}
            stepsSaved={stepsSaved}
            editingCell={editingCell}
            editDraft={editDraft}
            startEdit={startEdit}
            commitEdit={commitEdit}
            cancelEdit={() => { setEditingCell(null); setEditDraft(''); }}
            handleEditKeyDown={handleEditKeyDown}
            setEditDraft={setEditDraft}
            onGeneratePlan={handleGeneratePlan}
            onSaveSteps={handleSaveSteps}
            onRun={handleRun}
            isBusy={isBusy}
            isRunning={isRunning}
            isGenerating={isGenerating}
            isSavingSteps={isSavingSteps}
            formGoal={formGoal}
            runningJobId={runningJobId}
            progressSteps={progressSteps}
            progressCurrent={progressCurrent}
            progressTotal={progressTotal}
            browserUrl={browserUrl}
            browserTitle={browserTitle}
            selectedScreenshot={selectedScreenshot}
            onSelectScreenshot={setSelectedScreenshot}
            hasResult={hasResult}
            resultSteps={resultSteps}
            latestResult={latestResult}
            stepVersions={stepVersions}
            viewingVersionId={viewingVersionId}
            onViewVersion={handleViewVersion}
            onRestoreVersion={handleRestoreVersion}
            onBackToCurrent={handleBackToCurrent}
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
            stepVersions={stepVersions}
            viewingVersionId={viewingVersionId}
            viewedSteps={viewedSteps}
            editedSteps={editedSteps}
            editingCell={editingCell}
            editDraft={editDraft}
            startEdit={startEdit}
            commitEdit={commitEdit}
            cancelEdit={() => { setEditingCell(null); setEditDraft(''); }}
            handleEditKeyDown={handleEditKeyDown}
            setEditDraft={setEditDraft}
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
