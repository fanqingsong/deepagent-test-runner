import { useState, useEffect, useCallback } from 'react';
import {
  getTokenAnalytics,
  getTokenUsageByScope,
  getTokenUsageOverTime,
  getTokenCostBreakdown,
  getModelComparison,
  getAgentRankings,
  getTokenForecast,
} from '../../api/api-token';
import AlertBanner from '../AlertBanner';
import './TokenAnalytics.css';

function formatNumber(num) {
  if (!num && num !== 0) return '0';
  return num.toLocaleString();
}

function formatCurrency(num) {
  if (!num && num !== 0) return '$0.00';
  return `$${num.toFixed(2)}`;
}

function formatPercentage(value, total) {
  if (!total || total === 0) return '0%';
  return `${Math.round((value / total) * 100)}%`;
}

// Period Selector Component
function PeriodSelector({ value, onChange }) {
  const periods = [
    { value: 'hourly', label: 'Hourly' },
    { value: 'daily', label: 'Daily' },
    { value: 'weekly', label: 'Weekly' },
    { value: 'monthly', label: 'Monthly' },
  ];

  return (
    <div className="period-selector">
      {periods.map((period) => (
        <button
          key={period.value}
          className={`period-button ${value === period.value ? 'active' : ''}`}
          onClick={() => onChange(period.value)}
        >
          {period.label}
        </button>
      ))}
    </div>
  );
}

// Stat Card Component
function StatCard({ label, value, subtitle, trend, color = '#0f62fe' }) {
  return (
    <div className="stat-card" style={{ borderTopColor: color }}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-subtitle">{subtitle}</div>
      {trend !== undefined && (
        <div className={`stat-trend ${trend >= 0 ? 'up' : 'down'}`}>
          {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}% vs last period
        </div>
      )}
    </div>
  );
}

// Simple Pie Chart Component
function PieChart({ data, title }) {
  const canvasRef = useCallback((node) => {
    if (!node) return;

    const ctx = node.getContext('2d');
    const width = node.width = node.offsetWidth * 2;
    const height = node.height = 300 * 2;
    ctx.scale(2, 2);

    const effectiveWidth = width / 2;
    const effectiveHeight = height / 2;

    ctx.clearRect(0, 0, effectiveWidth, effectiveHeight);

    if (!data || data.length === 0) {
      ctx.fillStyle = '#6f6f6f';
      ctx.font = '14px IBM Plex Sans';
      ctx.textAlign = 'center';
      ctx.fillText('No data available', effectiveWidth / 2, effectiveHeight / 2);
      return;
    }

    const centerX = effectiveWidth / 2;
    const centerY = effectiveHeight / 2;
    const radius = Math.min(centerX, centerY) - 40;

    const colors = ['#0f62fe', '#0043ce', '#002d9c', '#4589ff', '#78a9ff', '#abccff'];
    const total = data.reduce((sum, item) => sum + item.value, 0);

    let startAngle = -Math.PI / 2;

    data.forEach((item, index) => {
      const sliceAngle = (item.value / total) * Math.PI * 2;
      const endAngle = startAngle + sliceAngle;

      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, startAngle, endAngle);
      ctx.closePath();
      ctx.fillStyle = colors[index % colors.length];
      ctx.fill();

      startAngle = endAngle;
    });

    // Draw legend
    const legendX = 20;
    let legendY = 20;

    data.forEach((item, index) => {
      ctx.fillStyle = colors[index % colors.length];
      ctx.fillRect(legendX, legendY, 12, 12);

      ctx.fillStyle = '#161616';
      ctx.font = '12px IBM Plex Sans';
      ctx.textAlign = 'left';
      ctx.fillText(
        `${item.label} (${formatPercentage(item.value, total)})`,
        legendX + 20,
        legendY + 10
      );

      legendY += 24;
    });

  }, [data]);

  return (
    <div className="chart-card">
      <h3 className="chart-title">{title}</h3>
      <div className="chart-container">
        <canvas ref={canvasRef} style={{ width: '100%', height: '300px' }} />
      </div>
    </div>
  );
}

// Simple Bar Chart Component
function BarChart({ data, title, xAxis, yAxis }) {
  const canvasRef = useCallback((node) => {
    if (!node) return;

    const ctx = node.getContext('2d');
    const width = node.width = node.offsetWidth * 2;
    const height = node.height = 300 * 2;
    ctx.scale(2, 2);

    const effectiveWidth = width / 2;
    const effectiveHeight = height / 2;

    ctx.clearRect(0, 0, effectiveWidth, effectiveHeight);

    if (!data || data.length === 0) {
      ctx.fillStyle = '#6f6f6f';
      ctx.font = '14px IBM Plex Sans';
      ctx.textAlign = 'center';
      ctx.fillText('No data available', effectiveWidth / 2, effectiveHeight / 2);
      return;
    }

    const padding = { top: 20, right: 20, bottom: 60, left: 60 };
    const chartWidth = effectiveWidth - padding.left - padding.right;
    const chartHeight = effectiveHeight - padding.top - padding.bottom;

    const maxValue = Math.max(...data.map(d => d.value || 0)) * 1.1;

    // Draw grid lines
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (chartHeight / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(effectiveWidth - padding.right, y);
      ctx.stroke();

      const value = maxValue - (maxValue / 5) * i;
      ctx.fillStyle = '#6f6f6f';
      ctx.font = '12px IBM Plex Sans';
      ctx.textAlign = 'right';
      ctx.fillText(formatNumber(Math.round(value)), padding.left - 10, y + 4);
    }

    // Draw bars
    const barWidth = (chartWidth / data.length) * 0.6;
    const barGap = (chartWidth / data.length) * 0.4;

    data.forEach((item, index) => {
      const x = padding.left + (barWidth + barGap) * index + barGap / 2;
      const barHeight = ((item.value || 0) / maxValue) * chartHeight;
      const y = padding.top + chartHeight - barHeight;

      ctx.fillStyle = '#0f62fe';
      ctx.fillRect(x, y, barWidth, barHeight);

      // X-axis label
      ctx.fillStyle = '#6f6f6f';
      ctx.font = '12px IBM Plex Sans';
      ctx.textAlign = 'center';
      const label = item.label || item[xAxis] || '';
      const shortLabel = label.length > 8 ? label.substring(0, 8) + '...' : label;
      ctx.fillText(shortLabel, x + barWidth / 2, effectiveHeight - padding.bottom + 20);
    });

  }, [data, xAxis, yAxis]);

  return (
    <div className="chart-card">
      <h3 className="chart-title">{title}</h3>
      <div className="chart-container">
        <canvas ref={canvasRef} style={{ width: '100%', height: '300px' }} />
      </div>
    </div>
  );
}

// Line Chart Component
function LineChart({ data, title }) {
  const canvasRef = useCallback((node) => {
    if (!node) return;

    const ctx = node.getContext('2d');
    const width = node.width = node.offsetWidth * 2;
    const height = node.height = 300 * 2;
    ctx.scale(2, 2);

    const effectiveWidth = width / 2;
    const effectiveHeight = height / 2;

    ctx.clearRect(0, 0, effectiveWidth, effectiveHeight);

    if (!data || data.length === 0) {
      ctx.fillStyle = '#6f6f6f';
      ctx.font = '14px IBM Plex Sans';
      ctx.textAlign = 'center';
      ctx.fillText('No data available', effectiveWidth / 2, effectiveHeight / 2);
      return;
    }

    const padding = { top: 20, right: 20, bottom: 40, left: 60 };
    const chartWidth = effectiveWidth - padding.left - padding.right;
    const chartHeight = effectiveHeight - padding.top - padding.bottom;

    const maxValue = Math.max(...data.map(d => d.value || 0)) * 1.1;

    // Draw grid lines
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (chartHeight / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(effectiveWidth - padding.right, y);
      ctx.stroke();

      const value = maxValue - (maxValue / 5) * i;
      ctx.fillStyle = '#6f6f6f';
      ctx.font = '12px IBM Plex Sans';
      ctx.textAlign = 'right';
      ctx.fillText(formatNumber(Math.round(value)), padding.left - 10, y + 4);
    }

    // Draw line
    ctx.strokeStyle = '#0f62fe';
    ctx.lineWidth = 2;
    ctx.beginPath();

    data.forEach((point, index) => {
      const x = padding.left + (chartWidth / (data.length - 1 || 1)) * index;
      const y = padding.top + chartHeight - ((point.value || 0) / maxValue) * chartHeight;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();

    // Draw data points
    ctx.fillStyle = '#0f62fe';
    data.forEach((point, index) => {
      const x = padding.left + (chartWidth / (data.length - 1 || 1)) * index;
      const y = padding.top + chartHeight - ((point.value || 0) / maxValue) * chartHeight;

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    });

    // X-axis labels
    ctx.fillStyle = '#6f6f6f';
    ctx.font = '12px IBM Plex Sans';
    ctx.textAlign = 'center';

    const labelCount = Math.min(data.length, 6);
    const step = Math.ceil(data.length / labelCount);

    data.forEach((point, index) => {
      if (index % step === 0 || index === data.length - 1) {
        const x = padding.left + (chartWidth / (data.length - 1 || 1)) * index;
        const label = point.label || point.timestamp || '';
        const shortLabel = label.length > 8 ? label.substring(0, 8) + '...' : label;
        ctx.fillText(shortLabel, x, effectiveHeight - padding.bottom + 20);
      }
    });

  }, [data]);

  return (
    <div className="chart-card">
      <h3 className="chart-title">{title}</h3>
      <div className="chart-container">
        <canvas ref={canvasRef} style={{ width: '100%', height: '300px' }} />
      </div>
    </div>
  );
}

// Ranking Table Component
function RankingTable({ data, title }) {
  return (
    <div className="ranking-table-card">
      <h3 className="ranking-title">{title}</h3>
      <div className="ranking-list">
        {data.map((item, index) => (
          <div key={item.id || item.name} className="ranking-item">
            <div className="ranking-position">#{index + 1}</div>
            <div className="ranking-info">
              <div className="ranking-name">{item.name || item.label}</div>
              <div className="ranking-subtitle">{item.subtitle || ''}</div>
            </div>
            <div className="ranking-value">{formatNumber(item.value || item.tokens)}</div>
            <div className="ranking-bar">
              <div
                className="ranking-bar-fill"
                style={{ width: `${item.percentage || 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Main Token Analytics Component
function TokenAnalytics() {
  const [period, setPeriod] = useState('daily');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [scopeData, setScopeData] = useState([]);
  const [timelineData, setTimelineData] = useState([]);
  const [costData, setCostData] = useState([]);
  const [modelData, setModelData] = useState([]);
  const [agentRankings, setAgentRankings] = useState([]);
  const [forecast, setForecast] = useState(null);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [
        analyticsData,
        scope,
        timeline,
        costs,
        models,
        agents,
        forecastData,
      ] = await Promise.all([
        getTokenAnalytics({ period }),
        getTokenUsageByScope(period),
        getTokenUsageOverTime(period),
        getTokenCostBreakdown(period),
        getModelComparison(period),
        getAgentRankings(period),
        getTokenForecast({ period }),
      ]);

      setAnalytics(analyticsData);
      setScopeData(scope);
      setTimelineData(timeline);
      setCostData(costs);
      setModelData(models);
      setAgentRankings(agents);
      setForecast(forecastData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  if (loading) {
    return (
      <div className="token-analytics">
        <div className="loading-state">Loading analytics data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="token-analytics">
        <AlertBanner
          message={`Error: ${error}`}
          type="error"
          onDismiss={() => setError(null)}
        />
      </div>
    );
  }

  const totalTokens = analytics?.total_tokens || 0;
  const totalCost = analytics?.total_cost || 0;
  const avgLatency = analytics?.avg_duration_ms || 0;
  const callCount = analytics?.call_count || 0;

  return (
    <div className="token-analytics">
      <div className="page-header">
        <h2 className="page-title">Token Analytics</h2>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      <div className="stats-grid">
        <StatCard
          label="Total Tokens"
          value={formatNumber(totalTokens)}
          subtitle="In selected period"
          trend={analytics?.trend?.tokens}
        />
        <StatCard
          label="Total Cost"
          value={formatCurrency(totalCost)}
          subtitle="Across all operations"
          trend={analytics?.trend?.cost}
        />
        <StatCard
          label="API Calls"
          value={formatNumber(callCount)}
          subtitle="Total requests"
          trend={analytics?.trend?.calls}
        />
        <StatCard
          label="Avg Latency"
          value={`${Math.round(avgLatency)}ms`}
          subtitle="Per request"
          trend={analytics?.trend?.latency}
          color="#24a148"
        />
      </div>

      <div className="charts-grid">
        <div className="chart-row">
          <PieChart
            data={scopeData}
            title="Usage by Scope"
          />
          <PieChart
            data={costData}
            title="Cost Breakdown"
          />
        </div>

        <div className="chart-row">
          <LineChart
            data={timelineData}
            title="Usage Over Time"
          />
          <BarChart
            data={modelData}
            title="Model Comparison"
            xAxis="model"
            yAxis="tokens"
          />
        </div>
      </div>

      <div className="rankings-grid">
        <RankingTable
          data={agentRankings}
          title="Top Agents by Usage"
        />
      </div>

      {forecast && (
        <div className="forecast-section">
          <h3 className="section-title">Forecast</h3>
          <div className="forecast-cards">
            <StatCard
              label="Predicted Usage (Next Period)"
              value={formatNumber(forecast.predicted_tokens)}
              subtitle={`${forecast.confidence || 85}% confidence`}
            />
            <StatCard
              label="Predicted Cost"
              value={formatCurrency(forecast.predicted_cost)}
              subtitle="Based on current trends"
            />
            <StatCard
              label="Budget Exhaustion Date"
              value={forecast.exhaustion_date || 'N/A'}
              subtitle="If current trend continues"
              color="#da1e28"
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default TokenAnalytics;
