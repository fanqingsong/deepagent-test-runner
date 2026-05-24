import { useState, useEffect, useRef, useCallback } from 'react';
import { getStudio, updateStudio, runStudio, publishStudio, getJobStatus, getStudioRunProgress, generateStudioPlan, saveStudioSteps, getStudioRunHistory, getTestRunDetails, getStudioStepVersions, restoreStudioStepVersion } from '../api';
import BrowserStream from './BrowserStream';
import './StudioWorkspace.css';

const STATUS_LABELS = {
  draft: 'Draft',
  generating: 'Generating',
  testing: 'Testing',
  passed: 'Passed',
  published: 'Published',
};

export default function StudioWorkspace({ studioId }) {
  const [studio, setStudio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSavingSteps, setIsSavingSteps] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [stepsSaved, setStepsSaved] = useState(false);
  const pollingRef = useRef(null);

  // Left panel form state
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formGoal, setFormGoal] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [configDirty, setConfigDirty] = useState(false);

  // Right panel plan editing state
  const [editedSteps, setEditedSteps] = useState([]);
  const [editingCell, setEditingCell] = useState(null); // { stepIdx, field }
  const [editDraft, setEditDraft] = useState('');
  const [planEdited, setPlanEdited] = useState(false);

  // Streaming progress state
  const [progressSteps, setProgressSteps] = useState([]);
  const [progressCurrent, setProgressCurrent] = useState(0);
  const [progressTotal, setProgressTotal] = useState(0);
  const [browserUrl, setBrowserUrl] = useState('');
  const [browserTitle, setBrowserTitle] = useState('');
  const [selectedScreenshot, setSelectedScreenshot] = useState(null);
  const [runningJobId, setRunningJobId] = useState(null);

  // Run history state
  const [runHistory, setRunHistory] = useState([]);
  const [runHistoryLoading, setRunHistoryLoading] = useState(false);
  const [expandedRunId, setExpandedRunId] = useState(null);
  const [expandedRunCases, setExpandedRunCases] = useState([]);
  const [expandedRunLoading, setExpandedRunLoading] = useState(false);

  // Step version state
  const [stepVersions, setStepVersions] = useState([]);
  const [viewingVersionId, setViewingVersionId] = useState(null);
  const [viewedSteps, setViewedSteps] = useState(null);

  const loadStudio = useCallback(async () => {
    try {
      const data = await getStudio(studioId);
      setStudio(data);
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
  }, [studioId]);

  useEffect(() => {
    loadStudio();
  }, [loadStudio]);

  const loadRunHistory = useCallback(async () => {
    if (!studioId) return;
    try {
      setRunHistoryLoading(true);
      const runs = await getStudioRunHistory(studioId, { limit: 50 });
      setRunHistory(runs);
    } catch {
      /* non-critical */
    } finally {
      setRunHistoryLoading(false);
    }
  }, [studioId]);

  useEffect(() => {
    loadRunHistory();
  }, [loadRunHistory]);

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
    } catch {
      setExpandedRunCases([]);
    } finally {
      setExpandedRunLoading(false);
    }
  };

  const loadStepVersions = useCallback(async () => {
    if (!studioId) return;
    try {
      const versions = await getStudioStepVersions(studioId);
      setStepVersions(versions);
    } catch {
      /* non-critical */
    }
  }, [studioId]);

  useEffect(() => {
    loadStepVersions();
  }, [loadStepVersions]);

  const handleViewVersion = (version) => {
    if (viewingVersionId === version.id) {
      setViewingVersionId(null);
      setViewedSteps(null);
      return;
    }
    setViewingVersionId(version.id);
    const snapshotSteps = (version.snapshot?.steps || []).map(s => ({ ...s }));
    setViewedSteps(snapshotSteps);
  };

  const handleRestoreVersion = async (versionId) => {
    try {
      setError(null);
      await restoreStudioStepVersion(studioId, versionId);
      setViewingVersionId(null);
      setViewedSteps(null);
      await loadStudio();
      loadStepVersions();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleBackToCurrent = () => {
    setViewingVersionId(null);
    setViewedSteps(null);
  };

  const pollJobStatus = async (jobId) => {
    let attempts = 0;
    const maxAttempts = 120;
    const poll = async () => {
      try {
        const job = await getJobStatus(jobId);
        try {
          const progress = await getStudioRunProgress(studioId);
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
          await loadStudio();
          loadRunHistory();
          loadStepVersions();
          return;
        }
        attempts++;
      } catch {
        attempts++;
      }
    };
    pollingRef.current = setInterval(poll, 2000);
  };

  const handleSaveConfig = async () => {
    try {
      setSavingConfig(true);
      setError(null);
      await updateStudio(studioId, {
        name: formName,
        url: formUrl,
        test_goal: formGoal,
        description: formDesc || null,
      });
      setConfigDirty(false);
      await loadStudio();
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
      // Save config first if dirty
      if (configDirty) {
        await updateStudio(studioId, {
          name: formName,
          url: formUrl,
          test_goal: formGoal,
          description: formDesc || null,
        });
        setConfigDirty(false);
      }
      await generateStudioPlan(studioId);
      await loadStudio();
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
      // Push edited steps to current_plan first
      if (planEdited) {
        await updateStudio(studioId, {
          current_plan: { ...studio.current_plan, steps: editedSteps },
        });
        setPlanEdited(false);
      }
      await saveStudioSteps(studioId);
      setStepsSaved(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsSavingSteps(false);
    }
  };

  const handleRun = async (opts = {}) => {
    try {
      setIsRunning(true);
      setError(null);
      // Sync edits before running
      if (planEdited) {
        await updateStudio(studioId, {
          current_plan: { ...studio.current_plan, steps: editedSteps },
        });
        setPlanEdited(false);
      }
      const result = await runStudio(studioId, {
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
      await publishStudio(studioId);
      await loadStudio();
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

  const cancelEdit = () => {
    setEditingCell(null);
    setEditDraft('');
  };

  const handleEditKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      commitEdit();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  };

  const onFormChange = (setter) => (e) => {
    setter(e.target.value);
    setConfigDirty(true);
  };

  const isBusy = isRunning || isGenerating || isSavingSteps;

  if (loading) return <div className="studio-workspace-loading">Loading...</div>;
  if (!studio) return <div className="studio-workspace-error">Studio not found</div>;

  const hasPlan = editedSteps.length > 0;
  const hasResult = studio.latest_result && studio.latest_result.status;
  const canPublish = studio.status === 'passed' && !publishing;
  const resultSteps = studio.latest_result?.steps || [];

  return (
    <div className="studio-workspace">
      {/* Header */}
      <div className="studio-workspace-header">
        <button className="studio-workspace-back" onClick={() => { window.location.hash = "studios"; }}>
          &larr; Back
        </button>
        <div className="studio-workspace-header-info">
          <h1 className="studio-workspace-name">{studio.name}</h1>
        </div>
        <div className="studio-workspace-header-actions">
          <span className={`studio-workspace-status-badge status-${studio.status}`}>
            {STATUS_LABELS[studio.status] || studio.status}
          </span>
          {canPublish && (
            <button className="studio-workspace-publish-btn" onClick={handlePublish} disabled={publishing}>
              {publishing ? 'Saving...' : 'Save to Tests'}
            </button>
          )}
          {studio.status === 'published' && (
            <span className="studio-workspace-published-tag">Saved to Tests</span>
          )}
        </div>
      </div>

      <div className="studio-workspace-body">
        {/* Left panel: config */}
        <div className="studio-workspace-left">
          <div className="studio-workspace-left-form">
            <div className="studio-workspace-field-group">
              <label className="studio-workspace-field-label">Name</label>
              <input
                className="studio-workspace-field-input"
                value={formName}
                onChange={onFormChange(setFormName)}
                disabled={isBusy}
              />
            </div>
            <div className="studio-workspace-field-group">
              <label className="studio-workspace-field-label">Target URL</label>
              <input
                className="studio-workspace-field-input"
                value={formUrl}
                onChange={onFormChange(setFormUrl)}
                placeholder="https://example.com"
                disabled={isBusy}
              />
            </div>
            <div className="studio-workspace-field-group">
              <label className="studio-workspace-field-label">Test Goal</label>
              <textarea
                className="studio-workspace-field-textarea"
                value={formGoal}
                onChange={onFormChange(setFormGoal)}
                placeholder="Describe what to test..."
                rows={4}
                disabled={isBusy}
              />
            </div>
            <div className="studio-workspace-field-group">
              <label className="studio-workspace-field-label">Description</label>
              <textarea
                className="studio-workspace-field-textarea"
                value={formDesc}
                onChange={onFormChange(setFormDesc)}
                placeholder="Optional description..."
                rows={2}
                disabled={isBusy}
              />
            </div>
          </div>
          <div className="studio-workspace-left-actions">
            <button
              className="studio-workspace-save-config-btn"
              onClick={handleSaveConfig}
              disabled={!configDirty || savingConfig || isBusy}
            >
              {savingConfig ? 'Saving...' : 'Save Config'}
            </button>
            <button
              className="studio-workspace-generate-btn"
              onClick={handleGeneratePlan}
              disabled={isBusy || !formGoal.trim()}
            >
              {isGenerating ? 'Generating...' : 'Generate Plan'}
            </button>
          </div>
        </div>

        {/* Right panel: plan + results */}
        <div className="studio-workspace-right">
          {error && (
            <div className="studio-workspace-msg-error">{error}</div>
          )}

          {!hasPlan && !hasResult && !isRunning && !isGenerating && (
            <div className="studio-workspace-empty">
              <p>Configure your Studio on the left, then click <strong>Generate Plan</strong> to create a test plan from your goal.</p>
            </div>
          )}

          {isGenerating && !hasPlan && (
            <div className="studio-workspace-running">
              <div className="studio-workspace-typing">
                <span></span><span></span><span></span>
              </div>
              <span className="studio-workspace-running-text">Generating test plan...</span>
            </div>
          )}

          {hasPlan && (
            <div className="studio-workspace-section">
              <h3 className="studio-workspace-section-title">
                Test Plan
                {viewingVersionId && <span className="studio-workspace-viewing-tag">Viewing past version</span>}
                {!viewingVersionId && stepsSaved && <span className="studio-workspace-saved-tag">Saved</span>}
              </h3>
              <table className="studio-workspace-steps-table">
                <thead>
                  <tr>
                    <th className="th-step">#</th>
                    <th className="th-type">Type</th>
                    <th className="th-desc">Description</th>
                    <th className="th-verify">Verification</th>
                  </tr>
                </thead>
                <tbody>
                  {(viewedSteps || editedSteps).map((step, i) => (
                    <tr key={i}>
                      <td className="td-step">{step.step_number || i + 1}</td>
                      <td className="td-type">{step.type}</td>
                      <td className="td-desc">
                        <EditableCell
                          value={step.description}
                          editing={!viewingVersionId && editingCell?.stepIdx === i && editingCell?.field === 'description'}
                          draft={editDraft}
                          onStartEdit={() => startEdit(i, 'description', step.description)}
                          onDraftChange={setEditDraft}
                          onKeyDown={handleEditKeyDown}
                          onBlur={commitEdit}
                        />
                      </td>
                      <td className="td-verify">
                        <EditableCell
                          value={step.verification}
                          editing={!viewingVersionId && editingCell?.stepIdx === i && editingCell?.field === 'verification'}
                          draft={editDraft}
                          onStartEdit={() => startEdit(i, 'verification', step.verification)}
                          onDraftChange={setEditDraft}
                          onKeyDown={handleEditKeyDown}
                          onBlur={commitEdit}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="studio-workspace-plan-actions">
                <button
                  className="studio-workspace-secondary-btn"
                  onClick={handleGeneratePlan}
                  disabled={isBusy}
                >
                  Regenerate
                </button>
                <button
                  className="studio-workspace-secondary-btn"
                  onClick={handleSaveSteps}
                  disabled={!hasPlan || isBusy}
                >
                  {isSavingSteps ? 'Saving...' : stepsSaved ? 'Saved' : 'Save Steps'}
                </button>
                <button
                  className="studio-workspace-run-btn"
                  onClick={() => handleRun({ useExistingPlan: true })}
                  disabled={!hasPlan || isBusy}
                >
                  {isRunning ? 'Running...' : 'Run Test'}
                </button>
              </div>
              {stepVersions.length > 0 && (
                <div className="studio-workspace-version-bar">
                  <span className="studio-workspace-version-label">Versions:</span>
                  {stepVersions.map(v => (
                    <button
                      key={v.id}
                      className={`studio-workspace-version-tag ${
                        viewingVersionId === v.id ? 'studio-workspace-version-tag--active' : ''
                      } ${v.run_status ? `studio-workspace-version-tag--${v.run_status}` : ''}`}
                      onClick={() => handleViewVersion(v)}
                      title={v.change_description || `v${v.version}`}
                    >
                      v{v.version}
                      {v.run_status && (
                        <span className={`version-status-badge version-status-${v.run_status}`}>
                          {v.run_status === 'passed' ? '✓' : '✗'}
                        </span>
                      )}
                    </button>
                  ))}
                  {viewingVersionId && (
                    <>
                      <button
                        className="studio-workspace-restore-btn"
                        onClick={() => handleRestoreVersion(viewingVersionId)}
                      >
                        Restore this version
                      </button>
                      <button
                        className="studio-workspace-secondary-btn"
                        onClick={handleBackToCurrent}
                      >
                        Back to current
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {studio.status === 'passed' && (
            <div className="studio-workspace-section studio-workspace-autosave-info">
              Steps saved automatically after test passed.
            </div>
          )}

          {hasResult && (
            <div className="studio-workspace-section">
              <h3 className="studio-workspace-section-title">
                Result: {studio.latest_result.status === 'passed' ? 'PASSED' : 'FAILED'}
                <span className="studio-workspace-result-counts">
                  {' '}{studio.latest_result.passed}/{studio.latest_result.total} steps
                  {studio.latest_result.duration ? ` (${studio.latest_result.duration}s)` : ''}
                </span>
              </h3>
              {resultSteps.length > 0 ? (
                <table className="studio-workspace-steps-table">
                  <thead>
                    <tr>
                      <th className="th-step">#</th>
                      <th className="th-desc">Step</th>
                      <th className="th-status">Status</th>
                      <th className="th-duration">Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultSteps.map((step, i) => (
                      <tr key={i} className={`row-${step.status}`}>
                        <td className="td-step">{i + 1}</td>
                        <td className="td-desc">
                          {step.description}
                          {step.error && <span className="step-error">{step.error}</span>}
                        </td>
                        <td className="td-status">
                          <span className={`step-badge step-${step.status}`}>
                            {step.status === 'passed' ? '✓' : step.status === 'failed' ? '✗' : '·'}
                          </span>
                        </td>
                        <td className="td-duration">{step.duration ? `${step.duration}ms` : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="studio-workspace-result-text">
                  {studio.latest_result.status === 'passed'
                    ? 'All steps passed!'
                    : 'Test failed. Edit the plan steps and click "Run Test" to retry.'}
                </p>
              )}
            </div>
          )}

          {runHistory.length > 0 && (
            <div className="studio-workspace-section">
              <h3 className="studio-workspace-section-title">
                Run History
                <span className="studio-workspace-result-counts">
                  {' '}{runHistory.length} runs
                </span>
              </h3>
              <table className="studio-workspace-steps-table">
                <thead>
                  <tr>
                    <th className="th-status">Status</th>
                    <th className="th-desc">Run</th>
                    <th className="th-steps-count">Steps</th>
                    <th className="th-duration">Duration</th>
                    <th className="th-time">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {runHistory.map((run) => (
                    <RunHistoryRow
                      key={run.run_id}
                      run={run}
                      isExpanded={expandedRunId === run.run_id}
                      expandedCases={expandedRunCases}
                      expandedLoading={expandedRunLoading}
                      onToggle={() => handleToggleRunExpand(run.run_id)}
                      onSelectScreenshot={setSelectedScreenshot}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {isRunning && (
            <>
              <div className="studio-workspace-section">
                <BrowserStream
                  jobId={runningJobId}
                  isRunning={isRunning}
                  progressSteps={progressSteps}
                  onSelectScreenshot={setSelectedScreenshot}
                />
              </div>

              <div className="studio-workspace-section">
                <h3 className="studio-workspace-section-title">
                  Running
                  <span className="studio-workspace-progress-counts">
                    {' '}{progressCurrent}/{progressTotal || '?'} steps completed
                  </span>
                </h3>
                {progressSteps.length > 0 ? (
                  <table className="studio-workspace-steps-table">
                    <thead>
                      <tr>
                        <th className="th-step">#</th>
                        <th className="th-screenshot">Preview</th>
                        <th className="th-desc">Step</th>
                        <th className="th-status">Status</th>
                        <th className="th-duration">Duration</th>
                      </tr>
                    </thead>
                    <tbody>
                      {progressSteps.map((step, i) => (
                        <tr key={i} className={`row-${step.status}`}>
                          <td className="td-step">{step.step_number || i + 1}</td>
                          <td className="td-screenshot">
                            {step.screenshot_path ? (
                              <button
                                className="step-screenshot-thumb"
                                onClick={() => setSelectedScreenshot(step.screenshot_path)}
                                title="Click to enlarge"
                              >
                                <img src={step.screenshot_path} alt={`Step ${step.step_number}`} />
                              </button>
                            ) : (
                              <span className="step-screenshot-placeholder">-</span>
                            )}
                          </td>
                          <td className="td-desc">
                            {step.description || `Step ${i + 1}`}
                            {step.error && <span className="step-error">{step.error}</span>}
                          </td>
                          <td className="td-status">
                            <span className={`step-badge step-${step.status}`}>
                              {step.status === 'passed' ? '✓' : step.status === 'failed' ? '✗' : '...'}
                            </span>
                          </td>
                          <td className="td-duration">{step.duration ? `${step.duration}ms` : '-'}</td>
                        </tr>
                      ))}
                      {progressTotal > progressSteps.length && (
                        <tr className="row-pending">
                          <td className="td-step">{progressSteps.length + 1}</td>
                          <td className="td-desc" colSpan={4}>
                            <span className="studio-workspace-typing">
                              <span></span><span></span><span></span>
                            </span>
                            <span className="studio-workspace-running-text">executing...</span>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                ) : (
                  <div className="studio-workspace-running">
                    <div className="studio-workspace-typing">
                      <span></span><span></span><span></span>
                    </div>
                    <span className="studio-workspace-running-text">Generating test plan...</span>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
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

function EditableCell({ value, editing, draft, onStartEdit, onDraftChange, onKeyDown, onBlur }) {
  if (editing) {
    return (
      <input
        className="studio-workspace-edit-input"
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={onBlur}
        autoFocus
      />
    );
  }
  return (
    <span className="studio-workspace-editable-cell" onClick={onStartEdit}>
      {value || '-'}
    </span>
  );
}

function BrowserPreview({ latestScreenshot, browserUrl, browserTitle, progressSteps, onSelectScreenshot }) {
  const stepsWithScreenshots = progressSteps.filter(s => s.screenshot_path);

  return (
    <div className="browser-preview">
      <div className="browser-preview-chrome">
        <div className="browser-preview-dots">
          <span className="browser-preview-dot"></span>
          <span className="browser-preview-dot"></span>
          <span className="browser-preview-dot"></span>
        </div>
        <div className="browser-preview-url-bar">
          {browserUrl || 'about:blank'}
        </div>
      </div>

      <div className="browser-preview-viewport">
        {latestScreenshot ? (
          <img
            src={latestScreenshot}
            alt="Latest browser state"
            className="browser-preview-screenshot"
          />
        ) : (
          <div className="browser-preview-placeholder">
            Waiting for first screenshot...
          </div>
        )}
      </div>

      <div className="browser-preview-status">
        {browserTitle && (
          <span className="browser-preview-title">{browserTitle}</span>
        )}
      </div>

      {stepsWithScreenshots.length > 0 && (
        <div className="browser-preview-thumbnails">
          {stepsWithScreenshots.map((step, i) => (
            <button
              key={i}
              className={`browser-preview-thumb ${
                step.screenshot_path === latestScreenshot ? 'browser-preview-thumb--active' : ''
              }`}
              onClick={() => onSelectScreenshot(step.screenshot_path)}
              title={`Step ${step.step_number}: ${step.description}`}
            >
              <img src={step.screenshot_path} alt={`Step ${step.step_number}`} />
              <span className={`browser-preview-thumb-badge step-${step.status}`}>
                {step.step_number}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ScreenshotLightbox({ src, onClose }) {
  if (!src) return null;
  return (
    <div className="screenshot-lightbox-overlay" onClick={onClose}>
      <div className="screenshot-lightbox-content" onClick={(e) => e.stopPropagation()}>
        <button className="screenshot-lightbox-close" onClick={onClose}>x</button>
        <img src={src} alt="Screenshot detail" className="screenshot-lightbox-image" />
      </div>
    </div>
  );
}

function RunHistoryRow({ run, isExpanded, expandedCases, expandedLoading, onToggle, onSelectScreenshot }) {
  const shortRunId = run.run_id ? run.run_id.slice(0, 8) : '-';
  const timeStr = run.created_at
    ? new Date(run.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '-';
  const durStr = run.total_duration != null ? `${(run.total_duration / 1000).toFixed(1)}s` : '-';

  return (
    <>
      <tr className={`row-${run.status} run-history-row`} onClick={onToggle} style={{ cursor: 'pointer' }}>
        <td className="td-status">
          <span className={`step-badge step-${run.status}`}>
            {run.status === 'passed' ? '✓' : run.status === 'failed' ? '✗' : '·'}
          </span>
        </td>
        <td className="td-desc" style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px' }}>
          {shortRunId}
        </td>
        <td className="td-steps-count">
          {run.passed ?? 0}/{run.total_tests ?? 0}
        </td>
        <td className="td-duration">{durStr}</td>
        <td className="td-time">{timeStr}</td>
      </tr>
      {isExpanded && (
        <tr className="run-history-expanded">
          <td colSpan={5} style={{ padding: 0 }}>
            <div className="run-history-expanded-content">
              {expandedLoading ? (
                <div className="studio-workspace-running">
                  <div className="studio-workspace-typing"><span></span><span></span><span></span></div>
                  <span className="studio-workspace-running-text">Loading details...</span>
                </div>
              ) : expandedCases.length === 0 ? (
                <p className="studio-workspace-result-text">No step details available.</p>
              ) : (
                <table className="studio-workspace-steps-table">
                  <thead>
                    <tr>
                      <th className="th-step">#</th>
                      <th className="th-desc">Step</th>
                      <th className="th-status">Status</th>
                      <th className="th-duration">Duration</th>
                      <th className="th-screenshot">Screenshot</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expandedCases.map((tc, i) => (
                      <tr key={tc.id || i} className={`row-${tc.status}`}>
                        <td className="td-step">{i + 1}</td>
                        <td className="td-desc">
                          {tc.description || tc.test_id || `Step ${i + 1}`}
                          {tc.error_message && <span className="step-error">{tc.error_message}</span>}
                        </td>
                        <td className="td-status">
                          <span className={`step-badge step-${tc.status}`}>
                            {tc.status === 'passed' ? '✓' : tc.status === 'failed' ? '✗' : '·'}
                          </span>
                        </td>
                        <td className="td-duration">{tc.duration ? `${tc.duration}ms` : '-'}</td>
                        <td className="td-screenshot">
                          {tc.screenshot_path ? (
                            <button
                              className="step-screenshot-thumb"
                              onClick={(e) => { e.stopPropagation(); onSelectScreenshot(tc.screenshot_path); }}
                              title="Click to enlarge"
                            >
                              <img src={tc.screenshot_path} alt={`Step ${i + 1}`} />
                            </button>
                          ) : (
                            <span className="step-screenshot-placeholder">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
