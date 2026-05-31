import { useState } from 'react';
import { copyTestCaseToWorkspace } from '../../api';
import Modal from '../Modal';
import './TestCasesMarketplaceCard.css';

export default function TestCasesMarketplaceCard({ testCase, onCopy }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [copying, setCopying] = useState(false);

  const handleUseClick = () => {
    setShowConfirm(true);
  };

  const handleConfirmCopy = async () => {
    try {
      setCopying(true);
      const copied = await copyTestCaseToWorkspace(testCase.id);
      setShowConfirm(false);
      if (onCopy) onCopy(copied);
    } catch (error) {
      console.error('Failed to copy testCase:', error);
      setCopying(false);
    }
  };

  const getInitials = (name) => {
    return name ? name.charAt(0).toUpperCase() : '?';
  };

  const getStatusColor = (status) => {
    const colors = {
      published: '#24a148',
      passed: '#24a148',
      testing: '#0f62fe',
      draft: '#8d8d8d',
    };
    return colors[status] || '#8d8d8d';
  };

  return (
    <>
      <div className="testCase-marketplace-card">
        <div className="testCase-marketplace-card-header">
          <div
            className="testCase-marketplace-card-icon"
            style={{ backgroundColor: testCase.color || '#0f62fe' }}
          >
            {getInitials(testCase.name)}
          </div>
          <div className="testCase-marketplace-card-meta">
            <span
              className="testCase-marketplace-card-status"
              style={{ color: getStatusColor(testCase.status) }}
            >
              {testCase.status === 'published' ? 'Published' : testCase.status}
            </span>
          </div>
        </div>

        <div className="testCase-marketplace-card-body">
          <h3 className="testCase-marketplace-card-title">{testCase.name}</h3>
          {testCase.description && (
            <p className="testCase-marketplace-card-description">{testCase.description}</p>
          )}
          {testCase.url && (
            <div className="testCase-marketplace-card-url">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                <path d="M6 1C3.24 1 1 3.24 1 6s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zm0 9c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4z"/>
                <path d="M5.5 3v3l2.5 1.5.5-.84-2-1.2V3h-1z"/>
              </svg>
              {testCase.url}
            </div>
          )}
          {testCase.test_goal && (
            <div className="testCase-marketplace-card-goal">
              <strong>Test Goal:</strong> {testCase.test_goal}
            </div>
          )}
        </div>

        <div className="testCase-marketplace-card-footer">
          <div className="testCase-marketplace-card-stats">
            {testCase.iteration_count > 0 && (
              <span className="testCase-marketplace-card-stat">
                v{testCase.iteration_count}
              </span>
            )}
            {testCase.latest_result?.total_tests && (
              <span className="testCase-marketplace-card-stat">
                {testCase.latest_result.total_tests} tests
              </span>
            )}
          </div>
          <button
            className="testCase-marketplace-card-use-btn"
            onClick={handleUseClick}
          >
            Use this test
          </button>
        </div>
      </div>

      <Modal
        isOpen={showConfirm}
        onClose={() => setShowConfirm(false)}
        title="Copy to Workspace"
      >
        <div className="testCase-marketplace-confirm">
          <p>
            Copy <strong>{testCase.name}</strong> to your workspace?
          </p>
          <p className="testCase-marketplace-confirm-sub">
            This will create a copy that you can modify and run independently.
          </p>
          <div className="testCase-marketplace-confirm-actions">
            <button
              className="testCase-btn-secondary"
              onClick={() => setShowConfirm(false)}
              disabled={copying}
            >
              Cancel
            </button>
            <button
              className="testCase-btn-primary"
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
