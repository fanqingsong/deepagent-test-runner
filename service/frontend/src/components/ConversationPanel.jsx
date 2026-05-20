import { useState, useEffect, useRef, useCallback } from 'react';
import Modal from './Modal';
import authService from '../services/authService';

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ||
  window.location.origin;
const CONVERSATION_API = `${BASE_URL}/api/v1/conversations`;

function ConversationPanel({
  isOpen,
  onClose,
  testDefinitionId,
  testGoal,
  url,
  onApproved,
}) {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [threadId, setThreadId] = useState(null);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const getAuthHeaders = useCallback(() => {
    const token = authService.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when loading finishes
  useEffect(() => {
    if (!isLoading && isOpen) {
      inputRef.current?.focus();
    }
  }, [isLoading, isOpen]);

  // Initialize conversation on mount
  useEffect(() => {
    if (!isOpen || !testDefinitionId || !testGoal) return;

    let cancelled = false;

    async function initConversation() {
      setIsLoading(true);
      setError(null);

      try {
        // Step 1: Create a conversation thread
        const createRes = await fetch(CONVERSATION_API + '/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
          },
          body: JSON.stringify({
            test_definition_id: testDefinitionId,
            thread_type: 'planning',
          }),
        });

        if (!createRes.ok) {
          const errText = await createRes.text();
          throw new Error(
            `Failed to create conversation: ${createRes.statusText} - ${errText}`
          );
        }

        const thread = await createRes.json();
        if (cancelled) return;

        const tid = thread.id || thread.thread_id || thread.threadId;
        setThreadId(tid);

        // Step 2: Send the initial goal to generate a plan
        const msgRes = await fetch(`${CONVERSATION_API}/${tid}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
          },
          body: JSON.stringify({ content: testGoal }),
        });

        if (!msgRes.ok) {
          const errText = await msgRes.text();
          throw new Error(
            `Failed to generate plan: ${msgRes.statusText} - ${errText}`
          );
        }

        const msgData = await msgRes.json();
        if (cancelled) return;

        // Backend returns SendMessageResponse: { assistant_message, updated_plan }
        const assistantContent =
          msgData.assistant_message?.content || '';

        setMessages([
          {
            role: 'assistant',
            content: assistantContent,
            metadata: msgData.assistant_message?.metadata || null,
          },
        ]);

        if (msgData.updated_plan) {
          setCurrentPlan(msgData.updated_plan);
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Conversation init error:', err);
          setError(err.message);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    initConversation();

    return () => {
      cancelled = true;
    };
  }, [isOpen, testDefinitionId, testGoal, getAuthHeaders]);

  const sendMessage = useCallback(
    async (content) => {
      if (!content.trim() || !threadId || isLoading) return;

      const userMessage = { role: 'user', content: content.trim() };
      setMessages((prev) => [...prev, userMessage]);
      setInputText('');
      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch(
          `${CONVERSATION_API}/${threadId}/messages`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...getAuthHeaders(),
            },
            body: JSON.stringify({ content: content.trim() }),
          }
        );

        if (!res.ok) {
          const errText = await res.text();
          throw new Error(`Failed to send message: ${res.statusText} - ${errText}`);
        }

        const data = await res.json();

        const assistantContent =
          data.assistant_message?.content || '';

        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: assistantContent,
            metadata: data.assistant_message?.metadata || null,
          },
        ]);

        if (data.updated_plan) {
          setCurrentPlan(data.updated_plan);
        }
      } catch (err) {
        console.error('Send message error:', err);
        setError(err.message);
        // Remove the user message on failure so they can retry
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setIsLoading(false);
      }
    },
    [threadId, isLoading, getAuthHeaders]
  );

  const handleApprove = useCallback(async () => {
    if (!threadId) return;

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${CONVERSATION_API}/${threadId}/approve`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
          },
        }
      );

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(
          `Failed to approve plan: ${res.statusText} - ${errText}`
        );
      }

      if (onApproved) {
        onApproved(currentPlan);
      }
    } catch (err) {
      console.error('Approve error:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [threadId, currentPlan, onApproved, getAuthHeaders]);

  const handleRegenerate = useCallback(async () => {
    if (!threadId) return;

    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `${CONVERSATION_API}/${threadId}/regenerate`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeaders(),
          },
          body: JSON.stringify({
            feedback:
              inputText.trim() || 'Please regenerate the test plan.',
          }),
        }
      );

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(
          `Failed to regenerate: ${res.statusText} - ${errText}`
        );
      }

      const data = await res.json();

      const assistantContent =
        data.assistant_message?.content || '';

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: assistantContent,
          metadata: data.assistant_message?.metadata || null,
        },
      ]);

      if (data.updated_plan) {
        setCurrentPlan(data.updated_plan);
      }

      setInputText('');
    } catch (err) {
      console.error('Regenerate error:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [threadId, inputText, getAuthHeaders]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputText);
    }
  };

  const handleSend = () => {
    sendMessage(inputText);
  };

  // Render plan steps inside an assistant message bubble
  const renderMessageContent = (msg) => {
    if (msg.role === 'assistant' && msg.metadata?.steps) {
      return (
        <div>
          <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
          <div
            style={{
              marginTop: 'var(--cds-spacing-sm)',
              borderTop: '1px solid var(--cds-border-subtle, #e0e0e0)',
              paddingTop: 'var(--cds-spacing-sm)',
            }}
          >
            <div
              style={{
                fontSize: 'var(--cds-caption-01)',
                fontWeight: 'var(--cds-font-weight-semibold, 600)',
                marginBottom: 'var(--cds-spacing-xs)',
                color: 'var(--cds-text-secondary)',
              }}
            >
              Plan Steps:
            </div>
            {msg.metadata.steps.map((step, idx) => (
              <div
                key={idx}
                style={{
                  fontSize: 'var(--cds-caption-01)',
                  lineHeight: '1.5',
                  marginBottom: 'var(--cds-spacing-xs)',
                  paddingLeft: 'var(--cds-spacing-sm)',
                  borderLeft: '2px solid var(--cds-interactive-01, #0f62fe)',
                }}
              >
                <strong>Step {step.step_number || idx + 1}:</strong>{' '}
                {step.description}
                {step.verification && (
                  <span
                    style={{
                      display: 'block',
                      color: 'var(--cds-text-secondary)',
                      fontSize: 'var(--cds-caption-01)',
                    }}
                  >
                    Verify: {step.verification}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      );
    }

    return <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>;
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="AI Test Plan Assistant">
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          height: 'calc(80vh - 120px)',
          minHeight: '500px',
          maxHeight: '700px',
        }}
      >
        {/* Info banner */}
        <div
          style={{
            padding: 'var(--cds-spacing-sm) var(--cds-spacing-md)',
            background: 'var(--cds-background-layer-01, #f4f4f4)',
            fontSize: 'var(--cds-caption-01)',
            color: 'var(--cds-text-secondary)',
            borderBottom: '1px solid var(--cds-border-subtle, #e0e0e0)',
            flexShrink: 0,
          }}
        >
          Describe your test goal in the chat below. The AI will generate and
          refine a test plan through conversation.
        </div>

        {/* Messages area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: 'var(--cds-spacing-md)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--cds-spacing-sm)',
          }}
        >
          {messages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                justifyContent:
                  msg.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <div
                style={{
                  maxWidth: msg.role === 'user' ? '70%' : '85%',
                  padding: '12px 16px',
                  marginBottom: 'var(--cds-spacing-xs)',
                  background:
                    msg.role === 'user'
                      ? 'var(--cds-interactive-01, #0f62fe)'
                      : '#ffffff',
                  color:
                    msg.role === 'user'
                      ? '#ffffff'
                      : 'var(--cds-text-primary, #161616)',
                  border:
                    msg.role === 'assistant'
                      ? '1px solid var(--cds-border-subtle, #e0e0e0)'
                      : 'none',
                  fontSize: 'var(--cds-body-short-01)',
                  lineHeight: '1.5',
                  fontFamily: 'var(--cds-font-family)',
                  wordBreak: 'break-word',
                }}
              >
                {renderMessageContent(msg)}
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-start',
              }}
            >
              <div
                style={{
                  maxWidth: '85%',
                  padding: '12px 16px',
                  background: '#ffffff',
                  color: 'var(--cds-text-secondary)',
                  border: '1px solid var(--cds-border-subtle, #e0e0e0)',
                  fontSize: 'var(--cds-body-short-01)',
                  fontFamily: 'var(--cds-font-family)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--cds-spacing-sm)',
                }}
              >
                <span
                  style={{
                    display: 'inline-block',
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: 'var(--cds-interactive-01, #0f62fe)',
                    animation: 'pulse 1.4s ease-in-out infinite',
                  }}
                />
                <span
                  style={{
                    display: 'inline-block',
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: 'var(--cds-interactive-01, #0f62fe)',
                    animation: 'pulse 1.4s ease-in-out 0.2s infinite',
                  }}
                />
                <span
                  style={{
                    display: 'inline-block',
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: 'var(--cds-interactive-01, #0f62fe)',
                    animation: 'pulse 1.4s ease-in-out 0.4s infinite',
                  }}
                />
                <span style={{ marginLeft: 'var(--cds-spacing-xs)' }}>
                  AI is thinking...
                </span>
                <style>{`
                  @keyframes pulse {
                    0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
                    40% { opacity: 1; transform: scale(1); }
                  }
                `}</style>
              </div>
            </div>
          )}

          {/* Error display */}
          {error && (
            <div
              style={{
                padding: 'var(--cds-spacing-sm) var(--cds-spacing-md)',
                background: '#fff4e5',
                color: 'var(--cds-text-primary, #161616)',
                border: '1px solid var(--cds-support-warning, #f1c21b)',
                fontSize: 'var(--cds-caption-01)',
                fontFamily: 'var(--cds-font-family)',
              }}
            >
              {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            borderTop: '1px solid var(--cds-border-subtle, #e0e0e0)',
            padding: 'var(--cds-spacing-sm)',
            background: 'var(--cds-background, #ffffff)',
            flexShrink: 0,
          }}
        >
          <input
            ref={inputRef}
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isLoading
                ? 'Waiting for response...'
                : 'Type feedback or ask for changes...'
            }
            disabled={isLoading || !threadId}
            style={{
              flex: 1,
              height: '48px',
              padding: '0 16px',
              border: 'none',
              borderBottom: '2px solid transparent',
              background: 'var(--cds-input-background, #f4f4f4)',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)',
              color: 'var(--cds-text-primary, #161616)',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={isLoading || !inputText.trim() || !threadId}
            style={{
              marginLeft: 'var(--cds-spacing-sm)',
              height: '48px',
              padding: '0 var(--cds-spacing-md)',
              background:
                isLoading || !inputText.trim() || !threadId
                  ? 'var(--cds-interactive-02, #393939)'
                  : 'var(--cds-interactive-01, #0f62fe)',
              color: '#ffffff',
              border: 'none',
              cursor:
                isLoading || !inputText.trim() || !threadId
                  ? 'not-allowed'
                  : 'pointer',
              fontWeight: 'var(--cds-font-weight-regular, 400)',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)',
              transition: 'background-color var(--cds-transition-fast, 0.1s)',
              opacity: isLoading || !inputText.trim() || !threadId ? 0.6 : 1,
              flexShrink: 0,
            }}
          >
            Send
          </button>
        </div>

        {/* Action buttons */}
        <div
          style={{
            display: 'flex',
            gap: 'var(--cds-spacing-sm)',
            padding: 'var(--cds-spacing-md)',
            borderTop: '1px solid var(--cds-border-subtle, #e0e0e0)',
            background: 'var(--cds-background, #ffffff)',
            flexShrink: 0,
          }}
        >
          <button
            type="button"
            onClick={handleApprove}
            disabled={isLoading || !currentPlan || !threadId}
            style={{
              flex: 1,
              height: 'var(--cds-button-height, 48px)',
              background:
                isLoading || !currentPlan || !threadId
                  ? 'var(--cds-interactive-02, #393939)'
                  : 'var(--cds-interactive-01, #0f62fe)',
              color: '#ffffff',
              border: 'none',
              cursor:
                isLoading || !currentPlan || !threadId
                  ? 'not-allowed'
                  : 'pointer',
              fontWeight: 'var(--cds-font-weight-regular, 400)',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)',
              transition: 'background-color var(--cds-transition-fast, 0.1s)',
              opacity:
                isLoading || !currentPlan || !threadId ? 0.6 : 1,
            }}
          >
            Approve Plan
          </button>
          <button
            type="button"
            onClick={handleRegenerate}
            disabled={isLoading || !threadId}
            style={{
              flex: 1,
              height: 'var(--cds-button-height, 48px)',
              background: 'var(--cds-button-secondary, #393939)',
              color: '#ffffff',
              border: 'none',
              cursor: isLoading || !threadId ? 'not-allowed' : 'pointer',
              fontWeight: 'var(--cds-font-weight-regular, 400)',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)',
              transition: 'background-color var(--cds-transition-fast, 0.1s)',
              opacity: isLoading || !threadId ? 0.6 : 1,
            }}
          >
            Regenerate
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            style={{
              flex: 1,
              height: 'var(--cds-button-height, 48px)',
              background: 'transparent',
              color: 'var(--cds-text-primary, #161616)',
              border: '1px solid var(--cds-border-subtle, #e0e0e0)',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              fontWeight: 'var(--cds-font-weight-regular, 400)',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)',
              transition:
                'background-color var(--cds-transition-fast, 0.1s)',
              opacity: isLoading ? 0.6 : 1,
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </Modal>
  );
}

export default ConversationPanel;
