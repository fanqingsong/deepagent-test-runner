import { useState, useEffect } from 'react';
import { copyTestCaseToWorkspace, getPublishedVersions } from '../../api';
import Modal from '../Modal';
import './TestCasesMarketplaceCard.css';

export default function TestCasesMarketplaceCard({ testCase, onCopy }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showVersionDetail, setShowVersionDetail] = useState(false);
  const [copying, setCopying] = useState(false);
  const [versions, setVersions] = useState([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState(null);

  const handleUseClick = () => {
    setShowConfirm(true);
  };

  const handleViewDetails = async () => {
    setShowDetails(true);
    // Load versions when opening details
    await loadVersions();
  };

  const loadVersions = async () => {
    try {
      setLoadingVersions(true);
      const data = await getPublishedVersions(testCase.id);
      setVersions(data || []);
    } catch (error) {
      console.error('Failed to load versions:', error);
      setVersions([]);
    } finally {
      setLoadingVersions(false);
    }
  };

  const handleViewVersionDetail = (version) => {
    setSelectedVersion(version);
    setShowVersionDetail(true);
  };

  const handleConfirmCopy = async () => {
    try {
      setCopying(true);
      const copied = await copyTestCaseToWorkspace(testCase.id);
      setShowConfirm(false);
      setShowDetails(false);
      if (onCopy) onCopy(copied);
    } catch (error) {
      console.error('Failed to copy testCase:', error);
      setCopying(false);
    }
  };

  const getInitials = (name) => {
    return name ? name.charAt(0).toUpperCase() : '?';
  };

  const getStatusLabel = (status) => {
    const labels = {
      published: 'Published',
      passed: 'Passed',
      testing: 'Testing',
      draft: 'Draft',
    };
    return labels[status] || status;
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

  const getVersionLabel = (version) => {
    // Format version number as integer for display
    const versionNum = Number.isInteger(version.version)
      ? version.version
      : Math.round(version.version * 10) / 10;

    if (version.review_status === 'published') {
      return `v${versionNum} (Published)`;
    } else if (version.review_status === 'approved') {
      return `v${versionNum} (Approved)`;
    } else {
      return `v${versionNum} (${version.review_status})`;
    }
  };

  const getVersionStatusColor = (status) => {
    const colors = {
      published: '#24a148',
      approved: '#defbe6',
      pending_review: '#f1c21b',
      rejected: '#da1e28',
      draft: '#8d8d8d',
    };
    return colors[status] || '#8d8d8d';
  };

  const getVersionStatusTextColor = (status) => {
    const colors = {
      published: '#24a148',
      approved: '#24a148',
      pending_review: '#b28a00',
      rejected: '#da1e28',
      draft: '#6f6f6f',
    };
    return colors[status] || '#6f6f6f';
  };

  return (
    <>
      <div className="test-cases-marketplace-card">
        <div className="test-cases-marketplace-card-header">
          <div
            className="test-cases-marketplace-card-icon"
            style={{ backgroundColor: testCase.color || getStatusColor(testCase.status) }}
          >
            {getInitials(testCase.name)}
          </div>
          <div className="test-cases-marketplace-card-meta">
            <span className={`test-cases-marketplace-card-status ${testCase.status}`}>
              {getStatusLabel(testCase.status)}
            </span>
          </div>
        </div>

        <div className="test-cases-marketplace-card-body">
          <h3 className="test-cases-marketplace-card-title">{testCase.name}</h3>
          {testCase.description && (
            <p className="test-cases-marketplace-card-description">{testCase.description}</p>
          )}
        </div>

        <div className="test-cases-marketplace-card-footer">
          <div className="test-cases-marketplace-card-stats">
            {testCase.iteration_count > 0 && (
              <span className="test-cases-marketplace-card-stat">
                v{testCase.iteration_count}
              </span>
            )}
            {testCase.latest_result?.total_tests && (
              <span className="test-cases-marketplace-card-stat">
                {testCase.latest_result.total_tests} tests
              </span>
            )}
          </div>
          <div className="test-cases-marketplace-card-actions">
            <button
              className="test-cases-marketplace-card-view-btn"
              onClick={handleViewDetails}
            >
              View Details
            </button>
            <button
              className="test-cases-marketplace-card-use-btn"
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
        <div className="test-cases-marketplace-confirm">
          <p>
            Copy <strong>{testCase.name}</strong> to your workspace?
          </p>
          <p className="test-cases-marketplace-confirm-sub">
            This will create a copy that you can modify and run independently.
          </p>
          <div className="test-cases-marketplace-confirm-actions">
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
        <div className="testcase-details-modal-content">
          <div className="testcase-details-header">
            <div
              className="testcase-details-icon"
              style={{
                backgroundColor: testCase.color || getStatusColor(testCase.status),
                color: '#ffffff'
              }}
            >
              {getInitials(testCase.name)}
            </div>
            <div className="testcase-details-title-section">
              <h2>{testCase.name}</h2>
              <div className="testcase-details-meta">
                <span className={`testcase-details-badge ${testCase.status}`}>
                  {getStatusLabel(testCase.status)}
                </span>
                {testCase.iteration_count > 0 && (
                  <span className="testcase-details-badge" style={{ color: '#6f6f6f', background: '#e0e0e0' }}>
                    v{testCase.iteration_count}
                  </span>
                )}
              </div>
            </div>
          </div>

          {testCase.description && (
            <div className="testcase-details-section">
              <div className="testcase-details-section-title">Description</div>
              <p className="testcase-details-description">{testCase.description}</p>
            </div>
          )}

          {testCase.test_goal && (
            <div className="testcase-details-section">
              <div className="testcase-details-section-title">Test Goal</div>
              <div className="testcase-details-goal">
                <strong>Goal:</strong> {testCase.test_goal}
              </div>
            </div>
          )}

          {/* Version History */}
          <div className="testcase-details-section">
            <div className="testcase-details-section-title">
              Version History {versions.length > 0 && `(${versions.length})`}
            </div>
            {loadingVersions ? (
              <div style={{ padding: '16px', color: '#6f6f6f' }}>Loading versions...</div>
            ) : versions.length > 0 ? (
              <div className="testcase-details-versions-list">
                {versions.map((version) => (
                  <div key={version.id} className="testcase-details-version-item">
                    <div className="testcase-details-version-header">
                      <span className="testcase-details-version-number">
                        {getVersionLabel(version)}
                      </span>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <span
                          className="testcase-details-version-status"
                          style={{
                            background: getVersionStatusColor(version.review_status),
                            color: getVersionStatusTextColor(version.review_status)
                          }}
                        >
                          {version.review_status === 'published' ? 'Published' :
                           version.review_status === 'approved' ? 'Approved' :
                           version.review_status === 'pending_review' ? 'Pending Review' :
                           version.review_status}
                        </span>
                        <button
                          className="testcase-details-version-view-btn"
                          onClick={() => handleViewVersionDetail(version)}
                        >
                          View Details
                        </button>
                      </div>
                    </div>
                    {version.created_at && (
                      <div className="testcase-details-version-date">
                        Created: {new Date(version.created_at).toLocaleString()}
                      </div>
                    )}
                    {version.change_description && (
                      <div className="testcase-details-version-desc">
                        {version.change_description}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '16px', color: '#6f6f6f' }}>No published versions available</div>
            )}
          </div>

          <div className="testcase-details-section">
            <div className="testcase-details-section-title">Test Information</div>
            <div className="testcase-details-info-grid">
              <div className="testcase-details-info-item">
                <span className="testcase-details-info-label">Status</span>
                <span className="testcase-details-info-value">{getStatusLabel(testCase.status)}</span>
              </div>
              {testCase.iteration_count > 0 && (
                <div className="testcase-details-info-item">
                  <span className="testcase-details-info-label">Current Version</span>
                  <span className="testcase-details-info-value">v{testCase.iteration_count}</span>
                </div>
              )}
              {testCase.url && (
                <div className="testcase-details-info-item" style={{ gridColumn: '1 / -1' }}>
                  <span className="testcase-details-info-label">Target URL</span>
                  <span className="testcase-details-info-value">
                    <a href={testCase.url} target="_blank" rel="noopener noreferrer">
                      {testCase.url}
                    </a>
                  </span>
                </div>
              )}
              <div className="testcase-details-info-item">
                <span className="testcase-details-info-label">Test Case ID</span>
                <span className="testcase-details-info-value">{testCase.id}</span>
              </div>
              {testCase.latest_result && (
                <>
                  {testCase.latest_result.total_tests && (
                    <div className="testcase-details-info-item">
                      <span className="testcase-details-info-label">Test Steps</span>
                      <span className="testcase-details-info-value">{testCase.latest_result.total_tests}</span>
                    </div>
                  )}
                  {testCase.latest_result.passed_tests != null && (
                    <div className="testcase-details-info-item">
                      <span className="testcase-details-info-label">Last Result</span>
                      <span className="testcase-details-info-value">
                        {testCase.latest_result.passed_tests}/{testCase.latest_result.total_tests} passed
                      </span>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="testcase-details-actions">
            <button
              className="testcase-details-close-btn"
              onClick={() => setShowDetails(false)}
            >
              Close
            </button>
            <button
              className="testcase-details-copy-btn"
              onClick={handleConfirmCopy}
              disabled={copying}
            >
              {copying ? 'Copying...' : 'Copy to My Workspace'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Version Detail Modal */}
      <Modal
        isOpen={showVersionDetail}
        onClose={() => setShowVersionDetail(false)}
        title=""
      >
        {selectedVersion && (
          <div className="testcase-details-modal-content">
            <div className="testcase-details-header">
              <div
                className="testcase-details-icon"
                style={{
                  backgroundColor: '#0f62fe',
                  color: '#ffffff'
                }}
              >
                {`v${selectedVersion.version}`}
              </div>
              <div className="testcase-details-title-section">
                <h2>
                  {testCase.name} - Version {selectedVersion.version}
                </h2>
                <div className="testcase-details-meta">
                  <span
                    className="testcase-details-badge"
                    style={{
                      background: getVersionStatusColor(selectedVersion.review_status),
                      color: getVersionStatusTextColor(selectedVersion.review_status)
                    }}
                  >
                    {selectedVersion.review_status === 'published' ? 'Published' :
                     selectedVersion.review_status === 'approved' ? 'Approved' :
                     selectedVersion.review_status === 'pending_review' ? 'Pending Review' :
                     selectedVersion.review_status || 'Unknown'}
                  </span>
                </div>
              </div>
            </div>

            {selectedVersion.change_description && (
              <div className="testcase-details-section">
                <div className="testcase-details-section-title">Change Description</div>
                <p className="testcase-details-description">{selectedVersion.change_description}</p>
              </div>
            )}

            <div className="testcase-details-section">
              <div className="testcase-details-section-title">Version Information</div>
              <div className="testcase-details-info-grid">
                <div className="testcase-details-info-item">
                  <span className="testcase-details-info-label">Version</span>
                  <span className="testcase-details-info-value">v{selectedVersion.version}</span>
                </div>
                <div className="testcase-details-info-item">
                  <span className="testcase-details-info-label">Version ID</span>
                  <span className="testcase-details-info-value">{selectedVersion.id}</span>
                </div>
                {selectedVersion.created_at && (
                  <div className="testcase-details-info-item">
                    <span className="testcase-details-info-label">Created At</span>
                    <span className="testcase-details-info-value">
                      {new Date(selectedVersion.created_at).toLocaleString()}
                    </span>
                  </div>
                )}
                {selectedVersion.snapshot?.test_definition_id && (
                  <div className="testcase-details-info-item">
                    <span className="testcase-details-info-label">Test Definition ID</span>
                    <span className="testcase-details-info-value">{selectedVersion.snapshot.test_definition_id}</span>
                  </div>
                )}
              </div>
            </div>

            {selectedVersion.snapshot?.steps && selectedVersion.snapshot.steps.length > 0 && (
              <div className="testcase-details-section">
                <div className="testcase-details-section-title">
                  Test Steps ({selectedVersion.snapshot.steps.length})
                </div>
                <div className="testcase-details-steps-list">
                  {selectedVersion.snapshot.steps.map((step, index) => (
                    <div key={index} className="testcase-details-step-item">
                      <div className="testcase-details-step-number">
                        {index + 1}
                      </div>
                      <div className="testcase-details-step-content">
                        <div className="testcase-details-step-action">
                          {step.action}
                        </div>
                        {step.expected_result && (
                          <div className="testcase-details-step-expected">
                            Expected: {step.expected_result}
                          </div>
                        )}
                        {step.description && (
                          <div className="testcase-details-step-description">
                            {step.description}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selectedVersion.snapshot?.test_goal && (
              <div className="testcase-details-section">
                <div className="testcase-details-section-title">Test Goal</div>
                <div className="testcase-details-goal">
                  {selectedVersion.snapshot.test_goal}
                </div>
              </div>
            )}

            {selectedVersion.snapshot?.test_url && (
              <div className="testcase-details-section">
                <div className="testcase-details-section-title">Test URL</div>
                <div className="testcase-details-info-value">
                  <a href={selectedVersion.snapshot.test_url} target="_blank" rel="noopener noreferrer">
                    {selectedVersion.snapshot.test_url}
                  </a>
                </div>
              </div>
            )}

            {selectedVersion.snapshot?.description && (
              <div className="testcase-details-section">
                <div className="testcase-details-section-title">Test Description</div>
                <p className="testcase-details-description">{selectedVersion.snapshot.description}</p>
              </div>
            )}

            <div className="testcase-details-actions">
              <button
                className="testcase-details-close-btn"
                onClick={() => setShowVersionDetail(false)}
              >
                Close
              </button>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}
