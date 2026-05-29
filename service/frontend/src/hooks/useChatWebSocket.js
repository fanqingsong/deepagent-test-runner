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

  // Streaming state
  const [currentSubagent, setCurrentSubagent] = useState(null);
  const [subagentProgress, setSubagentProgress] = useState({});
  const [todoList, setTodoList] = useState([]);
  const [activeToolCalls, setActiveToolCalls] = useState([]);
  const [streamingContent, setStreamingContent] = useState('');

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

            case 'token_delta':
              // Incremental content update
              setIsStreaming(true);
              setStreamingContent(prev => prev + (data.content || ''));
              setCurrentSubagent(data.source || 'main');
              callbacksRef.current.onTokenDelta?.(data);
              break;

            case 'subagent_started':
              setCurrentSubagent(data.subagent);
              setSubagentProgress({
                name: data.subagent,
                description: data.description,
                status: 'running',
                progress: 0
              });
              callbacksRef.current.onSubagentStarted?.(data);
              break;

            case 'subagent_progress':
              setSubagentProgress(prev => ({
                ...prev,
                status: data.status,
                progress: data.progress
              }));
              callbacksRef.current.onSubagentProgress?.(data);
              break;

            case 'subagent_completed':
              callbacksRef.current.onSubagentCompleted?.(data);
              break;

            case 'tool_call':
              setActiveToolCalls(prev => [...prev, {
                tool: data.tool,
                args: data.args,
                source: data.source,
                timestamp: new Date()
              }]);
              callbacksRef.current.onToolCall?.(data);
              break;

            case 'tool_result':
              setActiveToolCalls(prev =>
                prev.map(tc =>
                  tc.tool === data.tool
                    ? { ...tc, result: data.result, completed: true }
                    : tc
                )
              );
              callbacksRef.current.onToolResult?.(data);
              break;

            case 'todo_update':
              setTodoList(data.todos || []);
              callbacksRef.current.onTodoUpdate?.(data);
              break;

            case 'stream_complete':
              setIsStreaming(false);
              // Build the final assistant message
              callbacksRef.current.onMessage?.({
                role: 'assistant',
                content: data.content,
                tool_calls: data.tool_calls,
                timestamp: new Date().toISOString(),
              });
              break;

            case 'user_message':
              break;

            case 'assistant_message':
              // Legacy support for non-streaming mode
              setIsStreaming(false);
              callbacksRef.current.onMessage?.({
                role: 'assistant',
                content: data.content,
                tool_calls: data.tool_calls,
                timestamp: data.timestamp,
              });
              break;

            case 'error':
              setIsStreaming(false);
              callbacksRef.current.onError?.(data.content);
              break;

            case 'title_updated':
              callbacksRef.current.onTitleUpdated?.(data);
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
    setCurrentSubagent(null);
    setStreamingContent('');
    setTodoList([]);
    setActiveToolCalls([]);
    setSubagentProgress({});
  }, []);

  const sendMessage = useCallback((content, enableSearch = false, deepThinking = false) => {
    const msg = JSON.stringify({ content, enable_search: enableSearch, enable_deep_thinking: deepThinking });
    const ws = wsRef.current;

    // Reset streaming state for new message
    setStreamingContent('');
    setTodoList([]);
    setActiveToolCalls([]);
    setSubagentProgress({});

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
    currentSubagent,
    subagentProgress,
    todoList,
    activeToolCalls,
    streamingContent,
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
export function useChatMessages(threadId, { onTitleUpdated } = {}) {
  const [messages, setMessages] = useState([]);
  const {
    isConnected,
    isStreaming,
    currentSubagent,
    subagentProgress,
    todoList,
    activeToolCalls,
    streamingContent,
    sendMessage,
    connect,
    disconnect
  } = useChatWebSocket(
    threadId,
    {
      onMessage: (data) => {
        setMessages((prev) => [...prev, data]);
      },
      onTitleUpdated,
    }
  );

  const setInitialMessages = useCallback((initialMsgs) => {
    setMessages(initialMsgs);
  }, []);

  const sendUserMessage = useCallback(
    (content, enableSearch = false, deepThinking = false) => {
      const success = sendMessage(content, enableSearch, deepThinking);
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
    currentSubagent,
    subagentProgress,
    todoList,
    activeToolCalls,
    streamingContent,
    sendUserMessage,
    clearMessages,
    setInitialMessages,
    connect,
    disconnect,
  };
}
