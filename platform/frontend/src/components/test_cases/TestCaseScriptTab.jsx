import { useState, useEffect, useCallback, useRef } from 'react';
import { getScript, updateScript, validateScript, approveScript, runTestCase, getTestCaseRunHistory } from '../../api';
import useScriptGenerationStream from '../../hooks/useScriptGenerationStream';
import ScriptGenProgressPanel from './ScriptGenProgressPanel';

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

export default function TestCaseScriptTab({ testCaseId, appId, onRunComplete, readOnly }) {
  const [script, setScript] = useState('');
  const [scriptStatus, setScriptStatus] = useState('none');
  const [scriptMetadata, setScriptMetadata] = useState({});
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [runElapsed, setRunElapsed] = useState(0);
  const pollingRef = useRef(null);
  const timerRef = useRef(null);

  const stream = useScriptGenerationStream(testCaseId);

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

  // Sync stream result back to local state when generation completes
  useEffect(() => {
    if (stream.isComplete) {
      const r = stream.finalResult;
      // Prefer DB result, fall back to script extracted from tool args
      const finalScript = r?.playwright_script || stream.generatedScript || '';
      const finalStatus = r?.script_status || (finalScript ? 'draft' : 'failed');
      if (finalScript) {
        setScript(finalScript);
        setScriptStatus(finalStatus);
        setScriptMetadata(r?.script_metadata || {});
        setDirty(false);
      } else {
        setScriptStatus(finalStatus);
      }
    }
  }, [stream.isComplete, stream.finalResult, stream.generatedScript]);

  const handleGenerate = async () => {
    setError(null);
    setScriptStatus('generating');
    try {
      await stream.generate({ force_regenerate: scriptStatus !== 'none' });
    } catch (e) {
      setError(e.message);
      setScriptStatus('none');
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

  const handleRun = async () => {
    try {
      setIsRunning(true);
      setRunElapsed(0);
      setError(null);
      const result = await runTestCase(appId);
      const runId = result.run_id;

      // Start elapsed timer
      const startTime = Date.now();
      timerRef.current = setInterval(() => setRunElapsed(Math.floor((Date.now() - startTime) / 1000)), 1000);

      // Poll test_runs table for completion
      let attempts = 0;
      const poll = async () => {
        try {
          const runs = await getTestCaseRunHistory(appId, { limit: 1 });
          const latest = runs?.[0];
          if (latest && latest.run_id === runId && latest.status !== 'running' && latest.status !== 'pending') {
            cleanup();
            if (latest.status === 'error' || latest.status === 'failed') {
              setError(latest.error_message || `Test ${latest.status}`);
            }
            onRunComplete?.();
            return;
          }
          attempts++;
          if (attempts >= 90) { // 3 min timeout
            cleanup();
            setError('Execution timed out');
          }
        } catch {
          attempts++;
          if (attempts >= 90) {
            cleanup();
            setError('Execution timed out');
          }
        }
      };
      pollingRef.current = setInterval(poll, 2000);
    } catch (e) {
      setError(e.message);
      setIsRunning(false);
    }
  };

  const cleanup = () => {
    setIsRunning(false);
    setRunElapsed(0);
    if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
  };

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const statusColor = STATUS_COLORS[scriptStatus] || '#a0a0a0';
  const generating = stream.active;

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
          {!readOnly && (
          <button
            onClick={handleGenerate}
            disabled={generating || loading || isRunning}
            style={{
              padding: '6px 16px',
              background: '#0f62fe',
              color: '#fff',
              border: 'none',
              fontSize: '13px',
              fontWeight: 400,
              cursor: generating || isRunning ? 'wait' : 'pointer',
              opacity: generating || isRunning ? 0.6 : 1,
            }}
          >
            {generating ? 'Generating...' : (scriptStatus === 'none' ? 'Generate Script' : 'Regenerate')}
          </button>
          )}

          {!readOnly && script && dirty && (
            <button
              onClick={handleSave}
              disabled={loading || isRunning}
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

          {!readOnly && script && scriptStatus === 'draft' && (
            <button
              onClick={handleValidate}
              disabled={validating || isRunning}
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

          {!readOnly && scriptStatus === 'validated' && (
            <button
              onClick={handleApprove}
              disabled={loading || isRunning}
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

          {(scriptStatus === 'approved' || isRunning) && (
            <button
              onClick={handleRun}
              disabled={isRunning}
              style={{
                padding: '6px 16px',
                background: '#0f62fe',
                color: '#fff',
                border: 'none',
                fontSize: '13px',
                fontWeight: 600,
                cursor: isRunning ? 'wait' : 'pointer',
                opacity: isRunning ? 0.7 : 1,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              {isRunning ? (
                <>
                  <span className="test-case-workspace-typing"><span></span><span></span><span></span></span>
                  Running... {runElapsed}s
                </>
              ) : 'Run Test'}
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
      ) : stream.active || (!stream.isComplete && stream.currentStep) ? (
        <ScriptGenProgressPanel
          active={stream.active}
          currentStep={stream.currentStep}
          completedSteps={stream.completedSteps}
          streamingContent={stream.streamingContent}
          toolCalls={stream.toolCalls}
          generatedScript={stream.generatedScript}
          error={stream.error}
          isComplete={stream.isComplete}
          finalResult={stream.finalResult}
          progress={stream.progress}
          onCancel={stream.cancel}
        />
      ) : (
        <textarea
          value={script}
          onChange={(e) => { setScript(e.target.value); setDirty(true); }}
          placeholder={scriptStatus === 'none' ? 'Click "Generate Script" to create a Playwright test script...' : 'No script generated yet'}
          spellCheck={false}
          disabled={readOnly}
          style={{
            width: '100%',
            minHeight: '400px',
            padding: '16px',
            fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
            fontSize: '13px',
            lineHeight: '1.6',
            background: readOnly ? '#262626' : '#161616',
            color: readOnly ? '#8d8d8d' : '#f4f4f4',
            border: '1px solid #393939',
            resize: readOnly ? 'none' : 'vertical',
            outline: 'none',
            tabIndex: readOnly ? -1 : 0,
          }}
        />
      )}
    </div>
  );
}
