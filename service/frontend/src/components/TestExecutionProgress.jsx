import React, { useState, useEffect } from 'react';
import { useTestJobStatus } from '../hooks/useTestJobStatus';
import './TestExecutionProgress.css';

function TestExecutionProgress({ jobId, testInfo, onClose, onJobComplete }) {
  const { status, loading, error, isRunning, isCompleted } = useTestJobStatus(jobId);
  const [showDetails, setShowDetails] = useState(true);
  const [selectedStep, setSelectedStep] = useState(null);
  const [notifiedComplete, setNotifiedComplete] = useState(false);

  // Notify parent when job reaches a terminal state
  useEffect(() => {
    if (isCompleted && !notifiedComplete && status) {
      setNotifiedComplete(true);
      if (onJobComplete) {
        onJobComplete(status);
      }
    }
  }, [isCompleted, notifiedComplete, status, onJobComplete]);

  // 获取测试步骤数据
  const getTestSteps = () => {
    if (!status?.results?.test_runs) return [];

    const testRun = status.results.test_runs[0];
    if (!testRun?.test_cases) return [];

    return testRun.test_cases.map((testCase, index) => ({
      stepNumber: testCase.step_number || index + 1,
      description: testCase.description || `Step ${index + 1}`,
      status: testCase.status || 'pending',
      duration: testCase.duration || 0,
      screenshotPath: testCase.screenshot_path || null,
      verification: testCase.verification || null,
      error: testCase.error || null,
      details: testCase.details || ''
    }));
  };

  const testSteps = getTestSteps();

  const getStepStatus = (step) => {
    if (!step) return 'pending';
    return step.status;
  };

  const getStepIcon = (stepStatus) => {
    switch (stepStatus) {
      case 'passed': return '✅';
      case 'failed': return '❌';
      case 'running': return '🔄';
      case 'pending': return '⏳';
      default: return '❓';
    }
  };

  const getStepColor = (stepStatus) => {
    switch (stepStatus) {
      case 'passed': return '#4caf50';
      case 'failed': return '#f44336';
      case 'running': return '#ff9800';
      case 'pending': return '#9e9e9e';
      default: return '#666';
    }
  };

  const formatDuration = (ms) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const handleStepClick = (step) => {
    setSelectedStep(step);
  };

  return (
    <div className="test-execution-progress-overlay">
      <div className="test-execution-progress-modal">
        {/* Header */}
        <div className="progress-header">
          <div className="header-title">
            <h2>测试执行详情</h2>
            <div className="test-badge">{testInfo?.name || '未知测试'}</div>
          </div>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        {/* Status Overview */}
        <div className="status-overview">
          <div className="status-card">
            <div className="status-icon">
              {isRunning && '🔄'}
              {isCompleted && '✅'}
              {status?.status === 'failed' && '❌'}
              {!status && '⏳'}
            </div>
            <div className="status-info">
              <div className="status-title">
                {isRunning && '测试运行中'}
                {isCompleted && '测试完成'}
                {status?.status === 'failed' && '测试失败'}
                {!status && '初始化中...'}
              </div>
              <div className="status-message">
                {status?.message || '正在执行测试步骤...'}
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="progress-section">
            <div className="progress-header">
              <span>执行进度</span>
              <span className="progress-percentage">
                {Math.round((testSteps.filter(s => s.status === 'passed' || s.status === 'failed').length /
                Math.max(testSteps.length, 1)) * 100)}%
              </span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${(testSteps.filter(s => s.status === 'passed' || s.status === 'failed').length /
                    Math.max(testSteps.length, 1)) * 100}%`
                }}
              />
            </div>
            <div className="progress-stats">
              <span>总计: {testSteps.length} 步</span>
              <span>✅ 通过: {testSteps.filter(s => s.status === 'passed').length}</span>
              <span>❌ 失败: {testSteps.filter(s => s.status === 'failed').length}</span>
            </div>
          </div>
        </div>

        {/* Test Steps Timeline */}
        <div className="steps-section">
          <div className="steps-header">
            <h3>执行步骤</h3>
            <button
              className="toggle-button"
              onClick={() => setShowDetails(!showDetails)}
            >
              {showDetails ? '收起详情' : '展开详情'}
            </button>
          </div>

          <div className="steps-timeline">
            {testSteps.length === 0 ? (
              <div className="empty-state">
                {loading ? '正在加载测试步骤...' : '等待测试开始...'}
              </div>
            ) : (
              testSteps.map((step, index) => (
                <div
                  key={index}
                  className={`step-item ${getStepStatus(step)} ${selectedStep?.stepNumber === step.stepNumber ? 'selected' : ''}`}
                  onClick={() => handleStepClick(step)}
                >
                  <div className="step-marker">
                    <div className="step-icon">{getStepIcon(step.status)}</div>
                    {index < testSteps.length - 1 && <div className="step-line" />}
                  </div>

                  <div className="step-content">
                    <div className="step-header">
                      <span className="step-number">步骤 {step.stepNumber}</span>
                      <span className="step-duration">{formatDuration(step.duration)}</span>
                    </div>
                    <div className="step-description">{step.description}</div>

                    {showDetails && (
                      <div className="step-details">
                        {step.error && (
                          <div className="step-error">
                            <strong>错误:</strong> {step.error}
                          </div>
                        )}

                        {step.details && (
                          <div className="step-info">
                            <strong>详情:</strong> {step.details.substring(0, 200)}
                            {step.details.length > 200 && '...'}
                          </div>
                        )}

                        {step.screenshotPath && (
                          <div className="step-screenshot">
                            <strong>截图:</strong>
                            <a
                              href="#"
                              onClick={(e) => {
                                e.preventDefault();
                                handleStepClick(step);
                              }}
                              className="screenshot-link"
                            >
                              查看截图
                            </a>
                          </div>
                        )}

                        {step.verification && (
                          <div className="step-verification">
                            <strong>验证结果:</strong>
                            <div className="verification-status">
                              状态: {step.verification.verification_passed ? '✅ 通过' : '❌ 失败'}
                            </div>
                            {step.verification.assertions && step.verification.assertions.length > 0 && (
                              <div className="assertions-list">
                                {step.verification.assertions.map((assertion, idx) => (
                                  <div key={idx} className={`assertion ${assertion.passed ? 'passed' : 'failed'}`}>
                                    {assertion.passed ? '✅' : '❌'} {assertion.type}: {assertion.expected}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Step Detail Modal */}
        {selectedStep && (
          <div className="step-detail-modal" onClick={() => setSelectedStep(null)}>
            <div className="step-detail-content" onClick={(e) => e.stopPropagation()}>
              <div className="detail-header">
                <h3>步骤 {selectedStep.stepNumber} 详情</h3>
                <button onClick={() => setSelectedStep(null)}>×</button>
              </div>

              <div className="detail-body">
                {selectedStep.screenshotPath ? (
                  <div className="detail-screenshot">
                    <h4>执行截图</h4>
                    <img
                      src={`${window.location.origin}${selectedStep.screenshotPath}`}
                      alt={`Step ${selectedStep.stepNumber} screenshot`}
                      className="detail-image"
                      onError={(e) => {
                        console.error('Screenshot load error:', e);
                        e.target.style.display = 'none';
                        const errorDiv = document.createElement('div');
                        errorDiv.style.cssText = 'padding: 16px; background: #ffebee; border-radius: 8px; color: #c62828;';
                        errorDiv.textContent = `❌ 截图加载失败: ${selectedStep.screenshotPath}`;
                        e.target.parentElement.appendChild(errorDiv);
                      }}
                      onLoad={() => {
                        console.log('Screenshot loaded successfully:', selectedStep.screenshotPath);
                      }}
                    />
                  </div>
                ) : (
                  <div className="detail-screenshot">
                    <h4>执行截图</h4>
                    <div style={{
                      padding: '16px',
                      background: '#f8f9fa',
                      borderRadius: '8px',
                      textAlign: 'center',
                      color: '#666'
                    }}>
                      此步骤暂无截图
                    </div>
                  </div>
                )}

                <div className="detail-info">
                  <h4>步骤信息</h4>
                  <div className="info-row">
                    <strong>描述:</strong> {selectedStep.description}
                  </div>
                  <div className="info-row">
                    <strong>状态:</strong>
                    <span style={{ color: getStepColor(selectedStep.status) }}>
                      {getStepIcon(selectedStep.status)} {selectedStep.status}
                    </span>
                  </div>
                  <div className="info-row">
                    <strong>耗时:</strong> {formatDuration(selectedStep.duration)}
                  </div>

                  {selectedStep.error && (
                    <div className="info-row error">
                      <strong>错误:</strong> {selectedStep.error}
                    </div>
                  )}

                  {selectedStep.details && (
                    <div className="info-row">
                      <strong>执行详情:</strong> {selectedStep.details}
                    </div>
                  )}
                </div>

                {selectedStep.verification && (
                  <div className="detail-verification">
                    <h4>验证断言</h4>
                    {selectedStep.verification.assertions?.map((assertion, idx) => (
                      <div key={idx} className={`assertion-card ${assertion.passed ? 'passed' : 'failed'}`}>
                        <div className="assertion-header">
                          {assertion.passed ? '✅' : '❌'} {assertion.type}
                        </div>
                        <div className="assertion-body">
                          <div><strong>预期:</strong> {assertion.expected}</div>
                          <div><strong>实际:</strong> {assertion.actual}</div>
                          {assertion.evidence && (
                            <div><strong>证据:</strong> {assertion.evidence}</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="progress-footer">
          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}

          <div className="footer-actions">
            {isCompleted && (
              <button
                className="btn-primary"
                onClick={() => window.location.reload()}
              >
                查看完整结果
              </button>
            )}
            <button
              className="btn-secondary"
              onClick={onClose}
            >
              {isCompleted ? '关闭' : '在后台运行'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TestExecutionProgress;