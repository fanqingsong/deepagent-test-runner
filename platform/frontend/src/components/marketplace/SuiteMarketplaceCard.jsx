import { useState } from 'react';
import { copySuiteToWorkspace } from '../../api';
import Modal from '../Modal';
import './SuiteMarketplaceCard.css';

export default function SuiteMarketplaceCard({ suite, onCopy }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [copying, setCopying] = useState(false);

  const handleUseClick = () => {
    setShowConfirm(true);
  };

  const handleViewDetails = () => {
    setShowDetails(true);
  };

  const handleConfirmCopy = async () => {
    try {
      setCopying(true);
      const copied = await copySuiteToWorkspace(suite.id);
      setShowConfirm(false);
      setShowDetails(false);
      if (onCopy) onCopy(copied);
    } catch (error) {
      console.error('Failed to copy suite:', error);
      setCopying(false);
    }
  };

  const getInitials = (name) => {
    return name ? name.charAt(0).toUpperCase() : '?';
  };

  const getExecutionModeLabel = (mode) => {
    const labels = {
      sequential: 'Sequential',
      parallel: 'Parallel',
    };
    return labels[mode] || mode;
  };

  const testCount = suite.test_definition_ids?.length || 0;

  return (
    <>
      <div className="suite-marketplace-card">
        <div className="suite-marketplace-card-header">
          <div
            className="suite-marketplace-card-icon"
            style={{ backgroundColor: suite.color || '#0f62fe' }}
          >
            {getInitials(suite.name)}
          </div>
          <div className="suite-marketplace-card-meta">
            <span className="suite-marketplace-card-badge">
              {getExecutionModeLabel(suite.execution_mode)}
            </span>
            <span className="suite-marketplace-card-badge approved">
              Approved
            </span>
          </div>
        </div>

        <div className="suite-marketplace-card-body">
          <h3 className="suite-marketplace-card-title">{suite.name}</h3>
          {suite.description && (
            <p className="suite-marketplace-card-description">{suite.description}</p>
          )}
        </div>

        <div className="suite-marketplace-card-footer">
          <div className="suite-marketplace-card-stats">
            <span className="suite-marketplace-card-stat">
              {testCount} test{testCount !== 1 ? 's' : ''}
            </span>
            {suite.max_concurrency > 1 && suite.execution_mode === 'parallel' && (
              <span className="suite-marketplace-card-stat">
                Concurrency: {suite.max_concurrency}
              </span>
            )}
          </div>
          <div className="suite-marketplace-card-actions">
            <button
              className="suite-marketplace-card-view-btn"
              onClick={handleViewDetails}
            >
              View Details
            </button>
            <button
              className="suite-marketplace-card-use-btn"
              onClick={handleUseClick}
            >
              Copy to My Workspace
            </button>
          </div>
        </div>
      </div>

      {/* Copy Confirmation Modal */}
      <Modal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        title="Copy to Workspace"
      >
        <div className="suite-marketplace-confirm">
          <p>
            Copy <strong>{suite.name}</strong> to your workspace?
          </p>
          <p className="suite-marketplace-confirm-sub">
            This will create a copy that you can modify and run independently.
          </p>
          <div className="suite-marketplace-confirm-actions">
            <button
              className="studio-btn-secondary"
              onClick={() => setShowConfirm(false)}
              disabled={copying}
            >
              Cancel
            </button>
            <button
              className="studio-btn-primary"
              onClick={handleConfirmCopy}
              disabled={copying}
            >
              {copying ? 'Copying...' : 'Copy to Workspace'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Details Modal */}
      <Modal
        isOpen={showDetails}
        onClose={() => setShowDetails(false)}
        title=""
      >
        <div className="suite-details-modal-content">
          <div className="suite-details-header">
            <div
              className="suite-details-icon"
              style={{ backgroundColor: suite.color || '#0f62fe' }}
            >
              {getInitials(suite.name)}
            </div>
            <div className="suite-details-title-section">
              <h2>{suite.name}</h2>
              <div className="suite-details-meta">
                <span className="suite-details-badge">
                  {getExecutionModeLabel(suite.execution_mode)}
                </span>
                <span className="suite-details-badge approved">
                  Approved
                </span>
              </div>
            </div>
          </div>

          {suite.description && (
            <div className="suite-details-section">
              <div className="suite-details-section-title">Description</div>
              <p className="suite-details-description">{suite.description}</p>
            </div>
          )}

          <div className="suite-details-section">
            <div className="suite-details-section-title">Suite Information</div>
            <div className="suite-details-info-grid">
              <div className="suite-details-info-item">
                <span className="suite-details-info-label">Execution Mode</span>
                <span className="suite-details-info-value">{getExecutionModeLabel(suite.execution_mode)}</span>
              </div>
              <div className="suite-details-info-item">
                <span className="suite-details-info-label">Test Count</span>
                <span className="suite-details-info-value">{testCount} test{testCount !== 1 ? 's' : ''}</span>
              </div>
              {suite.execution_mode === 'parallel' && (
                <>
                  <div className="suite-details-info-item">
                    <span className="suite-details-info-label">Max Concurrency</span>
                    <span className="suite-details-info-value">{suite.max_concurrency || 1}</span>
                  </div>
                </>
              )}
              <div className="suite-details-info-item">
                <span className="suite-details-info-label">Suite ID</span>
                <span className="suite-details-info-value">{suite.id}</span>
              </div>
            </div>
          </div>

          {suite.test_definition_ids && suite.test_definition_ids.length > 0 && (
            <div className="suite-details-section">
              <div className="suite-details-section-title">Test Definitions ({suite.test_definition_ids.length})</div>
              <div className="suite-details-test-list">
                {suite.test_definition_ids.map((testId, index) => (
                  <div key={testId} className="suite-details-test-item">
                    Test #{index + 1} (ID: {testId})
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="suite-details-actions">
            <button
              className="suite-details-close-btn"
              onClick={() => setShowDetails(false)}
            >
              Close
            </button>
            <button
              className="suite-details-copy-btn"
              onClick={handleConfirmCopy}
              disabled={copying}
            >
              {copying ? 'Copying...' : 'Copy to My Workspace'}
            </button>
          </div>
        </div>
      </Modal>
    </>
  );
}
