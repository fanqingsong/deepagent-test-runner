/**
 * Chat stream hook using @langchain/react useStream.
 *
 * Connects to the LangGraph Platform Server for real-time
 * subagent tracking, tool calls, and token streaming.
 */
import { useMemo, useCallback, useRef } from 'react';
import { useStream } from '@langchain/react';
import authService from '../services/authService';

const LANGGRAPH_URL = import.meta.env.VITE_LANGGRAPH_URL || `${window.location.origin}/langgraph`;

export function useChatStream() {
  const threadIdRef = useRef(null);

  const stream = useStream({
    apiUrl: LANGGRAPH_URL,
    assistantId: 'chat',
    onThreadId: (id) => {
      threadIdRef.current = id;
    },
    filterSubagentMessages: true,
    defaultHeaders: authService.getAuthHeaders(),
  });

  // Convert LangChain BaseMessage[] to simple {role, content} for ChatModal
  const messages = useMemo(() => {
    return (stream.messages || []).map((msg) => {
      const role = msg.getType?.() === 'human' ? 'user' : 'assistant';
      const content = typeof msg.content === 'string'
        ? msg.content
        : Array.isArray(msg.content)
          ? msg.content.map((c) => c.text || c.content || String(c)).join('')
          : String(msg.content || '');

      // Extract tool calls if present
      const toolCalls = msg.tool_calls?.length > 0
        ? msg.tool_calls.map((tc) => ({
            name: tc.name,
            args: tc.args,
          }))
        : undefined;

      return { role, content, toolCalls };
    });
  }, [stream.messages]);

  // Derive current active subagent
  const currentSubagent = useMemo(() => {
    const active = stream.activeSubagents;
    if (!active || active.length === 0) return null;
    const sa = active[0];
    return {
      name: sa.name || sa.id,
      description: sa.description || 'Processing...',
      startTime: Date.now(),
      status: sa.status,
    };
  }, [stream.activeSubagents]);

  // Derive completed subagent history
  const subagentHistory = useMemo(() => {
    if (!stream.subagents) return [];
    return [...stream.subagents.values()]
      .filter((sa) => sa.status === 'complete' || sa.status === 'error')
      .map((sa) => ({
        name: sa.name || sa.id,
        duration: sa.duration,
        completedAt: Date.now(),
      }));
  }, [stream.subagents]);

  // Derive tool calls from the stream
  const toolCalls = useMemo(() => {
    const calls = [];
    if (stream.toolCalls) {
      for (const tc of stream.toolCalls) {
        calls.push({
          tool: tc.call?.name || tc.name || 'tool',
          args: tc.call?.args || tc.args || '',
          source: tc.source || '',
          timestamp: Date.now(),
          type: 'call',
        });
        if (tc.result !== undefined) {
          calls.push({
            tool: tc.call?.name || tc.name || 'tool',
            result: String(tc.result).substring(0, 500),
            source: tc.source || '',
            timestamp: Date.now(),
            type: 'result',
          });
        }
      }
    }
    return calls;
  }, [stream.toolCalls]);

  // Get streaming content from the last AI message (current turn only)
  const streamingContent = useMemo(() => {
    if (!stream.isLoading || !stream.messages?.length) return '';
    const msgs = stream.messages;
    // If the last message is human, the AI hasn't started responding yet
    if (msgs[msgs.length - 1].getType?.() === 'human') return '';
    for (let i = msgs.length - 1; i >= 0; i--) {
      const msg = msgs[i];
      if (msg.getType?.() === 'ai') {
        return typeof msg.content === 'string'
          ? msg.content
          : String(msg.content || '');
      }
    }
    return '';
  }, [stream.messages, stream.isLoading]);

  const sendMessage = useCallback(
    async (content, { enableSearch = false, enableDeepThinking = false } = {}) => {
      if (!content.trim()) return;

      await stream.submit(
        {
          messages: [{ type: 'human', content }],
        },
        {
          streamSubgraphs: true,
          configurable: {
            user_id: 1,
            enable_search: enableSearch,
            enable_deep_thinking: enableDeepThinking,
          },
        },
      );
    },
    [stream],
  );

  const stopStreaming = useCallback(() => {
    stream.stop();
  }, [stream]);

  const setThreadId = useCallback((id) => {
    threadIdRef.current = id;
    stream.switchThread(id);
  }, [stream]);

  const clearMessages = useCallback(() => {
    threadIdRef.current = null;
    stream.switchThread(null);
  }, [stream]);

  return {
    messages,
    isStreaming: stream.isLoading || false,
    streamingContent,
    currentSubagent,
    subagentHistory,
    toolCalls,
    error: stream.error?.message || null,
    sendMessage,
    stopStreaming,
    setThreadId,
    clearMessages,
    // Expose raw subagent data for advanced UI
    rawSubagents: stream.subagents,
    todos: stream.values?.todos || [],
  };
}
