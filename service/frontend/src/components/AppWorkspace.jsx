import { useState, useEffect, useRef, useCallback } from 'react';
import { getApp, updateApp, runApp, publishApp, getJobStatus, getAppRunProgress, generateAppPlan, saveAppSteps } from '../api';
import './AppWorkspace.css';

const STATUS_LABELS = {
  draft: 'Draft',
  generating: 'Generating',
  testing: 'Testing',
  passed: 'Passed',
  published: 'Published',
};

export default function AppWorkspace({ appId }) {
  const [app, setApp] = useState(null);
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

  const loadApp = useCallback(async () => {
    try {
      const data = await getApp(appId);
      setApp(data);
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
      if (!app) {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  }, [appId, app]);

  useEffect(() => {
    loadApp();
  }, [loadApp]);

  const pollJobStatus = async (jobId) => {
    let attempts = 0;
    const maxAttempts = 120;
    const poll = async () => {
      try {
        const job = await getJobStatus(jobId);
        try {
          const progress = await getAppRunProgress(appId);
          if (progress.completed_steps?.length > 0) {
            setProgressSteps(progress.completed_steps);
            setProgressCurrent(progress.current_step || 0);
            setProgressTotal(progress.total_steps || 0);
          }
        } catch { /* best-effort */ }

        if (job.status === 'completed' || attempts >= maxAttempts) {
          setIsRunning(false);
          setProgressSteps([]);
          setProgressCurrent(0);
          setProgressTotal(0);
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = null;
          await loadApp();
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
      await updateApp(appId, {
        name: formName,
        url: formUrl,
        test_goal: formGoal,
        description: formDesc || null,
      });
      setConfigDirty(false);
      await loadApp();
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
        await updateApp(appId, {
          name: formName,
          url: formUrl,
          test_goal: formGoal,
          description: formDesc || null,
        });
        setConfigDirty(false);
      }
      await generateAppPlan(appId);
      await loadApp();
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
        await updateApp(appId, {
          current_plan: { ...app.current_plan, steps: editedSteps },
        });
        setPlanEdited(false);
      }
      await saveAppSteps(appId);
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
        await updateApp(appId, {
          current_plan: { ...app.current_plan, steps: editedSteps },
        });
        setPlanEdited(false);
      }
      const result = await runApp(appId, {
        forceRegenerate: !!opts.forceRegenerate,
        useExistingPlan: !!opts.useExistingPlan,
      });
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
      await publishApp(appId);
      await loadApp();
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

  if (loading) return <div className="app-workspace-loading">Loading...</div>;
  if (!app) return <div className="app-workspace-error">App not found</div>;

  const hasPlan = editedSteps.length > 0;
  const hasResult = app.latest_result && app.latest_result.status;
  const canPublish = app.status === 'passed' && !publishing;
  const resultSteps = app.latest_result?.steps || [];

  return (
    <div className="app-workspace">
      {/* Header */}
      <div className="app-workspace-header">
        <button className="app-workspace-back" onClick={() => { window.location.hash = 'apps'; }}>
          &larr; Back
        </button>
        <div className="app-workspace-header-info">
          <h1 className="app-workspace-name">{app.name}</h1>
        </div>
        <div className="app-workspace-header-actions">
          <span className={`app-workspace-status-badge status-${app.status}`}>
            {STATUS_LABELS[app.status] || app.status}
          </span>
          {canPublish && (
            <button className="app-workspace-publish-btn" onClick={handlePublish} disabled={publishing}>
              {publishing ? 'Saving...' : 'Save to Tests'}
            </button>
          )}
          {app.status === 'published' && (
            <span className="app-workspace-published-tag">Saved to Tests</span>
          )}
        </div>
      </div>

      <div className="app-workspace-body">
        {/* Left panel: config */}
        <div className="app-workspace-left">
          <div className="app-workspace-left-form">
            <div className="app-workspace-field-group">
              <label className="app-workspace-field-label">Name</label>
              <input
                className="app-workspace-field-input"
                value={formName}
                onChange={onFormChange(setFormName)}
                disabled={isBusy}
              />
            </div>
            <div className="app-workspace-field-group">
              <label className="app-workspace-field-label">Target URL</label>
              <input
                className="app-workspace-field-input"
                value={formUrl}
                onChange={onFormChange(setFormUrl)}
                placeholder="https://example.com"
                disabled={isBusy}
              />
            </div>
            <div className="app-workspace-field-group">
              <label className="app-workspace-field-label">Test Goal</label>
              <textarea
                className="app-workspace-field-textarea"
                value={formGoal}
                onChange={onFormChange(setFormGoal)}
                placeholder="Describe what to test..."
                rows={4}
                disabled={isBusy}
              />
            </div>
            <div className="app-workspace-field-group">
              <label className="app-workspace-field-label">Description</label>
              <textarea
                className="app-workspace-field-textarea"
                value={formDesc}
                onChange={onFormChange(setFormDesc)}
                placeholder="Optional description..."
                rows={2}
                disabled={isBusy}
              />
            </div>
          </div>
          <div className="app-workspace-left-actions">
            <button
              className="app-workspace-save-config-btn"
              onClick={handleSaveConfig}
              disabled={!configDirty || savingConfig || isBusy}
            >
              {savingConfig ? 'Saving...' : 'Save Config'}
            </button>
            <button
              className="app-workspace-generate-btn"
              onClick={handleGeneratePlan}
              disabled={isBusy || !formGoal.trim()}
            >
              {isGenerating ? 'Generating...' : 'Generate Plan'}
            </button>
          </div>
        </div>

        {/* Right panel: plan + results */}
        <div className="app-workspace-right">
          {error && (
            <div className="app-workspace-msg-error">{error}</div>
          )}

          {!hasPlan && !hasResult && !isRunning && !isGenerating && (
            <div className="app-workspace-empty">
              <p>Configure your APP on the left, then click <strong>Generate Plan</strong> to create a test plan from your goal.</p>
            </div>
          )}

          {isGenerating && !hasPlan && (
            <div className="app-workspace-running">
              <div className="app-workspace-typing">
                <span></span><span></span><span></span>
              </div>
              <span className="app-workspace-running-text">Generating test plan...</span>
            </div>
          )}

          {hasPlan && (
            <div className="app-workspace-section">
              <h3 className="app-workspace-section-title">
                Test Plan
                {stepsSaved && <span className="app-workspace-saved-tag">Saved</span>}
              </h3>
              <table className="app-workspace-steps-table">
                <thead>
                  <tr>
                    <th className="th-step">#</th>
                    <th className="th-type">Type</th>
                    <th className="th-desc">Description</th>
                    <th className="th-verify">Verification</th>
                  </tr>
                </thead>
                <tbody>
                  {editedSteps.map((step, i) => (
                    <tr key={i}>
                      <td className="td-step">{step.step_number || i + 1}</td>
                      <td className="td-type">{step.type}</td>
                      <td className="td-desc">
                        <EditableCell
                          value={step.description}
                          editing={editingCell?.stepIdx === i && editingCell?.field === 'description'}
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
                          editing={editingCell?.stepIdx === i && editingCell?.field === 'verification'}
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
              <div className="app-workspace-plan-actions">
                <button
                  className="app-workspace-secondary-btn"
                  onClick={handleGeneratePlan}
                  disabled={isBusy}
                >
                  Regenerate
                </button>
                <button
                  className="app-workspace-secondary-btn"
                  onClick={handleSaveSteps}
                  disabled={!hasPlan || isBusy}
                >
                  {isSavingSteps ? 'Saving...' : stepsSaved ? 'Saved' : 'Save Steps'}
                </button>
                <button
                  className="app-workspace-run-btn"
                  onClick={() => handleRun({ useExistingPlan: true })}
                  disabled={!hasPlan || isBusy}
                >
                  {isRunning ? 'Running...' : 'Run Test'}
                </button>
              </div>
            </div>
          )}

          {app.status === 'passed' && (
            <div className="app-workspace-section app-workspace-autosave-info">
              Steps saved automatically after test passed.
            </div>
          )}

          {hasResult && (
            <div className="app-workspace-section">
              <h3 className="app-workspace-section-title">
                Result: {app.latest_result.status === 'passed' ? 'PASSED' : 'FAILED'}
                <span className="app-workspace-result-counts">
                  {' '}{app.latest_result.passed}/{app.latest_result.total} steps
                  {app.latest_result.duration ? ` (${app.latest_result.duration}s)` : ''}
                </span>
              </h3>
              {resultSteps.length > 0 ? (
                <table className="app-workspace-steps-table">
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
                <p className="app-workspace-result-text">
                  {app.latest_result.status === 'passed'
                    ? 'All steps passed!'
                    : 'Test failed. Edit the plan steps and click "Run Test" to retry.'}
                </p>
              )}
            </div>
          )}

          {isRunning && (
            <div className="app-workspace-section">
              <h3 className="app-workspace-section-title">
                Running
                <span className="app-workspace-progress-counts">
                  {' '}{progressCurrent}/{progressTotal || '?'} steps completed
                </span>
              </h3>
              {progressSteps.length > 0 ? (
                <table className="app-workspace-steps-table">
                  <thead>
                    <tr>
                      <th className="th-step">#</th>
                      <th className="th-desc">Step</th>
                      <th className="th-status">Status</th>
                      <th className="th-duration">Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {progressSteps.map((step, i) => (
                      <tr key={i} className={`row-${step.status}`}>
                        <td className="td-step">{step.step_number || i + 1}</td>
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
                        <td className="td-desc" colSpan={3}>
                          <span className="app-workspace-typing">
                            <span></span><span></span><span></span>
                          </span>
                          <span className="app-workspace-running-text">executing...</span>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              ) : (
                <div className="app-workspace-running">
                  <div className="app-workspace-typing">
                    <span></span><span></span><span></span>
                  </div>
                  <span className="app-workspace-running-text">Generating test plan...</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EditableCell({ value, editing, draft, onStartEdit, onDraftChange, onKeyDown, onBlur }) {
  if (editing) {
    return (
      <input
        className="app-workspace-edit-input"
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={onBlur}
        autoFocus
      />
    );
  }
  return (
    <span className="app-workspace-editable-cell" onClick={onStartEdit}>
      {value || '-'}
    </span>
  );
}
