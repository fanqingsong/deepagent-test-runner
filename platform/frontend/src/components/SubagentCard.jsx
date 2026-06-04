import { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const SUBAGENT_ICONS = {
  'test-query': '\u{1F50D}',
  'user-admin': '\u{1F464}',
  'test-reviewer': '\u{1F4CA}',
  'analytics': '\u{1F4C8}',
  'knowledge-base': '\u{1F4DA}',
  'search': '\u{1F310}',
  'email': '\u{1F4E7}',
  'data-analysis': '\u{1F4C8}',
  'sandbox-data-analysis': '\u{1F9EA}',
  'sql-query': '\u{1F5C3}️',
  'content-builder': '\u{1F4DD}',
  'deep-research': '\u{1F52C}',
  'planner': '\u{1F4CB}',
  'executor': '\u{2699}️',
  'reviewer': '\u{2705}',
  'main': '\u{1F916}',
};

function StatusBadge({ status }) {
  const labels = { pending: 'Pending', running: 'Running', complete: 'Done', error: 'Error' };
  return (
    <span className={`subagent-card-badge subagent-card-badge--${status}`}>
      {labels[status] || status}
    </span>
  );
}

export function SubagentCard({ subagent, defaultExpanded = true }) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const displayContent = useMemo(() => {
    const msgs = subagent.messages || [];
    for (let i = msgs.length - 1; i >= 0; i--) {
      const msg = msgs[i];
      if (msg.getType?.() === 'ai') {
        return typeof msg.content === 'string' ? msg.content : String(msg.content || '');
      }
    }
    return subagent.result || '';
  }, [subagent.messages, subagent.result]);

  const toolCallCount = (subagent.toolCalls || []).length;
  const icon = SUBAGENT_ICONS[subagent.name] || '\u{2699}️';
  const displayName = subagent.name.replace(/[-_]/g, ' ');

  return (
    <div className={`subagent-card subagent-card--${subagent.status}`}>
      <button className="subagent-card-header" onClick={() => setExpanded(!expanded)}>
        <div className="subagent-card-header-left">
          <span className="subagent-card-icon">{icon}</span>
          <div className="subagent-card-title-group">
            <span className="subagent-card-name">{displayName}</span>
            <span className="subagent-card-meta">
              {toolCallCount} tool call{toolCallCount !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
        <div className="subagent-card-header-right">
          <StatusBadge status={subagent.status} />
          <span className={`subagent-card-chevron ${expanded ? 'expanded' : ''}`}>&#9662;</span>
        </div>
      </button>

      {expanded && displayContent && (
        <div className="subagent-card-content">
          <div className="subagent-card-streaming-text">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{displayContent}</ReactMarkdown>
            {subagent.status === 'running' && <span className="subagent-card-cursor" />}
          </div>
        </div>
      )}

      {expanded && subagent.status === 'error' && (
        <div className="subagent-card-error">
          {String(subagent.error?.message || subagent.error || 'An error occurred')}
        </div>
      )}

      {expanded && toolCallCount > 0 && (
        <div className="subagent-card-tool-calls">
          {subagent.toolCalls.map((tc, i) => (
            <div key={i} className="subagent-card-tool-call">
              <span className="subagent-card-tool-name">
                {tc.call?.name || tc.name || 'tool'}
              </span>
              {tc.result !== undefined && (
                <span className="subagent-card-tool-result">done</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
