import React, { useState, useEffect } from 'react';
import { CloseIcon, AddIcon, TrashIcon } from './Icons';
import {
  listChatConversations,
  createChatConversation,
  deleteChatConversation
} from '../api';
import './ConversationList.css';

/**
 * Sidebar panel for managing multiple chat conversations.
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether the sidebar is open
 * @param {Function} props.onClose - Callback when sidebar is closed
 * @param {string|null} props.activeConversationId - Currently selected conversation ID
 * @param {Function} props.onSelectConversation - Callback when conversation is selected
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

  // Load conversations on mount and when refreshKey changes
  useEffect(() => {
    loadConversations();
  }, [refreshKey]);

  const loadConversations = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listChatConversations();
      setConversations(Array.isArray(data) ? data : (data.conversations || []));
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateConversation = async () => {
    try {
      const newConversation = await createChatConversation('New Chat');
      setConversations(prev => [newConversation, ...prev]);
      onSelectConversation(newConversation.id);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteConversation = async (conversationId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;

    try {
      await deleteChatConversation(conversationId);
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      if (activeConversationId === conversationId) {
        onSelectConversation(null);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSelectConversation = (conversationId) => {
    onSelectConversation(conversationId);
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
      {/* Header */}
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

      {/* New Conversation Button */}
      <div className="conversation-list-actions">
        <button
          className="conversation-new-btn"
          onClick={handleCreateConversation}
        >
          <AddIcon size={16} />
          New Chat
        </button>
      </div>

      {/* Conversations */}
      <div className="conversation-list-items">
        {isLoading && <div className="conversation-loading">Loading...</div>}
        {error && <div className="conversation-error">{error}</div>}
        {!isLoading && !error && conversations.length === 0 && (
          <div className="conversation-empty">No conversations yet</div>
        )}
        {conversations.map((conversation) => (
          <div
            key={conversation.id}
            className={`conversation-item ${
              conversation.id === activeConversationId ? 'active' : ''
            }`}
            onClick={() => handleSelectConversation(conversation.id)}
          >
            <div className="conversation-item-content">
              <div className="conversation-item-title">
                {conversation.title || 'New Conversation'}
              </div>
              <div className="conversation-item-time">
                {formatDate(conversation.updated_at || conversation.created_at)}
              </div>
            </div>
            <button
              className="conversation-delete-btn"
              onClick={(e) => handleDeleteConversation(conversation.id, e)}
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
