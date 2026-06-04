/**
 * Chat stream hook using @langchain/react useStream.
 *
 * Connects to the LangGraph Platform Server for real-time
 * subagent tracking, tool calls, and token streaming.
 */
import { useMemo, useCallback, useRef, useEffect } from 'react';
import { useStream } from '@langchain/react';
import { Client } from '@langchain/langgraph-sdk';
import authService from '../services/authService';

const LANGGRAPH_URL = import.meta.env.VITE_LANGGRAPH_URL || `${window.location.origin}/langgraph`;

export function useChatStream() {
  const threadIdRef = useRef(null);
  const titledThreadsRef = useRef(new Set());

  const client = useMemo(() => new Client({
    apiUrl: LANGGRAPH_URL,
    defaultHeaders: authService.getAuthHeaders(),
  }), []);

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
    const allMessages = stream.messages || [];

    // Collect chart URLs from preceding tool results for each assistant message
    const chartUrls = [];
    return allMessages.map((msg) => {
      const role = msg.getType?.() === 'human' ? 'user' : 'assistant';

      // Track chart URLs from tool results
      if (msg.getType?.() === 'tool') {
        try {
          const toolContent = typeof msg.content === 'string' ? msg.content : String(msg.content || '');
          const parsed = JSON.parse(toolContent);
          if (parsed?.chart_url?.startsWith('/api/v1/charts/') && parsed?.success) {
            chartUrls.push(parsed.chart_url);
          }
        } catch {}
      }

      let content = typeof msg.content === 'string'
        ? msg.content
        : Array.isArray(msg.content)
          ? msg.content.map((c) => c.text || c.content || String(c)).join('')
          : String(msg.content || '');

      // For assistant messages, append any chart URLs collected from preceding tool results
      // if they aren't already referenced as markdown images in the content
      if (role === 'assistant' && chartUrls.length > 0) {
        const unreferenced = chartUrls.filter(url => !content.includes(url));
        if (unreferenced.length > 0) {
          content += '\n\n' + unreferenced.map(url => `![Chart](${url})`).join('\n');
        }
        chartUrls.length = 0;
      }

      // Extract tool calls if present
      const toolCalls = msg.tool_calls?.length > 0
        ? msg.tool_calls.map((tc) => ({
            id: tc.id,
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

  // Derive enriched subagent card data from stream.subagents
  const subagentCards = useMemo(() => {
    if (!stream.subagents) return [];
    return [...stream.subagents.values()].map((sa) => ({
      id: sa.id,
      name: sa.toolCall?.args?.subagent_type || sa.toolCall?.args?.description || sa.name || sa.id,
      description: sa.toolCall?.args?.description || '',
      status: sa.status,
      result: sa.result,
      error: sa.error,
      messages: sa.messages || [],
      toolCalls: sa.toolCalls || [],
      startedAt: sa.startedAt,
      completedAt: sa.completedAt,
    }));
  }, [stream.subagents]);

  // Derive subagent progress stats
  const subagentProgress = useMemo(() => {
    if (!stream.subagents || stream.subagents.size === 0) {
      return { completed: 0, total: 0, percentage: 0 };
    }
    const all = [...stream.subagents.values()];
    const completed = all.filter((sa) => sa.status === 'complete' || sa.status === 'error').length;
    const total = all.length;
    return {
      completed,
      total,
      percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
    };
  }, [stream.subagents]);

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

  // Auto-generate thread title from first human message after AI responds
  useEffect(() => {
    const threadId = threadIdRef.current;
    const msgs = stream.messages;
    if (!threadId || !msgs || msgs.length < 2) return;
    if (titledThreadsRef.current.has(threadId)) return;
    if (stream.isLoading) return;

    const humanMsg = msgs.find((m) => m.getType?.() === 'human');
    const aiMsg = msgs.find((m) => m.getType?.() === 'ai');
    if (!humanMsg || !aiMsg) return;

    titledThreadsRef.current.add(threadId);
    const title = (typeof humanMsg.content === 'string'
      ? humanMsg.content
      : String(humanMsg.content || '')
    ).slice(0, 50);

    client.threads.update(threadId, { metadata: { title } }).catch(() => {});
  }, [stream.messages, stream.isLoading, client]);

  const sendMessage = useCallback(
    async (content, { enableSearch = false, enableDeepThinking = false } = {}) => {
      if (!content.trim()) return;

      // Get actual user ID from auth service
      const user = authService.getUser();
      const userId = user?.id || 1;

      await stream.submit(
        {
          messages: [{ type: 'human', content }],
        },
        {
          streamSubgraphs: true,
          configurable: {
            user_id: userId,
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
    subagentCards,
    subagentProgress,
    toolCalls,
    error: stream.error?.message || null,
    sendMessage,
    stopStreaming,
    setThreadId,
    clearMessages,
    // Expose raw subagent data for advanced UI
    rawSubagents: stream.subagents,
    stream,
    todos: stream.values?.todos || [],
  };
}
