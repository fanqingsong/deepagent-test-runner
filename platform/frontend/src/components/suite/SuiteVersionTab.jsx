import { useState, useEffect, useCallback } from 'react';
import { getSuiteVersions, restoreSuiteVersion, submitSuiteVersionForReview } from '../../api';
import '../test_cases/test-cases-shared.css';

const REVIEW_STATUS_LABELS = {
  draft: 'Draft',
  pending_review: 'Pending Review',
  approved: 'Approved',
  rejected: 'Rejected',
  published: 'Published',
};

const REVIEW_STATUS_COLORS = {
  draft: '#8d8d8d',
  pending_review: '#f1c21b',
  approved: '#198038',
  rejected: '#da1e28',
  published: '#6929c4',
};

const PERMISSION_LABELS = { view: 'View', edit: 'Edit', execute: 'Execute', admin: 'Admin' };

export default function SuiteVersionTab({
  suiteId,
  onVersionRestored,
  onVersionSubmitted,
  refreshKey,
}) {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewingId, setViewingId] = useState(null);
  const [restoring, setRestoring] = useState(false);
  const [submittingId, setSubmittingId] = useState(null);
  const [error, setError] = useState(null);
  const [snapshotSection, setSnapshotSection] = useState('all');

  const loadVersions = useCallback(async () => {
    if (!suiteId) return;
    try {
      setLoading(true);
      const data = await getSuiteVersions(suiteId);
      setVersions(data);
    } catch { /* non-critical */ } finally {
      setLoading(false);
    }
  }, [suiteId]);

  useEffect(() => { loadVersions(); }, [loadVersions, refreshKey]);

  const handleRestore = async (versionId) => {
    try {
      setRestoring(true);
      setError(null);
      await restoreSuiteVersion(suiteId, versionId);
      onVersionRestored?.();
      loadVersions();
      setViewingId(null);
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
      await submitSuiteVersionForReview(version.id);
      onVersionSubmitted?.();
      loadVersions();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmittingId(null);
    }
  };

  const handleViewSnapshot = (versionId) => {
    setViewingId(viewingId === versionId ? null : versionId);
    setSnapshotSection('all');
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
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
        No versions yet. Save changes to create version snapshots.
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <div className="test-case-section">
        <h3 className="test-case-section-title">
          Versions
          <span style={{ fontWeight: 400, color: '#525252', fontSize: '13px', marginLeft: '8px' }}>
            {versions.length} versions
          </span>
        </h3>

        {error && (
          <div style={{ padding: '8px 12px', background: '#fff1f1', color: '#da1e28', fontSize: '13px', marginBottom: '12px' }}>
            {error}
          </div>
        )}

        <table className="composer-versions-table">
          <thead>
            <tr>
              <th className="th-version">Version</th>
              <th className="th-status">Status</th>
              <th className="th-date">Created</th>
              <th className="th-desc">Description</th>
              <th className="th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {versions.map((v, index) => (
              <tr key={v.id} className={viewingId === v.id ? 'version-row--active' : ''}>
                <td className="td-version">
                  <div className="version-number">
                    v{v.version}
                    {index === 0 && (
                      <span className="version-current-badge">Current</span>
                    )}
                  </div>
                </td>
                <td className="td-status">
                  <span
                    className="version-status-badge"
                    style={{
                      background: REVIEW_STATUS_COLORS[v.review_status] || REVIEW_STATUS_COLORS.draft,
                      color: '#fff',
                    }}
                  >
                    {REVIEW_STATUS_LABELS[v.review_status] || v.review_status}
                  </span>
                </td>
                <td className="td-date">{formatDate(v.created_at)}</td>
                <td className="td-desc">{v.change_description || '-'}</td>
                <td className="td-actions">
                  <button
                    className="version-action-btn version-action-btn--view"
                    onClick={() => handleViewSnapshot(v.id)}
                    title="View snapshot"
                  >
                    View
                  </button>
                  {(v.review_status === 'draft' || v.review_status === 'rejected') && (
                    <button
                      className="version-action-btn version-action-btn--submit"
                      onClick={() => handleSubmitForReview(v)}
                      disabled={submittingId === v.id}
                      title="Submit for review"
                    >
                      {submittingId === v.id ? '...' : 'Submit'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Right Sidebar for Version Details */}
        {viewingId && viewed && (
          <>
            <div
              className={`version-sidebar-overlay ${viewingId ? 'visible' : 'hidden'}`}
              onClick={() => setViewingId(null)}
            />
            <div className={`version-sidebar ${viewingId ? 'visible' : 'hidden'}`}>
              <div className="version-sidebar-header">
                <div className="version-snapshot-title">
                  <h4>Snapshot for v{viewed.version}</h4>
                  <span
                    className="version-status-badge"
                    style={{
                      background: REVIEW_STATUS_COLORS[viewed.review_status] || REVIEW_STATUS_COLORS.draft,
                      color: '#fff',
                    }}
                  >
                    {REVIEW_STATUS_LABELS[viewed.review_status] || viewed.review_status}
                  </span>
                </div>
                <div className="version-snapshot-actions">
                  {viewed.review_status === 'rejected' && viewed.rejection_reason && (
                    <span style={{ fontSize: '12px', color: '#da1e28', marginRight: '12px' }}>
                      Rejection: {viewed.rejection_reason}
                    </span>
                  )}
                  <button
                    className="version-snapshot-close"
                    onClick={() => setViewingId(null)}
                  >
                    ✕
                  </button>
                </div>
              </div>

              <div className="version-snapshot-tabs">
                <button
                  className={`version-tab-btn ${snapshotSection === 'all' ? 'version-tab-btn--active' : ''}`}
                  onClick={() => setSnapshotSection('all')}
                >
                  All
                </button>
                <button
                  className={`version-tab-btn ${snapshotSection === 'config' ? 'version-tab-btn--active' : ''}`}
                  onClick={() => setSnapshotSection('config')}
                >
                  Configuration
                </button>
                <button
                  className={`version-tab-btn ${snapshotSection === 'entries' ? 'version-tab-btn--active' : ''}`}
                  onClick={() => setSnapshotSection('entries')}
                >
                  Test Entries
                </button>
                <button
                  className={`version-tab-btn ${snapshotSection === 'permissions' ? 'version-tab-btn--active' : ''}`}
                  onClick={() => setSnapshotSection('permissions')}
                >
                  Permissions
                </button>
              </div>

              <div className="version-sidebar-content">
                <div className="version-snapshot-content">
                  {(snapshotSection === 'all' || snapshotSection === 'config') && (
                    <div className="version-section-block">
                      <h5 className="version-section-title">Configuration</h5>
                      <div className="version-config-grid">
                        <div className="version-config-item">
                          <span className="version-config-label">Name:</span>
                          <span className="version-config-value">{snapshot.name || '-'}</span>
                        </div>
                        <div className="version-config-item">
                          <span className="version-config-label">Execution Mode:</span>
                          <span className="version-config-value">{snapshot.execution_mode || '-'}</span>
                        </div>
                        <div className="version-config-item">
                          <span className="version-config-label">Fail Strategy:</span>
                          <span className="version-config-value">{snapshot.fail_strategy || '-'}</span>
                        </div>
                        <div className="version-config-item full">
                          <span className="version-config-label">Description:</span>
                          <span className="version-config-value">{snapshot.description || '-'}</span>
                        </div>
                        {snapshot.is_dynamic && (
                          <div className="version-config-item">
                            <span className="version-config-label">Dynamic Suite:</span>
                            <span className="version-config-value">Yes</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {(snapshotSection === 'all' || snapshotSection === 'entries') && (
                    <div className="version-section-block">
                      <h5 className="version-section-title">
                        Test Entries
                        <span style={{ fontWeight: 400, color: '#525252', fontSize: '12px', marginLeft: '8px' }}>
                          ({snapshot.suite_entries?.length || snapshot.test_definition_ids?.length || 0} tests)
                        </span>
                      </h5>
                      {snapshot.suite_entries && snapshot.suite_entries.length > 0 ? (
                        <table className="version-entries-table">
                          <thead>
                            <tr>
                              <th>Order</th>
                              <th>Test ID</th>
                              <th>Condition</th>
                              <th>Enabled</th>
                            </tr>
                          </thead>
                          <tbody>
                            {snapshot.suite_entries.map((entry, idx) => (
                              <tr key={idx}>
                                <td>{entry.order || idx + 1}</td>
                                <td>{entry.test_definition_id}</td>
                                <td>{entry.condition || 'always'}</td>
                                <td>{entry.enabled !== false ? 'Yes' : 'No'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <div className="version-empty-state">
                          No test entries in this version.
                        </div>
                      )}
                    </div>
                  )}

                  {(snapshotSection === 'all' || snapshotSection === 'permissions') && (
                    <div className="version-section-block">
                      <h5 className="version-section-title">
                        Permissions
                        {snapshot.permissions && (
                          <span style={{ fontWeight: 400, color: '#525252', fontSize: '12px', marginLeft: '8px' }}>
                            ({snapshot.permissions.length} members)
                          </span>
                        )}
                      </h5>
                      {snapshot.permissions && snapshot.permissions.length > 0 ? (
                        <table className="version-permissions-table">
                          <thead>
                            <tr>
                              <th>User</th>
                              <th>Email</th>
                              <th>Permission</th>
                            </tr>
                          </thead>
                          <tbody>
                            {snapshot.permissions.map((perm, idx) => (
                              <tr key={idx}>
                                <td>{perm.username || `User ${perm.user_id}`}</td>
                                <td style={{ color: '#8d8d8d', fontSize: '12px' }}>{perm.email || '-'}</td>
                                <td>
                                  <span className="version-permission-badge">
                                    {PERMISSION_LABELS[perm.permission_type] || perm.permission_type}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <div className="version-empty-state">
                          No permissions in this version.
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
