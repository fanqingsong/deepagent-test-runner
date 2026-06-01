import { useState, useEffect, useMemo, useCallback } from 'react';
import { Client } from '@langchain/langgraph-sdk';
import { CloseIcon, AddIcon, TrashIcon } from './Icons';
import authService from '../services/authService';
import './ConversationList.css';

const LANGGRAPH_URL = import.meta.env.VITE_LANGGRAPH_URL || `${window.location.origin}/langgraph`;

/**
 * Sidebar panel for managing chat conversations via LangGraph threads.
 */
export function ConversationList({
  isOpen,
  onClose,
  activeConversationId,
  onSelectConversation,
  refreshKey = 0,
}) {
  const [conversations, setConversations] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const client = useMemo(() => new Client({
    apiUrl: LANGGRAPH_URL,
    defaultHeaders: authService.getAuthHeaders(),
  }), [refreshKey]);

  const loadConversations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const threads = await client.threads.search({ limit: 50 });
      setConversations(threads || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [client]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleCreateConversation = async () => {
    try {
      const thread = await client.threads.create({
        metadata: { title: 'New Chat' },
      });
      setConversations(prev => [thread, ...prev]);
      onSelectConversation(thread.thread_id);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteConversation = async (threadId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;

    try {
      await client.threads.delete(threadId);
      setConversations(prev => prev.filter(c => c.thread_id !== threadId));
      if (activeConversationId === threadId) {
        onSelectConversation(null);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  if (!isOpen) return null;

  return (
    <div className={`conversation-list-sidebar ${isOpen ? 'visible' : ''}`}>
      <div className="conversation-list-header">
        <h3>Conversations</h3>
        <button
          className="conversation-list-close-btn"
          onClick={onClose}
          aria-label="Close conversation list"
        >
          <CloseIcon size={20} />
        </button>
      </div>

      <div className="conversation-list-actions">
        <button
          className="conversation-new-btn"
          onClick={handleCreateConversation}
        >
          <AddIcon size={16} />
          New Chat
        </button>
      </div>

      <div className="conversation-list-items">
        {isLoading && <div className="conversation-loading">Loading...</div>}
        {error && <div className="conversation-error">{error}</div>}
        {!isLoading && !error && conversations.length === 0 && (
          <div className="conversation-empty">No conversations yet</div>
        )}
        {conversations.map((thread) => (
          <div
            key={thread.thread_id}
            className={`conversation-item ${
              thread.thread_id === activeConversationId ? 'active' : ''
            }`}
            onClick={() => onSelectConversation(thread.thread_id)}
          >
            <div className="conversation-item-content">
              <div className="conversation-item-title">
                {thread.metadata?.title || 'New Conversation'}
              </div>
              <div className="conversation-item-time">
                {formatDate(thread.updated_at || thread.created_at)}
              </div>
            </div>
            <button
              className="conversation-delete-btn"
              onClick={(e) => handleDeleteConversation(thread.thread_id, e)}
              aria-label="Delete conversation"
            >
              <TrashIcon size={16} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ConversationList;
