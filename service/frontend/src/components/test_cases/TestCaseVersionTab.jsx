import './test-cases-shared.css';

export default function TestCaseVersionTab({
  stepVersions,
  viewingVersionId,
  viewedSteps,
  editedSteps,
  editingCell,
  editDraft,
  startEdit,
  commitEdit,
  cancelEdit,
  handleEditKeyDown,
  setEditDraft,
  onViewVersion,
  onRestoreVersion,
  onBackToCurrent,
}) {
  if (stepVersions.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '48px', color: '#8d8d8d' }}>
        No versions yet. Save steps or run tests to create version snapshots.
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <div className="test-case-section">
        <h3 className="test-case-section-title">
          Version History
          <span style={{ fontWeight: 400, color: '#525252', fontSize: '13px', marginLeft: '8px' }}>
            {stepVersions.length} versions
          </span>
        </h3>

        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '16px' }}>
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
        </div>

        {viewingVersionId && viewedSteps && (
          <>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <button
                className="test-case-workspace-restore-btn"
                onClick={() => onRestoreVersion(viewingVersionId)}
              >
                Restore this version
              </button>
              <button
                className="test-case-workspace-secondary-btn"
                onClick={onBackToCurrent}
              >
                Back to current
              </button>
            </div>
            <table className="test-case-workspace-steps-table">
              <thead>
                <tr>
                  <th className="th-step">#</th>
                  <th className="th-type">Type</th>
                  <th className="th-desc">Description</th>
                  <th className="th-verify">Verification</th>
                </tr>
              </thead>
              <tbody>
                {viewedSteps.map((step, i) => (
                  <tr key={i}>
                    <td className="td-step">{step.step_number || i + 1}</td>
                    <td className="td-type">{step.type}</td>
                    <td className="td-desc">{step.description || '-'}</td>
                    <td className="td-verify">{step.verification || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {!viewingVersionId && (
          <p style={{ color: '#525252', fontSize: '13px' }}>
            Click a version above to view its step snapshot.
          </p>
        )}
      </div>
    </div>
  );
}
