/**
 * Root Cause Analysis Page (Causal GraphRAG)
 *
 * Three-part demo UI following IBM Carbon styling:
 *  1. Knowledge graph visualization (SVG) of a run's failure subgraph, with the
 *     failure community / error nodes highlighted.
 *  2. Causal attribution card: difference-in-differences pass-rate chart with
 *     the detected intervention point, effect size, p-value and refutation.
 *  3. LLM-generated natural-language root cause summary (markdown).
 *
 * A self-contained SVG renderer is used for reliability in the demo container.
 */

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  analyzeRunRootCause,
  analyzeGlobalRootCause,
  buildRootCauseGraph,
} from '../api';
import './RootCauseAnalysisPage.css';

const VERDICT_META = {
  regression: { label: 'Regression', color: '#da1e28', desc: '由脚本/用例变更引入的回归' },
  env_issue: { label: 'Environment Issue', color: '#ff832b', desc: '环境/浏览器相关问题' },
  flaky: { label: 'Flaky', color: '#f1c21b', desc: '非确定性的偶发失败' },
  healthy: { label: 'Healthy', color: '#24a148', desc: '通过率正常' },
  inconclusive: { label: 'Inconclusive', color: '#6f6f6f', desc: '证据不足，需更多数据' },
};

const GROUP_COLORS = {
  TestRun: '#0f62fe',
  TestDefinition: '#8a3ffc',
  TestCaseResult: '#009d9a',
  ErrorPattern: '#da1e28',
  Selector: '#ff832b',
  Environment: '#697077',
  Url: '#005d5d',
};

function VerdictBadge({ verdict }) {
  const meta = VERDICT_META[verdict] || VERDICT_META.inconclusive;
  return (
    <span className="rc-badge" style={{ backgroundColor: meta.color }}>
      {meta.label}
    </span>
  );
}

/* ----------------------------- Graph (SVG) ----------------------------- */

function GraphView({ subgraph }) {
  const nodes = subgraph?.nodes || [];
  const edges = subgraph?.edges || [];

  if (!nodes.length) {
    return <div className="rc-empty">No graph data. Build the graph and analyze a run.</div>;
  }

  const width = 760;
  const height = 460;
  const cx = width / 2;
  const cy = height / 2;

  // Layered radial layout by group, deterministic per node id.
  const ringOrder = ['TestRun', 'TestDefinition', 'TestCaseResult', 'ErrorPattern', 'Selector', 'Environment', 'Url'];
  const radii = { TestRun: 0, TestDefinition: 90, TestCaseResult: 150, ErrorPattern: 220, Selector: 300, Environment: 120, Url: 150 };

  const byGroup = {};
  nodes.forEach((n) => {
    byGroup[n.group] = byGroup[n.group] || [];
    byGroup[n.group].push(n);
  });

  const pos = {};
  ringOrder.forEach((group) => {
    const list = byGroup[group] || [];
    const r = radii[group] ?? 200;
    list.forEach((n, i) => {
      if (group === 'TestRun') {
        pos[n.id] = { x: cx, y: cy };
      } else {
        const angle = (2 * Math.PI * i) / Math.max(list.length, 1) + (group.length % 5);
        pos[n.id] = { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
      }
    });
  });
  // Any group not in ringOrder
  nodes.forEach((n, i) => {
    if (!pos[n.id]) {
      const angle = (2 * Math.PI * i) / nodes.length;
      pos[n.id] = { x: cx + 200 * Math.cos(angle), y: cy + 200 * Math.sin(angle) };
    }
  });

  const nodeRadius = (n) => {
    if (n.group === 'ErrorPattern') return 16;
    if (n.group === 'TestRun') return 14;
    if (n.group === 'TestDefinition') return 12;
    return 8;
  };

  return (
    <div className="rc-graph-wrap">
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="rc-graph-svg">
        {edges.map((e, i) => {
          const s = pos[e.source];
          const t = pos[e.target];
          if (!s || !t) return null;
          return (
            <g key={`e-${i}`}>
              <line x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#c6c6c6" strokeWidth="1" />
            </g>
          );
        })}
        {nodes.map((n) => {
          const p = pos[n.id];
          if (!p) return null;
          const color = GROUP_COLORS[n.group] || '#8d8d8d';
          const isFailedCase = n.group === 'TestCaseResult' && n.passed === 0;
          const fill = isFailedCase ? '#da1e28' : color;
          return (
            <g key={n.id}>
              <circle
                cx={p.x}
                cy={p.y}
                r={nodeRadius(n)}
                fill={fill}
                stroke="#fff"
                strokeWidth="2"
              >
                <title>{`${n.group}: ${n.label}`}</title>
              </circle>
              <text
                x={p.x}
                y={p.y + nodeRadius(n) + 11}
                textAnchor="middle"
                className="rc-graph-label"
              >
                {String(n.label).slice(0, 18)}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="rc-legend">
        {Object.entries(GROUP_COLORS).map(([g, c]) => (
          <span key={g} className="rc-legend-item">
            <span className="rc-legend-dot" style={{ backgroundColor: c }} />
            {g}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ------------------------- DID pass-rate chart ------------------------- */

function PassRateChart({ series, interventionAt }) {
  if (!series || series.length < 2) {
    return <div className="rc-empty">Not enough time-series data for a chart.</div>;
  }
  const width = 720;
  const height = 240;
  const padding = { top: 20, right: 20, bottom: 36, left: 40 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const xs = series.map((_, i) => i);
  const xScale = (i) => padding.left + (innerW * i) / Math.max(series.length - 1, 1);
  const yScale = (v) => padding.top + innerH * (1 - v);

  const pathD = series
    .map((pt, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(pt.pass_rate)}`)
    .join(' ');

  // Map intervention date to nearest index.
  let interventionIdx = -1;
  if (interventionAt) {
    const target = interventionAt.slice(0, 10);
    interventionIdx = series.findIndex((pt) => pt.date >= target);
  }

  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="rc-chart-svg">
      {[0, 0.25, 0.5, 0.75, 1].map((g) => (
        <g key={g}>
          <line x1={padding.left} y1={yScale(g)} x2={width - padding.right} y2={yScale(g)} stroke="#e0e0e0" />
          <text x={padding.left - 6} y={yScale(g) + 4} textAnchor="end" className="rc-axis-label">
            {Math.round(g * 100)}%
          </text>
        </g>
      ))}
      {interventionIdx >= 0 && (
        <g>
          <line
            x1={xScale(interventionIdx)}
            y1={padding.top}
            x2={xScale(interventionIdx)}
            y2={padding.top + innerH}
            stroke="#da1e28"
            strokeDasharray="4 3"
            strokeWidth="1.5"
          />
          <text x={xScale(interventionIdx) + 4} y={padding.top + 10} className="rc-axis-label" fill="#da1e28">
            intervention
          </text>
        </g>
      )}
      <path d={pathD} fill="none" stroke="#0f62fe" strokeWidth="2" />
      {series.map((pt, i) => (
        <circle key={i} cx={xScale(i)} cy={yScale(pt.pass_rate)} r="3" fill="#0f62fe">
          <title>{`${pt.date}: ${Math.round(pt.pass_rate * 100)}% (n=${pt.n})`}</title>
        </circle>
      ))}
      <text x={padding.left} y={height - 8} className="rc-axis-label">{series[0].date}</text>
      <text x={width - padding.right} y={height - 8} textAnchor="end" className="rc-axis-label">
        {series[series.length - 1].date}
      </text>
    </svg>
  );
}

/* --------------------------- Causal card --------------------------- */

function CausalCard({ causal }) {
  if (!causal) return null;
  const primary = causal.primary || {};
  const effect = primary.effect;
  const pValue = primary.p_value;
  const refutation = primary.refutation;
  const interventionAt = primary.intervention_at;

  return (
    <div className="rc-card">
      <div className="rc-card-header">
        <h3>Causal Attribution</h3>
        <span className="rc-engine">{primary.engine || 'n/a'} · {primary.method || ''}</span>
      </div>

      <div className="rc-metrics">
        <div className="rc-metric">
          <div className="rc-metric-value">{causal.overall_pass_rate != null ? `${Math.round(causal.overall_pass_rate * 100)}%` : 'N/A'}</div>
          <div className="rc-metric-label">Overall pass rate</div>
        </div>
        <div className="rc-metric">
          <div className="rc-metric-value" style={{ color: effect < 0 ? '#da1e28' : '#161616' }}>
            {effect != null ? effect.toFixed(2) : 'N/A'}
          </div>
          <div className="rc-metric-label">Causal effect</div>
        </div>
        <div className="rc-metric">
          <div className="rc-metric-value">{pValue != null ? pValue.toFixed(3) : 'N/A'}</div>
          <div className="rc-metric-label">p-value</div>
        </div>
        <div className="rc-metric">
          <div className="rc-metric-value">{causal.n_samples ?? 0}</div>
          <div className="rc-metric-label">Samples</div>
        </div>
      </div>

      {primary.treatment && (
        <div className="rc-treatment">
          <strong>Treatment:</strong> {primary.treatment}
          {primary.before_pass_rate != null && (
            <span> · before {Math.round(primary.before_pass_rate * 100)}% → after {Math.round(primary.after_pass_rate * 100)}%</span>
          )}
          {primary.suspect_environment && (
            <span> · suspect {Math.round(primary.suspect_pass_rate * 100)}% vs others {Math.round(primary.other_pass_rate * 100)}%</span>
          )}
        </div>
      )}

      {refutation && (
        <div className={`rc-refute ${refutation.passed ? 'ok' : 'warn'}`}>
          Refutation ({refutation.method}): placebo effect {refutation.new_effect?.toFixed?.(3)} —{' '}
          {refutation.passed ? 'estimate is robust' : 'estimate may be unstable'}
        </div>
      )}

      <div className="rc-chart">
        <PassRateChart series={causal.time_series} interventionAt={interventionAt} />
      </div>
    </div>
  );
}

/* --------------------------- Global view --------------------------- */

function GlobalView({ data }) {
  if (!data) return null;
  return (
    <div>
      <div className="rc-card rc-summary-card">
        <div className="rc-card-header"><h3>Failure Landscape ({data.days}d)</h3></div>
        <ReactMarkdown>{data.summary || ''}</ReactMarkdown>
      </div>
      <div className="rc-communities">
        {(data.communities || []).map((c) => (
          <div key={c.id} className="rc-card rc-community">
            <div className="rc-community-head">
              <span className="rc-community-title">Community #{c.id} · {c.label}</span>
              <span className="rc-community-count">{c.failure_count} failures</span>
            </div>
            <div className="rc-community-body">
              <div><strong>Categories:</strong> {(c.categories || []).join(', ') || '—'}</div>
              <div><strong>Patterns:</strong> {c.pattern_count}</div>
              {c.selectors?.length > 0 && (
                <div><strong>Selectors:</strong> {c.selectors.slice(0, 5).join(', ')}</div>
              )}
            </div>
          </div>
        ))}
        {(data.communities || []).length === 0 && (
          <div className="rc-empty">No failure communities detected.</div>
        )}
      </div>
    </div>
  );
}

/* ----------------------------- Page ----------------------------- */

function RootCauseAnalysisPage() {
  const [runId, setRunId] = useState('rc-demo-regression-039');
  const [mode, setMode] = useState('run'); // 'run' | 'global'
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(false);
  const [building, setBuilding] = useState(false);
  const [error, setError] = useState(null);
  const [runResult, setRunResult] = useState(null);
  const [globalResult, setGlobalResult] = useState(null);
  const [buildMsg, setBuildMsg] = useState(null);

  const handleBuild = async () => {
    setBuilding(true);
    setError(null);
    setBuildMsg(null);
    try {
      const res = await buildRootCauseGraph(90);
      const stats = res.stats || {};
      setBuildMsg(
        res.status === 'ok'
          ? `Graph built: ${stats.nodes_written || 0} rows, ${stats.failed_cases || 0} failures, ${stats.communities || 0} communities.`
          : (res.message || 'No data to build.')
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBuilding(false);
    }
  };

  const handleAnalyzeRun = async () => {
    if (!runId.trim()) return;
    setLoading(true);
    setError(null);
    setRunResult(null);
    try {
      const res = await analyzeRunRootCause(runId.trim());
      setRunResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeGlobal = async () => {
    setLoading(true);
    setError(null);
    setGlobalResult(null);
    try {
      const res = await analyzeGlobalRootCause(days);
      setGlobalResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rc-page">
      <div className="rc-header">
        <div>
          <h1>Root Cause Analysis</h1>
          <p className="rc-subtitle">GraphRAG + Causal Inference (Neo4j · dowhy · GLM)</p>
        </div>
        <button className="rc-btn-secondary" onClick={handleBuild} disabled={building}>
          {building ? 'Building…' : 'Build Graph'}
        </button>
      </div>

      {buildMsg && <div className="rc-info">{buildMsg}</div>}
      {error && <div className="rc-error">{error}</div>}

      <div className="rc-tabs">
        <button className={mode === 'run' ? 'active' : ''} onClick={() => setMode('run')}>
          Run Analysis (Local)
        </button>
        <button className={mode === 'global' ? 'active' : ''} onClick={() => setMode('global')}>
          Failure Communities (Global)
        </button>
      </div>

      {mode === 'run' ? (
        <>
          <div className="rc-controls">
            <input
              className="rc-input"
              value={runId}
              onChange={(e) => setRunId(e.target.value)}
              placeholder="Enter run_id (e.g. rc-demo-regression-039)"
              onKeyDown={(e) => e.key === 'Enter' && handleAnalyzeRun()}
            />
            <button className="rc-btn-primary" onClick={handleAnalyzeRun} disabled={loading}>
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>
          <div className="rc-quick">
            Try:&nbsp;
            {['rc-demo-regression-039', 'rc-demo-flaky-035', 'rc-demo-env-039'].map((id) => (
              <button key={id} className="rc-chip" onClick={() => { setRunId(id); }}>{id}</button>
            ))}
          </div>

          {runResult && (
            <>
              <div className="rc-verdict-row">
                <VerdictBadge verdict={runResult.verdict} />
                <span className="rc-verdict-desc">
                  {(VERDICT_META[runResult.verdict] || VERDICT_META.inconclusive).desc}
                </span>
                {runResult.community && (
                  <span className="rc-community-tag">
                    Community: {runResult.community.label} ({runResult.community.failure_count})
                  </span>
                )}
              </div>

              <div className="rc-card rc-summary-card">
                <div className="rc-card-header">
                  <h3>AI Root Cause Summary</h3>
                  <span className="rc-ai-badge">GLM</span>
                </div>
                <ReactMarkdown>{runResult.summary || ''}</ReactMarkdown>
              </div>

              <div className="rc-grid">
                <div className="rc-card">
                  <div className="rc-card-header"><h3>Failure Knowledge Graph</h3></div>
                  <GraphView subgraph={runResult.subgraph} />
                </div>
                <CausalCard causal={runResult.causal} />
              </div>
            </>
          )}
        </>
      ) : (
        <>
          <div className="rc-controls">
            <select className="rc-input" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <button className="rc-btn-primary" onClick={handleAnalyzeGlobal} disabled={loading}>
              {loading ? 'Loading…' : 'Analyze'}
            </button>
          </div>
          <GlobalView data={globalResult} />
        </>
      )}
    </div>
  );
}

export default RootCauseAnalysisPage;
