import React from 'react';

/**
 * SubagentStatus component displays the currently active subagent
 * with its name, description, and optional progress indicator.
 *
 * @param {Object} props
 * @param {string} props.subagent - The name of the currently active subagent
 * @param {string} props.description - Human-readable description of what the subagent is doing
 * @param {string} props.status - Current status text
 * @param {number} props.progress - Optional progress percentage (0-100)
 */
export function SubagentStatus({ subagent, progress, status, description }) {
  if (!subagent) return null;

  return (
    <div className="subagent-status-card">
      <div className="subagent-header">
        <div className="subagent-icon">
          {getSubagentIcon(subagent)}
        </div>
        <div className="subagent-info">
          <div className="subagent-name">{formatSubagentName(subagent)}</div>
          <div className="subagent-description">{description || status}</div>
        </div>
        <div className="subagent-status-indicator">
          <div className="status-dot running" />
        </div>
      </div>

      {progress !== undefined && progress !== null && (
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          />
        </div>
      )}
    </div>
  );
}

/**
 * Get an emoji icon for a subagent name.
 */
function getSubagentIcon(subagent) {
  const icons = {
    'test-query': '🔍',
    'user-admin': '👤',
    'test-reviewer': '📊',
    'analytics': '📈',
    'search': '🌐',
    'main': '🤖',
    'planner': '📋',
    'executor': '⚙️',
    'reviewer': '✅',
  };
  return icons[subagent] || '⚙️';
}

/**
 * Format a subagent name for display.
 * Converts kebab-case to Title Case.
 */
function formatSubagentName(name) {
  return name
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
