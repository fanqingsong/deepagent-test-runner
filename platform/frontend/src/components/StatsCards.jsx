import './StatsCards.css';

function StatsCards({ stats, totalDefinitions }) {
  const formatPercentage = (value) => {
    if (value === null || value === undefined) return '0%';
    return `${Math.round(value)}%`;
  };

  const formatDuration = (ms) => {
    if (ms === null || ms === undefined || ms === 0) return '-';
    const seconds = ms / 1000;
    if (seconds < 60) return `${Math.round(seconds)}s`;
    return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  };

  const getPassRate = () => {
    const totalPassed = parseInt(stats.total_passed) || 0;
    const totalFailed = parseInt(stats.total_failed) || 0;
    const total = totalPassed + totalFailed;
    if (total === 0) return 0;
    return (totalPassed / total) * 100;
  }

  return (
    <div className="stats-cards-container">
      {/* Total runs */}
      <div className="stats-card">
        <div className="stats-title">Total Runs</div>
        <div className="stats-value total">
          {stats.total_runs || stats.successful_runs || 0}
        </div>
        <div className="stats-subtitle">
          Success: {stats.successful_runs || 0} | Failed: {stats.failed_runs || 0}
        </div>
      </div>

      {/* Pass rate */}
      <div className="stats-card">
        <div className="stats-title">Pass Rate</div>
        <div className="stats-value passRate">
          {formatPercentage(getPassRate())}
        </div>
        <div className="stats-subtitle">
          {stats.total_passed || 0} Passed / {stats.total_failed || 0} Failed
        </div>
      </div>

      {/* Average duration */}
      <div className="stats-card">
        <div className="stats-title">Avg Duration</div>
        <div className="stats-value duration">
          {formatDuration(stats.avg_duration)}
        </div>
        <div className="stats-subtitle">
          Based on all completed test runs
        </div>
      </div>

      {/* Total tests */}
      <div className="stats-card">
        <div className="stats-title">Total Test Cases</div>
        <div className="stats-value tests">
          {totalDefinitions || 0}
        </div>
        <div className="stats-subtitle">
          Active test definitions
        </div>
      </div>
    </div>
  );
}

export default StatsCards;
