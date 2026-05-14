import { useQuery } from '@tanstack/react-query';
import { getDashboardData, getTestRuns } from '../api';

/**
 * 仪表板数据管理 Hook
 * 使用 React Query 实现自动缓存、后台刷新和错误处理
 *
 * @param {string} timeRange - 时间范围（如 '30d', '7d'）
 * @returns {Object} 仪表板数据和状态
 */
export const useDashboard = (timeRange = '30d') => {
  const days = parseInt(timeRange);

  // 获取仪表板统计数据
  const dashboardQuery = useQuery({
    queryKey: ['dashboard', days],
    queryFn: () => getDashboardData(days),
    staleTime: 5000, // 5秒内数据视为新鲜
  });

  // 获取最近测试运行
  const testRunsQuery = useQuery({
    queryKey: ['testRuns', 20],
    queryFn: () => getTestRuns(20),
    staleTime: 5000,
    refetchInterval: 10000, // 10秒自动刷新
  });

  return {
    dashboardData: dashboardQuery.data || {
      summary: {},
      byDay: [],
      totalDefinitions: 0
    },
    testRuns: testRunsQuery.data || [],
    isLoading: dashboardQuery.isLoading || testRunsQuery.isLoading,
    isError: dashboardQuery.isError || testRunsQuery.isError,
    error: dashboardQuery.error || testRunsQuery.error,
    isRefreshing: testRunsQuery.isFetching && !testRunsQuery.isLoading,
  };
};
