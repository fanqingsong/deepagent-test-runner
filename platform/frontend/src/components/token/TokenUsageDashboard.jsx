import { useState, useEffect, useCallback } from 'react';
import {
  getTokenUsage,
  getTokenUsageSummary,
  getTokenUsageOverTime,
  getTokenUsageByScope,
} from '../../api/api-token';
import AlertBanner from '../AlertBanner';
import './TokenUsageDashboard.css';

const STATUS_LABELS = {
  active: 'Active',
  warning: 'Warning',
  exhausted: 'Exhausted',
  pending: 'Pending',
};

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

// Status Badge Component
function StatusBadge({ status }) {
  return <span className={`status-badge ${status}`}>{STATUS_LABELS[status] || status}</span>;
}

// Summary Card Component
function SummaryCard({ label, value, subtitle, className, trend }) {
  return (
    <div className={`summary-card ${className || ''}`}>
      <div className="summary-card-label">{label}</div>
      <div className="summary-card-value">{value}</div>
      <div className="summary-card-subtitle">{subtitle}</div>
      {trend && (
        <div className={`summary-card-trend ${trend >= 0 ? 'up' : 'down'}`}>
          {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}% vs last period
        </div>
      )}
    </div>
  );
}

// Budget Gauge Component
function BudgetGauge({ label, used, total, status, threshold }) {
  const percentage = total > 0 ? Math.min(100, (used / total) * 100) : 0;
  const warningThreshold = threshold || 80;

  return (
    <div className="budget-gauge">
      <div className="budget-gauge-header">
        <span className="budget-gauge-label">{label}</span>
        <StatusBadge status={status} />
      </div>
      <div className="budget-gauge-track">
        <div
          className={`budget-gauge-fill ${percentage >= warningThreshold ? 'warning' : ''}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="budget-gauge-footer">
        <span className="budget-gauge-used">{formatNumber(used)} tokens</span>
        <span className="budget-gauge-total">of {formatNumber(total)} total</span>
        <span className="budget-gauge-percentage">{formatPercentage(used, total)}</span>
      </div>
    </div>
  );
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

// Trend Chart Component
function TrendChart({ data, period }) {
  const canvasRef = useCallback((node) => {
    if (!node) return;

    // Simple canvas-based line chart
    const ctx = node.getContext('2d');
    const width = node.width = node.offsetWidth * 2;
    const height = node.height = 300 * 2;
    ctx.scale(2, 2);

    const effectiveWidth = width / 2;
    const effectiveHeight = height / 2;

    // Clear canvas
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

    // Find min and max values
    const maxValue = Math.max(...data.map(d => d.value || 0)) * 1.1;
    const minValue = 0;

    // Draw grid lines
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (chartHeight / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(effectiveWidth - padding.right, y);
      ctx.stroke();

      // Y-axis labels
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

  }, [data, period]);

  return (
    <div className="trend-chart">
      <h3 className="chart-title">Token Usage Trend</h3>
      <div className="chart-container">
        <canvas ref={canvasRef} style={{ width: '100%', height: '300px' }} />
      </div>
    </div>
  );
}

// Main Token Usage Dashboard Component
function TokenUsageDashboard() {
  const [period, setPeriod] = useState('daily');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [usageData, setUsageData] = useState(null);
  const [summaryData, setSummaryData] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [alerts, setAlerts] = useState([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [usage, summary, trend, scope] = await Promise.all([
        getTokenUsage(period),
        getTokenUsageSummary(),
        getTokenUsageOverTime(period),
        getTokenUsageByScope(period),
      ]);

      setUsageData(usage);
      setSummaryData(summary);
      setTrendData(trend.timeline || []);

      // Generate alerts from data
      const generatedAlerts = [];

      if (summary && summary.total_tokens) {
        const budgetLimit = summary.budget_limit || 1000000;
        const usagePercentage = (summary.total_tokens / budgetLimit) * 100;

        if (usagePercentage >= 90) {
          generatedAlerts.push({
            id: 'budget-critical',
            type: 'error',
            title: 'Budget Critical',
            message: `Token usage at ${usagePercentage.toFixed(1)}% of budget limit`,
            timestamp: new Date().toISOString(),
          });
        } else if (usagePercentage >= 75) {
          generatedAlerts.push({
            id: 'budget-warning',
            type: 'warning',
            title: 'Budget Warning',
            message: `Token usage at ${usagePercentage.toFixed(1)}% of budget limit`,
            timestamp: new Date().toISOString(),
          });
        }
      }

      setAlerts(generatedAlerts);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <div className="token-usage-dashboard">
        <div className="loading-state">Loading token usage data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="token-usage-dashboard">
        <AlertBanner
          message={`Error loading token data: ${error}`}
          type="error"
          onDismiss={() => setError(null)}
        />
      </div>
    );
  }

  const totalTokens = summaryData?.total_tokens || 0;
  const budgetLimit = summaryData?.budget_limit || 1000000;
  const totalCost = summaryData?.total_cost || 0;
  const callCount = summaryData?.call_count || 0;

  return (
    <div className="token-usage-dashboard">
      <div className="dashboard-header">
        <h2 className="dashboard-title">Token Usage Dashboard</h2>
        <PeriodSelector value={period} onChange={setPeriod} />
      </div>

      {alerts.length > 0 && (
        <div className="dashboard-alerts">
          {alerts.map((alert) => (
            <AlertBanner
              key={alert.id}
              message={alert.message}
              type={alert.type === 'error' ? 'error' : 'warning'}
              onDismiss={() => setAlerts((prev) => prev.filter((a) => a.id !== alert.id))}
            />
          ))}
        </div>
      )}

      <div className="summary-cards">
        <SummaryCard
          label="Total Tokens Used"
          value={formatNumber(totalTokens)}
          subtitle="In selected period"
          className="blue"
        />
        <SummaryCard
          label="Budget Utilization"
          value={formatPercentage(totalTokens, budgetLimit)}
          subtitle={`of ${formatNumber(budgetLimit)} budget`}
          className={totalTokens / budgetLimit >= 0.9 ? 'red' : totalTokens / budgetLimit >= 0.75 ? 'yellow' : 'green'}
        />
        <SummaryCard
          label="Total Cost"
          value={formatCurrency(totalCost)}
          subtitle="Across all operations"
        />
        <SummaryCard
          label="API Calls"
          value={formatNumber(callCount)}
          subtitle="In selected period"
        />
      </div>

      <div className="budget-gauges">
        <BudgetGauge
          label="Global Budget"
          used={totalTokens}
          total={budgetLimit}
          status={totalTokens / budgetLimit >= 0.9 ? 'exhausted' : totalTokens / budgetLimit >= 0.75 ? 'warning' : 'active'}
          threshold={75}
        />
      </div>

      <TrendChart data={trendData} period={period} />
    </div>
  );
}

export default TokenUsageDashboard;
