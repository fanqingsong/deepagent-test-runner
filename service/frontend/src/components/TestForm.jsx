import { useState, useEffect } from 'react';
import authService from '../services/authService';
import ConversationPanel from './ConversationPanel';

// Use environment variable or current origin (works in local, Docker, production)
const BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || window.location.origin;
const TEST_API = `${BASE_URL}/api/v1`;

const createTest = async (testData) => {
  try {
    // Generate test_id if not provided
    if (!testData.test_id || testData.test_id.trim() === '') {
      const timestamp = Date.now().toString(36);
      const random = Math.random().toString(36).substring(2, 8);
      testData.test_id = `test-${timestamp}-${random}`;
    }

    // Use new AI planning approach - send test_goal instead of steps
    const createPayload = {
      name: testData.name,
      description: testData.description,
      test_id: testData.test_id,
      url: testData.url,
      environment: testData.environment,
      tags: testData.tags,
      test_goal: testData.test_goal,  // Send natural language goal
      plan_generation_status: 'pending'
    };

    console.log('=== Creating Test with AI Planning ===');
    console.log('Payload:', createPayload);
    console.log('====================');

    const testResponse = await fetch(`${TEST_API}/test-definitions/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authService.getAccessToken()}`
      },
      body: JSON.stringify(createPayload),
      mode: 'cors'
    });

    if (!testResponse.ok) {
      const errorText = await testResponse.text();
      console.error('Failed to create test. Status:', testResponse.status);
      console.error('Error response:', errorText);
      throw new Error(`Failed to create test: ${testResponse.statusText} - ${errorText}`);
    }

    const test = await testResponse.json();
    console.log('Test created successfully:', test);
    return test;
  } catch (error) {
    console.error('Error creating test:', error);
    throw error;
  }
};

const updateTest = async (testId, testData) => {
  try {
    // Use test_id instead of numeric ID for PUT request
    const testIdString = testData.test_id || testId.toString();

    // Update test with AI planning approach
    const updatePayload = {
      name: testData.name,
      description: testData.description,
      test_id: testData.test_id,
      url: testData.url,
      environment: testData.environment,
      tags: testData.tags,
      test_goal: testData.test_goal  // Update natural language goal
    };

    console.log('=== Updating Test ===');
    console.log('Test ID:', testIdString);
    console.log('Update payload:', updatePayload);
    console.log('====================');

    const testResponse = await fetch(`${TEST_API}/test-definitions/${testIdString}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authService.getAccessToken()}`
      },
      body: JSON.stringify(updatePayload),
      mode: 'cors'
    });

    if (!testResponse.ok) {
      const errorText = await testResponse.text();
      console.error('Failed to update test. Status:', testResponse.status);
      console.error('Error response:', errorText);
      throw new Error(`Failed to update test: ${testResponse.statusText} - ${errorText}`);
    }

    const test = await testResponse.json();
    return test;
  } catch (error) {
    console.error('Error updating test:', error);
    throw error;
  }
};

function TestForm(props) {
  const { onTestCreated, editingTest, onCancel } = props;

  const getAuthHeadersSafe = () => {
    const token = typeof authService?.getAccessToken === 'function' ? authService.getAccessToken() : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    test_id: '',
    url: '',
    environment: {},
    tags: [],
    test_goal: ''  // Changed from test_steps_text to test_goal
  });

  const [envKey, setEnvKey] = useState('');
  const [envValue, setEnvValue] = useState('');
  const [tagInput, setTagInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [validationErrors, setValidationErrors] = useState({});

  // AI Conversation state
  const [showConversation, setShowConversation] = useState(false);
  const [createdTestId, setCreatedTestId] = useState(null);

  // Load test data when editing
  useEffect(() => {
    if (editingTest) {
      setFormData({
        name: editingTest.name || '',
        description: editingTest.description || '',
        test_id: editingTest.test_id || '',
        url: editingTest.url || '',
        environment: editingTest.environment || {},
        tags: editingTest.tags || [],
        test_goal: editingTest.test_goal || ''  // Load test_goal instead of steps
      });
    }
  }, [editingTest]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Clear previous errors
    setValidationErrors({});

    // Validation
    const errors = {};

    if (!formData.name.trim()) {
      errors.name = 'Test name is required';
    }

    if (!formData.url.trim()) {
      errors.url = 'URL is required';
    }

    // Validate that test goal is provided
    if (!formData.test_goal || formData.test_goal.trim().length === 0) {
      errors.test_goal = 'Test goal is required. Please describe what you want to test.';
    } else if (formData.test_goal.trim().length < 10) {
      errors.test_goal = 'Test goal is too short. Please provide more details (at least 10 characters).';
    }

    // If there are validation errors, display them and stop submission
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      return;
    }

    setSubmitting(true);
    try {
      if (editingTest) {
        // For editing, just update the test goal directly
        await updateTest(editingTest.id, formData);
        alert('Test updated successfully!');
        onTestCreated();
      } else {
        // For new tests, create test definition then show AI conversation button
        const test = await createTest(formData);

        // Store created test ID and show conversation button (not auto-open)
        setCreatedTestId(test.id);
        setShowConversation(false);

        alert('Test created successfully! Click "Start AI Conversation" to begin AI-powered test planning.');
      }
    } catch (error) {
      alert(`Failed to ${editingTest ? 'update' : 'create'} test: ` + error.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    }
  };

  const handleConversationApproved = (approvedPlan) => {
    setShowConversation(false);
    setCreatedTestId(null);

    // Reset form after successful conversation
    setFormData({
      name: '',
      description: '',
      test_id: '',
      url: '',
      environment: {},
      tags: [],
      test_goal: ''
    });

    onTestCreated();
  };

  const handleConversationClose = () => {
    setShowConversation(false);
    setCreatedTestId(null);
    onTestCreated();
  };


  const addEnvironmentVar = () => {
    if (!envKey.trim()) {
      alert('Key is required');
      return;
    }
    setFormData({
      ...formData,
      environment: { ...formData.environment, [envKey]: envValue }
    });
    setEnvKey('');
    setEnvValue('');
  };

  const removeEnvironmentVar = (keyToRemove) => {
    const newEnv = { ...formData.environment };
    delete newEnv[keyToRemove];
    setFormData({
      ...formData,
      environment: newEnv
    });
  };

  const addTag = () => {
    if (!tagInput.trim()) return;
    if (!formData.tags.includes(tagInput)) {
      setFormData({
        ...formData,
        tags: [...formData.tags, tagInput]
      });
    }
    setTagInput('');
  };

  const removeTag = (tagToRemove) => {
    setFormData({
      ...formData,
      tags: formData.tags.filter(t => t !== tagToRemove)
    });
  };

  return (
    <div style={{background: 'var(--cds-background)', borderRadius: 'var(--cds-border-radius)', padding: 'var(--cds-spacing-xl)'}}>
      <h2 style={{marginTop: 0, marginBottom: 'var(--cds-spacing-lg)', color: editingTest ? 'var(--cds-support-warning)' : 'var(--cds-support-success)', fontSize: 'var(--cds-heading-04)', fontWeight: 'var(--cds-font-weight-regular)'}}>
        {editingTest ? '✏️ Edit Test' : 'Create New Test'}
      </h2>

      <form onSubmit={handleSubmit}>
        <div style={{marginBottom: 'var(--cds-spacing-lg)'}}>
          <label style={{display: 'block', fontWeight: 'var(--cds-font-weight-regular)', marginBottom: 'var(--cds-spacing-xs)', fontSize: 'var(--cds-caption-01)', letterSpacing: 'var(--cds-letter-spacing-caption)'}}>
            Test Name <span style={{color: 'var(--cds-support-error)'}}>*</span>
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
            placeholder="e.g., User Registration Test"
            required
            style={{
              width: '100%',
              padding: '0 16px',
              border: validationErrors.name ? '2px solid var(--cds-support-error)' : 'none',
              borderBottom: validationErrors.name ? '2px solid var(--cds-support-error)' : '2px solid transparent',
              borderRadius: 'var(--cds-border-radius)',
              background: 'var(--cds-input-background)',
              height: 'var(--cds-input-height)',
              boxSizing: 'border-box',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)'
            }}
          />
          {validationErrors.name && (
            <div style={{color: 'var(--cds-support-error)', fontSize: 'var(--cds-label-01)', marginTop: 'var(--cds-spacing-xs)'}}>
              {validationErrors.name}
            </div>
          )}
        </div>

        <div style={{marginBottom: 'var(--cds-spacing-lg)'}}>
          <label style={{display: 'block', fontWeight: 'var(--cds-font-weight-regular)', marginBottom: 'var(--cds-spacing-xs)', fontSize: 'var(--cds-caption-01)', letterSpacing: 'var(--cds-letter-spacing-caption)'}}>
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
            placeholder="What does this test do?"
            rows={3}
            style={{
              width: '100%',
              padding: 'var(--cds-spacing-sm) 16px',
              border: 'none',
              borderBottom: '2px solid transparent',
              borderRadius: 'var(--cds-border-radius)',
              background: 'var(--cds-input-background)',
              boxSizing: 'border-box',
              resize: 'vertical',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)'
            }}
          />
        </div>

        <div style={{marginBottom: 'var(--cds-spacing-lg)'}}>
          <label style={{display: 'block', fontWeight: 'var(--cds-font-weight-regular)', marginBottom: 'var(--cds-spacing-xs)', fontSize: 'var(--cds-caption-01)', letterSpacing: 'var(--cds-letter-spacing-caption)'}}>
            Test ID
          </label>
          <input
            type="text"
            value={formData.test_id}
            onChange={(e) => setFormData({...formData, test_id: e.target.value})}
            placeholder="e.g., login-001"
            style={{
              width: '100%',
              padding: '0 16px',
              border: 'none',
              borderBottom: '2px solid transparent',
              borderRadius: 'var(--cds-border-radius)',
              background: 'var(--cds-input-background)',
              height: 'var(--cds-input-height)',
              boxSizing: 'border-box',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)'
            }}
          />
        </div>

        <div style={{marginBottom: 'var(--cds-spacing-lg)'}}>
          <label style={{display: 'block', fontWeight: 'var(--cds-font-weight-regular)', marginBottom: 'var(--cds-spacing-xs)', fontSize: 'var(--cds-caption-01)', letterSpacing: 'var(--cds-letter-spacing-caption)'}}>
            Test URL <span style={{color: 'var(--cds-support-error)'}}>*</span>
          </label>
          <input
            type="url"
            value={formData.url}
            onChange={(e) => setFormData({...formData, url: e.target.value})}
            placeholder="https://example.com/login"
            required
            style={{
              width: '100%',
              padding: '0 16px',
              border: validationErrors.url ? '2px solid var(--cds-support-error)' : 'none',
              borderBottom: validationErrors.url ? '2px solid var(--cds-support-error)' : '2px solid transparent',
              borderRadius: 'var(--cds-border-radius)',
              background: 'var(--cds-input-background)',
              height: 'var(--cds-input-height)',
              boxSizing: 'border-box',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)'
            }}
          />
          {validationErrors.url && (
            <div style={{color: 'var(--cds-support-error)', fontSize: 'var(--cds-label-01)', marginTop: 'var(--cds-spacing-xs)'}}>
              {validationErrors.url}
            </div>
          )}
        </div>

        <div style={{marginBottom: 'var(--cds-spacing-lg)'}}>
          <label style={{display: 'block', fontWeight: 'var(--cds-font-weight-regular)', marginBottom: 'var(--cds-spacing-xs)', fontSize: 'var(--cds-caption-01)', letterSpacing: 'var(--cds-letter-spacing-caption)'}}>
            Environment Variables
          </label>
          <div style={{display: 'flex', gap: 'var(--cds-spacing-sm)', marginBottom: 'var(--cds-spacing-sm)'}}>
            <input
              type="text"
              value={envKey}
              onChange={(e) => setEnvKey(e.target.value)}
              placeholder="KEY"
              style={{
                flex: 1,
                padding: '0 16px',
                border: 'none',
                borderBottom: '2px solid transparent',
                borderRadius: 'var(--cds-border-radius)',
                background: 'var(--cds-input-background)',
                height: 'var(--cds-input-height)',
                fontSize: 'var(--cds-body-short-01)',
                fontFamily: 'var(--cds-font-family)'
              }}
            />
            <input
              type="text"
              value={envValue}
              onChange={(e) => setEnvValue(e.target.value)}
              placeholder="value"
              style={{
                flex: 1,
                padding: '0 16px',
                border: 'none',
                borderBottom: '2px solid transparent',
                borderRadius: 'var(--cds-border-radius)',
                background: 'var(--cds-input-background)',
                height: 'var(--cds-input-height)',
                fontSize: 'var(--cds-body-short-01)',
                fontFamily: 'var(--cds-font-family)'
              }}
            />
            <button
              type="button"
              onClick={addEnvironmentVar}
              style={{
                padding: 'var(--cds-spacing-sm) var(--cds-spacing-md)',
                background: 'var(--cds-button-secondary)',
                color: 'var(--cds-text-on-color)',
                border: 'none',
                borderRadius: 'var(--cds-border-radius)',
                cursor: 'pointer',
                height: 'var(--cds-input-height)',
                fontSize: 'var(--cds-body-short-01)',
                fontFamily: 'var(--cds-font-family)'
              }}
            >
              +
            </button>
          </div>
          {Object.entries(formData.environment).map(([key, value]) => (
            <div key={key} style={{
              fontSize: 'var(--cds-caption-01)',
              color: 'var(--cds-text-secondary)',
              marginBottom: 'var(--cds-spacing-xs)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--cds-spacing-xs)'
            }}>
              <span>{key} = {value}</span>
              <button
                type="button"
                onClick={() => removeEnvironmentVar(key)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--cds-support-error)',
                  cursor: 'pointer',
                  fontSize: 'var(--cds-body-short-01)'
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>

        <div style={{marginBottom: 'var(--cds-spacing-lg)'}}>
          <label style={{display: 'block', fontWeight: 'var(--cds-font-weight-regular)', marginBottom: 'var(--cds-spacing-xs)', fontSize: 'var(--cds-caption-01)', letterSpacing: 'var(--cds-letter-spacing-caption)'}}>
            Tags
          </label>
          <div style={{display: 'flex', gap: 'var(--cds-spacing-sm)', marginBottom: 'var(--cds-spacing-sm)'}}>
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              placeholder="Add tag"
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
              style={{
                flex: 1,
                padding: '0 16px',
                border: 'none',
                borderBottom: '2px solid transparent',
                borderRadius: 'var(--cds-border-radius)',
                background: 'var(--cds-input-background)',
                height: 'var(--cds-input-height)',
                fontSize: 'var(--cds-body-short-01)',
                fontFamily: 'var(--cds-font-family)'
              }}
            />
          </div>
          <div>
            {formData.tags.map(tag => (
              <span
                key={tag}
                style={{
                  display: 'inline-block',
                  fontSize: 'var(--cds-caption-01)',
                  background: 'var(--cds-tag-blue)',
                  color: 'var(--cds-tag-blue-text)',
                  padding: 'var(--cds-spacing-xs) var(--cds-spacing-sm)',
                  borderRadius: 'var(--cds-border-radius-tag)',
                  marginRight: 'var(--cds-spacing-xs)',
                  marginBottom: 'var(--cds-spacing-xs)'
                }}
              >
                {tag}
                <button
                  type="button"
                  onClick={() => removeTag(tag)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--cds-support-error)',
                    cursor: 'pointer',
                    marginLeft: 'var(--cds-spacing-xs)',
                    fontSize: 'var(--cds-body-short-01)'
                  }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>

        <div style={{marginBottom: 'var(--cds-spacing-lg)'}}>
          <label style={{display: 'block', fontWeight: 'var(--cds-font-weight-regular)', marginBottom: 'var(--cds-spacing-xs)', fontSize: 'var(--cds-caption-01)', letterSpacing: 'var(--cds-letter-spacing-caption)'}}>
            Test Goal / Requirements <span style={{color: 'var(--cds-support-error)'}}>*</span>
          </label>
          <textarea
            value={formData.test_goal}
            onChange={(e) => setFormData({...formData, test_goal: e.target.value})}
            placeholder="Describe what you want to test in natural language...

Example: I want to test the user login flow. Verify that users can successfully log in with valid credentials and cannot log in with invalid credentials. Also check that the 'Remember Me' feature works correctly and that the password reset functionality is accessible from the login page."
            rows={8}
            required
            style={{
              width: '100%',
              padding: 'var(--cds-spacing-sm) 16px',
              border: validationErrors.test_goal ? '2px solid var(--cds-support-error)' : 'none',
              borderBottom: validationErrors.test_goal ? '2px solid var(--cds-support-error)' : '2px solid transparent',
              borderRadius: 'var(--cds-border-radius)',
              background: 'var(--cds-input-background)',
              boxSizing: 'border-box',
              resize: 'vertical',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)',
              lineHeight: '1.5'
            }}
          />
          {validationErrors.test_goal && (
            <div style={{color: 'var(--cds-support-error)', fontSize: 'var(--cds-label-01)', marginTop: 'var(--cds-spacing-xs)'}}>
              {validationErrors.test_goal}
            </div>
          )}
          <div style={{fontSize: 'var(--cds-caption-01)', color: 'var(--cds-text-secondary)', marginTop: 'var(--cds-spacing-xs)'}}>
            💡 AI will analyze your goal and generate an optimal test plan automatically. Be specific about what you want to test.
          </div>
        </div>

        <div style={{display: 'flex', gap: 'var(--cds-spacing-sm)', marginTop: 'var(--cds-spacing-lg)'}}>
          <button
            type="submit"
            disabled={submitting}
            style={{
              flex: 1,
              padding: 'var(--cds-button-padding-sm)',
              background: submitting ? 'var(--cds-interactive-02)' : (editingTest ? 'var(--cds-support-warning)' : 'var(--cds-support-success)'),
              color: 'var(--cds-text-on-color)',
              border: 'none',
              borderRadius: 'var(--cds-border-radius)',
              cursor: submitting ? 'not-allowed' : 'pointer',
              fontWeight: 'var(--cds-font-weight-regular)',
              height: 'var(--cds-button-height)',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)'
            }}
          >
            {submitting ? (editingTest ? 'Updating...' : 'Creating...') : (editingTest ? 'Update Test' : 'Create Test')}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            style={{
              flex: 1,
              padding: 'var(--cds-button-padding-sm)',
              background: 'var(--cds-button-secondary)',
              color: 'var(--cds-text-on-color)',
              border: 'none',
              borderRadius: 'var(--cds-border-radius)',
              cursor: 'pointer',
              height: 'var(--cds-button-height)',
              fontSize: 'var(--cds-body-short-01)',
              fontFamily: 'var(--cds-font-family)'
            }}
          >
            {editingTest ? 'Cancel' : 'Clear'}
          </button>
        </div>

        {/* Show AI Conversation button for newly created tests */}
        {createdTestId && !showConversation && (
          <div style={{marginTop: 'var(--cds-spacing-md)', textAlign: 'center'}}>
            <button
              type="button"
              onClick={() => setShowConversation(true)}
              style={{
                width: '100%',
                padding: 'var(--cds-button-padding-sm)',
                background: '#0f62fe',
                color: '#ffffff',
                border: '2px solid #0f62fe',
                borderRadius: 'var(--cds-border-radius)',
                cursor: 'pointer',
                fontWeight: 'var(--cds-font-weight-regular)',
                height: 'var(--cds-button-height)',
                fontSize: 'var(--cds-body-short-01)',
                fontFamily: 'var(--cds-font-family)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--cds-spacing-sm)'
              }}
            >
              🤖 Start AI Conversation
            </button>
            <p style={{fontSize: 'var(--cds-caption-01)', color: 'var(--cds-text-secondary)', marginTop: 'var(--cds-spacing-xs)'}}>
              Test created successfully! Click to start AI-powered test planning conversation.
            </p>
          </div>
        )}
      </form>

      {/* AI Conversation Panel for multi-turn test planning */}
      {showConversation && createdTestId && (
        <ConversationPanel
          isOpen={showConversation}
          onClose={handleConversationClose}
          testDefinitionId={createdTestId}
          testGoal={formData.test_goal}
          url={formData.url}
          onApproved={handleConversationApproved}
        />
      )}
    </div>
  );
}

export default TestForm;