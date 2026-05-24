export default function RunHistoryRow({ run, isExpanded, expandedCases, expandedLoading, onToggle, onSelectScreenshot }) {
  const shortRunId = run.run_id ? run.run_id.slice(0, 8) : '-';
  const timeStr = run.created_at
    ? new Date(run.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '-';
  const durStr = run.total_duration != null ? `${(run.total_duration / 1000).toFixed(1)}s` : '-';

  return (
    <>
      <tr className={`row-${run.status} run-history-row`} onClick={onToggle} style={{ cursor: 'pointer' }}>
        <td className="td-status">
          <span className={`step-badge step-${run.status}`}>
            {run.status === 'passed' ? '✓' : run.status === 'failed' ? '✗' : '·'}
          </span>
        </td>
        <td className="td-desc" style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px' }}>
          {shortRunId}
        </td>
        <td className="td-steps-count">
          {run.passed ?? 0}/{run.total_tests ?? 0}
        </td>
        <td className="td-duration">{durStr}</td>
        <td className="td-time">{timeStr}</td>
      </tr>
      {isExpanded && (
        <tr className="run-history-expanded">
          <td colSpan={5} style={{ padding: 0 }}>
            <div className="run-history-expanded-content">
              {expandedLoading ? (
                <div className="studio-workspace-running">
                  <div className="studio-workspace-typing"><span></span><span></span><span></span></div>
                  <span className="studio-workspace-running-text">Loading details...</span>
                </div>
              ) : expandedCases.length === 0 ? (
                <p className="studio-workspace-result-text">No step details available.</p>
              ) : (
                <table className="studio-workspace-steps-table">
                  <thead>
                    <tr>
                      <th className="th-step">#</th>
                      <th className="th-desc">Step</th>
                      <th className="th-status">Status</th>
                      <th className="th-duration">Duration</th>
                      <th className="th-screenshot">Screenshot</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expandedCases.map((tc, i) => (
                      <tr key={tc.id || i} className={`row-${tc.status}`}>
                        <td className="td-step">{i + 1}</td>
                        <td className="td-desc">
                          {tc.description || tc.test_id || `Step ${i + 1}`}
                          {tc.error_message && <span className="step-error">{tc.error_message}</span>}
                        </td>
                        <td className="td-status">
                          <span className={`step-badge step-${tc.status}`}>
                            {tc.status === 'passed' ? '✓' : tc.status === 'failed' ? '✗' : '·'}
                          </span>
                        </td>
                        <td className="td-duration">{tc.duration ? `${tc.duration}ms` : '-'}</td>
                        <td className="td-screenshot">
                          {tc.screenshot_path ? (
                            <button
                              className="step-screenshot-thumb"
                              onClick={(e) => { e.stopPropagation(); onSelectScreenshot(tc.screenshot_path); }}
                              title="Click to enlarge"
                            >
                              <img src={tc.screenshot_path} alt={`Step ${i + 1}`} />
                            </button>
                          ) : (
                            <span className="step-screenshot-placeholder">-</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
