/**
 * System Status Radar Chart Component (Pure SVG)
 *
 * Displays system health status using a radar chart with multiple dimensions.
 * IBM Carbon-inspired design system.
 * No external chart libraries required.
 */

import { useMemo } from 'react';
import './SystemStatusRadar.css';

/**
 * Calculate health score from metrics (0-100)
 */
function calculateHealthScores(metrics) {
  if (!metrics) {
    return {
      testExecution: 50,
      llmPerformance: 50,
      resources: 50,
      userActivity: 50,
      alertLevel: 50,
    };
  }

  const testMetrics = metrics.test_execution?.test_runs_24h || {};
  const llmMetrics = metrics.llm_performance?.token_usage_24h || {};
  const resourceMetrics = metrics.resources || {};
  const userMetrics = metrics.user_activity || {};
  const alertsGenerated = metrics.alerts_generated || [];

  // Test Execution Health: Based on pass rate
  const passRate = testMetrics.pass_rate || 0;
  const testExecutionScore = Math.round(passRate * 100);

  // LLM Performance: Based on response time
  const avgResponse = metrics.llm_performance?.avg_response_time_ms || 0;
  const responseScore = Math.max(0, Math.min(100, 100 - (avgResponse / 50)));
  const llmPerformanceScore = Math.round(responseScore);

  // Resource Status: Check if all resources are healthy
  let resourceHealth = 100;
  if (resourceMetrics.database?.status !== 'healthy') resourceHealth -= 30;
  if (resourceMetrics.temporal?.status !== 'healthy') resourceHealth -= 30;
  if (resourceMetrics.redis?.status !== 'healthy') resourceHealth -= 30;
  const resourcesScore = Math.max(0, resourceHealth);

  // User Activity: Based on active users
  const activeUsers = userMetrics.active_users_24h || 0;
  const userActivityScore = Math.min(100, Math.round(50 + activeUsers * 5));

  // Alert Level: Inverse of number of alerts
  const alertCount = alertsGenerated.length || 0;
  const alertLevelScore = Math.max(0, Math.round(100 - alertCount * 10));

  return {
    testExecution: testExecutionScore,
    llmPerformance: llmPerformanceScore,
    resources: resourcesScore,
    userActivity: userActivityScore,
    alertLevel: alertLevelScore,
  };
}

/**
 * Get color based on score
 */
function getScoreColor(score) {
  if (score >= 90) return { main: 'rgba(25, 128, 25, 0.7)', border: '#198038', label: '#198038' };
  if (score >= 70) return { main: 'rgba(106, 176, 76, 0.7)', border: '#27ae60', label: '#27ae60' };
  if (score >= 50) return { main: 'rgba(255, 193, 7, 0.7)', border: '#f1c40f', label: '#f1c40f' };
  if (score >= 30) return { main: 'rgba(255, 152, 0, 0.7)', border: '#e67e22', label: '#e67e22' };
  return { main: 'rgba(244, 67, 54, 0.7)', border: '#e74c3c', label: '#e74c3c' };
}

/**
 * Get status label from score
 */
function getStatusLabel(score) {
  if (score >= 90) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 50) return 'Fair';
  if (score >= 30) return 'Poor';
  return 'Critical';
}

/**
 * Get overall status from scores
 */
function getOverallStatus(scores) {
  const average = Object.values(scores).reduce((sum, val) => sum + val, 0) / Object.values(scores).length;

  if (average >= 80) return { status: 'Excellent', color: '#198038' };
  if (average >= 60) return { status: 'Good', color: '#27ae60' };
  if (average >= 40) return { status: 'Fair', color: '#f1c40f' };
  if (average >= 20) return { status: 'Poor', color: '#e67e22' };
  return { status: 'Critical', color: '#e74c3c' };
}

/**
 * Convert polar coordinates to Cartesian
 */
function polarToCartesian(centerX, centerY, radius, angleInRadians) {
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians),
  };
}

function SystemStatusRadar({ metrics = null, size = 'medium' }) {
  const scores = useMemo(() => calculateHealthScores(metrics), [metrics]);
  const overallStatus = useMemo(() => getOverallStatus(scores), [scores]);

  // Radar chart dimensions
  const centerX = 150;
  const centerY = 150;
  const radius = 100;
  const maxScore = 100;

  // Chart labels
  const labels = [
    { text: 'Test Execution', subtext: '测试执行', score: scores.testExecution },
    { text: 'LLM Performance', subtext: 'LLM性能', score: scores.llmPerformance },
    { text: 'Resources', subtext: '系统资源', score: scores.resources },
    { text: 'User Activity', subtext: '用户活跃度', score: scores.userActivity },
    { text: 'Alert Level', subtext: '告警级别', score: scores.alertLevel },
  ];

  const numPoints = labels.length;
  const angleStep = (Math.PI * 2) / numPoints;

  // Generate polygon points
  const polygonPoints = labels.map((label, index) => {
    const angle = (index * angleStep) - Math.PI / 2;
    const normalizedScore = label.score / maxScore;
    const pointRadius = normalizedScore * radius;
    return polarToCartesian(centerX, centerY, pointRadius, angle);
  });

  // Generate axis lines and labels
  const axes = labels.map((label, index) => {
    const angle = (index * angleStep) - Math.PI / 2;
    const endPoint = polarToCartesian(centerX, centerY, radius, angle);
    const labelPoint = polarToCartesian(centerX, centerY, radius * 1.15, angle);
    const color = getScoreColor(label.score);
    const statusLabel = getStatusLabel(label.score);

    return {
      endPoint,
      labelPoint,
      color,
      score: label.score,
      status: statusLabel,
      text: label.text,
      subtext: label.subtext,
    };
  });

  // Generate grid levels (20%, 40%, 60%, 80%, 100%)
  const gridLevels = [0.2, 0.4, 0.6, 0.8, 1.0].map(level => {
    const levelRadius = level * radius;
    return {
      radius: levelRadius,
      value: Math.round(level * 100),
    };
  });

  const containerSize = size === 'small' ? 300 : size === 'large' ? 400 : 320;

  return (
    <div className={`system-status-radar size-${size}`}>
      <div className="radar-header">
        <h3>System Health Overview</h3>
        <div
          className="overall-status-badge"
          style={{
            backgroundColor: overallStatus.color,
            color: '#fff'
          }}
        >
          {overallStatus.status}
        </div>
      </div>

      <div className="radar-chart-container">
        <svg
          width={containerSize}
          height={containerSize}
          viewBox={`0 0 ${containerSize} ${containerSize}`}
          className="radar-svg"
        >
          {/* Grid circles */}
          {gridLevels.map((level, index) => (
            <circle
              key={`grid-${index}`}
              cx={centerX}
              cy={centerY}
              r={level.radius}
              fill="none"
              stroke="rgba(255, 255, 255, 0.1)"
              strokeWidth="1"
            />
          ))}

          {/* Axis lines */}
          {axes.map((axis, index) => (
            <g key={`axis-${index}`}>
              {/* Axis line */}
              <line
                x1={centerX}
                y1={centerY}
                x2={axis.endPoint.x}
                y2={axis.endPoint.y}
                stroke="rgba(255, 255, 255, 0.1)"
                strokeWidth="1"
              />

              {/* Label */}
              <text
                x={axis.labelPoint.x}
                y={axis.labelPoint.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={axis.color.label}
                fontSize={size === 'small' ? 10 : 12}
                fontWeight="600"
              >
                <tspan x={axis.labelPoint.x} dy="-0.6em">{axis.text}</tspan>
                <tspan x={axis.labelPoint.x} dy="0.9em" fontSize={size === 'small' ? 9 : 11} fontWeight="400">
                  {axis.subtext}: {axis.score}
                </tspan>
              </text>

              {/* Score dot on axis */}
              <circle
                cx={axis.endPoint.x}
                cy={axis.endPoint.y}
                r="4"
                fill={axis.color.border}
                stroke="#fff"
                strokeWidth="2"
              />
            </g>
          ))}

          {/* Data polygon */}
          <polygon
            points={polygonPoints.map(p => `${p.x},${p.y}`).join(' ')}
            fill="rgba(25, 128, 25, 0.2)"
            stroke="#198038"
            strokeWidth="2"
            strokeOpacity="0.8"
          />

          {/* Data points */}
          {polygonPoints.map((point, index) => {
            const color = getScoreColor(
              labels[index].score
            );
            return (
              <circle
                key={`point-${index}`}
                cx={point.x}
                cy={point.y}
                r="6"
                fill={color.main}
                stroke="#fff"
                strokeWidth="2"
              />
            );
          })}

          {/* Center circle */}
          <circle
            cx={centerX}
            cy={centerY}
            r="3"
            fill="rgba(255, 255, 255, 0.3)"
          />
        </svg>

        {/* Center score display */}
        <div className="radar-center-score">
          {Math.round(Object.values(scores).reduce((sum, val) => sum + val, 0) / Object.values(scores).length)}
        </div>
      </div>

      {/* Legend */}
      <div className="radar-legend">
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#198038' }}></span>
          <span className="legend-label">Excellent (90-100)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#27ae60' }}></span>
          <span className="legend-label">Good (70-89)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#f1c40f' }}></span>
          <span className="legend-label">Fair (50-69)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#e67e22' }}></span>
          <span className="legend-label">Poor (30-49)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color" style={{ backgroundColor: '#e74c3c' }}></span>
          <span className="legend-label">Critical (0-29)</span>
        </div>
      </div>
    </div>
  );
}

export default SystemStatusRadar;
