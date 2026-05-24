import { useQuery } from '@tanstack/react-query';
import { getSuiteDashboard, getSuiteRunTimeline, getSuiteRunEntries } from '../api';

export const useDashboard = (timeRange = '30d') => {
  const days = parseInt(timeRange);

  const suiteDashboard = useQuery({
    queryKey: ['suite-dashboard', days],
    queryFn: () => getSuiteDashboard(days),
    staleTime: 30000,
    refetchInterval: 30000,
  });

  return {
    dashboardData: suiteDashboard.data || { summary: {}, suites: [] },
    isLoading: suiteDashboard.isLoading,
    isError: suiteDashboard.isError,
    error: suiteDashboard.error,
    isRefreshing: suiteDashboard.isFetching && !suiteDashboard.isLoading,
  };
};

export const useSuiteTimeline = (suiteId, options = {}) => {
  return useQuery({
    queryKey: ['suite-timeline', suiteId],
    queryFn: () => getSuiteRunTimeline(suiteId, 10),
    enabled: !!suiteId,
    staleTime: 15000,
    refetchInterval: options.isRunning ? 5000 : false,
    ...options,
  });
};

export const useSuiteRunEntries = (runId, options = {}) => {
  return useQuery({
    queryKey: ['suite-run-entries', runId],
    queryFn: () => getSuiteRunEntries(runId),
    enabled: !!runId,
    staleTime: 30000,
    ...options,
  });
};
