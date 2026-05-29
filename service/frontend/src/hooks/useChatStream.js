/**
 * Custom SSE chat stream hook.
 *
 * Replaces @langchain/react's useStream with direct SSE parsing
 * for structured events from ChatAgent.chat_stream().
 *
 * Events handled:
 * - token_delta:        streaming text tokens
 * - subagent_started:   subagent begins work
 * - subagent_progress:  progress update within a subagent
 * - subagent_completed: subagent finishes
 * - tool_call:          tool invoked by a subagent
 * - tool_result:        tool returned a result
 * - stream_complete:    final event with full content
 * - error:              stream error
 */
import { useState, useRef, useCallback } from 'react';

const SSE_URL = import.meta.env.VITE_CHAT_STREAM_URL || '/api/v1/chat/stream';

function getAuthToken() {
  return (
    localStorage.getItem('access_token') ||
    sessionStorage.getItem('access_token') ||
    localStorage.getItem('session_token') ||
    sessionStorage.getItem('session_token') ||
    ''
  );
}

/**
 * Parse an SSE text stream into {event, data} objects.
 */
async function* parseSSE(reader) {
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = '';
  let currentData = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    // Keep the last (possibly incomplete) line in the buffer
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        currentData = line.slice(6);
      } else if (line === '' && currentData) {
        // Empty line signals end of event
        try {
          yield { event: currentEvent || 'message', data: JSON.parse(currentData) };
        } catch {
          yield { event: currentEvent || 'message', data: currentData };
        }
        currentEvent = '';
        currentData = '';
      }
    }
  }

  // Flush any remaining event
  if (currentData) {
    try {
      yield { event: currentEvent || 'message', data: JSON.parse(currentData) };
    } catch {
      yield { event: currentEvent || 'message', data: currentData };
    }
  }
}

export function useChatStream() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [currentSubagent, setCurrentSubagent] = useState(null);
  const [subagentHistory, setSubagentHistory] = useState([]);
  const [toolCalls, setToolCalls] = useState([]);
  const [error, setError] = useState(null);

  const abortRef = useRef(null);
  const threadIdRef = useRef(`thread-${Date.now()}`);

  const sendMessage = useCallback(
    async (content, { enableSearch = false, enableDeepThinking = false } = {}) => {
      if (!content.trim() || isStreaming) return;

      const userMsg = { role: 'user', content };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      setStreamingContent('');
      setCurrentSubagent(null);
      setSubagentHistory([]);
      setToolCalls([]);
      setError(null);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch(SSE_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getAuthToken()}`,
          },
          body: JSON.stringify({
            messages: [{ role: 'user', content }],
            config: {
              configurable: { thread_id: threadIdRef.current },
            },
            enable_search: enableSearch,
            enable_deep_thinking: enableDeepThinking,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        let accumulated = '';

        for await (const { event, data } of parseSSE(reader)) {
          switch (event) {
            case 'token_delta':
              accumulated += data.content || '';
              setStreamingContent(accumulated);
              break;

            case 'subagent_started':
              setCurrentSubagent({
                name: data.subagent,
                description: data.description,
                startTime: Date.now(),
              });
              break;

            case 'subagent_progress':
              setCurrentSubagent((prev) =>
                prev ? { ...prev, status: data.status } : prev
              );
              break;

            case 'subagent_completed':
              setSubagentHistory((prev) => [
                ...prev,
                {
                  name: data.subagent,
                  duration: data.duration,
                  completedAt: Date.now(),
                },
              ]);
              setCurrentSubagent(null);
              break;

            case 'tool_call':
              setToolCalls((prev) => [
                ...prev,
                {
                  tool: data.tool,
                  args: data.args,
                  source: data.source,
                  timestamp: Date.now(),
                  type: 'call',
                },
              ]);
              break;

            case 'tool_result':
              setToolCalls((prev) => [
                ...prev,
                {
                  tool: data.tool,
                  result: data.result,
                  source: data.source,
                  timestamp: Date.now(),
                  type: 'result',
                },
              ]);
              break;

            case 'stream_complete': {
              const finalContent = data.content || accumulated || 'No response.';
              setMessages((prev) => [
                ...prev,
                { role: 'assistant', content: finalContent },
              ]);
              setStreamingContent('');
              setIsStreaming(false);
              break;
            }

            case 'error':
              setError(data.content || 'Unknown error');
              setIsStreaming(false);
              break;
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message);
        }
        setIsStreaming(false);
      } finally {
        abortRef.current = null;
      }
    },
    [isStreaming]
  );

  const stopStreaming = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const setThreadId = useCallback((id) => {
    threadIdRef.current = id;
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setStreamingContent('');
    setCurrentSubagent(null);
    setSubagentHistory([]);
    setToolCalls([]);
    setError(null);
    threadIdRef.current = `thread-${Date.now()}`;
  }, []);

  return {
    messages,
    isStreaming,
    streamingContent,
    currentSubagent,
    subagentHistory,
    toolCalls,
    error,
    sendMessage,
    stopStreaming,
    setThreadId,
    clearMessages,
  };
}
