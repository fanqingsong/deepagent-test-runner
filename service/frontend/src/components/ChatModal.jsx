import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  CloseIcon,
  MaximizeIcon,
  RestoreIcon,
  ToolIcon,
  ChatListIcon,
  CompressIcon
} from './Icons';
import { useChatMessages } from '../hooks/useChatWebSocket';
import { sendSimpleChatMessage, compressConversation } from '../api';
import { useChatTranslations } from '../locales/chatTranslations';
import { ConversationList } from './ConversationList';
import './ChatModal.css';

const STORAGE_KEYS = {
  WIDTH: 'chat-modal-width',
  MAXIMIZED: 'chat-modal-maximized',
  SHOW_TOOL_CALLS: 'chat-show-tool-calls'
};

const DEFAULT_WIDTH = 800;
const MIN_WIDTH = 320;
const MAX_WIDTH = 800;

/**
 * Sidebar panel for chat interface with the AI assistant.
 * Slides in from the right side of the screen.
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether the sidebar is open
 * @param {Function} props.onClose - Callback when sidebar is closed
 * @param {string|null} props.threadId - Conversation thread ID
 * @param {string} props.language - Language code ('en' or 'zh')
 */
export function ChatModal({ isOpen, onClose, threadId = null, language = 'en' }) {
  const [inputValue, setInputValue] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef(null);
  const [localThreadId, setLocalThreadId] = useState(threadId);
  const { t } = useChatTranslations(language);

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

  // Tool call visibility state
  const [showToolCalls, setShowToolCalls] = useState(() => {
    return localStorage.getItem(STORAGE_KEYS.SHOW_TOOL_CALLS) !== 'false';
  });

  // Conversation list state
  const [showConversationList, setShowConversationList] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);

  // Local state for messages when using REST API
  const [localMessages, setLocalMessages] = useState([]);

  // Use WebSocket if threadId is provided, otherwise use local state
  const { messages: wsMessages, isConnected, isStreaming, sendUserMessage, clearMessages } = useChatMessages(
    localThreadId || ''
  );

  // Use WebSocket messages if threadId exists, otherwise use local messages
  const messages = localThreadId ? wsMessages : localMessages;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Persist width and maximized state
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.WIDTH, width.toString());
  }, [width]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.MAXIMIZED, isMaximized.toString());
  }, [isMaximized]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.SHOW_TOOL_CALLS, showToolCalls.toString());
  }, [showToolCalls]);

  // Resize handlers
  const handleMouseDown = useCallback((e) => {
    if (isMaximized) return;
    setIsResizing(true);
    e.preventDefault();
  }, [isMaximized]);

  const handleMouseMove = useCallback((e) => {
    if (!isResizing) return;

    const newWidth = window.innerWidth - e.clientX;
    const clampedWidth = Math.min(Math.max(newWidth, MIN_WIDTH), MAX_WIDTH);
    setWidth(clampedWidth);
  }, [isResizing]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

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

  // Toggle maximize
  const toggleMaximize = useCallback(() => {
    setIsMaximized(prev => !prev);
  }, []);

  // Toggle tool calls visibility
  const toggleToolCalls = useCallback(() => {
    setShowToolCalls(prev => !prev);
  }, []);

  // Conversation list handlers
  const toggleConversationList = useCallback(() => {
    setShowConversationList(prev => !prev);
  }, []);

  const handleSelectConversation = useCallback((conversationId) => {
    setActiveConversationId(conversationId);
    setLocalThreadId(conversationId);
    // Reset messages when switching conversations
    setLocalMessages([]);
  }, []);

  const handleCompressConversation = async () => {
    if (!activeConversationId) {
      alert('Please select a conversation first');
      return;
    }

    try {
      const result = await compressConversation(activeConversationId);
      // Reload messages after compression
      setLocalMessages([]);
      // Show success message
      alert(result.response);
    } catch (error) {
      console.error('Error compressing conversation:', error);
      alert('Failed to compress conversation');
    }
  };

  const handleSendMessage = async () => {
    const content = inputValue.trim();
    if (!content || isThinking) return;

    setInputValue('');
    setIsThinking(true);

    try {
      if (localThreadId) {
        // Use WebSocket
        const success = sendUserMessage(content);
        if (!success) {
          throw new Error('Failed to send message via WebSocket');
        }
      } else {
        // Use REST API for stateless chat
        const response = await sendSimpleChatMessage(content);

        // The response already includes formatted tool results
        // No need to extract and combine them separately
        const finalContent = response.response || 'No response from assistant.';

        // Add user message
        setLocalMessages((prev) => [...prev, { role: 'user', content }]);
        // Add assistant response (tool_calls are only for UI display of what tools were used)
        setLocalMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: finalContent,
            tool_calls: response.tool_calls,
          },
        ]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setLocalMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
        },
      ]);
    } finally {
      setIsThinking(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearConversation = () => {
    clearMessages();
    setLocalMessages([]);
    setLocalThreadId(null);
  };

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
              {localThreadId && isConnected && <span className="connection-indicator connected" />}
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
            {messages.length === 0 && (
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

            {(isThinking || isStreaming) && (
              <div className="chat-message assistant-message">
                <div className="message-content thinking">
                  <span className="thinking-dots">
                    <span>.</span>
                    <span>.</span>
                    <span>.</span>
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="chat-modal-input-area">
            <textarea
              className="chat-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={t('inputPlaceholder')}
              rows={1}
              disabled={isThinking}
            />
            <button
              className="chat-send-btn"
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isThinking}
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
