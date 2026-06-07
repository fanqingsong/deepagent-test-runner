import { useState, useEffect, useCallback } from 'react';
import { getPendingReviews } from '../../api';
import PermissionGate from '../PermissionGate';
import ReviewDetailModal from './ReviewDetailModal';
import './ReviewPanel.css';

export default function ReviewPanel() {
  const [pendingItems, setPendingItems] = useState({ tests: [], suites: [] });
  const [loading, setLoading] = useState(true);
  const [reviewItem, setReviewItem] = useState(null);

  const loadPending = useCallback(async () => {
    try {
      setLoading(true);
      const pending = await getPendingReviews();
      setPendingItems(pending);
    } catch { /* silent */ } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPending(); }, [loadPending]);

  const handleReview = (item) => {
    setReviewItem(item);
  };

  const handleReviewed = () => {
    setReviewItem(null);
    loadPending();
  };

  const totalPending = pendingItems.tests.length + pendingItems.suites.length;

  return (
    <div className="review-panel">
      <div className="review-panel-header">
        <h2>Review Management</h2>
        <span className="review-panel-count">{totalPending} pending</span>
      </div>

      {loading ? (
        <div className="review-panel-loading">Loading...</div>
      ) : (
        <>
          {/* Pending Items */}
          {totalPending === 0 ? (
            <div className="review-panel-empty">No items to review</div>
          ) : (
            <>
              {/* Pending Tests */}
              <PermissionGate permission="review:test">
                {pendingItems.tests.length > 0 && (
                  <div className="review-section">
                    <h3 className="review-section-title">Pending Tests ({pendingItems.tests.length})</h3>
                    <div className="review-list">
                      {pendingItems.tests.map(item => (
                        <div key={`test-${item.id}`} className="review-item">
                          <div className="review-item-info">
                            <span className="review-item-name">
                              {item.name}
                              {item.version_number != null && (
                                <span className="review-item-badge">v{item.version_number}</span>
                              )}
                            </span>
                            {item.description && <span className="review-item-desc">{item.description}</span>}
                            <span className="review-item-meta">
                              ID: {item.id}
                              {item.version_id && ` | Version ID: ${item.version_id}`}
                              {item.created_by && ` | Submitted by: ${item.created_by}`}
                            </span>
                          </div>
                          <div className="review-item-actions">
                            <button className="review-btn review-btn-review" onClick={() => handleReview(item)}>
                              Review
                            </button>
                          </div>
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
                    <h3 className="review-section-title">Pending Suites ({pendingItems.suites.length})</h3>
                    <div className="review-list">
                      {pendingItems.suites.map(item => (
                        <div key={`suite-${item.id}`} className="review-item">
                          <div className="review-item-info">
                            <span className="review-item-name">
                              {item.name}
                              {item.version_number != null && (
                                <span className="review-item-badge">v{item.version_number}</span>
                              )}
                            </span>
                            {item.description && <span className="review-item-desc">{item.description}</span>}
                            <span className="review-item-meta">
                              ID: {item.id}
                              {item.version_id && ` | Version ID: ${item.version_id}`}
                              {item.created_by && ` | Submitted by: ${item.created_by}`}
                            </span>
                          </div>
                          <div className="review-item-actions">
                            <button className="review-btn review-btn-review" onClick={() => handleReview(item)}>
                              Review
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </PermissionGate>
            </>
          )}
        </>
      )}

      {reviewItem && (
        <ReviewDetailModal
          item={reviewItem}
          onClose={() => setReviewItem(null)}
          onReviewed={handleReviewed}
        />
      )}
    </div>
  );
}
