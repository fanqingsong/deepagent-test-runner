import { useState } from 'react';
import Modal from './Modal';

function PlanReviewModal({ testGoal, generatedPlan, onApprove, onModify, onRegenerate, onClose }) {
  const [modifications, setModifications] = useState([]);
  const [selectedStep, setSelectedStep] = useState(null);
  const [isRegenerating, setIsRegenerating] = useState(false);

  const handleApprove = () => {
    onApprove(modifications);
  };

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      await onRegenerate();
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleStepClick = (step) => {
    setSelectedStep(step);
  };

  const addModification = (stepNumber, field, value) => {
    setModifications(prev => {
      const existing = prev.findIndex(mod => mod.step_number === stepNumber);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = {
          ...updated[existing],
          [field]: value
        };
        return updated;
      } else {
        return [...prev, { step_number, [field]: value }];
      }
    });
  };

  if (!generatedPlan || !generatedPlan.steps) {
    return (
      <Modal isOpen={true} onClose={onClose} title="AI Plan Generation">
        <div style={{padding: 'var(--cds-spacing-lg)'}}>
          <p>Generating AI test plan...</p>
          <div style={{marginTop: 'var(--cds-spacing-lg)', textAlign: 'center'}}>
            <div style={{display: 'inline-block', padding: '20px', borderRadius: '50%', background: 'var(--cds-interactive-02)', animation: 'spin 1s linear infinite'}}>⚙️</div>
            <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal isOpen={true} onClose={onClose} title="Review AI-Generated Test Plan">
      <div style={{padding: 'var(--cds-spacing-lg)'}}>
        {/* User's Goal Section */}
        <div style={{marginBottom: 'var(--cds-spacing-xl)', padding: 'var(--cds-spacing-md)', background: 'var(--cds-background)', borderRadius: 'var(--cds-border-radius)'}}>
          <h3 style={{marginTop: 0, marginBottom: 'var(--cds-spacing-sm)', fontSize: 'var(--cds-heading-03)', fontWeight: 'var(--cds-font-weight-regular)'}}>
            🎯 Your Test Goal
          </h3>
          <p style={{margin: 0, fontSize: 'var(--cds-body-short-01)', lineHeight: '1.5'}}>
            {testGoal}
          </p>
        </div>

        {/* AI Generated Plan Section */}
        <div style={{marginBottom: 'var(--cds-spacing-xl)'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--cds-spacing-md)'}}>
            <h3 style={{marginTop: 0, fontSize: 'var(--cds-heading-03)', fontWeight: 'var(--cds-font-weight-regular)'}}>
              🤖 AI-Generated Test Plan
            </h3>
            <div style={{fontSize: 'var(--cds-caption-01)', color: 'var(--cds-text-secondary)'}}>
              {generatedPlan.steps?.length || 0} steps • ~{generatedPlan.estimated_duration || 60}s estimated
            </div>
          </div>

          {/* Plan Metadata */}
          {generatedPlan.risk_factors && generatedPlan.risk_factors.length > 0 && (
            <div style={{marginBottom: 'var(--cds-spacing-md)', padding: 'var(--cds-spacing-sm)', background: '#fff4e5', borderRadius: 'var(--cds-border-radius)', borderLeft: '3px solid var(--cds-support-warning)'}}>
              <div style={{fontSize: 'var(--cds-caption-01)', fontWeight: 'var(--cds-font-weight-semibold)'}}>
                ⚠️ Risk Factors: {generatedPlan.risk_factors.join(', ')}
              </div>
            </div>
          )}

          {generatedPlan.success_criteria && generatedPlan.success_criteria.length > 0 && (
            <div style={{marginBottom: 'var(--cds-spacing-md)', padding: 'var(--cds-spacing-sm)', background: '#defbe6', borderRadius: 'var(--cds-border-radius)', borderLeft: '3px solid var(--cds-support-success)'}}>
              <div style={{fontSize: 'var(--cds-caption-01)', fontWeight: 'var(--cds-font-weight-semibold)'}}>
                ✅ Success Criteria: {generatedPlan.success_criteria.join(', ')}
              </div>
            </div>
          )}

          {/* Test Steps */}
          <div style={{background: 'var(--cds-background)', borderRadius: 'var(--cds-border-radius)', overflow: 'hidden'}}>
            {generatedPlan.steps?.map((step, idx) => (
              <div
                key={idx}
                onClick={() => handleStepClick(step)}
                style={{
                  padding: 'var(--cds-spacing-md)',
                  borderBottom: idx < generatedPlan.steps.length - 1 ? '1px solid var(--cds-border-subtle)' : 'none',
                  cursor: 'pointer',
                  transition: 'background-color var(--cds-transition-fast)',
                  ':hover': { backgroundColor: 'var(--cds-hover-layer)' }
                }}
              >
                <div style={{display: 'flex', alignItems: 'flex-start', gap: 'var(--cds-spacing-md)'}}>
                  {/* Step Number */}
                  <div style={{
                    flexShrink: 0,
                    width: '32px',
                    height: '32px',
                    borderRadius: '50%',
                    background: 'var(--cds-interactive-01)',
                    color: 'var(--cds-text-on-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 'var(--cds-font-weight-semibold)',
                    fontSize: 'var(--cds-body-short-01)'
                  }}>
                    {step.step_number}
                  </div>

                  {/* Step Details */}
                  <div style={{flex: 1}}>
                    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 'var(--cds-spacing-xs)'}}>
                      <div style={{fontSize: 'var(--cds-body-short-01)', fontWeight: 'var(--cds-font-weight-semibold)'}}>
                        {step.description}
                      </div>
                      <div style={{
                        padding: '2px 8px',
                        borderRadius: 'var(--cds-border-radius-tag)',
                        background: step.confidence > 0.8 ? 'var(--cds-tag-green)' : step.confidence > 0.6 ? 'var(--cds-tag-yellow)' : 'var(--cds-tag-red)',
                        color: 'white',
                        fontSize: 'var(--cds-caption-01)',
                        fontWeight: 'var(--cds-font-weight-regular)'
                      }}>
                        {Math.round((step.confidence || 0.8) * 100)}% confidence
                      </div>
                    </div>

                    {step.verification && (
                      <div style={{fontSize: 'var(--cds-caption-01)', color: 'var(--cds-text-secondary)', marginTop: 'var(--cds-spacing-xs)'}}>
                        ✓ {step.verification}
                      </div>
                    )}

                    {step.fallback_strategies && step.fallback_strategies.length > 0 && (
                      <div style={{fontSize: 'var(--cds-caption-01)', color: 'var(--cds-text-secondary)', marginTop: 'var(--cds-spacing-xs)'}}>
                        🔄 Fallback: {step.fallback_strategies.join(', ')}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Selected Step Details */}
        {selectedStep && (
          <div style={{marginBottom: 'var(--cds-spacing-xl)', padding: 'var(--cds-spacing-md)', background: 'var(--cds-background)', borderRadius: 'var(--cds-border-radius)'}}>
            <h4 style={{marginTop: 0, marginBottom: 'var(--cds-spacing-sm)', fontSize: 'var(--cds-heading-04)', fontWeight: 'var(--cds-font-weight-regular)'}}>
              Edit Step {selectedStep.step_number}
            </h4>
            <div style={{display: 'flex', flexDirection: 'column', gap: 'var(--cds-spacing-sm)'}}>
              <div>
                <label style={{display: 'block', fontSize: 'var(--cds-caption-01)', marginBottom: 'var(--cds-spacing-xs)'}}>Description</label>
                <textarea
                  value={selectedStep.description}
                  onChange={(e) => {
                    const updated = { ...selectedStep, description: e.target.value };
                    setSelectedStep(updated);
                    addModification(selectedStep.step_number, 'description', e.target.value);
                  }}
                  rows={2}
                  style={{
                    width: '100%',
                    padding: 'var(--cds-spacing-sm)',
                    border: '1px solid var(--cds-border-subtle)',
                    borderRadius: 'var(--cds-border-radius)',
                    fontFamily: 'var(--cds-font-family)',
                    fontSize: 'var(--cds-body-short-01)'
                  }}
                />
              </div>
              <div>
                <label style={{display: 'block', fontSize: 'var(--cds-caption-01)', marginBottom: 'var(--cds-spacing-xs)'}}>Verification</label>
                <input
                  type="text"
                  value={selectedStep.verification || ''}
                  onChange={(e) => {
                    const updated = { ...selectedStep, verification: e.target.value };
                    setSelectedStep(updated);
                    addModification(selectedStep.step_number, 'verification', e.target.value);
                  }}
                  style={{
                    width: '100%',
                    padding: 'var(--cds-spacing-sm)',
                    border: '1px solid var(--cds-border-subtle)',
                    borderRadius: 'var(--cds-border-radius)',
                    fontFamily: 'var(--cds-font-family)',
                    fontSize: 'var(--cds-body-short-01)'
                  }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{display: 'flex', gap: 'var(--cds-spacing-sm)', marginTop: 'var(--cds-spacing-lg)'}}>
          <button
            onClick={handleApprove}
            disabled={isRegenerating}
            style={{
              flex: 1,
              padding: 'var(--cds-button-padding-sm)',
              background: isRegenerating ? 'var(--cds-interactive-02)' : 'var(--cds-button-primary)',
              color: 'var(--cds-text-on-color)',
              border: 'none',
              borderRadius: 'var(--cds-border-radius)',
              cursor: isRegenerating ? 'not-allowed' : 'pointer',
              fontWeight: 'var(--cds-font-weight-regular)',
              height: 'var(--cds-button-height)',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)',
              opacity: isRegenerating ? 0.6 : 1
            }}
          >
            {isRegenerating ? 'Processing...' : '✅ Approve & Execute'}
          </button>
          <button
            onClick={() => {
              setModifications([]);
              setSelectedStep(null);
              onModify(modifications);
            }}
            disabled={modifications.length === 0 || isRegenerating}
            style={{
              flex: 1,
              padding: 'var(--cds-button-padding-sm)',
              background: modifications.length > 0 ? 'var(--cds-button-primary)' : 'var(--cds-button-secondary)',
              color: 'var(--cds-text-on-color)',
              border: 'none',
              borderRadius: 'var(--cds-border-radius)',
              cursor: modifications.length > 0 && !isRegenerating ? 'pointer' : 'not-allowed',
              fontWeight: 'var(--cds-font-weight-regular)',
              height: 'var(--cds-button-height)',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)',
              opacity: (modifications.length === 0 || isRegenerating) ? 0.6 : 1
            }}
          >
            ✏️ Apply Modifications ({modifications.length})
          </button>
          <button
            onClick={handleRegenerate}
            disabled={isRegenerating}
            style={{
              flex: 1,
              padding: 'var(--cds-button-padding-sm)',
              background: 'var(--cds-button-secondary)',
              color: 'var(--cds-text-on-color)',
              border: 'none',
              borderRadius: 'var(--cds-border-radius)',
              cursor: isRegenerating ? 'not-allowed' : 'pointer',
              fontWeight: 'var(--cds-font-weight-regular)',
              height: 'var(--cds-button-height)',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)',
              opacity: isRegenerating ? 0.6 : 1
            }}
          >
            🔄 Regenerate Plan
          </button>
        </div>

        {/* Info Section */}
        <div style={{marginTop: 'var(--cds-spacing-md)', padding: 'var(--cds-spacing-md)', background: 'var(--cds-background)', borderRadius: 'var(--cds-border-radius)', fontSize: 'var(--cds-caption-01)', color: 'var(--cds-text-secondary)'}}>
          💡 <strong>Tip:</strong> Click on any step to edit it before approving. The AI will execute your approved plan with adaptive error recovery.
        </div>
      </div>
    </Modal>
  );
}

export default PlanReviewModal;