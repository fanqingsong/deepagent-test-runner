import { useState } from 'react';
import { generateDescription } from '../../api';

export default function TestCaseConfigTab({
  formName, formUrl, formGoal, formDesc,
  configDirty, isBusy, savingConfig, readOnly,
  onFormChange, onSaveConfig, testCaseId,
}) {
  const isNew = !formUrl && !formGoal;
  const [generatingDesc, setGeneratingDesc] = useState(false);
  const [descError, setDescError] = useState(null);

  const handleGenerateDescription = async () => {
    if (!formGoal || !testCaseId) {
      setDescError('Please enter a test goal first');
      return;
    }

    try {
      setGeneratingDesc(true);
      setDescError(null);
      const data = await generateDescription(testCaseId);
      onFormChange('desc')({ target: { value: data.description } });
    } catch (e) {
      setDescError(e.message);
    } finally {
      setGeneratingDesc(false);
    }
  };

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
      <div className="test-case-workspace-field-group">
        <label className="test-case-workspace-field-label">Name</label>
        <input
          className="test-case-workspace-field-input"
          value={formName}
          onChange={onFormChange('name')}
          disabled={readOnly || isBusy}
        />
      </div>
      <div className="test-case-workspace-field-group" style={{ marginTop: '16px' }}>
        <label className="test-case-workspace-field-label">Target URL</label>
        <input
          className="test-case-workspace-field-input"
          value={formUrl}
          onChange={onFormChange('url')}
          placeholder="https://example.com"
          disabled={readOnly || isBusy}
        />
      </div>
      <div className="test-case-workspace-field-group" style={{ marginTop: '16px' }}>
        <label className="test-case-workspace-field-label">Test Goal</label>
        <textarea
          className="test-case-workspace-field-textarea"
          value={formGoal}
          onChange={onFormChange('goal')}
          placeholder="Describe what you want to test in natural language..."
          rows={4}
          disabled={readOnly || isBusy}
        />
      </div>
      <div className="test-case-workspace-field-group" style={{ marginTop: '16px' }}>
        <label className="test-case-workspace-field-label">
          Description
          {!readOnly && !isNew && testCaseId && (
            <button
              type="button"
              onClick={handleGenerateDescription}
              disabled={generatingDesc || isBusy || !formGoal}
              style={{
                marginLeft: '12px',
                padding: '4px 12px',
                fontSize: '12px',
                background: '#f4f4f4',
                border: '1px solid #8d8d8d',
                borderRadius: '0',
                cursor: generatingDesc || !formGoal ? 'not-allowed' : 'pointer',
                opacity: generatingDesc || !formGoal ? 0.5 : 1,
              }}
            >
              {generatingDesc ? 'Generating...' : 'Generate from Goal'}
            </button>
          )}
        </label>
        <textarea
          className="test-case-workspace-field-textarea"
          value={formDesc}
          onChange={onFormChange('desc')}
          placeholder="Optional additional description..."
          rows={2}
          disabled={readOnly || isBusy}
        />
        {descError && (
          <div style={{
            marginTop: '8px',
            fontSize: '12px',
            color: '#da1e28',
          }}>
            {descError}
          </div>
        )}
      </div>
      {!readOnly && (
      <div style={{ display: 'flex', gap: '8px', marginTop: '20px' }}>
        <button
          className="test-case-workspace-secondary-btn"
          onClick={onSaveConfig}
          disabled={!configDirty || savingConfig || isBusy}
        >
          {savingConfig ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
      )}
    </div>
  );
}
