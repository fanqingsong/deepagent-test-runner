import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import authService from '../services/authService';
import TestExecutionProgress from './TestExecutionProgress';
import TestDetailModal from './TestDetailModal';
import RunHistoryModal from './RunHistoryModal';
import FailureRecoveryPanel from './FailureRecoveryPanel';
import './TestList.css';

function TestList({ tests, onRunTest, onEditTest }) {
  const { isAdmin } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTag, setSelectedTag] = useState(null);
  const [showRegression, setShowRegression] = useState(false);
  const [runningJob, setRunningJob] = useState(null);
  const [detailTest, setDetailTest] = useState(null);
  const [historyTest, setHistoryTest] = useState(null);
  const [showFailurePanel, setShowFailurePanel] = useState(false);
  const [failedRunId, setFailedRunId] = useState(null);
  const [failedTestDefId, setFailedTestDefId] = useState(null);

  const getAuthHeadersSafe = () => {
    const token = typeof authService?.getAccessToken === 'function' ? authService.getAccessToken() : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const filteredTests = tests.filter(test => {
    const matchesSearch = test.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (test.description && test.description.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesTag = !selectedTag || (test.tags && test.tags.includes(selectedTag));
    const matchesRegression = !showRegression || test.is_regression === true || (test.tags && test.tags.includes('regression'));
    return matchesSearch && matchesTag && matchesRegression;
  });

  const allTags = [...new Set(tests.flatMap(t => t.tags || []))];

  const handleTestRun = async (testId) => {
    try {
      console.log('Starting test with ID:', testId);

      if (!testId) {
        alert('测试ID无效，无法启动测试');
        return null;
      }

      const numericTestId = parseInt(testId);
      if (isNaN(numericTestId)) {
        alert('测试ID格式无效');
        return null;
      }

      const requestData = { test_definition_ids: [numericTestId] };

      const response = await fetch(`${window.location.origin}/api/v1/jobs/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...getAuthHeadersSafe()
        },
        mode: 'cors',
        body: JSON.stringify(requestData)
      });

      if (response.ok) {
        const job = await response.json();
        const test = tests.find(t => t.id === testId);

        // 显示运行状态模态框
        setRunningJob({
          jobId: job.job_id,
          testInfo: { name: test?.name || 'Unknown', id: testId }
        });

        return job;
      } else {
        const errorText = await response.text();
        alert(`启动测试失败: ${response.status} ${response.statusText}\n详情: ${errorText}`);
        return null;
      }
    } catch (err) {
      alert('启动测试时出错: ' + err.message);
      return null;
    }
  };

  const handleCloseModal = () => {
    setRunningJob(null);
  };

  // Called by TestExecutionProgress when the job reaches a terminal state
  const handleJobComplete = (jobStatus) => {
    if (jobStatus.status === 'failed') {
      const runId = jobStatus.results?.test_runs?.[0]?.id
        || jobStatus.results?.run_id
        || jobStatus.run_id
        || null;
      const testDefId = runningJob?.testInfo?.id || null;

      setFailedRunId(runId);
      setFailedTestDefId(testDefId);
      setShowFailurePanel(true);
    }
  };

  // Called after the user clicks Retry inside FailureRecoveryPanel
  const handleRetryFromFailure = () => {
    setShowFailurePanel(false);
    setFailedRunId(null);
    setFailedTestDefId(null);
    // Close the execution progress modal since we are re-running
    setRunningJob(null);
  };

  const handleCloseFailurePanel = () => {
    setShowFailurePanel(false);
    setFailedRunId(null);
    setFailedTestDefId(null);
  };

  const handleViewDetails = (test) => {
    setDetailTest(test);
  };

  const handleViewRunHistory = (test) => {
    setHistoryTest(test);
  };

  return (
    <div className="test-list">
      <h2 className="list-title">测试用例 ({tests.length})</h2>

      {/* Role-based messaging */}
      {isAdmin && (
        <div style={{
          fontSize: '13px',
          color: '#666',
          marginBottom: '16px',
          padding: '8px 12px',
          background: '#e3f2fd',
          borderRadius: '4px',
          borderLeft: '3px solid #2196f3'
        }}>
          👑 管理员模式 - 显示所有用户的测试用例
        </div>
      )}

      <div className="list-controls">
        <input
          type="text"
          className="search-input"
          placeholder="搜索测试用例..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />

        <div className="list-controls-actions">
          <button
            className={`regression-toggle-btn ${showRegression ? 'active' : ''}`}
            onClick={() => setShowRegression(!showRegression)}
          >
            {showRegression ? '显示全部测试' : '仅显示回归测试'}
          </button>
        </div>

        {allTags.length > 0 && (
          <div className="tag-filters">
            <button
              className={`tag-filter-btn ${!selectedTag ? 'active' : ''}`}
              onClick={() => setSelectedTag(null)}
            >
              全部
            </button>
            {allTags.map(tag => (
              <button
                key={tag}
                className={`tag-filter-btn ${selectedTag === tag ? 'active' : ''}`}
                onClick={() => setSelectedTag(tag)}
              >
                {tag}
              </button>
            ))}
          </div>
        )}
      </div>

      {filteredTests.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🧪</div>
          <p className="empty-title">没有找到测试用例</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="test-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>描述</th>
                <th>标签</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredTests.map((test, index) => {
                if (!test.id) {
                  console.warn('Test missing id:', test);
                  return null;
                }
                return (
                  <tr key={test.id} className="test-row">
                    <td className="name-cell">
                      <div className="test-name">{test.name}</div>
                    </td>
                    <td className="description-cell">
                      <div className="test-description">
                        {test.description || '无描述'}
                      </div>
                    </td>
                    <td className="tags-cell">
                      <div className="test-tags">
                        {test.tags && test.tags.length > 0 ? (
                          test.tags.map(tag => (
                            <span key={tag} className="tag-badge">{tag}</span>
                          ))
                        ) : (
                          <span className="no-tags">无标签</span>
                        )}
                      </div>
                    </td>
                    <td className="actions-cell">
                      <div className="action-buttons">
                        <button
                          onClick={() => handleTestRun(test.id)}
                          className="action-btn run-btn"
                          title="立即执行"
                          aria-label="立即执行测试"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8 5v14l11-7z"/>
                          </svg>
                        </button>
                        <button
                          onClick={() => handleViewDetails(test)}
                          className="action-btn detail-btn"
                          title="查看详情"
                          aria-label="查看测试详情"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3z"/>
                          </svg>
                        </button>
                        <button
                          onClick={() => handleViewRunHistory(test)}
                          className="action-btn history-btn"
                          title="运行历史"
                          aria-label="查看运行历史"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L13 5v8zm5 0v-6h-3v6h5V8h-5V5h-3v6h5z"/>
                          </svg>
                        </button>
                        <button
                          onClick={() => onEditTest(test)}
                          className="action-btn edit-btn"
                          title="编辑"
                          aria-label="编辑测试"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Test Execution Progress Modal */}
      {runningJob && (
        <TestExecutionProgress
          jobId={runningJob.jobId}
          testInfo={runningJob.testInfo}
          onClose={handleCloseModal}
          onJobComplete={handleJobComplete}
        />
      )}

      {/* Test Detail Modal */}
      {detailTest && (
        <TestDetailModal
          test={detailTest}
          onClose={() => setDetailTest(null)}
          onViewRunHistory={handleViewRunHistory}
        />
      )}

      {/* Run History Modal */}
      {historyTest && (
        <RunHistoryModal
          test={historyTest}
          onClose={() => setHistoryTest(null)}
        />
      )}

      {/* Failure Recovery Panel */}
      <FailureRecoveryPanel
        isOpen={showFailurePanel}
        onClose={handleCloseFailurePanel}
        runId={failedRunId}
        testDefinitionId={failedTestDefId}
        onRetry={handleRetryFromFailure}
      />
    </div>
  );
}

export default TestList;
