import { useState, useEffect } from 'react';
import { getJobs, getJobStatus } from '../api';

function RunHistoryModal({ test, onClose }) {
  const [loading, setLoading] = useState(true);
  const [jobs, setJobs] = useState([]);
  const [error, setError] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobDetails, setJobDetails] = useState(null);

  useEffect(() => {
    fetchRunHistory();
  }, [test.id]);

  const fetchRunHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const allJobs = await getJobs();
      // Filter jobs that include this test definition
      const testJobs = allJobs.filter(job =>
        job.test_definition_ids && job.test_definition_ids.includes(test.id)
      );
      setJobs(testJobs);
    } catch (err) {
      setError('Failed to load run history: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewJobDetails = async (jobId) => {
    try {
      const details = await getJobStatus(jobId);
      setJobDetails(details);
      setSelectedJob(jobId);
    } catch (err) {
      alert('Failed to load job details: ' + err.message);
    }
  };

  const copyResultsToClipboard = (format = 'text') => {
    if (!jobDetails || !jobDetails.results) return;

    const testRuns = jobDetails.results.test_runs || [];

    if (format === 'json') {
      // Copy as JSON format - exact structure requested by user
      const jsonData = {
        test_runs: testRuns.map(run => ({
          run_id: run.run_id,
          test_definition_id: run.test_definition_id,
          start_time: run.start_time,
          end_time: run.end_time,
          total_duration: run.total_duration || run.duration,
          total_tests: run.total_tests,
          passed: run.passed,
          failed: run.failed,
          skipped: run.skipped || 0,
          status: run.status,
          test_cases: run.test_cases || run.test_steps || []
        }))
      };

      const jsonText = JSON.stringify(jsonData, null, 2);

      navigator.clipboard.writeText(jsonText).then(() => {
        alert('✅ JSON格式测试结果已复制到剪贴板！');
      }).catch(err => {
        console.error('Failed to copy:', err);
        alert('❌ 复制失败，请手动复制');
      });
    } else {
      // Copy as formatted text
      let copyText = `📊 测试运行结果 - ${test.name}\n`;
      copyText += `🕐 时间: ${formatDate(jobDetails.created_at)}\n`;
      copyText += `📈 状态: ${getStatusText(jobDetails.status)}\n`;
      copyText += `\n`;

      testRuns.forEach((run, index) => {
        copyText += `${index + 1}. 测试用例 #${run.test_definition_id || 'N/A'}\n`;
        copyText += `   状态: ${run.status === 'passed' ? '✅ 通过' : '❌ 失败'}\n`;

        if (run.error) {
          copyText += `   错误: ${run.error}\n`;
        }

        if (run.total_tests !== undefined) {
          copyText += `   统计: 总计 ${run.total_tests} | 通过 ${run.passed} | 失败 ${run.failed}\n`;
        }

        if (run.duration || run.total_duration) {
          copyText += `   耗时: ${Math.round(run.duration || run.total_duration)}ms\n`;
        }

        // Copy test cases details if available
        if (run.test_cases && run.test_cases.length > 0) {
          copyText += `   测试步骤:\n`;
          run.test_cases.forEach((testCase, idx) => {
            copyText += `     ${idx + 1}. ${testCase.description}\n`;
            copyText += `        状态: ${testCase.status}\n`;
            if (testCase.error) {
              copyText += `        错误: ${testCase.error}\n`;
            }
            if (testCase.duration) {
              copyText += `        耗时: ${testCase.duration}ms\n`;
            }
          });
        }

        copyText += `\n`;
      });

      // Copy to clipboard
      navigator.clipboard.writeText(copyText).then(() => {
        alert('✅ 测试结果已复制到剪贴板！');
      }).catch(err => {
        console.error('Failed to copy:', err);
        alert('❌ 复制失败，请手动复制');
      });
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      'completed': '#4caf50',
      'running': '#ff9800',
      'pending': '#2196f3',
      'failed': '#f44336',
      'cancelled': '#9e9e9e'
    };
    return colors[status] || '#9e9e9e';
  };

  const getStatusText = (status) => {
    const texts = {
      'completed': '已完成',
      'running': '运行中',
      'pending': '等待中',
      'failed': '失败',
      'cancelled': '已取消'
    };
    return texts[status] || status;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('zh-CN');
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
        maxWidth: '900px',
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

        <h2 style={{marginTop: 0, color: '#1976d2'}}>运行记录 - {test.name}</h2>

        {loading ? (
          <div style={{textAlign: 'center', padding: '40px'}}>
            <div style={{color: '#666'}}>加载中...</div>
          </div>
        ) : error ? (
          <div style={{color: 'red', padding: '20px', background: '#ffebee', borderRadius: '4px'}}>
            {error}
          </div>
        ) : jobs.length === 0 ? (
          <div style={{
            background: '#e3f2fd',
            border: '1px solid #2196f3',
            borderRadius: '4px',
            padding: '20px',
            textAlign: 'center',
            color: '#1976d2'
          }}>
            📊 此测试用例还没有运行记录
          </div>
        ) : (
          <div>
            <div style={{marginBottom: '16px'}}>
              <strong>共 {jobs.length} 条运行记录</strong>
            </div>

            <table style={{width: '100%', borderCollapse: 'collapse'}}>
              <thead>
                <tr style={{background: '#f5f5f5'}}>
                  <th style={{padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd'}}>Job ID</th>
                  <th style={{padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd'}}>状态</th>
                  <th style={{padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd'}}>创建时间</th>
                  <th style={{padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd'}}>进度</th>
                  <th style={{padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd'}}>操作</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.job_id} style={{borderBottom: '1px solid #eee'}}>
                    <td style={{padding: '12px', fontFamily: 'monospace', fontSize: '12px'}}>
                      {job.job_id.substring(0, 8)}...
                    </td>
                    <td style={{padding: '12px'}}>
                      <span style={{
                        padding: '4px 8px',
                        borderRadius: '4px',
                        background: getStatusColor(job.status),
                        color: 'white',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}>
                        {getStatusText(job.status)}
                      </span>
                    </td>
                    <td style={{padding: '12px', fontSize: '13px'}}>
                      {formatDate(job.created_at)}
                    </td>
                    <td style={{padding: '12px', fontSize: '13px'}}>
                      {job.progress !== undefined ? `${Math.round(job.progress * 100)}%` : 'N/A'}
                    </td>
                    <td style={{padding: '12px'}}>
                      <button
                        onClick={() => handleViewJobDetails(job.job_id)}
                        style={{
                          padding: '4px 8px',
                          background: '#2196f3',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                      >
                        查看详情
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {selectedJob && jobDetails && (
              <div style={{
                marginTop: '24px',
                padding: '16px',
                background: '#f9f9f9',
                borderRadius: '6px',
                borderTop: '2px solid #2196f3'
              }}>
                <h3 style={{marginTop: 0, marginBottom: '12px'}}>运行详情</h3>
                <div style={{fontSize: '13px', marginBottom: '8px'}}>
                  <strong>状态:</strong> {getStatusText(jobDetails.status)}<br/>
                  <strong>进度:</strong> {jobDetails.message || `${Math.round(jobDetails.progress * 100)}%`}<br/>
                  <strong>开始时间:</strong> {formatDate(jobDetails.started_at)}<br/>
                  <strong>完成时间:</strong> {formatDate(jobDetails.completed_at)}
                </div>

                {jobDetails.results && jobDetails.results.test_runs && jobDetails.results.test_runs.length > 0 && (
                  <div style={{marginTop: '12px'}}>
                    <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px'}}>
                      <strong>测试结果:</strong>
                      <div style={{display: 'flex', gap: '8px'}}>
                        <button
                          onClick={() => copyResultsToClipboard('text')}
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
                          title="复制格式化文本到剪贴板"
                        >
                          📋 复制文本
                        </button>
                        <button
                          onClick={() => copyResultsToClipboard('json')}
                          style={{
                            padding: '4px 12px',
                            background: '#2196f3',
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
                          title="复制JSON格式到剪贴板"
                        >
                          { } 复制JSON
                        </button>
                      </div>
                    </div>
                    {jobDetails.results.test_runs.map((run, index) => (
                      <div key={index} style={{
                        padding: '8px',
                        marginTop: '8px',
                        background: run.status === 'passed' ? '#e8f5e9' : '#ffebee',
                        borderRadius: '4px',
                        fontSize: '12px'
                      }}>
                        <strong>状态:</strong> {run.status === 'passed' ? '✅ 通过' : '❌ 失败'}
                        {run.error && <div><strong>错误:</strong> {run.error}</div>}
                        {run.total_tests !== undefined && (
                          <div>
                            <strong>用例数:</strong> {run.total_tests} |
                            <strong> 通过:</strong> {run.passed} |
                            <strong> 失败:</strong> {run.failed}
                          </div>
                        )}
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
  );
}

export default RunHistoryModal;
