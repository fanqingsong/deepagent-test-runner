import { useState, useEffect } from 'react';
import { getSuiteRunDetail } from '../../api';

const STATUS_MAP = {
  pending: { label: 'Pending', color: '#8d8d8d' },
  running: { label: 'Running', color: '#0f62fe' },
  completed: { label: 'Completed', color: '#42be65' },
  passed: { label: 'Passed', color: '#198038' },
  failed: { label: 'Failed', color: '#da1e28' },
  cancelled: { label: 'Cancelled', color: '#8d8d8d' },
  partial: { label: 'Partial', color: '#f1c21b' },
  skipped: { label: 'Skipped', color: '#8d8d8d' },
};

function StatusBadge({ status }) {
  const info = STATUS_MAP[status] || { label: status, color: '#8d8d8d' };
  return (
    <span style={{
      padding: '2px 8px',
      fontSize: '12px',
      border: `1px solid ${info.color}`,
      color: info.color,
    }}>
      {info.label}
    </span>
  );
}

function formatDuration(ms) {
  if (!ms) return '-';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function DetailPanel({ detail, onClose }) {
  if (!detail) return null;

  return (
    <>
      {/* Background overlay */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.3)',
          zIndex: 999,
        }}
      />
      {/* Side panel */}
      <div style={{
        position: 'fixed',
        top: 0, right: 0, bottom: 0,
        width: '520px',
        background: '#fff',
        borderLeft: '1px solid #e0e0e0',
        boxShadow: '-4px 0 12px rgba(0,0,0,0.08)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid #e0e0e0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: '#161616' }}>
              Run Details
            </h3>
            <span style={{ fontSize: '11px', color: '#8d8d8d', fontFamily: '"IBM Plex Mono", monospace' }}>
              {detail.run_id}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: '#f4f4f4',
              border: 'none',
              fontSize: '16px',
              cursor: 'pointer',
              color: '#161616',
              padding: '6px 12px',
              borderRadius: '0',
              fontWeight: 600,
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#e0e0e0'}
            onMouseLeave={(e) => e.currentTarget.style.background = '#f4f4f4'}
          >
            Close
          </button>
        </div>

      {/* Summary */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid #e0e0e0',
        display: 'flex',
        gap: '16px',
        fontSize: '13px',
        color: '#525252',
        flexShrink: 0,
        flexWrap: 'wrap',
      }}>
        <span><StatusBadge status={detail.status} /></span>
        <span>
          Passed <b style={{ color: '#198038' }}>{detail.passed}</b>
          {' / '}
          Failed <b style={{ color: '#da1e28' }}>{detail.failed}</b>
          {' / '}
          Skipped <b style={{ color: '#8d8d8d' }}>{detail.skipped}</b>
        </span>
        <span>Duration {formatDuration(detail.total_duration)}</span>
        <span>{detail.triggered_by}</span>
      </div>

      {/* Entry list */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <table className="composer-table" style={{ fontSize: '13px' }}>
          <thead>
            <tr>
              <th style={{ width: '32px', textAlign: 'center' }}>#</th>
              <th>Test Definition</th>
              <th style={{ width: '80px', textAlign: 'center' }}>Status</th>
              <th style={{ width: '72px', textAlign: 'right' }}>Duration</th>
            </tr>
          </thead>
          <tbody>
            {(detail.entries || []).map((entry) => (
              <tr key={entry.id}>
                <td style={{ textAlign: 'center', color: '#0f62fe', fontWeight: 600 }}>
                  {entry.entry_order}
                </td>
                <td>
                  <span style={{ color: '#0f62fe', fontWeight: 600, marginRight: '4px' }}>
                    #{entry.test_definition_id}
                  </span>
                  {entry.error_message && (
                    <div style={{ marginTop: '2px', fontSize: '11px', color: '#da1e28', lineHeight: '1.3' }}>
                      {entry.error_message}
                    </div>
                  )}
                </td>
                <td style={{ textAlign: 'center' }}>
                  <StatusBadge status={entry.status} />
                </td>
                <td style={{ textAlign: 'right', fontSize: '12px', color: '#525252' }}>
                  {formatDuration(entry.duration)}
                </td>
              </tr>
            ))}
            {(!detail.entries || detail.entries.length === 0) && (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', color: '#8d8d8d', padding: '16px' }}>
                  No entry records
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
    </>
  );
}

export default function SuiteRunHistoryTab({ runs, loading }) {
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const handleViewDetail = async (runId) => {
    setSelectedRunId(runId);
    setDetail(null);
    try {
      setDetailLoading(true);
      const data = await getSuiteRunDetail(runId);
      setDetail(data);
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedRunId(null);
    setDetail(null);
  };

  // ESC key to close detail panel
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && (selectedRunId || detailLoading)) {
        handleCloseDetail();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedRunId, detailLoading]);

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#525252', fontSize: '13px' }}>
        Loading run history...
      </div>
    );
  }

  if (!runs.length) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#8d8d8d', fontSize: '13px' }}>
        No run history
      </div>
    );
  }

  return (
    <>
      <div style={{ padding: '20px' }}>
        <table className="composer-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th style={{ width: '80px', textAlign: 'center' }}>Status</th>
                <th style={{ width: '120px', textAlign: 'center' }}>Passed/Failed/Skipped</th>
                <th style={{ width: '80px', textAlign: 'center' }}>Triggered By</th>
                <th style={{ width: '140px', textAlign: 'right' }}>Created At</th>
                <th style={{ width: '64px', textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr
                  key={run.id}
                  className={selectedRunId === run.run_id ? 'composer-table-row--active' : ''}
                >
                  <td style={{ fontFamily: '"IBM Plex Mono", monospace', fontSize: '12px' }}>
                    {run.run_id?.slice(0, 12)}...
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <StatusBadge status={run.status} />
                  </td>
                  <td style={{ textAlign: 'center', fontSize: '13px', color: '#525252' }}>
                    <span style={{ color: '#198038' }}>{run.passed}</span>
                    {' / '}
                    <span style={{ color: '#da1e28' }}>{run.failed}</span>
                    {' / '}
                    <span style={{ color: '#8d8d8d' }}>{run.skipped}</span>
                  </td>
                  <td style={{ textAlign: 'center', fontSize: '12px', color: '#525252' }}>
                    {run.triggered_by}
                  </td>
                  <td style={{ textAlign: 'right', fontSize: '12px', color: '#525252', whiteSpace: 'nowrap' }}>
                    {run.created_at ? new Date(run.created_at).toLocaleString() : '-'}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      style={{
                        background: 'none',
                        border: '1px solid #0f62fe',
                        color: '#0f62fe',
                        padding: '2px 8px',
                        fontSize: '11px',
                        cursor: 'pointer',
                        fontFamily: 'inherit',
                      }}
                      onClick={() => handleViewDetail(run.run_id)}
                    >
                      Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Detail side panel */}
      {(selectedRunId || detailLoading) && (
        <DetailPanel
          detail={detail}
          onClose={handleCloseDetail}
        />
      )}

      {/* Loading overlay for detail */}
      {detailLoading && (
        <div style={{
          position: 'fixed', top: 0, right: '520px', bottom: 0, width: '200px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#8d8d8d', fontSize: '13px', zIndex: 999,
        }}>
          Loading details...
        </div>
      )}
    </>
  );
}
