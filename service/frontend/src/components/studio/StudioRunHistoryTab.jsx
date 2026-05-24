import RunHistoryRow from './RunHistoryRow';
import './studio-shared.css';

export default function StudioRunHistoryTab({
  runHistory,
  runHistoryLoading,
  expandedRunId,
  expandedRunCases,
  expandedLoading,
  onToggleRunExpand,
  onSelectScreenshot,
}) {
  if (runHistoryLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '48px', color: '#525252' }}>
        Loading run history...
      </div>
    );
  }

  if (runHistory.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '48px', color: '#8d8d8d' }}>
        No run history yet
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <div className="studio-section">
        <h3 className="studio-section-title">
          Run History
          <span style={{ fontWeight: 400, color: '#525252', fontSize: '13px', marginLeft: '8px' }}>
            {runHistory.length} runs
          </span>
        </h3>
        <table className="studio-workspace-steps-table">
          <thead>
            <tr>
              <th className="th-status">Status</th>
              <th className="th-desc">Run</th>
              <th className="th-steps-count">Steps</th>
              <th className="th-duration">Duration</th>
              <th className="th-time">Time</th>
            </tr>
          </thead>
          <tbody>
            {runHistory.map((run) => (
              <RunHistoryRow
                key={run.run_id}
                run={run}
                isExpanded={expandedRunId === run.run_id}
                expandedCases={expandedRunCases}
                expandedLoading={expandedLoading}
                onToggle={() => onToggleRunExpand(run.run_id)}
                onSelectScreenshot={onSelectScreenshot}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
