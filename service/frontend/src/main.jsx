import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

// 创建 QueryClient 实例
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,        // 5秒内数据视为新鲜
      gcTime: 10 * 60 * 1000, // 10分钟后清理缓存
      refetchOnWindowFocus: false, // 窗口聚焦时不自动刷新
      retry: 1,               // 失败重试1次
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
