import { useState, useEffect, useCallback } from 'react';
import { getStepVersions, restoreTestCaseVersion, submitVersionForReview } from '../../api';
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

const SCRIPT_STATUS_LABELS = {
  none: 'None',
  generating: 'Generating...',
  draft: 'Draft',
  validated: 'Validated',
  approved: 'Approved',
  failed: 'Failed',
};

export default function TestCaseVersionTab({
  testCaseId,
  onVersionRestored,
  onVersionSubmitted,
}) {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewingId, setViewingId] = useState(null);
  const [restoring, setRestoring] = useState(false);
  const [submittingId, setSubmittingId] = useState(null);
  const [error, setError] = useState(null);

  const loadVersions = useCallback(async () => {
    if (!testCaseId) return;
    try {
      setLoading(true);
      const data = await getStepVersions(testCaseId);
      setVersions(data);
    } catch { /* non-critical */ } finally {
      setLoading(false);
    }
  }, [testCaseId]);

  useEffect(() => { loadVersions(); }, [loadVersions]);

  const handleRestore = async () => {
    if (!viewingId) return;
    try {
      setRestoring(true);
      setError(null);
      await restoreTestCaseVersion(testCaseId, viewingId);
      setViewingId(null);
      onVersionRestored?.();
      loadVersions();
    } catch (e) {
      setError(e.message);
    } finally {
      setRestoring(false);
    }
  };

  const handleSubmitForReview = async (version) => {
    try {
      setSubmittingId(version.id);
      setError(null);
      await submitVersionForReview(testCaseId, version.id);
      onVersionSubmitted?.();
      loadVersions();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmittingId(null);
    }
  };

  const viewed = versions.find(v => v.id === viewingId);
  const snapshot = viewed?.snapshot || {};

  if (loading && versions.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '48px', color: '#525252' }}>
        Loading versions...
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '48px', color: '#8d8d8d' }}>
        No versions yet. Run a test or save changes to create version snapshots.
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <div className="test-case-section">
        <h3 className="test-case-section-title">
          Version History
          <span style={{ fontWeight: 400, color: '#525252', fontSize: '13px', marginLeft: '8px' }}>
            {versions.length} versions
          </span>
        </h3>

        {error && (
          <div style={{ padding: '8px 12px', background: '#fff1f1', color: '#da1e28', fontSize: '13px', marginBottom: '12px' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '16px' }}>
          {versions.map(v => (
            <button
              key={v.id}
              className={`test-case-workspace-version-tag ${
                viewingId === v.id ? 'test-case-workspace-version-tag--active' : ''
              } ${v.run_status ? `test-case-workspace-version-tag--${v.run_status}` : ''}`}
              onClick={() => setViewingId(viewingId === v.id ? null : v.id)}
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

        {viewingId && viewed && (
          <>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                className="test-case-workspace-restore-btn"
                onClick={handleRestore}
                disabled={restoring}
              >
                {restoring ? 'Restoring...' : 'Restore this version'}
              </button>
              <button
                className="test-case-workspace-secondary-btn"
                onClick={() => setViewingId(null)}
              >
                Back to current
              </button>

              <span style={{
                display: 'inline-block',
                padding: '1px 10px',
                fontSize: '11px',
                fontWeight: 600,
                color: '#fff',
                background: REVIEW_STATUS_COLORS[viewed.review_status || 'draft'],
                marginLeft: '8px',
              }}>
                {REVIEW_STATUS_LABELS[viewed.review_status || 'draft']}
              </span>

              {(viewed.review_status === 'draft' || viewed.review_status === 'rejected') && (
                <button
                  className="test-case-workspace-run-btn"
                  style={{ height: '28px', fontSize: '12px', padding: '0 12px' }}
                  onClick={() => handleSubmitForReview(viewed)}
                  disabled={submittingId === viewed.id}
                >
                  {submittingId === viewed.id ? 'Submitting...' : 'Submit for Review'}
                </button>
              )}

              {viewed.review_status === 'rejected' && viewed.rejection_reason && (
                <span style={{ fontSize: '12px', color: '#da1e28', marginLeft: '4px' }}>
                  Reason: {viewed.rejection_reason}
                </span>
              )}
            </div>

            <div style={{ fontSize: '12px', color: '#525252', marginBottom: '8px' }}>
              {viewed.change_description || `Version ${viewed.version}`}
              {snapshot.script_status && (
                <span style={{ marginLeft: '12px', color: '#8d8d8d' }}>
                  Script: {SCRIPT_STATUS_LABELS[snapshot.script_status] || snapshot.script_status}
                </span>
              )}
            </div>

            {snapshot.playwright_script ? (
              <pre style={{
                width: '100%',
                maxHeight: '400px',
                padding: '16px',
                fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
                fontSize: '13px',
                lineHeight: '1.6',
                background: '#161616',
                color: '#f4f4f4',
                border: '1px solid #393939',
                overflow: 'auto',
                margin: 0,
                whiteSpace: 'pre-wrap',
              }}>
                {snapshot.playwright_script}
              </pre>
            ) : (
              <div style={{ padding: '24px', color: '#8d8d8d', fontSize: '13px', background: '#f4f4f4', border: '1px solid #e0e0e0' }}>
                No script in this version.
              </div>
            )}
          </>
        )}

        {!viewingId && (
          <p style={{ color: '#525252', fontSize: '13px' }}>
            Click a version above to view its snapshot.
          </p>
        )}
      </div>
    </div>
  );
}
