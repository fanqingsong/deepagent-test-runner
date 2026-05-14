import React, { useEffect } from 'react';

/**
 * 刷新指示器组件
 * 在数据后台刷新时显示右上角小型提示
 *
 * @param {boolean} refreshing - 是否正在刷新
 */
const RefreshIndicator = ({ refreshing }) => {
  useEffect(() => {
    // 添加全局动画样式
    if (!document.getElementById('refresh-indicator-styles')) {
      const style = document.createElement('style');
      style.id = 'refresh-indicator-styles';
      style.innerHTML = `
        @keyframes refresh-indicator-spin {
          to { transform: rotate(360deg); }
        }
        @keyframes refresh-indicator-fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `;
      document.head.appendChild(style);
    }
  }, []);

  if (!refreshing) return null;

  return (
    <div style={{
      position: 'fixed',
      top: '20px',
      right: '20px',
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 16px',
      background: 'var(--cds-background-layer, #ffffff)',
      border: '1px solid var(--cds-border-weak, #e0e0e0)',
      borderRadius: 'var(--cds-border-radius, 0px)',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      fontSize: '14px',
      color: 'var(--cds-text-primary, #161616)',
      zIndex: 1000,
      animation: 'refresh-indicator-fadeIn 0.3s ease-in-out',
    }}>
      <div style={{
        width: '16px',
        height: '16px',
        border: '2px solid rgba(0,0,0,0.1)',
        borderTopColor: 'var(--cds-interactive-01, #0f62fe)',
        borderRadius: '50%',
        animation: 'refresh-indicator-spin 0.6s linear infinite',
      }}></div>
      <span>更新中...</span>
    </div>
  );
};

export default RefreshIndicator;
