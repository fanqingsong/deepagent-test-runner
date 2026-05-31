import { useState, useEffect, useRef } from 'react';

/**
 * Live browser stream component via WebSocket.
 * Connects to /ws/browser-stream/{jobId} and renders real-time browser screenshots.
 */
function BrowserStream({ jobId, isRunning, progressSteps, onSelectScreenshot }) {
  const [frame, setFrame] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const frameCountRef = useRef(0);
  const jobIdRef = useRef(jobId);
  const isRunningRef = useRef(isRunning);

  // Keep refs in sync
  jobIdRef.current = jobId;
  isRunningRef.current = isRunning;

  useEffect(() => {
    if (!isRunning || !jobId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/browser-stream/${jobId}`;

    let alive = true;

    function doConnect() {
      if (!alive) return;
      if (!isRunningRef.current || !jobIdRef.current) return;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (alive) setConnected(true);
      };

      ws.onmessage = (event) => {
        if (!alive) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'frame') {
            frameCountRef.current += 1;
            setFrame({
              path: data.path + '?t=' + frameCountRef.current,
              url: data.url,
              title: data.title,
              timestamp: data.timestamp,
            });
          } else if (data.type === 'end') {
            ws.close();
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!alive) return;
        setConnected(false);
        wsRef.current = null;
        if (isRunningRef.current) {
          reconnectTimerRef.current = setTimeout(doConnect, 2000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    doConnect();

    return () => {
      alive = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
    };
  }, [isRunning, jobId]);

  // Reset frame when not running
  useEffect(() => {
    if (!isRunning) {
      setFrame(null);
      frameCountRef.current = 0;
    }
  }, [isRunning]);

  const stepsWithScreenshots = (progressSteps || []).filter(s => s.screenshot_path);

  return (
    <div className="browser-preview" style={{ position: 'relative' }}>
      {/* Debug info - remove after testing */}
      <div style={{
        position: 'absolute', top: 0, right: 0, zIndex: 999,
        background: '#333', color: '#0f0', padding: '4px 8px',
        fontSize: '11px', fontFamily: 'monospace', borderRadius: '0 0 0 4px',
      }}>
        WS:{connected ? 'ON' : 'OFF'} JOB:{jobId || 'none'} RUN:{isRunning ? 'Y' : 'N'}
      </div>
      <div className="browser-preview-chrome">
        <div className="browser-preview-dots">
          <span className="browser-preview-dot"></span>
          <span className="browser-preview-dot"></span>
          <span className="browser-preview-dot"></span>
        </div>
        <div className="browser-preview-url-bar">
          {frame?.url || 'about:blank'}
          <span className="browser-stream-status" style={{
            marginLeft: '8px',
            fontSize: '11px',
            padding: '2px 6px',
            borderRadius: '2px',
            background: connected ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)',
            color: connected ? '#16a34a' : '#dc2626',
          }}>
            {connected ? 'LIVE' : 'CONNECTING...'}
          </span>
        </div>
      </div>

      <div className="browser-preview-viewport">
        {frame?.path ? (
          <img
            src={frame.path}
            alt="Live browser state"
            className="browser-preview-screenshot"
            style={{ width: '100%', display: 'block' }}
          />
        ) : (
          <div className="browser-preview-placeholder">
            {isRunning ? 'Waiting for browser stream...' : 'No active browser session'}
          </div>
        )}
      </div>

      <div className="browser-preview-status">
        {frame?.title && (
          <span className="browser-preview-title">{frame.title}</span>
        )}
      </div>

      {stepsWithScreenshots.length > 0 && (
        <div className="browser-preview-thumbnails">
          {stepsWithScreenshots.map((step, i) => (
            <button
              key={i}
              className={`browser-preview-thumb ${
                step.screenshot_path === frame?.path?.split('?')[0] ? 'browser-preview-thumb--active' : ''
              }`}
              onClick={() => onSelectScreenshot && onSelectScreenshot(step.screenshot_path)}
              title={`Step ${step.step_number}: ${step.description}`}
            >
              <img src={step.screenshot_path} alt={`Step ${step.step_number}`} />
              <span className={`browser-preview-thumb-badge step-${step.status}`}>
                {step.step_number}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default BrowserStream;
