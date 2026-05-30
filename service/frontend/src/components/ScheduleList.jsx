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
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  );

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;

    setDeletingId(id);
    try {
      await deleteSchedule(id);
    } catch (err) {
      alert('Delete failed: ' + err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const getCronDisplay = (cronExpression) => cronExpression || 'Not set';

  const getStatusBadge = (schedule) => {
    const isActive = schedule.is_active;
    return (
      <span className={`status-badge ${isActive ? 'active' : 'inactive'}`}>
        {isActive ? 'Enabled' : 'Disabled'}
      </span>
    );
  };

  const formatTime = (isoString) => {
    if (!isoString) return '-';
    return new Date(isoString).toLocaleString('en-US');
  };

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="error-container">
        <span className="error-icon">!</span>
        <span>Error: {error?.message || String(error)}</span>
      </div>
    );
  }

  return (
    <div className="schedule-list">
      {schedules.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon" style={{ fontSize: '48px', marginBottom: '16px' }}>&#128197;</div>
          <p className="empty-title">No schedules yet</p>
          <p className="empty-subtitle">Click "Create Schedule" to set up a scheduled test run</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="schedule-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Cron</th>
                <th>Timezone</th>
                <th>Last Run</th>
                <th>Next Run</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedSchedules.map((schedule) => (
                <tr key={schedule.id} className="schedule-row">
                  <td className="name-cell">
                    <div className="schedule-name">{schedule.name}</div>
                    <div style={{ fontSize: '12px', color: '#525252', marginTop: '2px' }}>
                      {schedule.schedule_type}
                    </div>
                  </td>
                  <td>{getStatusBadge(schedule)}</td>
                  <td className="cron-cell">
                    <code>{getCronDisplay(schedule.cron_expression)}</code>
                  </td>
                  <td>{schedule.timezone || 'UTC'}</td>
                  <td>{formatTime(schedule.last_run_time)}</td>
                  <td>{formatTime(schedule.next_run_time)}</td>
                  <td className="actions-cell">
                    <div className="action-buttons">
                      <button
                        type="button"
                        className="action-btn trigger-btn"
                        onClick={() => onTriggerSchedule(schedule.id)}
                        title="Trigger now"
                      >
                        Trigger
                      </button>
                      <button
                        type="button"
                        className="action-btn toggle-btn"
                        onClick={() => onToggleSchedule(schedule.id, !schedule.is_active)}
                        title={schedule.is_active ? 'Disable' : 'Enable'}
                      >
                        {schedule.is_active ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        type="button"
                        className="action-btn edit-btn"
                        onClick={() => onEditSchedule(schedule)}
                        title="Edit"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="action-btn delete-btn"
                        onClick={() => handleDelete(schedule.id)}
                        disabled={deletingId === schedule.id || isDeleting}
                        title="Delete"
                      >
                        {deletingId === schedule.id ? 'Deleting...' : 'Delete'}
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
