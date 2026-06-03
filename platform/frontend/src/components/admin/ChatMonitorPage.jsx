import { useState } from 'react';
import {
  useChatMetrics,
  useChatSubagentUsage,
  useChatSessions,
  useSessionMessages,
} from '../../hooks/useChatMonitor';
import './ChatMonitorPage.css';

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

function formatTokens(n) {
  if (!n) return '0';
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

export default function ChatMonitorPage() {
  const [days, setDays] = useState(30);
  const [selectedThreadId, setSelectedThreadId] = useState(null);

  const { data: metrics = {}, isLoading: metricsLoading } = useChatMetrics(days);
  const { data: subagents = [], isLoading: subagentsLoading } = useChatSubagentUsage(days);
  const { data: sessionsData = {}, isLoading: sessionsLoading } = useChatSessions({ limit: 100 });
  const { data: messagesData, isLoading: messagesLoading } = useSessionMessages(selectedThreadId);

  const sessions = sessionsData.items || [];
  const messages = messagesData?.messages || [];
  const maxSubagentCount = Math.max(...subagents.map((s) => s.call_count), 1);

  const selectedSession = sessions.find((s) => s.thread_id === selectedThreadId);

  return (
    <div className="chat-monitor-page">
      {/* Header */}
      <div className="chat-monitor-header">
        <h2>Chat Monitor</h2>
        <div className="chat-monitor-range-btns">
          {[7, 30, 90].map((d) => (
            <button key={d} className={days === d ? 'active' : ''} onClick={() => setDays(d)}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="chat-monitor-stats">
        <div className="cm-stat-card">
          <div className="cm-stat-card-label">Active Sessions</div>
          <div className="cm-stat-card-value blue">{metrics.active_sessions ?? 0}</div>
        </div>
        <div className="cm-stat-card">
          <div className="cm-stat-card-label">Total Sessions</div>
          <div className="cm-stat-card-value">{metrics.total_sessions ?? 0}</div>
        </div>
        <div className="cm-stat-card">
          <div className="cm-stat-card-label">Total Messages</div>
          <div className="cm-stat-card-value">{metrics.total_messages ?? 0}</div>
        </div>
        <div className="cm-stat-card">
          <div className="cm-stat-card-label">Tokens Used</div>
          <div className="cm-stat-card-value">{formatTokens(metrics.total_tokens)}</div>
        </div>
      </div>

      {/* Subagent Breakdown */}
      {subagents.length > 0 && (
        <div className="cm-subagent-section">
          <h3>Subagent Distribution</h3>
          {subagents.map((s) => (
            <div className="cm-subagent-bar-row" key={s.subagent_name}>
              <div className="cm-subagent-name">{s.subagent_name}</div>
              <div className="cm-subagent-track">
                <div
                  className="cm-subagent-fill"
                  style={{ width: `${(s.call_count / maxSubagentCount) * 100}%` }}
                />
              </div>
              <div className="cm-subagent-count">{s.call_count} calls</div>
            </div>
          ))}
        </div>
      )}

      {/* Session List + Detail */}
      <div className="cm-content">
        {/* Left: Session List */}
        <div className="cm-session-list">
          <div className="cm-session-list-header">
            Sessions ({sessions.length})
          </div>
          {sessionsLoading ? (
            <div className="cm-loading">Loading sessions...</div>
          ) : sessions.length === 0 ? (
            <div className="cm-empty-state">No chat sessions found</div>
          ) : (
            sessions.map((s) => (
              <div
                key={s.thread_id}
                className={`cm-session-item ${selectedThreadId === s.thread_id ? 'selected' : ''}`}
                onClick={() => setSelectedThreadId(s.thread_id)}
              >
                <div className="cm-session-item-top">
                  <div className="cm-session-user">
                    <span className={`cm-session-status ${s.status}`} />
                    User #{s.user_id}
                  </div>
                  <div className="cm-session-time">{formatTime(s.last_message_at)}</div>
                </div>
                <div className="cm-session-meta">
                  {(s.subagents_used || []).slice(0, 3).map((name) => (
                    <span className="cm-session-tag" key={name}>{name}</span>
                  ))}
                  {s.message_count > 0 && (
                    <span className="cm-session-tag">{s.message_count} msgs</span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Right: Session Detail */}
        <div className="cm-session-detail">
          {!selectedThreadId ? (
            <div className="cm-empty-state">Select a session to view conversation</div>
          ) : messagesLoading ? (
            <div className="cm-loading">Loading messages...</div>
          ) : (
            <>
              <div className="cm-detail-header">
                <div>
                  <div className="cm-detail-title">
                    {selectedSession?.title || `Session ${selectedThreadId.slice(0, 8)}...`}
                  </div>
                  <div className="cm-detail-info">
                    User #{selectedSession?.user_id} | Started {formatTime(selectedSession?.created_at)}
                  </div>
                </div>
                <div className="cm-detail-metrics">
                  <div>Tokens: <span>{formatTokens(selectedSession?.total_tokens)}</span></div>
                  <div>Messages: <span>{selectedSession?.message_count ?? 0}</span></div>
                </div>
              </div>
              <div className="cm-messages">
                {messages.length === 0 ? (
                  <div className="cm-empty-state">No messages in this conversation</div>
                ) : (
                  messages.map((msg, i) => (
                    <div className="cm-message" key={i}>
                      <div className={`cm-message-role ${msg.role}`}>{msg.role}</div>
                      <div className="cm-message-content">{msg.content}</div>
                      {msg.tool_calls && msg.tool_calls.length > 0 && (
                        <div className="cm-message-tool-calls">
                          {msg.tool_calls.map((tc, j) => (
                            <div key={j}>{tc.name}({JSON.stringify(tc.args).slice(0, 100)})</div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
