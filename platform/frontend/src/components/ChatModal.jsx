import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  CloseIcon,
  MaximizeIcon,
  RestoreIcon,
  ToolIcon,
  ChatListIcon,
  WebSearchIcon,
  DeepThinkingIcon
} from './Icons';
import { useChatStream } from '../hooks/useChatStream';
import { useChatTranslations } from '../locales/chatTranslations';
import { ConversationList } from './ConversationList';
import './ChatModal.css';
import { VoiceButton } from './VoiceButton';
import { AudioPlayer } from './AudioPlayer';
import { SpeakerIcon } from './Icons';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import { useVoicePlayback } from '../hooks/useVoicePlayback';
import { getVoiceConfig, transcribeAudio } from '../services/voiceService';

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
    rawSubagents,
    todos,
  } = useChatStream();

  // Redirect to login on auth failure (401)
  useEffect(() => {
    if (error && /401|Unauthorized|Invalid.*token/i.test(error)) {
      window.location.hash = 'login';
    }
  }, [error]);

  // Resize state
  const [width, setWidth] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.WIDTH);
    return saved ? Math.min(Math.max(parseInt(saved), MIN_WIDTH), MAX_WIDTH) : DEFAULT_WIDTH;
  });
  const [isMaximized, setIsMaximized] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEYS.MAXIMIZED);
    return saved === null ? true : saved === 'true';
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

  // Voice state
  const { isRecording, start: startRecording, stop: stopRecording } = useVoiceRecorder();
  const { play: playAudio, isPlaying: isAudioPlaying } = useVoicePlayback();
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [autoPlay, setAutoPlay] = useState(() => localStorage.getItem('voice-auto-play') !== 'false');
  const [selectedVoice, setSelectedVoice] = useState('alex');
  const [voiceLoading, setVoiceLoading] = useState(false);
  const lastAssistantMsgRef = useRef(null);

  // Check voice config on mount
  useEffect(() => {
    getVoiceConfig().then((config) => {
      setVoiceEnabled(config.voice_enabled);
      if (config.default_voice) setSelectedVoice(config.default_voice);
    }).catch(() => setVoiceEnabled(false));
  }, []);

  useEffect(() => { localStorage.setItem('voice-auto-play', autoPlay.toString()); }, [autoPlay]);

  // Conversation list state
  const [showConversationList, setShowConversationList] = useState(true);
  const [activeConversationId, setActiveConversationId] = useState(null);

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
  useEffect(() => { scrollToBottom(); }, [messages, streamingContent, currentSubagent, toolCalls]);

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
    setThreadId(conversationId);
  }, [setThreadId]);

  const handleSendMessage = async () => {
    const content = inputValue.trim();
    if (!content || isStreaming) return;

    setInputValue('');
    sendMessage(content, { enableSearch, enableDeepThinking: deepThinking });
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearConversation = () => {
    clearMessages();
    setActiveConversationId(null);
    setShowConversationList(true);
  };

  const handleStartNewChat = () => {
    clearMessages();
    setActiveConversationId(null);
    setShowConversationList(false);
  };

  const handleVoiceRecord = async () => {
    if (isRecording) {
      const blob = await stopRecording();
      if (!blob) return;
      setVoiceLoading(true);
      try {
        const { text } = await transcribeAudio(blob);
        if (text?.trim()) {
          setInputValue('');
          sendMessage(text.trim(), { enableSearch, enableDeepThinking: deepThinking });
        }
      } catch (err) {
        console.error('Voice transcription failed:', err);
      } finally {
        setVoiceLoading(false);
      }
    } else {
      await startRecording();
    }
  };

  // Auto-play TTS when AI response completes
  useEffect(() => {
    if (!autoPlay || !voiceEnabled || isStreaming) return;
    const assistantMsgs = messages.filter((m) => m.role === 'assistant');
    const lastMsg = assistantMsgs[assistantMsgs.length - 1];
    if (lastMsg && lastMsg.content) {
      const key = `${assistantMsgs.length - 1}:${lastMsg.content}`;
      if (key !== lastAssistantMsgRef.current) {
        lastAssistantMsgRef.current = key;
        playAudio(lastMsg.content, selectedVoice, `msg-${messages.indexOf(lastMsg)}`);
      }
    }
  }, [messages, isStreaming, autoPlay, voiceEnabled, selectedVoice, playAudio]);

  const hasStreamActivity = currentSubagent || subagentHistory.length > 0 || toolCalls.length > 0;

  if (!isOpen) return null;

  return (
    <div className={`chat-modal-overlay ${isOpen ? 'visible' : 'hidden'}`} onClick={onClose}>
      <div
        ref={containerRef}
        className={`chat-modal-container ${isOpen ? 'visible' : ''} ${isMaximized ? 'maximized' : ''} ${showConversationList ? 'show-sidebar' : ''}`}
        style={{ width: isMaximized ? '100vw' : `${width}px` }}
        onClick={(e) => e.stopPropagation()}
      >
        <ConversationList
          isOpen={showConversationList}
          onClose={() => setShowConversationList(false)}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
        />

        <div className="chat-modal-main">
          <div
            ref={resizeHandleRef}
            className={`chat-resize-handle ${isResizing ? 'active' : ''}`}
            onMouseDown={handleMouseDown}
            style={{ display: isMaximized ? 'none' : 'block' }}
          />

          <div className="chat-modal-header">
            <div className="chat-modal-title">
              <h3>{t('chatTitle')}</h3>
              <span className="connection-indicator connected" />
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

          <div className="chat-modal-messages">
            {messages.length === 0 && !isStreaming && (
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

            {messages.map((message, index) => (
              <div
                key={index}
                className={`chat-message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
              >
                <div className="message-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                </div>

                {voiceEnabled && message.role === 'assistant' && message.content && (
                  <AudioPlayer
                    messageId={`msg-${index}`}
                    text={message.content}
                    voice={selectedVoice}
                    isPlaying={isAudioPlaying(`msg-${index}`)}
                    onPlay={playAudio}
                  />
                )}

                {message.toolCalls?.length > 0 && showToolCalls && (
                  <div className="message-tool-calls">
                    {message.toolCalls
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

            {isStreaming && (
              <div className="chat-message assistant-message streaming">
                {todos && todos.length > 0 && (
                  <div className="execution-todos">
                    {todos.map((todo, i) => (
                      <div key={`todo-${i}`} className={`execution-todo-item ${todo.completed ? 'completed' : ''}`}>
                        <span className="execution-todo-check">{todo.completed ? '✓' : '○'}</span>
                        <span className="execution-todo-text">{todo.content || todo.title || String(todo)}</span>
                      </div>
                    ))}
                  </div>
                )}
                {hasStreamActivity && (
                  <div className="execution-timeline">
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

                <div className="message-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {streamingContent || (currentSubagent ? '' : 'Thinking...')}
                  </ReactMarkdown>
                </div>
              </div>
            )}

            {error && (
              <div className="chat-message assistant-message">
                <div className="message-content error">
                  Error: {error}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

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
            {voiceEnabled && (
              <VoiceButton
                isRecording={isRecording}
                onStart={startRecording}
                onStop={handleVoiceRecord}
                disabled={isStreaming || voiceLoading}
              />
            )}
            {voiceEnabled && (
              <button
                className={`chat-voice-toggle ${autoPlay ? 'active' : ''}`}
                onClick={() => setAutoPlay(prev => !prev)}
                title={autoPlay ? 'Disable auto-play' : 'Enable auto-play'}
              >
                <SpeakerIcon size={16} />
                <span className="chat-voice-toggle-label">Auto</span>
              </button>
            )}
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
              disabled={isStreaming}
            />
            <button
              className="chat-send-btn"
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isStreaming}
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
