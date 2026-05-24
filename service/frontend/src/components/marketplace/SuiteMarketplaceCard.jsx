import { useState } from 'react';
import { copySuiteToWorkspace } from '../../api';
import Modal from '../Modal';
import './SuiteMarketplaceCard.css';

export default function SuiteMarketplaceCard({ suite, onCopy }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [copying, setCopying] = useState(false);

  const handleUseClick = () => {
    setShowConfirm(true);
  };

  const handleConfirmCopy = async () => {
    try {
      setCopying(true);
      const copied = await copySuiteToWorkspace(suite.id);
      setShowConfirm(false);
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
          <div className="suite-marketplace-card-icon">
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
          <button
            className="suite-marketplace-card-use-btn"
            onClick={handleUseClick}
          >
            Use this suite
          </button>
        </div>
      </div>

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
    </>
  );
}
