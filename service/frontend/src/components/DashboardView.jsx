import React, { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useDashboard, useSuiteTimeline, useSuiteRunEntries } from '../hooks/useDashboard';
import { useLlmUsage } from '../hooks/useLlmUsage';
import RefreshIndicator from './RefreshIndicator';
import './DashboardView.css';

const STATUS_LABELS = {
  passed: 'Passed',
  failed: 'Failed',
  running: 'Running',
  pending: 'Pending',
  skipped: 'Skipped',
  cancelled: 'Cancelled',
  completed: 'Completed',
  partial: 'Partial',
};

function formatDuration(ms) {
  if (!ms && ms !== 0) return '-';
  const s = ms / 1000;
  if (s < 60) return `${Math.round(s)}s`;
  return `${Math.round(s / 60)}m ${Math.round(s % 60)}s`;
}

function formatTime(isoStr) {
  if (!isoStr) return '-';
  const d = new Date(isoStr);
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function StatusDot({ status }) {
  return <span className={`status-dot ${status}`} />;
}

// --- Stats Cards ---
function StatsCards({ summary }) {
  const cards = [
    { label: 'Test Suites', value: summary.total_suites ?? 0, sub: 'Created suites', className: 'blue' },
    { label: 'Suite Runs', value: summary.total_runs ?? 0, sub: 'In selected period', className: '' },
    { label: 'Pass Rate', value: `${summary.pass_rate ?? 0}%`, sub: 'Test case pass ratio', className: (summary.pass_rate ?? 0) >= 80 ? 'green' : 'red' },
    { label: 'Avg Duration', value: formatDuration(summary.avg_duration), sub: 'Suite execution average', className: '' },
    { label: 'Test Executions', value: summary.total_tests_executed ?? 0, sub: 'Total test cases run', className: '' },
  ];

  return (
    <div className="dashboard-stats">
      {cards.map((c) => (
        <div className="stat-card" key={c.label}>
          <div className="stat-card-label">{c.label}</div>
          <div className={`stat-card-value ${c.className}`}>{c.value}</div>
          <div className="stat-card-sub">{c.sub}</div>
        </div>
      ))}
    </div>
  );
}

// --- LLM Usage Cards ---
function LlmUsageCards({ summary, byAgent }) {
  const totalTokens = summary.total_tokens || 0;
  const callCount = summary.call_count || 0;
  const avgLatency = summary.avg_duration_ms || 0;

  const cards = [
    { label: 'Total Tokens', value: totalTokens.toLocaleString(), sub: 'Across all agents', className: 'blue' },
    { label: 'LLM Calls', value: callCount.toLocaleString(), sub: 'In selected period', className: '' },
    { label: 'Avg Latency', value: formatDuration(avgLatency), sub: 'Per LLM call', className: '' },
  ];

  return (
    <div className="dashboard-stats llm-usage-stats">
      {cards.map((c) => (
        <div className="stat-card" key={c.label}>
          <div className="stat-card-label">{c.label}</div>
          <div className={`stat-card-value ${c.className}`}>{c.value}</div>
          <div className="stat-card-sub">{c.sub}</div>
        </div>
      ))}
      {byAgent.length > 0 && (
        <div className="stat-card llm-agent-breakdown">
          <div className="stat-card-label">By Agent</div>
          <div className="llm-agent-bars">
            {byAgent.map((a) => (
              <div key={a.agent_type} className="llm-agent-bar-row">
                <span className="llm-agent-name">{a.agent_type}</span>
                <div className="llm-agent-bar-track">
                  <div
                    className="llm-agent-bar-fill"
                    style={{ width: `${Math.min(100, (a.total_tokens / totalTokens) * 100)}%` }}
                  />
                </div>
                <span className="llm-agent-value">{(a.total_tokens || 0).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// --- Suite List Panel ---
function SuiteListPanel({ suites, selectedId, onSelect }) {
  return (
    <div className="suite-list-panel">
      <div className="suite-list-header">
        Test Suites
        <span className="suite-count-badge">{suites.length}</span>
      </div>
      {suites.length === 0 ? (
        <div style={{ padding: 24, textAlign: 'center', color: '#8d8d8d', fontSize: 13 }}>
          No test suites yet
        </div>
      ) : (
        suites.map((suite) => (
          <div
            key={suite.id}
            className={`suite-list-item ${selectedId === suite.id ? 'active' : ''}`}
            onClick={() => onSelect(suite.id)}
          >
            <div className="suite-list-item-name">{suite.name}</div>
            <div className="suite-list-item-badges">
              <span className="suite-badge mode">
                {suite.execution_mode === 'parallel' ? 'Parallel' : 'Sequential'}
              </span>
              {suite.is_dynamic && <span className="suite-badge dynamic">Dynamic</span>}
              <span className="suite-badge count">{suite.test_count} tests</span>
            </div>
            <div className="suite-list-item-status">
              {suite.latest_run ? (
                <>
                  <StatusDot status={suite.latest_run.status} />
                  {STATUS_LABELS[suite.latest_run.status] || suite.latest_run.status}
                  {' · '}
                  {suite.latest_run.passed}/{suite.latest_run.total_tests} passed
                </>
              ) : (
                'No runs yet'
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// --- Test Cases (inside a run entry) ---
function TestCaseList({ testCases }) {
  if (!testCases || testCases.length === 0) return null;

  return (
    <div className="test-cases-list">
      {testCases.map((tc, i) => (
        <React.Fragment key={tc.test_id || i}>
          <div className="test-case-item">
            <span className="test-case-connector">{i === testCases.length - 1 ? '└' : '├'}</span>
            <span className={`test-case-status-dot ${tc.status}`} />
            <span className="test-case-desc">{tc.description || tc.test_id || `Step ${i + 1}`}</span>
            <span className="test-case-duration">{formatDuration(tc.duration)}</span>
          </div>
          {tc.status === 'failed' && tc.error_message && (
            <div className="test-case-error">{tc.error_message}</div>
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

// --- Run Entry (inside a timeline run) ---
function RunEntry({ entry, runId, expandedEntryId, onToggleExpand }) {
  const isExpanded = expandedEntryId === entry.entry_order;
  const { data: runEntriesData, isLoading } = useSuiteRunEntries(
    isExpanded && entry.status !== 'pending' ? runId : null
  );

  const entryTestCases = runEntriesData?.entries?.find(
    (e) => e.entry_order === entry.entry_order
  )?.test_cases || [];

  return (
    <div className={`run-entry ${entry.status}`}>
      <div className="run-entry-header" onClick={() => onToggleExpand(entry.entry_order)}>
        <span className="run-entry-order">{entry.entry_order}.</span>
        <span className="run-entry-name">{entry.test_name}</span>
        <span className={`run-entry-status ${entry.status}`}>
          {STATUS_LABELS[entry.status] || entry.status}
        </span>
        <span className="run-entry-duration">{formatDuration(entry.duration)}</span>
        <span className={`run-entry-expand-icon ${isExpanded ? 'expanded' : ''}`}>▶</span>
      </div>
      {entry.error_message && (
        <div className="run-entry-error">{entry.error_message}</div>
      )}
      {isExpanded && isLoading && (
        <div className="timeline-loading"><span className="spinner" /> Loading test cases...</div>
      )}
      {isExpanded && !isLoading && entryTestCases.length > 0 && (
        <TestCaseList testCases={entryTestCases} />
      )}
      {isExpanded && !isLoading && entryTestCases.length === 0 && entry.status === 'pending' && (
        <div style={{ padding: '8px 12px', fontSize: 12, color: '#8d8d8d' }}>Pending execution</div>
      )}
    </div>
  );
}

// --- Timeline Run ---
function TimelineRun({ run, isExpanded, onToggle }) {
  const hasEntries = run.entries && run.entries.length > 0;
  const runId = run.run_id;
  const [expandedEntryId, setExpandedEntryId] = useState(null);

  const handleToggleEntry = useCallback((entryOrder) => {
    setExpandedEntryId((prev) => (prev === entryOrder ? null : entryOrder));
  }, []);

  return (
    <div className="timeline-run">
      <div className={`timeline-run-dot ${run.status}`} />
      <div
        className={`timeline-run-summary ${isExpanded ? 'expanded' : ''}`}
        onClick={hasEntries ? onToggle : undefined}
        style={{ cursor: hasEntries ? 'pointer' : 'default' }}
      >
        <span className="timeline-run-time">{formatTime(run.created_at)}</span>
        <span className="timeline-run-status">
          <StatusDot status={run.status} /> {STATUS_LABELS[run.status] || run.status}
        </span>
        <span className="timeline-run-stats">
          <span className="passed-count">{run.passed}</span>/
          <span className="failed-count">{run.failed}</span>/{run.skipped || 0}
        </span>
        <span className="timeline-run-duration">{formatDuration(run.total_duration)}</span>
        {run.triggered_by && (
          <span className="timeline-run-trigger">{run.triggered_by}</span>
        )}
        {hasEntries && (
          <span className={`timeline-run-expand ${isExpanded ? 'expanded' : ''}`}>▶</span>
        )}
      </div>

      {isExpanded && hasEntries && (
        <div className="timeline-run-entries">
          {run.entries.map((entry) => (
            <RunEntry
              key={entry.entry_order}
              entry={entry}
              runId={runId}
              expandedEntryId={expandedEntryId}
              onToggleExpand={handleToggleEntry}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// --- Timeline Panel ---
function TimelinePanel({ suiteId, suiteName, suiteMeta }) {
  const { data: runs = [], isLoading, isError } = useSuiteTimeline(suiteId);

  if (!suiteId) {
    return (
      <div className="timeline-panel">
        <div className="timeline-empty">
          <div className="timeline-empty-icon">◀</div>
          <div className="timeline-empty-text">Select a test suite</div>
          <div className="timeline-empty-sub">Choose a suite from the left list to view run timeline</div>
        </div>
      </div>
    );
  }

  return (
    <div className="timeline-panel">
      <div className="timeline-suite-header">
        <h2 className="timeline-suite-name">{suiteName || 'Loading...'}</h2>
        {suiteMeta && (
          <div className="timeline-suite-meta">
            <span>{suiteMeta.execution_mode === 'parallel' ? 'Parallel execution' : 'Sequential execution'}</span>
            <span>{suiteMeta.test_count} tests</span>
            <span>Strategy: {suiteMeta.fail_strategy === 'fail_fast' ? 'Fail fast' : 'Continue'}</span>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="timeline-loading"><span className="spinner" /> Loading runs...</div>
      ) : isError ? (
        <div className="timeline-loading" style={{ color: '#da1e28' }}>Load failed</div>
      ) : runs.length === 0 ? (
        <div className="timeline-empty">
          <div className="timeline-empty-icon">📋</div>
          <div className="timeline-empty-text">No runs yet</div>
          <div className="timeline-empty-sub">This suite has not been executed yet</div>
        </div>
      ) : (
        <TimelineView runs={runs} />
      )}
    </div>
  );
}

function TimelineView({ runs }) {
  const [expandedRunId, setExpandedRunId] = useState(null);

  const handleToggle = useCallback((runId) => {
    setExpandedRunId((prev) => (prev === runId ? null : runId));
  }, []);

  return (
    <div className="timeline">
      {runs.map((run) => (
        <TimelineRun
          key={run.run_id}
          run={run}
          isExpanded={expandedRunId === run.run_id}
          onToggle={() => handleToggle(run.run_id)}
        />
      ))}
    </div>
  );
}

// --- Main Dashboard ---
function DashboardView() {
  const { user, isAdmin } = useAuth();
  const [timeRange, setTimeRange] = useState('30d');
  const [selectedSuiteId, setSelectedSuiteId] = useState(null);

  const {
    dashboardData,
    isLoading,
    isError,
    error,
    isRefreshing,
  } = useDashboard(timeRange);

  const { summary = {}, suites = [] } = dashboardData;
  const selectedSuite = suites.find((s) => s.id === selectedSuiteId);

  const days = parseInt(timeRange);
  const { summary: llmSummary = {}, byAgent: llmByAgent = [] } = useLlmUsage(days);

  useEffect(() => {
    if (!selectedSuiteId && suites.length > 0) {
      setSelectedSuiteId(suites[0].id);
    }
  }, [selectedSuiteId, suites]);

  if (isLoading) {
    return (
      <div className="suite-dashboard">
        <div className="timeline-loading" style={{ padding: 80 }}>
          <span className="spinner" /> Loading dashboard data...
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="suite-dashboard">
        <div className="dashboard-error">{error?.message || 'Load failed'}</div>
      </div>
    );
  }

  const ranges = [
    { value: '7d', label: '7 days' },
    { value: '30d', label: '30 days' },
    { value: '90d', label: '90 days' },
  ];

  return (
    <div className="suite-dashboard">
      <RefreshIndicator refreshing={isRefreshing} />

      <div className="dashboard-header">
        <h1 className="dashboard-title">Test Dashboard</h1>
        <div className="dashboard-controls">
          <div className="time-range-group">
            {ranges.map((r) => (
              <button
                key={r.value}
                className={`time-range-btn ${timeRange === r.value ? 'active' : ''}`}
                onClick={() => setTimeRange(r.value)}
              >
                {r.label}
              </button>
            ))}
          </div>
          <div className={`role-badge ${isAdmin ? 'admin' : ''}`}>
            {isAdmin ? 'Admin View' : 'Personal View'}
          </div>
        </div>
      </div>

      <StatsCards summary={summary} />

      <LlmUsageCards summary={llmSummary} byAgent={llmByAgent} />

      <div className="dashboard-content">
        <SuiteListPanel
          suites={suites}
          selectedId={selectedSuiteId}
          onSelect={setSelectedSuiteId}
        />
        <TimelinePanel
          suiteId={selectedSuiteId}
          suiteName={selectedSuite?.name}
          suiteMeta={selectedSuite}
        />
      </div>
    </div>
  );
}

export default DashboardView;
