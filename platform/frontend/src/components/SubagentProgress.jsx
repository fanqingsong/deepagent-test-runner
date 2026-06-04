export function SubagentProgress({ completed, total, percentage }) {
  if (total === 0) return null;

  return (
    <div className="subagent-progress">
      <div className="subagent-progress-labels">
        <span className="subagent-progress-text">Subagent progress</span>
        <span className="subagent-progress-count">{completed}/{total} complete</span>
      </div>
      <div className="subagent-progress-bar">
        <div
          className="subagent-progress-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
