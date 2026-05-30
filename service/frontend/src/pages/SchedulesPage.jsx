import { useState, useCallback } from 'react';
import ScheduleList from '../components/ScheduleList';
import ScheduleForm from '../components/ScheduleForm';
import Modal from '../components/Modal';
import { triggerSchedule, toggleSchedule } from '../api';

export default function SchedulesPage() {
  const [showForm, setShowForm] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [message, setMessage] = useState(null);

  const showMessage = useCallback((text, type = 'success') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  }, []);

  const handleCreate = () => {
    setEditingSchedule(null);
    setShowForm(true);
  };

  const handleEdit = (schedule) => {
    setEditingSchedule(schedule);
    setShowForm(true);
  };

  const handleFormSuccess = () => {
    setShowForm(false);
    setEditingSchedule(null);
    setRefreshKey(k => k + 1);
    showMessage(editingSchedule ? 'Schedule updated' : 'Schedule created');
  };

  const handleTrigger = async (scheduleId) => {
    try {
      await triggerSchedule(scheduleId);
      showMessage('Schedule triggered successfully');
    } catch (err) {
      showMessage(err.message, 'error');
    }
  };

  const handleToggle = async (scheduleId, isActive) => {
    try {
      await toggleSchedule(scheduleId, isActive);
      setRefreshKey(k => k + 1);
      showMessage(isActive ? 'Schedule enabled' : 'Schedule disabled');
    } catch (err) {
      showMessage(err.message, 'error');
    }
  };

  return (
    <div style={{ padding: 'var(--cds-layout-sm)', background: 'var(--cds-background)' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 'var(--cds-layout-md)',
      }}>
        <h2 style={{
          margin: 0,
          fontSize: 'var(--cds-heading-01, 28px)',
          fontWeight: 'var(--cds-font-weight-light, 300)',
        }}>
          Schedules
        </h2>
        <button
          onClick={handleCreate}
          style={{
            padding: 'var(--cds-button-padding-sm, 0 16px)',
            background: 'var(--cds-button-primary, #0f62fe)',
            color: 'var(--cds-text-on-color, #fff)',
            border: 'none',
            cursor: 'pointer',
            fontWeight: 'var(--cds-font-weight-regular, 400)',
            fontSize: 'var(--cds-body-short-01, 14px)',
            height: 'var(--cds-button-height-compact, 32px)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--cds-spacing-sm, 8px)',
          }}
        >
          + Create Schedule
        </button>
      </div>

      {message && (
        <div style={{
          padding: '12px 16px',
          marginBottom: '16px',
          background: message.type === 'error' ? '#fff1f1' : '#defbe6',
          color: message.type === 'error' ? '#da1e28' : '#047857',
          fontSize: '14px',
        }}>
          {message.text}
        </div>
      )}

      <ScheduleList
        key={refreshKey}
        onEditSchedule={handleEdit}
        onTriggerSchedule={handleTrigger}
        onToggleSchedule={handleToggle}
      />

      <Modal
        isOpen={showForm}
        onClose={() => { setShowForm(false); setEditingSchedule(null); }}
        title={editingSchedule ? `Edit: ${editingSchedule.name}` : 'Create Schedule'}
      >
        <ScheduleForm
          editingSchedule={editingSchedule}
          onScheduleCreated={handleFormSuccess}
          onCancel={() => { setShowForm(false); setEditingSchedule(null); }}
        />
      </Modal>
    </div>
  );
}
