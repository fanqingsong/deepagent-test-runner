export default function BrowserPreview({ latestScreenshot, browserUrl, browserTitle, progressSteps, onSelectScreenshot }) {
  const stepsWithScreenshots = progressSteps.filter(s => s.screenshot_path);

  return (
    <div className="browser-preview">
      <div className="browser-preview-chrome">
        <div className="browser-preview-dots">
          <span className="browser-preview-dot"></span>
          <span className="browser-preview-dot"></span>
          <span className="browser-preview-dot"></span>
        </div>
        <div className="browser-preview-url-bar">
          {browserUrl || 'about:blank'}
        </div>
      </div>

      <div className="browser-preview-viewport">
        {latestScreenshot ? (
          <img
            src={latestScreenshot}
            alt="Latest browser state"
            className="browser-preview-screenshot"
          />
        ) : (
          <div className="browser-preview-placeholder">
            Waiting for first screenshot...
          </div>
        )}
      </div>

      <div className="browser-preview-status">
        {browserTitle && (
          <span className="browser-preview-title">{browserTitle}</span>
        )}
      </div>

      {stepsWithScreenshots.length > 0 && (
        <div className="browser-preview-thumbnails">
          {stepsWithScreenshots.map((step, i) => (
            <button
              key={i}
              className={`browser-preview-thumb ${
                step.screenshot_path === latestScreenshot ? 'browser-preview-thumb--active' : ''
              }`}
              onClick={() => onSelectScreenshot(step.screenshot_path)}
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
