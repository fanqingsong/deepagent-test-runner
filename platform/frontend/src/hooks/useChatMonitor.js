import { useQuery } from '@tanstack/react-query';
import { getChatSessions, getChatMetrics, getChatSubagentUsage, getChatSessionMessages } from '../api';

export const useChatSessions = (params = {}) => {
  return useQuery({
    queryKey: ['chat-sessions', params],
    queryFn: () => getChatSessions(params),
    staleTime: 30000,
  });
};

export const useChatMetrics = (days = 30) => {
  return useQuery({
    queryKey: ['chat-metrics', days],
    queryFn: () => getChatMetrics(days),
    staleTime: 60000,
  });
};

export const useChatSubagentUsage = (days = 30) => {
  return useQuery({
    queryKey: ['chat-subagent-usage', days],
    queryFn: () => getChatSubagentUsage(days),
    staleTime: 60000,
  });
};

export const useSessionMessages = (threadId) => {
  return useQuery({
    queryKey: ['chat-session-messages', threadId],
    queryFn: () => getChatSessionMessages(threadId),
    enabled: !!threadId,
    staleTime: 30000,
  });
};
