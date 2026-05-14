// DEPRECATED: Replaced by single textarea in TestForm.jsx
// This component is kept for backward compatibility but is no longer used.
// The new implementation uses a single textarea where users enter all steps (one per line).

function StepEditor({ steps, onChange }) {
  const addStep = () => {
    const newStep = {
      id: steps.length + 1,
      description: `Step ${steps.length + 1}: Enter action description here`
    };
    onChange([...steps, newStep]);
  };

  const updateStep = (index, value) => {
    const updatedSteps = [...steps];
    updatedSteps[index].description = value;
    onChange(updatedSteps);
  };

  const removeStep = (index) => {
    const updatedSteps = steps.filter((_, i) => i !== index);
    // Update id numbers
    updatedSteps.forEach((step, i) => step.id = i + 1);
    onChange(updatedSteps);
  };

  return (
    <div>
      <div style={{marginBottom: '12px', fontWeight: 'bold'}}>
        Test Steps ({steps.length})
      </div>

      {steps.map((step, index) => (
        <div
          key={index}
          style={{
            border: '1px solid #ddd',
            borderRadius: '4px',
            padding: '12px',
            marginBottom: '8px',
            background: '#fafafa'
          }}
        >
          <div style={{display: 'flex', alignItems: 'flex-start', gap: '8px'}}>
            <span style={{
              background: '#1976d2',
              color: 'white',
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              fontWeight: 'bold',
              flexShrink: 0
            }}>
              {step.id}
            </span>
            <textarea
              placeholder="Describe what to do in this step (e.g., 'Navigate to example.com', 'Click the login button', 'Enter username: admin')"
              value={step.description}
              onChange={(e) => updateStep(index, e.target.value)}
              rows={2}
              style={{
                flex: 1,
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                resize: 'vertical',
                fontSize: '14px'
              }}
            />
            <button
              onClick={() => removeStep(index)}
              style={{
                padding: '4px 8px',
                background: '#f44336',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px',
                flexShrink: 0
              }}
            >
              Remove
            </button>
          </div>
        </div>
      ))}

      <button
        onClick={addStep}
        style={{
          width: '100%',
          padding: '8px',
          background: '#2196f3',
          color: '#fff',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontWeight: 'bold'
        }}
      >
        + Add Step
      </button>
    </div>
  );
}

export default StepEditor;
