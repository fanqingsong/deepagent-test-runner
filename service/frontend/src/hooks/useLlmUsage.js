import { useQuery } from '@tanstack/react-query';
import { getLlmUsageSummary, getLlmUsageByAgent } from '../api';

export const useLlmUsage = (days = 30) => {
  const summary = useQuery({
    queryKey: ['llm-usage-summary', days],
    queryFn: () => getLlmUsageSummary(days),
    staleTime: 60000,
  });

  const byAgent = useQuery({
    queryKey: ['llm-usage-by-agent', days],
    queryFn: () => getLlmUsageByAgent(days),
    staleTime: 60000,
  });

  return {
    summary: summary.data || {},
    byAgent: byAgent.data || [],
    isLoading: summary.isLoading || byAgent.isLoading,
  };
};
