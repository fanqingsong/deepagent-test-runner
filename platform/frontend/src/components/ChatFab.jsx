import React from 'react';
import { ChatIcon } from './Icons';
import './ChatFab.css';

/**
 * Floating Action Button (FAB) for opening the chat interface.
 * Positioned in the bottom-right corner of the screen.
 */
export function ChatFab({ onClick, hasUnreadMessages = false, className = '' }) {
  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('ChatFab clicked!');
    if (onClick) {
      onClick();
    }
  };

  return (
    <button
      onClick={handleClick}
      className={`chat-fab ${className}`}
      aria-label="Open chat"
      style={{ display: 'flex' }}
    >
      <ChatIcon size={24} />

      {hasUnreadMessages && (
        <span className="unread-badge" />
      )}
    </button>
  );
}

export default ChatFab;
