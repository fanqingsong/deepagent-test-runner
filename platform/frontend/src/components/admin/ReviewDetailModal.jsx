import { useState, useEffect } from 'react';
import { getReviewDetail, approveVersion, rejectVersion, publishVersion, approveSuite, rejectSuite, approveSuiteVersion, rejectSuiteVersion, publishSuiteVersion } from '../../api';

export default function ReviewDetailModal({ item, onClose, onReviewed }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);

  useEffect(() => {
    const loadDetails = async () => {
      try {
        setLoading(true);
        let type;
        if (item.type === 'suite') {
          type = 'suite';
        } else if (item.type === 'suite_version') {
          type = 'suite_version';
        } else {
          type = 'version';
        }
        const data = await getReviewDetail(type, item.version_id || item.id);
        setDetails(data);
      } catch (e) {
        alert(e.message);
      } finally {
        setLoading(false);
      }
    };
    loadDetails();
  }, [item]);

  const handleApprove = async () => {
    try {
      setActionLoading(true);
      if (item.type === 'suite') {
        await approveSuite(item.id);
      } else if (item.type === 'suite_version') {
        await approveSuiteVersion(item.version_id || item.id);
        await publishSuiteVersion(item.version_id || item.id);
      } else {
        await approveVersion(item.version_id || item.id);
        await publishVersion(item.version_id || item.id);
      }
      alert('Successfully approved!');
      onReviewed();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      alert('Please enter a rejection reason');
      return;
    }
    try {
      setActionLoading(true);
      if (item.type === 'suite') {
        await rejectSuite(item.id, rejectReason);
      } else if (item.type === 'suite_version') {
        await rejectSuiteVersion(item.version_id || item.id, rejectReason);
      } else {
        await rejectVersion(item.version_id || item.id, rejectReason);
      }
      alert('Successfully rejected!');
      onReviewed();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  const renderSnapshot = (snapshot) => {
    if (!snapshot || typeof snapshot !== 'object') return null;
    return (
      <div className="review-detail-snapshot">
        {snapshot.name && (
          <div className="review-detail-row">
            <span className="review-detail-label">Name:</span>
            <span className="review-detail-value">{snapshot.name}</span>
          </div>
        )}
        {snapshot.description && (
          <div className="review-detail-row">
            <span className="review-detail-label">Description:</span>
            <span className="review-detail-value">{snapshot.description}</span>
          </div>
        )}
        {snapshot.url && (
          <div className="review-detail-row">
            <span className="review-detail-label">URL:</span>
            <span className="review-detail-value">{snapshot.url}</span>
          </div>
        )}
        {snapshot.test_goal && (
          <div className="review-detail-row">
            <span className="review-detail-label">Test Goal:</span>
            <span className="review-detail-value">{snapshot.test_goal}</span>
          </div>
        )}
        {snapshot.tags && Array.isArray(snapshot.tags) && snapshot.tags.length > 0 && (
          <div className="review-detail-row">
            <span className="review-detail-label">Tags:</span>
            <span className="review-detail-value">{snapshot.tags.join(', ')}</span>
          </div>
        )}
        {snapshot.execution_mode && (
          <div className="review-detail-row">
            <span className="review-detail-label">Execution Mode:</span>
            <span className="review-detail-value">{snapshot.execution_mode}</span>
          </div>
        )}
        {snapshot.steps && Array.isArray(snapshot.steps) && snapshot.steps.length > 0 && (
          <div className="review-detail-steps">
            <div className="review-detail-label">Test Steps ({snapshot.steps.length}):</div>
            {snapshot.steps.map((step, idx) => (
              <div key={idx} className="review-detail-step">
                <strong>Step {idx + 1}:</strong> {step.description || step.action || step.name || JSON.stringify(step)}
              </div>
            ))}
          </div>
        )}
        {snapshot.plan && (
          <div className="review-detail-plan">
            <div className="review-detail-label">Test Plan:</div>
            <div className="review-detail-plan-content">{snapshot.plan}</div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="review-modal-overlay" onClick={onClose}>
      <div className="review-modal-content" onClick={e => e.stopPropagation()}>
        <div className="review-modal-header">
          <h3>Review Details</h3>
          <button className="review-modal-close" onClick={onClose}>&times;</button>
        </div>

        {loading ? (
          <div className="review-modal-loading">Loading...</div>
        ) : details ? (
          <>
            <div className="review-modal-body">
              <div className="review-detail-section">
                <h4>Basic Information</h4>
                <div className="review-detail-row">
                  <span className="review-detail-label">Type:</span>
                  <span className="review-detail-value">{details.type}</span>
                </div>
                <div className="review-detail-row">
                  <span className="review-detail-label">Name:</span>
                  <span className="review-detail-value">{details.name}</span>
                </div>
                {details.description && (
                  <div className="review-detail-row">
                    <span className="review-detail-label">Description:</span>
                    <span className="review-detail-value">{details.description}</span>
                  </div>
                )}
                {details.version_number != null && (
                  <div className="review-detail-row">
                    <span className="review-detail-label">Version:</span>
                    <span className="review-detail-value">v{details.version_number}</span>
                  </div>
                )}
                <div className="review-detail-row">
                  <span className="review-detail-label">Created by:</span>
                  <span className="review-detail-value">{details.created_by || 'Unknown'}</span>
                </div>
                <div className="review-detail-row">
                  <span className="review-detail-label">Created at:</span>
                  <span className="review-detail-value">{new Date(details.created_at).toLocaleString()}</span>
                </div>
                {details.change_description && (
                  <div className="review-detail-row">
                    <span className="review-detail-label">Change Description:</span>
                    <span className="review-detail-value">{details.change_description}</span>
                  </div>
                )}
              </div>

              {details.snapshot && (
                <div className="review-detail-section">
                  <h4>Content Snapshot</h4>
                  {renderSnapshot(details.snapshot)}
                </div>
              )}

              {details.playwright_script && (
                <div className="review-detail-section">
                  <h4>Playwright Script</h4>
                  <div className="review-detail-script">
                    <pre>{details.playwright_script}</pre>
                  </div>
                  <div className="review-detail-row">
                    <span className="review-detail-label">Script Status:</span>
                    <span className="review-detail-value">{details.script_status || 'unknown'}</span>
                  </div>
                </div>
              )}

              {details.test_ids && Array.isArray(details.test_ids) && (
                <div className="review-detail-section">
                  <h4>Test Cases ({details.test_ids.length})</h4>
                  <div className="review-detail-test-list">
                    {details.test_ids.map(id => (
                      <span key={id} className="review-detail-test-id">ID: {id}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="review-modal-footer">
              {showRejectInput ? (
                <div className="review-modal-reject-form">
                  <input
                    type="text"
                    placeholder="Rejection reason..."
                    value={rejectReason}
                    onChange={e => setRejectReason(e.target.value)}
                    className="review-modal-reject-input"
                  />
                  <button
                    className="review-btn review-btn-reject"
                    onClick={handleReject}
                    disabled={actionLoading}
                  >
                    {actionLoading ? 'Processing...' : 'Confirm Reject'}
                  </button>
                  <button
                    className="review-btn review-btn-cancel"
                    onClick={() => {
                      setShowRejectInput(false);
                      setRejectReason('');
                    }}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <>
                  <button
                    className="review-btn review-btn-approve"
                    onClick={handleApprove}
                    disabled={actionLoading}
                  >
                    {actionLoading ? 'Processing...' : 'Approve'}
                  </button>
                  <button
                    className="review-btn review-btn-reject-outline"
                    onClick={() => setShowRejectInput(true)}
                    disabled={actionLoading}
                  >
                    Reject
                  </button>
                  <button className="review-btn review-btn-cancel" onClick={onClose}>
                    Close
                  </button>
                </>
              )}
            </div>
          </>
        ) : (
          <div className="review-modal-error">Failed to load details</div>
        )}
      </div>
    </div>
  );
}
