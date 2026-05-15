import { useState } from 'react';
import { useSchedules } from '../hooks/useSchedules';
import './ScheduleList.css';

export default function ScheduleList({
  onEditSchedule,
  onTriggerSchedule,
  onToggleSchedule,
}) {
  const { schedules, isLoading, isError, error, deleteSchedule, isDeleting } = useSchedules();
  const [deletingId, setDeletingId] = useState(null);

  const sortedSchedules = [...schedules].sort(
    (a, b) => new Date(a.created_at) - new Date(b.created_at)
  );

  const handleDelete = async (id) => {
    if (!confirm('确定要删除这个调度吗？')) return;

    setDeletingId(id);
    try {
      await deleteSchedule(id);
    } catch (err) {
      alert('删除失败: ' + err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const getCronDisplay = (cronExpression) => cronExpression || '未设置';

  const getStatusBadge = (schedule) => {
    const isActive = schedule.is_active;
    return (
      <span className={`status-badge ${isActive ? 'active' : 'inactive'}`}>
        {isActive ? '启用' : '禁用'}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>加载中...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="error-container">
        <span className="error-icon">⚠️</span>
        <span>错误: {error?.message || String(error)}</span>
      </div>
    );
  }

  return (
    <div className="schedule-list">
      <h2 className="list-title">调度列表</h2>
      {schedules.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📅</div>
          <p className="empty-title">还没有调度任务</p>
          <p className="empty-subtitle">点击"创建调度"来创建定时任务</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="schedule-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>状态</th>
                <th>Cron</th>
                <th>时区</th>
                <th>下次运行</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {sortedSchedules.map((schedule) => (
                <tr key={schedule.id} className="schedule-row">
                  <td className="name-cell">
                    <div className="schedule-name">{schedule.name}</div>
                  </td>
                  <td>{getStatusBadge(schedule)}</td>
                  <td className="cron-cell">
                    <code>{getCronDisplay(schedule.cron_expression)}</code>
                  </td>
                  <td>{schedule.timezone || 'UTC'}</td>
                  <td>
                    {schedule.next_run_at
                      ? new Date(schedule.next_run_at).toLocaleString('zh-CN')
                      : '-'}
                  </td>
                  <td className="actions-cell">
                    <div className="action-buttons">
                      <button
                        type="button"
                        className="action-btn trigger-btn"
                        onClick={() => onTriggerSchedule(schedule.id)}
                        title="立即触发"
                      >
                        触发
                      </button>
                      <button
                        type="button"
                        className="action-btn toggle-btn"
                        onClick={() => onToggleSchedule(schedule.id, !schedule.is_active)}
                        title={schedule.is_active ? '禁用' : '启用'}
                      >
                        {schedule.is_active ? '禁用' : '启用'}
                      </button>
                      <button
                        type="button"
                        className="action-btn edit-btn"
                        onClick={() => onEditSchedule(schedule)}
                        title="编辑"
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        className="action-btn delete-btn"
                        onClick={() => handleDelete(schedule.id)}
                        disabled={deletingId === schedule.id || isDeleting}
                        title="删除"
                      >
                        {deletingId === schedule.id ? '删除中...' : '删除'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
