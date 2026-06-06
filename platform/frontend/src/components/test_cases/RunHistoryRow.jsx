export default function RunHistoryRow({ run, isExpanded, expandedCases, expandedLoading, onToggle }) {
  const timeStr = run.created_at
    ? new Date(run.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '-';
  const durStr = run.total_duration != null ? `${(run.total_duration / 1000).toFixed(1)}s` : '-';
  const errorPreview = run.error_message
    ? run.error_message.split('\n')[0].slice(0, 80) + (run.error_message.length > 80 ? '...' : '')
    : null;

  return (
    <>
      <tr className={`row-${run.status} run-history-row`} onClick={onToggle} style={{ cursor: 'pointer' }}>
        <td className="td-status">
          <span className={`step-badge step-${run.status}`}>
            {run.status === 'passed' ? '✓' : run.status === 'failed' ? '✗' : '·'}
          </span>
        </td>
        <td className="td-duration">{durStr}</td>
        <td className="td-time">{timeStr}</td>
        <td className="td-error">
          {errorPreview ? (
            <span className="run-error-preview">{errorPreview}</span>
          ) : (
            <span style={{ color: '#a8a8a8' }}>—</span>
          )}
        </td>
      </tr>
      {isExpanded && (
        <tr className="run-history-expanded">
          <td colSpan={4} style={{ padding: 0 }}>
            <div className="run-history-detail">
              {expandedLoading ? (
                <div className="test-case-workspace-running">
                  <div className="test-case-workspace-typing"><span></span><span></span><span></span></div>
                  <span className="test-case-workspace-running-text">Loading details...</span>
                </div>
              ) : (
                <>
                  {run.error_message && (
                    <div className="run-detail-error">
                      <div className="run-detail-error-label">Error</div>
                      <pre className="run-detail-error-text">{run.error_message}</pre>
                    </div>
                  )}
                  {expandedCases.length > 0 && (
                    <div className="run-detail-steps">
                      <div className="run-detail-steps-label">Step Results</div>
                      <ul className="run-detail-step-list">
                        {expandedCases.map((tc, i) => (
                          <li key={tc.id || i} className={`run-detail-step-item step-${tc.status}`}>
                            <span className={`step-badge step-${tc.status}`}>
                              {tc.status === 'passed' ? '✓' : tc.status === 'failed' ? '✗' : '·'}
                            </span>
                            <span className="run-detail-step-desc">
                              {tc.description || tc.test_id || `Step ${i + 1}`}
                            </span>
                            <span className="run-detail-step-duration">
                              {tc.duration ? `${tc.duration}ms` : '—'}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="run-detail-meta">
                    <span>Duration: {durStr}</span>
                    <span className="run-detail-meta-sep">|</span>
                    <span>Status: {run.status}</span>
                  </div>
                </>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
