export default function SuiteConfigTab({
  formName, formDesc, formMode, formConcurrency, formFailStrategy,
  configDirty, savingConfig,
  onChangeName, onChangeDesc, onChangeMode, onChangeConcurrency, onChangeFailStrategy,
  onSaveConfig,
  // Schedule props
  formScheduleEnabled, formCronExpression, formTimezone,
  formScheduleAllowConcurrent, formScheduleMaxRetries, formScheduleRetryInterval,
  nextRunTime, lastRunTime,
  onChangeScheduleEnabled, onChangeCronExpression, onChangeTimezone,
  onChangeScheduleAllowConcurrent, onChangeScheduleMaxRetries, onChangeScheduleRetryInterval,
}) {
  const cronPresets = [
    { label: 'Hourly', value: '0 * * * *' },
    { label: 'Daily at 2 AM', value: '0 2 * * *' },
    { label: 'Weekly on Monday 9 AM', value: '0 9 * * 1' },
    { label: 'Monthly on 1st at 3 AM', value: '0 3 1 * *' },
    { label: 'Weekdays at 9 AM', value: '0 9 * * 1-5' },
  ];

  const formatTime = (t) => {
    if (!t) return '--';
    try {
      return new Date(t).toLocaleString('en-US');
    } catch {
      return '--';
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '600px' }}>
      <div className="studio-workspace-field-group">
        <label className="studio-workspace-field-label">Name</label>
        <input
          className="studio-workspace-field-input"
          value={formName}
          onChange={onChangeName}
          placeholder="Test suite name"
        />
      </div>

      <div className="studio-workspace-field-group" style={{ marginTop: '16px' }}>
        <label className="studio-workspace-field-label">Description</label>
        <textarea
          className="studio-workspace-field-textarea"
          value={formDesc}
          onChange={onChangeDesc}
          placeholder="Optional description..."
          rows={2}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
        <div className="studio-workspace-field-group">
          <label className="studio-workspace-field-label">Execution Mode</label>
          <select
            className="studio-workspace-field-input"
            value={formMode}
            onChange={onChangeMode}
          >
            <option value="sequential">Sequential</option>
            <option value="parallel">Parallel</option>
          </select>
        </div>

        <div className="studio-workspace-field-group">
          <label className="studio-workspace-field-label">Failure Strategy</label>
          <select
            className="studio-workspace-field-input"
            value={formFailStrategy}
            onChange={onChangeFailStrategy}
          >
            <option value="continue">Continue</option>
            <option value="fail_fast">Fail fast</option>
          </select>
        </div>
      </div>

      {formMode === 'parallel' && (
        <div className="studio-workspace-field-group" style={{ marginTop: '16px' }}>
          <label className="studio-workspace-field-label">Max Concurrency</label>
          <input
            className="studio-workspace-field-input"
            type="number"
            min={1}
            max={10}
            value={formConcurrency}
            onChange={onChangeConcurrency}
          />
        </div>
      )}

      {/* Schedule Section */}
      <div style={{ marginTop: '24px', borderTop: '1px solid #e0e0e0', paddingTop: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <label className="studio-workspace-field-label" style={{ marginBottom: 0 }}>Scheduled Run</label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px' }}>
            <input
              type="checkbox"
              checked={formScheduleEnabled}
              onChange={(e) => onChangeScheduleEnabled(e.target.checked)}
            />
            Enable
          </label>
        </div>

        {formScheduleEnabled && (
          <>
            <div className="studio-workspace-field-group" style={{ marginTop: '12px' }}>
              <label className="studio-workspace-field-label">Cron Expression</label>
              <select
                className="studio-workspace-field-input"
                value=""
                onChange={(e) => {
                  if (e.target.value) onChangeCronExpression(e.target.value);
                }}
                style={{ marginBottom: '8px' }}
              >
                <option value="">Select preset...</option>
                {cronPresets.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label} ({p.value})
                  </option>
                ))}
              </select>
              <input
                className="studio-workspace-field-input"
                value={formCronExpression || ''}
                onChange={(e) => onChangeCronExpression(e.target.value)}
                placeholder="0 2 * * * (min hour day month weekday)"
              />
              <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                Format: minute hour day month weekday
              </div>
            </div>

            <div className="studio-workspace-field-group" style={{ marginTop: '16px' }}>
              <label className="studio-workspace-field-label">Timezone</label>
              <select
                className="studio-workspace-field-input"
                value={formTimezone}
                onChange={(e) => onChangeTimezone(e.target.value)}
              >
                <option value="Asia/Shanghai">Asia/Shanghai (CST)</option>
                <option value="UTC">UTC</option>
                <option value="America/New_York">America/New_York</option>
                <option value="Europe/London">Europe/London</option>
              </select>
            </div>

            {/* Advanced schedule options */}
            <details style={{ marginTop: '16px' }}>
              <summary style={{ fontSize: '13px', color: '#0f62fe', cursor: 'pointer', userSelect: 'none' }}>
                Advanced Options
              </summary>
              <div style={{ marginTop: '12px', paddingLeft: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', marginBottom: '12px' }}>
                  <input
                    type="checkbox"
                    checked={formScheduleAllowConcurrent}
                    onChange={(e) => onChangeScheduleAllowConcurrent(e.target.checked)}
                  />
                  Allow concurrent execution
                </label>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div className="studio-workspace-field-group">
                    <label className="studio-workspace-field-label">Max Retries</label>
                    <input
                      className="studio-workspace-field-input"
                      type="number"
                      min={0}
                      max={10}
                      value={formScheduleMaxRetries}
                      onChange={(e) => onChangeScheduleMaxRetries(parseInt(e.target.value) || 0)}
                    />
                  </div>
                  <div className="studio-workspace-field-group">
                    <label className="studio-workspace-field-label">Retry Interval (sec)</label>
                    <input
                      className="studio-workspace-field-input"
                      type="number"
                      min={10}
                      max={3600}
                      value={formScheduleRetryInterval}
                      onChange={(e) => onChangeScheduleRetryInterval(parseInt(e.target.value) || 60)}
                    />
                  </div>
                </div>
              </div>
            </details>

            {/* Schedule status */}
            <div style={{ marginTop: '16px', fontSize: '12px', color: '#6b7280', display: 'flex', gap: '24px' }}>
              <span>Next run: {formatTime(nextRunTime)}</span>
              <span>Last run: {formatTime(lastRunTime)}</span>
            </div>
          </>
        )}
      </div>

      <div style={{ display: 'flex', gap: '8px', marginTop: '20px' }}>
        <button
          className="studio-workspace-secondary-btn"
          onClick={onSaveConfig}
          disabled={!configDirty || savingConfig}
        >
          {savingConfig ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
    </div>
  );
}
