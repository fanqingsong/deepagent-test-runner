import { useState, useEffect, useCallback } from 'react';
import { generateScript, getScript, updateScript, validateScript, approveScript } from '../../api';

const STATUS_LABELS = {
  none: 'None',
  generating: 'Generating...',
  draft: 'Draft',
  validated: 'Validated',
  approved: 'Approved',
  failed: 'Failed',
};

const STATUS_COLORS = {
  none: '#a0a0a0',
  generating: '#f0ab00',
  draft: '#8a3ffc',
  validated: '#42be65',
  approved: '#0f62fe',
  failed: '#da1e28',
};

export default function TestCaseScriptTab({ testCaseId }) {
  const [script, setScript] = useState('');
  const [scriptStatus, setScriptStatus] = useState('none');
  const [scriptMetadata, setScriptMetadata] = useState({});
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState(null);
  const [dirty, setDirty] = useState(false);

  const loadScript = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getScript(testCaseId);
      setScript(data.playwright_script || '');
      setScriptStatus(data.script_status || 'none');
      setScriptMetadata(data.script_metadata || {});
      setDirty(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [testCaseId]);

  useEffect(() => {
    loadScript();
  }, [loadScript]);

  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      const data = await generateScript(testCaseId, { force_regenerate: scriptStatus !== 'none' });
      setScript(data.playwright_script || '');
      setScriptStatus(data.script_status || 'none');
      setScriptMetadata(data.script_metadata || {});
      setDirty(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await updateScript(testCaseId, script);
      setScriptStatus(data.script_status || 'none');
      setDirty(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    try {
      setValidating(true);
      setError(null);
      const data = await validateScript(testCaseId);
      setScriptStatus(data.script_status || 'none');
      setScriptMetadata(data.script_metadata || {});
    } catch (e) {
      setError(e.message);
    } finally {
      setValidating(false);
    }
  };

  const handleApprove = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await approveScript(testCaseId);
      setScriptStatus(data.script_status || 'none');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const statusColor = STATUS_COLORS[scriptStatus] || '#a0a0a0';

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <span style={{
          padding: '4px 12px',
          background: statusColor + '20',
          color: statusColor,
          fontSize: '12px',
          fontWeight: 600,
          letterSpacing: '0.5px',
          textTransform: 'uppercase',
        }}>
          {STATUS_LABELS[scriptStatus] || scriptStatus}
        </span>

        {scriptMetadata.attempts && (
          <span style={{ fontSize: '12px', color: '#6f6f6f' }}>
            Attempts: {scriptMetadata.attempts}
          </span>
        )}

        <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
          <button
            onClick={handleGenerate}
            disabled={generating || loading}
            style={{
              padding: '6px 16px',
              background: '#0f62fe',
              color: '#fff',
              border: 'none',
              fontSize: '13px',
              fontWeight: 400,
              cursor: generating ? 'wait' : 'pointer',
              opacity: generating ? 0.6 : 1,
            }}
          >
            {generating ? 'Generating...' : (scriptStatus === 'none' ? 'Generate Script' : 'Regenerate')}
          </button>

          {script && dirty && (
            <button
              onClick={handleSave}
              disabled={loading}
              style={{
                padding: '6px 16px',
                background: '#393939',
                color: '#fff',
                border: 'none',
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              Save
            </button>
          )}

          {script && scriptStatus === 'draft' && (
            <button
              onClick={handleValidate}
              disabled={validating}
              style={{
                padding: '6px 16px',
                background: '#697077',
                color: '#fff',
                border: 'none',
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              {validating ? 'Validating...' : 'Validate'}
            </button>
          )}

          {scriptStatus === 'validated' && (
            <button
              onClick={handleApprove}
              disabled={loading}
              style={{
                padding: '6px 16px',
                background: '#42be65',
                color: '#fff',
                border: 'none',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Approve for Regression
            </button>
          )}
        </div>
      </div>

      {error && (
        <div style={{ padding: '8px 12px', background: '#fff1f1', color: '#da1e28', fontSize: '13px' }}>
          {error}
        </div>
      )}

      {scriptMetadata.last_error && scriptStatus !== 'validated' && (
        <div style={{ padding: '8px 12px', background: '#fff8e1', color: '#8a6914', fontSize: '13px' }}>
          Last error: {scriptMetadata.last_error}
        </div>
      )}

      {loading && !script ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#6f6f6f' }}>
          Loading...
        </div>
      ) : (
        <textarea
          value={script}
          onChange={(e) => { setScript(e.target.value); setDirty(true); }}
          placeholder={scriptStatus === 'none' ? 'Click "Generate Script" to create a Playwright test script...' : 'No script generated yet'}
          spellCheck={false}
          style={{
            width: '100%',
            minHeight: '400px',
            padding: '16px',
            fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
            fontSize: '13px',
            lineHeight: '1.6',
            background: '#161616',
            color: '#f4f4f4',
            border: '1px solid #393939',
            resize: 'vertical',
            outline: 'none',
            tabIndex: 0,
          }}
        />
      )}
    </div>
  );
}
