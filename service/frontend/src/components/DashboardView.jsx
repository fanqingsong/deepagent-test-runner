import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useDashboard } from '../hooks/useDashboard';
import StatsCards from './StatsCards';
// import ChartsSection from './ChartsSection';  // Temporarily disabled due to loading issues
import RecentTests from './RecentTests';
import RefreshIndicator from './RefreshIndicator';

function DashboardView() {
  const { user, isAdmin } = useAuth();
  const [timeRange, setTimeRange] = useState('30d');

  // 使用 React Query hook
  const {
    dashboardData,
    testRuns,
    isLoading,
    isError,
    error,
    isRefreshing
  } = useDashboard(timeRange);

  const handleTimeRangeChange = (newRange) => {
    setTimeRange(newRange);
  };

  // 首次加载：全屏loading
  if (isLoading) {
    return (
      <div style={{
        padding: '40px',
        textAlign: 'center',
        fontSize: '16px',
        color: '#666'
      }}>
        加载仪表板数据中...
      </div>
    );
  }

  // 错误状态
  if (isError) {
    return (
      <div style={{
        padding: '40px',
        textAlign: 'center',
        fontSize: '16px',
        color: '#f44336'
      }}>
        {error?.message || '加载失败'}
      </div>
    );
  }

  return (
    <div style={{
      padding: '24px',
      maxWidth: '1400px',
      margin: '0 auto'
    }}>
      {/* 刷新指示器 */}
      <RefreshIndicator refreshing={isRefreshing} />

      <h1 style={{
        fontSize: '28px',
        fontWeight: 'bold',
        marginBottom: '8px',
        color: '#333'
      }}>
        测试仪表板
      </h1>

      {/* Role-based messaging */}
      <div style={{
        fontSize: '14px',
        color: '#666',
        marginBottom: '24px',
        padding: '12px 16px',
        background: isAdmin ? '#e3f2fd' : '#f5f5f5',
        borderRadius: '4px',
        borderLeft: `4px solid ${isAdmin ? '#2196f3' : '#9e9e9e'}`
      }}>
        {isAdmin ? '👑 管理员视图 - 查看所有用户的测试数据' : '👤 个人视图 - 仅显示您创建的测试数据'}
      </div>

      {/* 统计卡片 */}
      <StatsCards stats={dashboardData.summary || {}} totalDefinitions={dashboardData.totalDefinitions || 0} />

      {/* 图表区域 - 暂时禁用 */}
      {/*
      <ChartsSection
        dashboardData={dashboardData}
        timeRange={timeRange}
        onTimeRangeChange={handleTimeRangeChange}
      />
      */}

      {/* 最近测试运行 */}
      <div style={{ marginTop: '24px' }}>
        <RecentTests testRuns={testRuns} />
      </div>
    </div>
  );
}

export default DashboardView;