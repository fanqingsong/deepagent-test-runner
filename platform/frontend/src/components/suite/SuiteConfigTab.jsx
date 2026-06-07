export default function SuiteConfigTab({
  formName, formDesc, formMode, formConcurrency, formFailStrategy,
  configDirty, savingConfig, readOnly,
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
    <div className="suite-config-container">
      <div className="studio-workspace-field-group">
        <label className="studio-workspace-field-label">Name</label>
        <input
          className="studio-workspace-field-input"
          value={formName}
          onChange={onChangeName}
          placeholder="Test suite name"
          disabled={readOnly}
        />
      </div>

      <div className="studio-workspace-field-group">
        <label className="studio-workspace-field-label">Description</label>
        <textarea
          className="studio-workspace-field-textarea"
          value={formDesc}
          onChange={onChangeDesc}
          placeholder="Optional description..."
          rows={2}
          disabled={readOnly}
        />
      </div>

      <div className="studio-workspace-field-row">
        <div className="studio-workspace-field-group studio-workspace-field-group--inline">
          <label className="studio-workspace-field-label">Execution Mode</label>
          <select
            className="studio-workspace-field-input"
            value={formMode}
            onChange={onChangeMode}
            disabled={readOnly}
          >
            <option value="sequential">Sequential</option>
            <option value="parallel">Parallel</option>
          </select>
        </div>

        <div className="studio-workspace-field-group studio-workspace-field-group--inline">
          <label className="studio-workspace-field-label">Failure Strategy</label>
          <select
            className="studio-workspace-field-input"
            value={formFailStrategy}
            onChange={onChangeFailStrategy}
            disabled={readOnly}
          >
            <option value="continue">Continue</option>
            <option value="fail_fast">Fail fast</option>
          </select>
        </div>
      </div>

      {formMode === 'parallel' && (
        <div className="studio-workspace-field-group">
          <label className="studio-workspace-field-label">Max Concurrency</label>
          <input
            className="studio-workspace-field-input"
            type="number"
            min={1}
            max={10}
            value={formConcurrency}
            onChange={onChangeConcurrency}
            disabled={readOnly}
          />
        </div>
      )}

      {/* Schedule Section */}
      <div className="studio-workspace-schedule-divider">
        <div className="studio-workspace-schedule-header">
          <label className="studio-workspace-field-label">Scheduled Run</label>
          <label className={`studio-workspace-checkbox-label ${readOnly ? 'studio-workspace-checkbox-label--disabled' : ''}`}>
            <input
              type="checkbox"
              checked={formScheduleEnabled}
              onChange={(e) => onChangeScheduleEnabled(e.target.checked)}
              disabled={readOnly}
            />
            Enable
          </label>
        </div>

        {formScheduleEnabled && (
          <>
            <div className="studio-workspace-field-group">
              <label className="studio-workspace-field-label">Cron Expression</label>
              <select
                className="studio-workspace-field-input studio-workspace-field-input--preset"
                value=""
                onChange={(e) => {
                  if (e.target.value) onChangeCronExpression(e.target.value);
                }}
                disabled={readOnly}
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
                disabled={readOnly}
              />
              <span className="studio-workspace-helper-text">
                Format: minute hour day month weekday
              </span>
            </div>

            <div className="studio-workspace-field-group">
              <label className="studio-workspace-field-label">Timezone</label>
              <select
                className="studio-workspace-field-input"
                value={formTimezone}
                onChange={(e) => onChangeTimezone(e.target.value)}
                disabled={readOnly}
              >
                <option value="Asia/Shanghai">Asia/Shanghai (CST)</option>
                <option value="UTC">UTC</option>
                <option value="America/New_York">America/New_York</option>
                <option value="Europe/London">Europe/London</option>
              </select>
            </div>

            {/* Advanced schedule options */}
            <details className="studio-workspace-details">
              <summary>Advanced Options</summary>
              <div className="studio-workspace-details-content">
                <label className="studio-workspace-checkbox-label">
                  <input
                    type="checkbox"
                    checked={formScheduleAllowConcurrent}
                    onChange={(e) => onChangeScheduleAllowConcurrent(e.target.checked)}
                    disabled={readOnly}
                  />
                  Allow concurrent execution
                </label>

                <div className="studio-workspace-field-row">
                  <div className="studio-workspace-field-group">
                    <label className="studio-workspace-field-label">Max Retries</label>
                    <input
                      className="studio-workspace-field-input"
                      type="number"
                      min={0}
                      max={10}
                      value={formScheduleMaxRetries}
                      onChange={(e) => onChangeScheduleMaxRetries(parseInt(e.target.value) || 0)}
                      disabled={readOnly}
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
                      disabled={readOnly}
                    />
                  </div>
                </div>
              </div>
            </details>

            {/* Schedule status */}
            <div className="studio-workspace-schedule-status">
              <span>Next run: {formatTime(nextRunTime)}</span>
              <span>Last run: {formatTime(lastRunTime)}</span>
            </div>
          </>
        )}
      </div>

      <div className="studio-workspace-actions">
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
