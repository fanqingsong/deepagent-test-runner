export default function StudioConfigTab({
  formName, formUrl, formGoal, formDesc,
  configDirty, isBusy, savingConfig,
  onFormChange, onSaveConfig,
}) {
  const isNew = !formUrl && !formGoal;

  return (
    <div style={{ padding: '20px', maxWidth: '600px' }}>
      {isNew && (
        <div style={{
          marginBottom: '20px',
          padding: '12px 16px',
          background: '#edf5ff',
          borderRadius: '0',
          fontSize: '14px',
          color: '#161616',
          borderLeft: '3px solid #0f62fe',
        }}>
          Please fill in the test configuration, then click "Save Configuration"
        </div>
      )}
      <div className="studio-workspace-field-group">
        <label className="studio-workspace-field-label">Name</label>
        <input
          className="studio-workspace-field-input"
          value={formName}
          onChange={onFormChange('name')}
          disabled={isBusy}
        />
      </div>
      <div className="studio-workspace-field-group" style={{ marginTop: '16px' }}>
        <label className="studio-workspace-field-label">Target URL</label>
        <input
          className="studio-workspace-field-input"
          value={formUrl}
          onChange={onFormChange('url')}
          placeholder="https://example.com"
          disabled={isBusy}
        />
      </div>
      <div className="studio-workspace-field-group" style={{ marginTop: '16px' }}>
        <label className="studio-workspace-field-label">Test Goal</label>
        <textarea
          className="studio-workspace-field-textarea"
          value={formGoal}
          onChange={onFormChange('goal')}
          placeholder="Describe what you want to test in natural language..."
          rows={4}
          disabled={isBusy}
        />
      </div>
      <div className="studio-workspace-field-group" style={{ marginTop: '16px' }}>
        <label className="studio-workspace-field-label">Description</label>
        <textarea
          className="studio-workspace-field-textarea"
          value={formDesc}
          onChange={onFormChange('desc')}
          placeholder="Optional additional description..."
          rows={2}
          disabled={isBusy}
        />
      </div>
      <div style={{ display: 'flex', gap: '8px', marginTop: '20px' }}>
        <button
          className="studio-workspace-secondary-btn"
          onClick={onSaveConfig}
          disabled={!configDirty || savingConfig || isBusy}
        >
          {savingConfig ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
    </div>
  );
}
