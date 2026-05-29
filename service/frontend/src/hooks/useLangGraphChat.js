/**
 * LangGraph Chat Hook
 *
 * 使用官方 @langchain/react 的 useStream hook 包装
 */
import { useStream } from '@langchain/react';
import { LANGGRAPH_CONFIG } from '../config/langgraph';

export function useLangGraphChat(threadId) {
  // 获取访问 token
  const getAuthToken = () => {
    return localStorage.getItem('access_token') ||
           sessionStorage.getItem('access_token') ||
           localStorage.getItem('session_token') ||
           sessionStorage.getItem('session_token') ||
           '';
  };

  const stream = useStream({
    ...LANGGRAPH_CONFIG,
    // 在配置中传递 thread_id
    config: {
      configurable: {
        thread_id: threadId || 'default-thread'
      }
    },
    // 认证头
    headers: {
      'Authorization': `Bearer ${getAuthToken()}`,
    },
  });

  return {
    // 流式状态
    stream,
    isStreaming: stream.isProcessing,

    // 消息列表
    messages: stream.values?.messages || [],

    // Subagent 状态列表
    subagents: stream.subagents || [],

    // Todo list
    todos: stream.values?.todos || [],

    // 提交消息
    submit: stream.submit,

    // 当前流式内容（用于实时显示）
    streamingContent: stream.values?.messages?.[
      stream.values?.messages?.length - 1
    ]?.content || '',
  };
}
