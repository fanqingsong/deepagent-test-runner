import EditableCell from './EditableCell';
import BrowserStream from '../BrowserStream';
import './studio-shared.css';

export default function StudioPlanTab({
  // Plan data
  editedSteps, viewedSteps, hasPlan, planEdited, stepsSaved,
  // Editing
  editingCell, editDraft, startEdit, commitEdit, cancelEdit, handleEditKeyDown, setEditDraft,
  // Actions
  onGeneratePlan, onSaveSteps, onRun, isBusy, isRunning, isGenerating, isSavingSteps,
  formGoal,
  // Progress
  runningJobId, progressSteps, progressCurrent, progressTotal,
  browserUrl, browserTitle, selectedScreenshot, onSelectScreenshot,
  // Result
  hasResult, resultSteps, latestResult,
  // Versions
  stepVersions, viewingVersionId, onViewVersion, onRestoreVersion, onBackToCurrent,
}) {
  return (
    <div style={{ padding: '20px' }}>
      {!hasPlan && !hasResult && !isRunning && !isGenerating && (
        <div style={{ textAlign: 'center', padding: '48px', color: '#525252' }}>
          <p style={{ marginBottom: '16px' }}>No test plan yet. Generate one from your test goal.</p>
          <button
            className="studio-workspace-run-btn"
            onClick={onGeneratePlan}
            disabled={isBusy || !formGoal?.trim()}
          >
            Generate Plan
          </button>
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
        <div className="studio-section">
          <h3 className="studio-section-title">
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
          <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
            <button
              className="studio-workspace-secondary-btn"
              onClick={onGeneratePlan}
              disabled={isBusy}
            >
              Regenerate
            </button>
            <button
              className="studio-workspace-secondary-btn"
              onClick={onSaveSteps}
              disabled={!hasPlan || isBusy}
            >
              {isSavingSteps ? 'Saving...' : stepsSaved ? 'Saved' : 'Save Steps'}
            </button>
            <button
              className="studio-workspace-run-btn"
              onClick={() => onRun({ useExistingPlan: true })}
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
                  onClick={() => onViewVersion(v)}
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
                    onClick={() => onRestoreVersion(viewingVersionId)}
                  >
                    Restore this version
                  </button>
                  <button
                    className="studio-workspace-secondary-btn"
                    onClick={onBackToCurrent}
                  >
                    Back to current
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {hasResult && (
        <div className="studio-section">
          <h3 className="studio-section-title">
            Result: {latestResult.status === 'passed' ? 'PASSED' : 'FAILED'}
            <span style={{ fontWeight: 400, color: '#525252', fontSize: '13px', marginLeft: '8px' }}>
              {latestResult.passed}/{latestResult.total} steps
              {latestResult.duration ? ` (${latestResult.duration}s)` : ''}
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
              {latestResult.status === 'passed'
                ? 'All steps passed!'
                : 'Test failed. Edit the plan steps and click "Run Test" to retry.'}
            </p>
          )}
        </div>
      )}

      {isRunning && (
        <>
          <div className="studio-section">
            <BrowserStream
              jobId={runningJobId}
              isRunning={isRunning}
              progressSteps={progressSteps}
              onSelectScreenshot={onSelectScreenshot}
            />
          </div>
          <div className="studio-section">
            <h3 className="studio-section-title">
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
                            onClick={() => onSelectScreenshot(step.screenshot_path)}
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
  );
}
