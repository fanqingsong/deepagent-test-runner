import { useState } from 'react';
import { submitVersionForReview } from '../../api';
import PermissionGate from '../PermissionGate';
import './test-cases-shared.css';

const REVIEW_STATUS_LABELS = {
  draft: 'Draft',
  pending_review: 'Pending Review',
  approved: 'Approved',
  rejected: 'Rejected',
};

const REVIEW_STATUS_COLORS = {
  draft: '#8d8d8d',
  pending_review: '#f1c21b',
  approved: '#198038',
  rejected: '#da1e28',
};

export default function TestCaseVersionTab({
  testCaseId,
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
  onVersionSubmitted,
}) {
  const [submittingId, setSubmittingId] = useState(null);

  const handleSubmitForReview = async (version) => {
    try {
      setSubmittingId(version.id);
      await submitVersionForReview(testCaseId, version.id);
      if (onVersionSubmitted) onVersionSubmitted();
    } catch (e) {
      alert(e.message);
    } finally {
      setSubmittingId(null);
    }
  };

  if (stepVersions.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '48px', color: '#8d8d8d' }}>
        No versions yet. Save steps or run tests to create version snapshots.
      </div>
    );
  }

  const viewedVersion = stepVersions.find(v => v.id === viewingVersionId);

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
              className={`test-case-workspace-version-tag ${
                viewingVersionId === v.id ? 'test-case-workspace-version-tag--active' : ''
              } ${v.run_status ? `test-case-workspace-version-tag--${v.run_status}` : ''}`}
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
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
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

              {viewedVersion && (
                <>
                  <span style={{
                    display: 'inline-block',
                    padding: '1px 10px',
                    fontSize: '11px',
                    fontWeight: 600,
                    color: '#fff',
                    background: REVIEW_STATUS_COLORS[viewedVersion.review_status || 'draft'],
                    marginLeft: '8px',
                  }}>
                    {REVIEW_STATUS_LABELS[viewedVersion.review_status || 'draft']}
                  </span>

                  <PermissionGate permission="update:app">
                    {(viewedVersion.review_status === 'draft' || viewedVersion.review_status === 'rejected') && (
                      <button
                        className="test-case-workspace-run-btn"
                        style={{ height: '28px', fontSize: '12px', padding: '0 12px' }}
                        onClick={() => handleSubmitForReview(viewedVersion)}
                        disabled={submittingId === viewedVersion.id}
                      >
                        {submittingId === viewedVersion.id ? 'Submitting...' : 'Submit for Review'}
                      </button>
                    )}
                  </PermissionGate>

                  {viewedVersion.review_status === 'rejected' && viewedVersion.rejection_reason && (
                    <span style={{ fontSize: '12px', color: '#da1e28', marginLeft: '4px' }}>
                      Reason: {viewedVersion.rejection_reason}
                    </span>
                  )}
                </>
              )}
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
