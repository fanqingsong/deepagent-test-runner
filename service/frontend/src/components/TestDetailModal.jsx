import { useState, useEffect } from 'react';
import authService from '../services/authService';
import { getJobStatus } from '../api';

function TestDetailModal({ test, onClose, onViewRunHistory }) {
  const [loading, setLoading] = useState(true);
  const [testDetails, setTestDetails] = useState(null);
  const [error, setError] = useState(null);

  const getAuthHeadersSafe = () => {
    const token = typeof authService?.getAccessToken === 'function' ? authService.getAccessToken() : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  useEffect(() => {
    fetchTestDetails();
  }, [test.id]);

  const fetchTestDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/test-steps/test-definition/${test.id}`, {
        headers: getAuthHeadersSafe()
      });
      if (!response.ok) {
        throw new Error('Failed to fetch test details');
      }
      const steps = await response.json();
      setTestDetails({
        ...test,
        steps: steps
      });
    } catch (err) {
      setError('Failed to load test details: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStepTypeLabel = (stepType) => {
    const labels = {
      'navigate': '🌐 导航',
      'click': '🖱️ 点击',
      'fill': '✏️ 填写',
      'wait': '⏰ 等待',
      'screenshot': '📸 截图',
      'assert': '✅ 断言'
    };
    return labels[stepType] || stepType;
  };

  // Format steps for cleaner display (single-textarea style)
  const formatStepsForDisplay = (steps) => {
    return steps.map((step, index) => {
      const desc = step.description || `${step.type} ${step.params?.selector || ''} ${step.params?.value || ''}`.trim();
      return `${index + 1}. ${desc}`;
    }).join('\n');
  };

  // Copy test steps to clipboard
  const copyStepsToClipboard = () => {
    if (!testDetails || !testDetails.steps) return;

    let copyText = `📋 测试用例: ${testDetails.name}\n`;
    copyText += `🔗 URL: ${testDetails.url || 'N/A'}\n`;
    copyText += `🆔 Test ID: ${testDetails.test_id || 'N/A'}\n`;

    if (testDetails.description) {
      copyText += `📝 描述: ${testDetails.description}\n`;
    }

    copyText += `\n✨ 测试步骤 (${testDetails.steps.length}):\n\n`;
    copyText += formatStepsForDisplay(testDetails.steps);

    navigator.clipboard.writeText(copyText).then(() => {
      alert('✅ 测试步骤已复制到剪贴板！');
    }).catch(err => {
      console.error('Failed to copy:', err);
      alert('❌ 复制失败，请手动复制');
    });
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        background: 'white',
        borderRadius: '8px',
        width: '90%',
        maxWidth: '800px',
        maxHeight: '80vh',
        overflow: 'auto',
        padding: '24px',
        position: 'relative'
      }}>
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: 'none',
            border: 'none',
            fontSize: '24px',
            cursor: 'pointer',
            color: '#666'
          }}
        >
          ×
        </button>

        <h2 style={{marginTop: 0, color: '#1976d2'}}>测试用例详情</h2>

        {loading ? (
          <div style={{textAlign: 'center', padding: '40px'}}>
            <div style={{color: '#666'}}>加载中...</div>
          </div>
        ) : error ? (
          <div style={{color: 'red', padding: '20px', background: '#ffebee', borderRadius: '4px'}}>
            {error}
          </div>
        ) : testDetails ? (
          <div>
            <div style={{marginBottom: '24px', paddingBottom: '16px', borderBottom: '1px solid #eee'}}>
              <h3 style={{marginTop: 0, marginBottom: '8px'}}>{testDetails.name}</h3>
              {testDetails.description && (
                <p style={{color: '#666', marginTop: 0}}>{testDetails.description}</p>
              )}
              <div style={{fontSize: '13px', color: '#666', marginTop: '8px'}}>
                <strong>Test ID:</strong> {testDetails.test_id || 'N/A'}<br/>
                <strong>URL:</strong> {testDetails.url || 'N/A'}<br/>
                {testDetails.tags && testDetails.tags.length > 0 && (
                  <><strong>标签:</strong> {testDetails.tags.join(', ')} </>
                )}
              </div>
            </div>

            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px'}}>
              <h3 style={{marginTop: 0, marginBottom: '0'}}>测试步骤 ({testDetails.steps?.length || 0})</h3>
              {testDetails.steps && testDetails.steps.length > 0 && (
                <button
                  onClick={copyStepsToClipboard}
                  style={{
                    padding: '4px 12px',
                    background: '#4caf50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  title="复制测试步骤到剪贴板"
                >
                  📋 复制步骤
                </button>
              )}
            </div>

            {testDetails.steps && testDetails.steps.length > 0 ? (
              <div style={{
                background: '#f9f9f9',
                borderRadius: '6px',
                padding: '16px',
                border: '1px solid #e0e0e0'
              }}>
                <pre style={{
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  wordWrap: 'break-word',
                  fontFamily: 'var(--cds-font-family)',
                  fontSize: 'var(--cds-body-short-01)',
                  lineHeight: '1.6',
                  color: '#333'
                }}>
                  {formatStepsForDisplay(testDetails.steps)}
                </pre>
              </div>
            ) : (
              <div style={{
                background: '#fff3cd',
                border: '1px solid #ffc107',
                borderRadius: '4px',
                padding: '16px',
                textAlign: 'center',
                color: '#856404'
              }}>
                ⚠️ 此测试用例没有定义任何步骤
              </div>
            )}

            <div style={{marginTop: '24px', display: 'flex', gap: '12px', justifyContent: 'flex-end'}}>
              <button
                onClick={() => onViewRunHistory(test)}
                style={{
                  padding: '8px 16px',
                  background: '#2196f3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                📊 查看运行记录
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default TestDetailModal;
