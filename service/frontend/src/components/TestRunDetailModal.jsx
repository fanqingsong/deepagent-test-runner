import React, { useState, useEffect } from 'react';
import { getTestRunDetails, saveAsRegression } from '../api';
import './TestRunDetailModal.css';
import './Modal.css';

function TestRunDetailModal({ run, onClose }) {
  const [testCases, setTestCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [screenshotUrl, setScreenshotUrl] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadTestCases();
  }, [run]);

  const loadTestCases = async () => {
    setLoading(true);
    setError(null);
    try {
      // Pass run.run_id (UUID string) instead of run.id (integer primary key)
      const cases = await getTestRunDetails(run.run_id);
      setTestCases(cases);
    } catch (err) {
      setError('加载测试用例失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const className = `status-badge ${status || 'running'}`;
    const label = {
      passed: '通过',
      failed: '失败',
      running: '运行中',
      skipped: '跳过'
    };
    return (
      <span className={className}>
        {label[status] || label.running}
      </span>
    );
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '-';
    // timestamp is in milliseconds
    const date = new Date(parseInt(timestamp));
    if (isNaN(date.getTime())) return '-';
    return date.toLocaleTimeString('zh-CN');
  };

  const handleSaveRegression = async () => {
    if (saving) return;
    setSaving(true);
    try {
      await saveAsRegression(run.test_definition_id, run.run_id);
      alert('已成功保存为回归测试');
      onClose();
    } catch (err) {
      alert('保存回归测试失败: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container test-run-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">测试运行详情</h2>
          <button className="modal-close-btn" onClick={onClose} aria-label="关闭">
            ✕
          </button>
        </div>

        <div className="modal-body">
          {/* Run Summary */}
          <div className="run-summary">
            <div className="summary-item">
              <span className="summary-label">测试名称：</span>
              <span className="summary-value">{run.test_name || '未知测试'}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">运行ID：</span>
              <span className="summary-value">{run.run_id}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">状态：</span>
              <span className="summary-value">{getStatusBadge(run.status)}</span>
            </div>
            {run.error_message && (
              <div className="summary-item full-width">
                <span className="summary-label">失败原因：</span>
                <span className="summary-value error-message-text">{run.error_message}</span>
              </div>
            )}
            <div className="summary-item">
              <span className="summary-label">执行时间：</span>
              <span className="summary-value">
                {new Date(run.created_at).toLocaleString('zh-CN')}
              </span>
            </div>
            {(run.total_tests > 0 || run.passed > 0 || run.failed > 0) && (
              <>
                <div className="summary-item">
                  <span className="summary-label">总测试数：</span>
                  <span className="summary-value">{run.total_tests || 0}</span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">通过：</span>
                  <span className="summary-value success">{run.passed || 0}</span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">失败：</span>
                  <span className="summary-value failure">{run.failed || 0}</span>
                </div>
                <div className="summary-item">
                  <span className="summary-label">跳过：</span>
                  <span className="summary-value skipped">{run.skipped || 0}</span>
                </div>
              </>
            )}
          </div>

          {/* Test Cases */}
          <div className="test-cases-section">
            <h3>测试用例详情</h3>

            {loading ? (
              <div className="loading-state">加载中...</div>
            ) : error ? (
              <div className="error-state">{error}</div>
            ) : testCases.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">⚠️</div>
                <p className="empty-title">暂无测试用例数据</p>
                {run.error_message && (
                  <div className="empty-error-details">
                    <strong>失败原因：</strong>
                    <div className="error-message-box">{run.error_message}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="test-cases-table-container">
                <table className="test-cases-table">
                  <thead>
                    <tr>
                      <th>测试ID</th>
                      <th>描述</th>
                      <th>状态</th>
                      <th>截图</th>
                      <th>执行时长</th>
                      <th>开始时间</th>
                      <th>结束时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {testCases.map((testCase, index) => (
                      <tr key={testCase.id || index}>
                        <td className="test-id-cell">{testCase.test_id}</td>
                        <td className="description-cell">
                          <div className="test-description">{testCase.description}</div>
                          {testCase.error_message && (
                            <div className="error-message">{testCase.error_message}</div>
                          )}
                        </td>
                        <td className="status-cell">
                          {getStatusBadge(testCase.status)}
                        </td>
                        <td className="screenshot-cell">
                          {testCase.screenshot_path ? (
                            <img
                              src={testCase.screenshot_path}
                              alt={`步骤 ${index + 1} 截图`}
                              className="screenshot-thumbnail"
                              onClick={() => setScreenshotUrl(testCase.screenshot_path)}
                            />
                          ) : (
                            <span className="no-screenshot">-</span>
                          )}
                        </td>
                        <td className="duration-cell">
                          {formatDuration(testCase.duration / 1000)}
                        </td>
                        <td className="time-cell">
                          {formatTimestamp(testCase.start_time)}
                        </td>
                        <td className="time-cell">
                          {formatTimestamp(testCase.end_time)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          {(run.status === 'passed' || run.status === 'completed') && (
            <button
              className="btn-primary"
              onClick={handleSaveRegression}
              disabled={saving}
              style={{
                background: 'var(--cds-button-primary)',
                color: 'var(--cds-text-on-color)',
                opacity: saving ? 0.7 : 1
              }}
            >
              {saving ? '保存中...' : '保存为回归测试'}
            </button>
          )}
          <button className="btn-secondary" onClick={onClose}>
            关闭
          </button>
        </div>

        {screenshotUrl && (
          <div className="screenshot-lightbox" onClick={() => setScreenshotUrl(null)}>
            <div className="screenshot-lightbox-content" onClick={(e) => e.stopPropagation()}>
              <button className="screenshot-lightbox-close" onClick={() => setScreenshotUrl(null)}>✕</button>
              <img src={screenshotUrl} alt="截图" className="screenshot-fullsize" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default TestRunDetailModal;
