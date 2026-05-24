import React, { useState } from 'react';
import TestRunDetailModal from './TestRunDetailModal';
import './RecentTests.css';

function RecentTests({ testRuns = [], onRefresh }) {
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const [selectedRun, setSelectedRun] = useState(null);

  // Use real data only - no mock data
  const displayData = testRuns;

  // Calculate pagination data
  const totalPages = Math.ceil(displayData.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const currentPageData = displayData.slice(startIndex, endIndex);

  const getStatusBadge = (status) => {
    const className = `status-badge ${status || 'running'}`;
    const label = {
      passed: 'Passed',
      failed: 'Failed',
      running: 'Running'
    };
    return (
      <span className={className}>
        {label[status] || label.running}
      </span>
    );
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
    setCurrentPage(1);
  };

  const handleRowClick = (run) => {
    setSelectedRun(run);
  };

  const handleCloseDetail = () => {
    setSelectedRun(null);
  };

  return (
    <div className="recent-tests">
      <div className="recent-tests-header">
        <h3>Recent Test Runs</h3>
        <div className="pagination-info">
          Showing {currentPageData.length > 0 ? `${startIndex + 1}-${Math.min(endIndex, displayData.length)} / ${displayData.length} records` : '0 records'}
        </div>
      </div>

      {displayData.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📊</div>
          <p className="empty-title">No test run records</p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="tests-table">
              <thead>
                <tr>
                  <th>Test Name</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {currentPageData.map((run, index) => (
                  <tr
                    key={run.id || `${startIndex + index}`}
                    onClick={() => handleRowClick(run)}
                    className="clickable-row"
                  >
                    <td className="test-name">
                      {run.test_name || run.name || `Test #${startIndex + index + 1}`}
                    </td>
                    <td className="status-cell">
                      <div className="status-with-error">
                        {getStatusBadge(run.status || 'running')}
                        {(run.status === 'failed' && run.error_message) && (
                          <div className="error-tooltip" title={run.error_message}>
                            ⚠️
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="duration-cell">
                      {formatDuration(run.duration)}
                    </td>
                    <td className="time-cell">
                      {formatTime(run.timestamp || run.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination controls */}
          {totalPages > 1 && (
            <div className="pagination-controls">
              <div className="pagination-info">
                Page {currentPage} / {totalPages}
              </div>

              <div className="pagination-buttons">
                <button
                  onClick={() => handlePageChange(1)}
                  disabled={currentPage === 1}
                  className="pagination-btn"
                  aria-label="First page"
                >
                  First
                </button>

                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="pagination-btn"
                  aria-label="Previous page"
                >
                  Previous
                </button>

                {/* Page number buttons */}
                {Array.from({length: Math.min(5, totalPages)}, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }

                  const isActive = pageNum === currentPage;
                  return (
                    <button
                      key={pageNum}
                      onClick={() => handlePageChange(pageNum)}
                      className={`pagination-btn page-number ${isActive ? 'active' : ''}`}
                      aria-label={`Page ${pageNum}`}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      {pageNum}
                    </button>
                  );
                })}

                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="pagination-btn"
                  aria-label="Next page"
                >
                  Next
                </button>

                <button
                  onClick={() => handlePageChange(totalPages)}
                  disabled={currentPage === totalPages}
                  className="pagination-btn"
                  aria-label="Last page"
                >
                  Last
                </button>
              </div>

              <div className="page-size-selector">
                <label>Items per page:</label>
                <select
                  value={pageSize}
                  onChange={(e) => handlePageSizeChange(parseInt(e.target.value))}
                  className="page-size-select"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>
            </div>
          )}
        </>
      )}

      {/* Test Run Detail Modal */}
      {selectedRun && (
        <TestRunDetailModal
          run={selectedRun}
          onClose={handleCloseDetail}
        />
      )}
    </div>
  );
}

export default RecentTests;
