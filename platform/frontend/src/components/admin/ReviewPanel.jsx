import { useState, useEffect, useCallback } from 'react';
import {
  getPendingReviews, approveVersion, rejectVersion,
  approveSuite, rejectSuite,
} from '../../api';
import PermissionGate from '../PermissionGate';
import './ReviewPanel.css';

export default function ReviewPanel() {
  const [pendingItems, setPendingItems] = useState({ tests: [], suites: [] });
  const [loading, setLoading] = useState(true);
  const [rejectingId, setRejectingId] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [actionLoading, setActionLoading] = useState({});

  const loadPending = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getPendingReviews();
      setPendingItems(data);
    } catch { /* silent */ } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPending(); }, [loadPending]);

  const handleApproveTest = async (item) => {
    try {
      setActionLoading(prev => ({ ...prev, [`test-${item.id}`]: true }));
      if (item.version_id) {
        await approveVersion(item.version_id);
      } else {
        const { approveTest } = await import('../../api');
        await approveTest(item.id);
      }
      await loadPending();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [`test-${item.id}`]: false }));
    }
  };

  const handleRejectTest = async (item) => {
    if (!rejectReason.trim()) { alert('Please enter a rejection reason'); return; }
    try {
      setActionLoading(prev => ({ ...prev, [`test-${item.id}`]: true }));
      if (item.version_id) {
        await rejectVersion(item.version_id, rejectReason);
      } else {
        const { rejectTest } = await import('../../api');
        await rejectTest(item.id, rejectReason);
      }
      setRejectingId(null);
      setRejectReason('');
      await loadPending();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [`test-${item.id}`]: false }));
    }
  };

  const handleApproveSuite = async (id) => {
    try {
      setActionLoading(prev => ({ ...prev, [`suite-${id}`]: true }));
      await approveSuite(id);
      await loadPending();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [`suite-${id}`]: false }));
    }
  };

  const handleRejectSuite = async (id) => {
    if (!rejectReason.trim()) { alert('Please enter a rejection reason'); return; }
    try {
      setActionLoading(prev => ({ ...prev, [`suite-${id}`]: true }));
      await rejectSuite(id, rejectReason);
      setRejectingId(null);
      setRejectReason('');
      await loadPending();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [`suite-${id}`]: false }));
    }
  };

  const totalPending = pendingItems.tests.length + pendingItems.suites.length;

  return (
    <div className="review-panel">
      <div className="review-panel-header">
        <h2>Review Management</h2>
        <span className="review-panel-count">{totalPending} items pending review</span>
      </div>

      {loading ? (
        <div className="review-panel-loading">Loading...</div>
      ) : totalPending === 0 ? (
        <div className="review-panel-empty">No pending review items</div>
      ) : (
        <>
          {/* Pending Tests (version-based) */}
          <PermissionGate permission="review:test">
            {pendingItems.tests.length > 0 && (
              <div className="review-section">
                <h3 className="review-section-title">Test Cases ({pendingItems.tests.length})</h3>
                <div className="review-list">
                  {pendingItems.tests.map(item => (
                    <div key={`test-${item.id}`} className="review-item">
                      <div className="review-item-info">
                        <span className="review-item-name">
                          {item.name}
                          {item.version_number != null && (
                            <span style={{
                              marginLeft: '8px',
                              fontSize: '11px',
                              fontWeight: 600,
                              color: '#fff',
                              background: '#0f62fe',
                              padding: '1px 6px',
                            }}>
                              v{item.version_number}
                            </span>
                          )}
                        </span>
                        {item.description && <span className="review-item-desc">{item.description}</span>}
                        <span className="review-item-meta">
                          ID: {item.id}
                          {item.version_id && ` | Version ID: ${item.version_id}`}
                          {item.created_by && ` | Submitted by: ${item.created_by}`}
                        </span>
                      </div>
                      {rejectingId === `test-${item.id}` ? (
                        <div className="review-item-reject-form">
                          <input
                            type="text"
                            placeholder="Rejection reason..."
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            className="review-reject-input"
                          />
                          <button className="review-btn review-btn-reject" onClick={() => handleRejectTest(item)} disabled={actionLoading[`test-${item.id}`]}>
                            Confirm Reject
                          </button>
                          <button className="review-btn review-btn-cancel" onClick={() => { setRejectingId(null); setRejectReason(''); }}>
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <div className="review-item-actions">
                          <button className="review-btn review-btn-approve" onClick={() => handleApproveTest(item)} disabled={actionLoading[`test-${item.id}`]}>
                            {actionLoading[`test-${item.id}`] ? 'Processing...' : 'Approve'}
                          </button>
                          <button className="review-btn review-btn-reject-outline" onClick={() => setRejectingId(`test-${item.id}`)}>
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </PermissionGate>

          {/* Pending Suites */}
          <PermissionGate permission="review:suite">
            {pendingItems.suites.length > 0 && (
              <div className="review-section">
                <h3 className="review-section-title">Test Suites ({pendingItems.suites.length})</h3>
                <div className="review-list">
                  {pendingItems.suites.map(item => (
                    <div key={`suite-${item.id}`} className="review-item">
                      <div className="review-item-info">
                        <span className="review-item-name">{item.name}</span>
                        {item.description && <span className="review-item-desc">{item.description}</span>}
                        <span className="review-item-meta">ID: {item.id} | Submitted by: {item.created_by || 'Unknown'}</span>
                      </div>
                      {rejectingId === `suite-${item.id}` ? (
                        <div className="review-item-reject-form">
                          <input
                            type="text"
                            placeholder="Rejection reason..."
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            className="review-reject-input"
                          />
                          <button className="review-btn review-btn-reject" onClick={() => handleRejectSuite(item.id)} disabled={actionLoading[`suite-${item.id}`]}>
                            Confirm Reject
                          </button>
                          <button className="review-btn review-btn-cancel" onClick={() => { setRejectingId(null); setRejectReason(''); }}>
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <div className="review-item-actions">
                          <button className="review-btn review-btn-approve" onClick={() => handleApproveSuite(item.id)} disabled={actionLoading[`suite-${item.id}`]}>
                            {actionLoading[`suite-${item.id}`] ? 'Processing...' : 'Approve'}
                          </button>
                          <button className="review-btn review-btn-reject-outline" onClick={() => setRejectingId(`suite-${item.id}`)}>
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </PermissionGate>
        </>
      )}
    </div>
  );
}
