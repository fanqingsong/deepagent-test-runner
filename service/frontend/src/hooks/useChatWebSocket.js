import { useState, useEffect, useRef, useCallback } from 'react';
import { getChatWebSocketURL } from '../api';

/**
 * Custom hook for managing chat WebSocket connection.
 *
 * @param {string} threadId - The conversation thread ID
 * @param {Object} options - Configuration options
 * @param {Function} options.onMessage - Callback for incoming messages
 * @param {Function} options.onConnected - Callback when connection is established
 * @param {Function} options.onDisconnected - Callback when connection is closed
 * @param {Function} options.onError - Callback for errors
 * @returns {Object} - Connection state and methods
 */
export function useChatWebSocket(threadId, options = {}) {
  const { onMessage, onConnected, onDisconnected, onError } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Don't connect if no threadId provided
    if (!threadId) {
      return;
    }

    try {
      const wsUrl = getChatWebSocketURL(threadId);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        onConnected?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case 'connected':
              // Connection established
              break;

            case 'user_message':
              // User message confirmation
              break;

            case 'assistant_message':
              // AI response
              setIsStreaming(true);
              onMessage?.({
                role: 'assistant',
                content: data.content,
                tool_calls: data.tool_calls,
                timestamp: data.timestamp,
              });
              setIsStreaming(false);
              break;

            case 'error':
              onError?.(data.content);
              break;

            default:
              onMessage?.(data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsStreaming(false);
        onDisconnected?.();

        // Attempt to reconnect
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.('WebSocket connection error');
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      onError?.('Failed to create WebSocket connection');
    }
  }, [threadId, onConnected, onMessage, onDisconnected, onError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsStreaming(false);
  }, []);

  const sendMessage = useCallback((content) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ content }));
      return true;
    }
    return false;
  }, []);

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    isStreaming,
    sendMessage,
    connect,
    disconnect,
  };
}

/**
 * Custom hook for managing chat messages with WebSocket.
 *
 * @param {string} threadId - The conversation thread ID
 * @returns {Object} - Messages and chat methods
 */
export function useChatMessages(threadId) {
  const [messages, setMessages] = useState([]);
  const { isConnected, isStreaming, sendMessage, connect, disconnect } = useChatWebSocket(
    threadId,
    {
      onMessage: (data) => {
        setMessages((prev) => [...prev, data]);
      },
    }
  );

  const sendUserMessage = useCallback(
    (content) => {
      const success = sendMessage(content);
      if (success) {
        setMessages((prev) => [...prev, { role: 'user', content }]);
      }
      return success;
    },
    [sendMessage]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isConnected,
    isStreaming,
    sendUserMessage,
    clearMessages,
    connect,
    disconnect,
  };
}
