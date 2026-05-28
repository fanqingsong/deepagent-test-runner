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
  // Use refs for callbacks to avoid re-render loops
  const callbacksRef = useRef(options);
  callbacksRef.current = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const threadIdRef = useRef(threadId);
  threadIdRef.current = threadId;
  const pendingRef = useRef([]);
  const MAX_RECONNECT_ATTEMPTS = 5;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const currentThreadId = threadIdRef.current;
    if (!currentThreadId) {
      return;
    }

    try {
      const wsUrl = getChatWebSocketURL(currentThreadId);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        callbacksRef.current.onConnected?.();

        // Flush any messages queued while connecting
        const pending = pendingRef.current.splice(0);
        for (const msg of pending) {
          ws.send(msg);
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          switch (data.type) {
            case 'connected':
              break;

            case 'user_message':
              break;

            case 'assistant_message':
              setIsStreaming(true);
              callbacksRef.current.onMessage?.({
                role: 'assistant',
                content: data.content,
                tool_calls: data.tool_calls,
                timestamp: data.timestamp,
              });
              setIsStreaming(false);
              break;

            case 'error':
              callbacksRef.current.onError?.(data.content);
              break;

            default:
              callbacksRef.current.onMessage?.(data);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsStreaming(false);
        callbacksRef.current.onDisconnected?.();

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
        callbacksRef.current.onError?.('WebSocket connection error');
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Error creating WebSocket:', error);
      callbacksRef.current.onError?.('Failed to create WebSocket connection');
    }
  }, []); // No dependencies — uses refs for everything

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

  const sendMessage = useCallback((content, enableSearch = false) => {
    const msg = JSON.stringify({ content, enable_search: enableSearch });
    const ws = wsRef.current;

    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(msg);
      return true;
    }

    // Queue for when connection opens (CONNECTING state)
    if (ws?.readyState === WebSocket.CONNECTING) {
      pendingRef.current.push(msg);
      return true;
    }

    return false;
  }, []);

  // Only connect/disconnect when threadId changes
  useEffect(() => {
    if (threadId) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [threadId, connect, disconnect]);

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
    (content, enableSearch = false) => {
      const success = sendMessage(content, enableSearch);
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
