import { useRef, useEffect } from 'react';
import './ScriptGenProgressPanel.css';

const ALL_STEPS = [
  'Fetching page context',
  'Generating script',
  'Validating script',
  'Executing in sandbox',
  'Saving result',
];

function StepIcon({ status }) {
  if (status === 'running') return <div className="sgen-spinner" />;
  if (status === 'done') return <span style={{ color: '#24a148' }}>&#10003;</span>;
  if (status === 'error') return <span style={{ color: '#da1e28' }}>&#10007;</span>;
  return <span style={{ color: '#c6c6c6' }}>&#9679;</span>;
}

function getStepStatus(stepName, currentStep, completedSteps) {
  const isCompleted = completedSteps.some(s => s.step === stepName && s.status === 'done');
  const isErrored = completedSteps.some(s => s.step === stepName && s.status === 'error');

  if (isCompleted) return 'done';
  if (isErrored) return 'error';
  if (currentStep === stepName) return 'running';
  if (currentStep && stepName === 'Generating script' && currentStep.startsWith('Generat')) return 'running';
  if (currentStep && stepName === 'Executing in sandbox' && currentStep.startsWith('Retry')) return 'done';
  return 'pending';
}

export default function ScriptGenProgressPanel({
  active,
  currentStep,
  completedSteps,
  streamingContent,
  toolCalls,
  generatedScript,
  error,
  isComplete,
  finalResult,
  progress,
  onCancel,
}) {
  const streamingRef = useRef(null);
  const scriptRef = useRef(null);

  useEffect(() => {
    if (streamingRef.current) {
      streamingRef.current.scrollTop = streamingRef.current.scrollHeight;
    }
  }, [streamingContent]);

  useEffect(() => {
    if (scriptRef.current) {
      scriptRef.current.scrollTop = scriptRef.current.scrollHeight;
    }
  }, [generatedScript]);

  const connectionClass = error ? 'error' : active ? '' : isComplete ? '' : 'idle';

  const visibleSteps = ALL_STEPS.filter(step => {
    if (step === 'Generating script') return true;
    const status = getStepStatus(step, currentStep, completedSteps);
    return status !== 'pending';
  });
  if (visibleSteps.length === 0) visibleSteps.push(ALL_STEPS[0]);

  const savedScript = finalResult?.playwright_script;
  const displayScript = savedScript || generatedScript;

  return (
    <div className="sgen-panel">
      {/* Header */}
      <div className="sgen-header">
        <div className={`sgen-connection-dot ${connectionClass}`} />
        <span className="sgen-title">
          {isComplete ? 'Generation complete' : active ? currentStep || 'Starting...' : 'Script Generation'}
        </span>
        <span className="sgen-progress-label">
          {completedSteps.length}/{ALL_STEPS.length} steps
        </span>
        {active && (
          <button className="sgen-cancel-btn" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>

      {/* Progress bar */}
      <div className="sgen-progress-bar">
        <div
          className="sgen-progress-fill"
          style={{ width: `${progress.percent}%` }}
        />
      </div>

      {/* Steps */}
      <div className="sgen-steps">
        {visibleSteps.map((step) => {
          const status = getStepStatus(step, currentStep, completedSteps);
          return (
            <div className={`sgen-step`} key={step}>
              <div className={`sgen-step-icon ${status}`}>
                <StepIcon status={status} />
              </div>
              <div className="sgen-step-body">
                <div className={`sgen-step-name ${status === 'running' ? 'active' : status === 'done' ? 'completed' : ''}`}>
                  {step}
                  {status === 'running' && currentStep?.startsWith('Retry') && ' (retry)'}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Generated script preview */}
      {displayScript && (
        <div className="sgen-script-section">
          <div className="sgen-script-header">
            Generated Script
            {savedScript && <span className="sgen-script-saved">saved</span>}
            {!savedScript && generatedScript && <span className="sgen-script-unsaved">not saved</span>}
          </div>
          <pre className="sgen-script-code" ref={scriptRef}>{displayScript}</pre>
        </div>
      )}

      {/* Streaming LLM thinking */}
      {streamingContent && (
        <details className="sgen-thinking-details">
          <summary className="sgen-thinking-summary">Agent thinking</summary>
          <div className="sgen-streaming">
            <div className="sgen-streaming-content" ref={streamingRef}>
              {streamingContent}
              {active && <span className="sgen-cursor" />}
            </div>
          </div>
        </details>
      )}

      {/* Tool calls */}
      {toolCalls.length > 0 && (
        <details className="sgen-thinking-details" open>
          <summary className="sgen-thinking-summary">Tool calls ({toolCalls.length})</summary>
          <div className="sgen-tool-calls">
            {toolCalls.map((tc, i) => (
              <div className="sgen-tool-call" key={i}>
                <span className={`sgen-tool-status ${tc.status}`}>{tc.status}</span>
                <span className="sgen-tool-name">{tc.tool}</span>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* Error */}
      {error && <div className="sgen-error">{error}</div>}

      {/* Completion */}
      {isComplete && (
        <div className={`sgen-complete ${!savedScript ? 'sgen-complete-partial' : ''}`}>
          {savedScript
            ? (finalResult.script_status === 'validated'
              ? 'Script validated and saved successfully'
              : finalResult.script_status === 'draft'
                ? 'Script saved as draft (execution had issues)'
                : `Script saved — ${finalResult.script_status}`)
            : generatedScript
              ? 'Script generated but could not be saved to database'
              : 'Generation completed with errors — no script produced'
          }
        </div>
      )}
    </div>
  );
}
