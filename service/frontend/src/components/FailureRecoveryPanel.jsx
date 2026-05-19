import { useState, useEffect, useRef, useCallback } from 'react';
import Modal from './Modal';
import authService from '../services/authService';
import './FailureRecoveryPanel.css';

/**
 * FailureRecoveryPanel - Modal that opens when a test run fails.
 * Shows failure details and a conversation interface for recovery actions.
 *
 * Props:
 *   isOpen            - boolean controlling modal visibility
 *   onClose           - callback to close the modal
 *   runId             - the test run ID that failed
 *   testDefinitionId  - the test definition ID for retry
 *   onRetry           - callback after a retry is kicked off
 */
function FailureRecoveryPanel({ isOpen, onClose, runId, testDefinitionId, onRetry }) {
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [failedSteps, setFailedSteps] = useState([]);
  const [stepsExpanded, setStepsExpanded] = useState(true);
  const [expandedScreenshot, setExpandedScreenshot] = useState(null);
  const [sendingMessage, setSendingMessage] = useState(false);
  const messagesEndRef = useRef(null);

  const getAuthHeaders = useCallback(() => {
    const token = authService.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  const API_BASE = `${window.location.origin}/api/v1`;

  // Fetch failure conversation when the modal opens
  useEffect(() => {
    if (!isOpen || !runId) return;

    let cancelled = false;

    const fetchFailureConversation = async () => {
      setIsLoading(true);
      setMessages([]);
      setFailedSteps([]);
      setConversation(null);

      try {
        const response = await fetch(`${API_BASE}/conversations/failure/${runId}`, {
          headers: {
            Accept: 'application/json',
            ...getAuthHeaders(),
          },
        });

        if (!response.ok) {
          console.warn('Failure conversation not found, showing generic failure state');
          setConversation({ id: null, summary: 'Test execution failed', error: 'No detailed conversation available.' });
          setIsLoading(false);
          return;
        }

        const data = await response.json();

        if (cancelled) return;

        setConversation(data);

        // Extract messages from the conversation thread
        const threadMessages = data.messages || data.thread?.messages || [];
        setMessages(threadMessages);

        // Extract failed steps from conversation metadata or test cases
        const steps = data.failed_steps || data.metadata?.failed_steps || [];
        setFailedSteps(steps);
      } catch (err) {
        if (!cancelled) {
          console.error('Error fetching failure conversation:', err);
          setConversation({
            id: null,
            summary: 'Test execution failed',
            error: 'Failed to load failure details.',
          });
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchFailureConversation();
    return () => { cancelled = true; };
  }, [isOpen, runId, API_BASE, getAuthHeaders]);

  // Auto-scroll to the bottom of messages when they change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = useCallback(async (text) => {
    if (!text.trim() || sendingMessage || !runId) return;

    const userMessage = {
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setSendingMessage(true);

    try {
      const response = await fetch(`${API_BASE}/conversations/failure/${runId}/respond`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ message: text.trim() }),
      });

      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.status}`);
      }

      const data = await response.json();

      // Append the assistant's reply
      if (data.message || data.reply) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.message || data.reply || 'Message received.',
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    } catch (err) {
      console.error('Error sending recovery message:', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, there was an error processing your message. Please try again.',
          timestamp: new Date().toISOString(),
          isError: true,
        },
      ]);
    } finally {
      setSendingMessage(false);
    }
  }, [runId, sendingMessage, API_BASE, getAuthHeaders]);

  const handleRegenerateStep = useCallback(() => {
    handleSendMessage('[recovery_action: regenerate_step]');
  }, [handleSendMessage]);

  const handleRetry = useCallback(async () => {
    if (!testDefinitionId) return;

    try {
      const numericId = parseInt(testDefinitionId, 10);
      if (isNaN(numericId)) {
        console.error('Invalid test definition ID for retry:', testDefinitionId);
        return;
      }

      const response = await fetch(`${API_BASE}/jobs/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ test_definition_ids: [numericId] }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Retry failed:', errorText);
        return;
      }

      const job = await response.json();

      if (onRetry) {
        onRetry(job);
      }
    } catch (err) {
      console.error('Error retrying test:', err);
    }
  }, [testDefinitionId, API_BASE, getAuthHeaders, onRetry]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(inputText);
    }
  }, [inputText, handleSendMessage]);

  const formatTimestamp = (ts) => {
    if (!ts) return '';
    try {
      const date = ts instanceof Date ? ts : new Date(ts);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Test Execution Failed - Recovery"
    >
      <div className="failure-recovery-panel">
        {/* Failure Summary Card */}
        <div className="failure-summary-card">
          <div className="failure-summary-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="var(--cds-support-error)">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
            </svg>
          </div>
          <div className="failure-summary-content">
            <div className="failure-summary-title">
              {conversation?.summary || 'Test execution failed'}
            </div>
            {conversation?.error && (
              <div className="failure-summary-error">{conversation.error}</div>
            )}
            {runId && (
              <div className="failure-summary-run-id">Run ID: {runId}</div>
            )}
          </div>
        </div>

        {/* Failed Steps Section (collapsible) */}
        {failedSteps.length > 0 && (
          <div className="failure-steps-section">
            <button
              className="failure-steps-toggle"
              onClick={() => setStepsExpanded(!stepsExpanded)}
              type="button"
            >
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="currentColor"
                style={{
                  transform: stepsExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                  transition: 'transform var(--cds-transition-normal)',
                }}
              >
                <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z"/>
              </svg>
              <span>Failed Steps ({failedSteps.length})</span>
            </button>

            {stepsExpanded && (
              <div className="failure-steps-list">
                {failedSteps.map((step, index) => (
                  <div key={step.step_number || index} className="failure-step-card">
                    <div className="failure-step-header">
                      <span className="failure-step-number">
                        Step {step.step_number || index + 1}
                      </span>
                    </div>
                    <div className="failure-step-description">
                      {step.description || 'No description available'}
                    </div>
                    {step.error && (
                      <div className="failure-step-error">{step.error}</div>
                    )}
                    {step.screenshot_path && (
                      <div className="failure-step-screenshot">
                        <img
                          src={`${window.location.origin}${step.screenshot_path}`}
                          alt={`Step ${step.step_number || index + 1} screenshot`}
                          className="failure-step-screenshot-thumb"
                          onClick={() => setExpandedScreenshot(
                            `${window.location.origin}${step.screenshot_path}`
                          )}
                          onError={(e) => { e.target.style.display = 'none'; }}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Screenshot Lightbox */}
        {expandedScreenshot && (
          <div
            className="failure-screenshot-lightbox"
            onClick={() => setExpandedScreenshot(null)}
          >
            <div
              className="failure-screenshot-lightbox-content"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                className="failure-screenshot-lightbox-close"
                onClick={() => setExpandedScreenshot(null)}
                type="button"
                aria-label="Close screenshot"
              >
                &times;
              </button>
              <img
                src={expandedScreenshot}
                alt="Full size screenshot"
                className="failure-screenshot-lightbox-img"
              />
            </div>
          </div>
        )}

        {/* Chat Section */}
        <div className="failure-chat-section">
          <div className="failure-chat-messages">
            {isLoading ? (
              <div className="failure-chat-loading">Loading failure details...</div>
            ) : messages.length === 0 ? (
              <div className="failure-chat-empty">
                No conversation messages yet. Use the input below to start a recovery conversation.
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`failure-chat-message failure-chat-message-${msg.role}`}
                >
                  <div className="failure-chat-message-content">
                    {msg.content}
                  </div>
                  <div className="failure-chat-message-time">
                    {formatTimestamp(msg.timestamp)}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Row */}
          <div className="failure-chat-input-row">
            <input
              type="text"
              className="failure-chat-input"
              placeholder="Type a recovery message..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sendingMessage}
            />
            <button
              className="failure-chat-send-btn"
              onClick={() => handleSendMessage(inputText)}
              disabled={!inputText.trim() || sendingMessage}
              type="button"
              aria-label="Send message"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </div>

        {/* Action Buttons Row */}
        <div className="failure-actions-row">
          <button
            className="failure-action-btn failure-action-regenerate"
            onClick={handleRegenerateStep}
            disabled={sendingMessage}
            type="button"
          >
            Regenerate Failed Step
          </button>
          <button
            className="failure-action-btn failure-action-edit"
            onClick={onClose}
            type="button"
          >
            Edit Test
          </button>
          <button
            className="failure-action-btn failure-action-retry"
            onClick={handleRetry}
            disabled={sendingMessage}
            type="button"
          >
            Retry
          </button>
        </div>
      </div>
    </Modal>
  );
}

export default FailureRecoveryPanel;
