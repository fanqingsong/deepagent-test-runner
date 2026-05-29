import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  CloseIcon,
  MaximizeIcon,
  RestoreIcon,
  ToolIcon,
  ChatListIcon,
  CompressIcon,
  WebSearchIcon,
  DeepThinkingIcon
} from './Icons';
import { useChatStream } from '../hooks/useChatStream';
import { sendSimpleChatMessage, compressConversation } from '../api';
import { useChatTranslations } from '../locales/chatTranslations';
import { ConversationList } from './ConversationList';
import { SubagentStatus } from './SubagentStatus';
import './ChatModal.css';

const STORAGE_KEYS = {
  WIDTH: 'chat-modal-width',
  MAXIMIZED: 'chat-modal-maximized',
  SHOW_TOOL_CALLS: 'chat-show-tool-calls',
  ENABLE_SEARCH: 'chat-enable-search',
  DEEP_THINKING: 'chat-deep-thinking'
};

const DEFAULT_WIDTH = 800;
const MIN_WIDTH = 320;
const MAX_WIDTH = 800;

/**
 * Get an emoji icon for a subagent name.
 */
function getSubagentIcon(name) {
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
  return icons[name] || '⚙️';
}

function formatDuration(seconds) {
  if (!seconds) return '';
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  return `${seconds.toFixed(1)}s`;
}

/**
 * Sidebar panel for chat interface with the AI assistant.
 */
export function ChatModal({ isOpen, onClose, threadId = null, language = 'en' }) {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);
  const { t } = useChatTranslations(language);

  const {
    messages,
    isStreaming,
    streamingContent,
    currentSubagent,
    subagentHistory,
    toolCalls,
    error,
    sendMessage,
    stopStreaming,
    setThreadId,
    clearMessages,
  } = useChatStream();

  // Resize state
  const [width, setWidth] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.WIDTH);
    return saved ? Math.min(Math.max(parseInt(saved), MIN_WIDTH), MAX_WIDTH) : DEFAULT_WIDTH;
  });
  const [isMaximized, setIsMaximized] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.MAXIMIZED) === 'true';
  });
  const [isResizing, setIsResizing] = useState(false);
  const resizeHandleRef = useRef(null);
  const containerRef = useRef(null);

  const [showToolCalls, setShowToolCalls] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.SHOW_TOOL_CALLS) !== 'false';
  });

  const [enableSearch, setEnableSearch] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.ENABLE_SEARCH) === 'true';
  });

  const [deepThinking, setDeepThinking] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.DEEP_THINKING) === 'true';
  });

  // Conversation list state
  const [showConversationList, setShowConversationList] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState(null);

  // Local messages for REST API fallback (no thread)
  const [localMessages, setLocalMessages] = useState([]);
  const [isThinkingLocal, setIsThinkingLocal] = useState(false);

  // Which mode: streaming (has threadId) or REST
  const [useStreamMode, setUseStreamMode] = useState(false);

  // Combined messages for display
  const displayMessages = useStreamMode ? messages : localMessages;

  // Persist settings
  useEffect(() => { localStorage.setItem(STORAGE_KEYS.WIDTH, width.toString()); }, [width]);
  useEffect(() => { localStorage.setItem(STORAGE_KEYS.MAXIMIZED, isMaximized.toString()); }, [isMaximized]);
  useEffect(() => { localStorage.setItem(STORAGE_KEYS.SHOW_TOOL_CALLS, showToolCalls.toString()); }, [showToolCalls]);
  useEffect(() => { localStorage.setItem(STORAGE_KEYS.ENABLE_SEARCH, enableSearch.toString()); }, [enableSearch]);
  useEffect(() => { localStorage.setItem(STORAGE_KEYS.DEEP_THINKING, deepThinking.toString()); }, [deepThinking]);

  // Auto-scroll
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  useEffect(() => { scrollToBottom(); }, [displayMessages, streamingContent, currentSubagent, toolCalls]);

  // Resize handlers
  const handleMouseDown = useCallback((e) => {
    if (isMaximized) return;
    setIsResizing(true);
    e.preventDefault();
  }, [isMaximized]);

  const handleMouseMove = useCallback((e) => {
    if (!isResizing) return;
    const newWidth = window.innerWidth - e.clientX;
    setWidth(Math.min(Math.max(newWidth, MIN_WIDTH), MAX_WIDTH));
  }, [isResizing]);

  const handleMouseUp = useCallback(() => { setIsResizing(false); }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isResizing, handleMouseMove, handleMouseUp]);

  const toggleMaximize = useCallback(() => { setIsMaximized(prev => !prev); }, []);
  const toggleToolCalls = useCallback(() => { setShowToolCalls(prev => !prev); }, []);
  const toggleConversationList = useCallback(() => { setShowConversationList(prev => !prev); }, []);

  const handleSelectConversation = useCallback((conversationId) => {
    setActiveConversationId(conversationId);
    setUseStreamMode(true);
    setThreadId(conversationId);
    setLocalMessages([]);
  }, [setThreadId]);

  const handleCompressConversation = async () => {
    if (!activeConversationId) return;
    try {
      await compressConversation(activeConversationId);
    } catch (err) {
      console.error('Error compressing conversation:', err);
    }
  };

  const handleSendMessage = async () => {
    const content = inputValue.trim();
    if (!content || isStreaming || isThinkingLocal) return;

    setInputValue('');

    if (useStreamMode) {
      // Use SSE streaming
      sendMessage(content, { enableSearch, enableDeepThinking: deepThinking });
    } else {
      // Use REST API fallback
      setIsThinkingLocal(true);
      try {
        const response = await sendSimpleChatMessage(content, enableSearch, deepThinking);
        const finalContent = response.response || 'No response from assistant.';
        setLocalMessages(prev => [
          ...prev,
          { role: 'user', content },
          { role: 'assistant', content: finalContent, tool_calls: response.tool_calls },
        ]);
      } catch (err) {
        console.error('Error sending message:', err);
        setLocalMessages(prev => [
          ...prev,
          { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' },
        ]);
      } finally {
        setIsThinkingLocal(false);
      }
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearConversation = () => {
    if (useStreamMode) {
      clearMessages();
    } else {
      setLocalMessages([]);
    }
    setActiveConversationId(null);
    setShowConversationList(true);
  };

  const handleStartNewChat = () => {
    setUseStreamMode(true);
    clearMessages();
    setActiveConversationId(null);
    setShowConversationList(false);
  };

  // Check if there's activity to show during streaming
  const hasStreamActivity = currentSubagent || subagentHistory.length > 0 || toolCalls.length > 0;

  const isInputDisabled = isStreaming || isThinkingLocal;

  if (!isOpen) return null;

  return (
    <div className={`chat-modal-overlay ${isOpen ? 'visible' : 'hidden'}`} onClick={onClose}>
      <div
        ref={containerRef}
        className={`chat-modal-container ${isOpen ? 'visible' : ''} ${isMaximized ? 'maximized' : ''} ${showConversationList ? 'show-sidebar' : ''}`}
        style={{ width: isMaximized ? '100vw' : `${width}px` }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Conversation List Sidebar */}
        <ConversationList
          isOpen={showConversationList}
          onClose={() => setShowConversationList(false)}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
        />

        {/* Main Chat Area */}
        <div className="chat-modal-main">
          {/* Resize Handle */}
          <div
            ref={resizeHandleRef}
            className={`chat-resize-handle ${isResizing ? 'active' : ''}`}
            onMouseDown={handleMouseDown}
            style={{ display: isMaximized ? 'none' : 'block' }}
          />

          {/* Header */}
          <div className="chat-modal-header">
            <div className="chat-modal-title">
              <h3>{t('chatTitle')}</h3>
              {useStreamMode && <span className="connection-indicator connected" />}
            </div>
            <div className="chat-modal-actions">
              <button
                className={`chat-modal-action-btn ${showConversationList ? 'active' : ''}`}
                onClick={toggleConversationList}
                title="Conversations"
              >
                <ChatListIcon size={16} />
              </button>
              <button
                className="chat-modal-action-btn"
                onClick={handleCompressConversation}
                title="Compress Conversation"
              >
                <CompressIcon size={16} />
              </button>
              <button
                className="chat-modal-action-btn"
                onClick={toggleToolCalls}
                title={showToolCalls ? 'Hide Tool Calls' : 'Show Tool Calls'}
                style={{ color: showToolCalls ? '#0f62fe' : '#525252' }}
              >
                <ToolIcon size={16} />
              </button>
              <button
                className="chat-modal-action-btn"
                onClick={toggleMaximize}
                title={isMaximized ? 'Restore' : 'Maximize'}
              >
                {isMaximized ? <RestoreIcon size={16} /> : <MaximizeIcon size={16} />}
              </button>
              <button
                className="chat-modal-action-btn"
                onClick={handleClearConversation}
                title={t('clearButton')}
              >
                {t('clearButton')}
              </button>
              <button className="chat-modal-close-btn" onClick={onClose} aria-label="Close chat">
                <CloseIcon size={20} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="chat-modal-messages">
            {displayMessages.length === 0 && !isStreaming && (
              <div className="chat-welcome-message">
                <p>👋 {t('chatWelcome')}</p>
                <p>{t('chatWelcomeHelp')}</p>
                <ul>
                  <li>{t('chatHelpQuery')}</li>
                  <li>{t('chatHelpUsers')}</li>
                  <li>{t('chatHelpRoles')}</li>
                  <li>{t('chatHelpApprove')}</li>
                </ul>
              </div>
            )}

            {displayMessages.map((message, index) => (
              <div
                key={index}
                className={`chat-message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
              >
                <div className="message-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                </div>

                {message.tool_calls && message.tool_calls.length > 0 && showToolCalls && (
                  <div className="message-tool-calls">
                    {message.tool_calls
                      .filter(tc => tc.args && Object.keys(tc.args).length > 0)
                      .map((toolCall, toolIndex) => (
                        <div key={toolIndex} className="tool-call-card">
                          <div className="tool-call-icon">⚙️</div>
                          <div className="tool-call-details">
                            <div className="tool-call-name">{toolCall.name || 'tool'}</div>
                            <div className="tool-call-args">
                              {JSON.stringify(toolCall.args || {}, null, 2)}
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            ))}

            {/* Streaming execution process */}
            {isStreaming && (
              <div className="chat-message assistant-message streaming">
                {/* Execution timeline */}
                {hasStreamActivity && (
                  <div className="execution-timeline">
                    {/* Completed subagents */}
                    {subagentHistory.map((sa, i) => (
                      <div key={`sa-${i}`} className="execution-step completed">
                        <div className="execution-step-icon">{getSubagentIcon(sa.name)}</div>
                        <div className="execution-step-info">
                          <span className="execution-step-name">{sa.name}</span>
                          <span className="execution-step-duration">{formatDuration(sa.duration)}</span>
                        </div>
                        <div className="execution-step-check">✓</div>
                      </div>
                    ))}

                    {/* Active subagent */}
                    {currentSubagent && (
                      <div className="execution-step active">
                        <div className="execution-step-icon">{getSubagentIcon(currentSubagent.name)}</div>
                        <div className="execution-step-info">
                          <span className="execution-step-name">{currentSubagent.name}</span>
                          <span className="execution-step-status">
                            {currentSubagent.description || currentSubagent.status || 'Processing...'}
                          </span>
                        </div>
                        <div className="execution-step-spinner">
                          <div className="spinner" />
                        </div>
                      </div>
                    )}

                    {/* Recent tool calls during streaming */}
                    {showToolCalls && toolCalls.slice(-5).map((tc, i) => (
                      <div key={`tc-${i}`} className={`execution-tool-call ${tc.type}`}>
                        <span className="execution-tool-icon">{tc.type === 'result' ? '📄' : '🔧'}</span>
                        <span className="execution-tool-name">{tc.tool}</span>
                        <span className="execution-tool-detail">
                          {tc.type === 'result'
                            ? (tc.result ? String(tc.result).substring(0, 80) : '')
                            : (tc.args ? String(tc.args).substring(0, 80) : '')}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Streaming content */}
                <div className="message-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {streamingContent || (currentSubagent ? '' : 'Thinking...')}
                  </ReactMarkdown>
                </div>
              </div>
            )}

            {/* REST API thinking state */}
            {isThinkingLocal && (
              <div className="chat-message assistant-message">
                <div className="message-content thinking">
                  <span className="thinking-dots">
                    <span>.</span><span>.</span><span>.</span>
                  </span>
                </div>
              </div>
            )}

            {/* Error display */}
            {error && (
              <div className="chat-message assistant-message">
                <div className="message-content error">
                  Error: {error}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="chat-modal-input-area">
            <button
              className={`chat-search-toggle-btn ${enableSearch ? 'active' : ''}`}
              onClick={() => setEnableSearch(prev => !prev)}
              title={t('webSearchToggle')}
            >
              <WebSearchIcon size={16} />
              <span className="chat-search-toggle-label">{t('webSearchToggle')}</span>
            </button>
            <button
              className={`chat-search-toggle-btn ${deepThinking ? 'active' : ''}`}
              onClick={() => setDeepThinking(prev => !prev)}
              title={t('deepThinkingToggle')}
            >
              <DeepThinkingIcon size={16} />
              <span className="chat-search-toggle-label">{t('deepThinkingToggle')}</span>
            </button>
            {isStreaming && (
              <button className="chat-stop-btn" onClick={stopStreaming} title="Stop">
                Stop
              </button>
            )}
            <textarea
              className="chat-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={t('inputPlaceholder')}
              rows={1}
              disabled={isInputDisabled}
            />
            <button
              className="chat-send-btn"
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isInputDisabled}
            >
              {t('sendButton')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatModal;
