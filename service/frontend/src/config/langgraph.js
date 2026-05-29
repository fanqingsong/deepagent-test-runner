/**
 * LangGraph Server 连接配置
 */
export const LANGGRAPH_CONFIG = {
  // API URL - 指向 FastAPI SSE 端点
  apiUrl: process.env.NODE_ENV === 'production'
    ? '/api/v1/chat/stream'
    : 'http://localhost:8085/api/v1/chat/stream',

  // 聊天 assistant ID
  assistantId: 'chat-agent',

  // 超时配置 (5分钟)
  timeout: 300000,
};
