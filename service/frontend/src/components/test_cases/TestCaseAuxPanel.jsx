import { useState, useEffect, useRef, useCallback } from 'react';
import { getConversation, sendMessage, createConversation } from '../../api';
import './TestCaseAuxPanel.css';

const QUICK_ACTIONS = [
  { label: 'Optimize Test Steps', prompt: 'Please help me optimize the current test case steps to make them clearer and more comprehensive' },
  { label: 'Explain Failure', prompt: 'Please analyze the recent test run results and explain the cause of the failed steps' },
  { label: 'Generate New Scenarios', prompt: 'Please suggest some additional test scenarios based on the current test case' },
];

export default function TestCaseAuxPanel({ testCaseId, onClose }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const messagesEndRef = useRef(null);

  const loadConversation = useCallback(async () => {
    if (!testCaseId) return;
    try {
      // Try to get existing conversation for this studio/app
      const conv = await createConversation(testCaseId, 'assistant', {});
      if (conv?.id) {
        setThreadId(conv.id);
        const detail = await getConversation(conv.id);
        const existing = (detail?.messages || []).map(m => ({
          role: m.role,
          content: m.content,
          timestamp: m.created_at,
        }));
        setMessages(existing);
      }
    } catch {
      // No existing conversation, start fresh
      setMessages([]);
    }
  }, [testCaseId]);

  useEffect(() => { loadConversation(); }, [loadConversation]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text) => {
    const content = text || input.trim();
    if (!content || loading) return;

    const userMsg = { role: 'user', content, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      let tid = threadId;
      if (!tid) {
        const conv = await createConversation(testCaseId, 'assistant', {});
        tid = conv.id;
        setThreadId(tid);
      }
      const result = await sendMessage(tid, content);
      const aiMsg = {
        role: 'assistant',
        content: result?.content || result?.message || 'No response',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${e.message}`,
        timestamp: new Date().toISOString(),
        isError: true,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="studio-aux-panel">
      <div className="studio-aux-header">
        <span className="studio-aux-title">AI Assistant</span>
        <button className="studio-aux-close" onClick={onClose}>x</button>
      </div>

      <div className="studio-aux-messages">
        {messages.length === 0 && (
          <div className="studio-aux-welcome">
            <p>AI Assistant can help you optimize test steps, analyze failure causes, and suggest new test scenarios.</p>
            <div className="studio-aux-quick-actions">
              {QUICK_ACTIONS.map(action => (
                <button
                  key={action.label}
                  className="studio-aux-quick-btn"
                  onClick={() => handleSend(action.prompt)}
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`studio-aux-message studio-aux-message--${msg.role}`}>
            <div className={`studio-aux-bubble ${msg.isError ? 'studio-aux-bubble--error' : ''}`}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="studio-aux-message studio-aux-message--assistant">
            <div className="studio-aux-bubble studio-aux-bubble--typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="studio-aux-input-area">
        <textarea
          className="studio-aux-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          rows={2}
          disabled={loading}
        />
        <button
          className="studio-aux-send-btn"
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
        >
          Send
        </button>
      </div>
    </div>
  );
}
