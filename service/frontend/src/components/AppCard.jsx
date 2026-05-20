const STATUS_MAP = {
  draft: { label: '草稿', color: '#a8a8a8' },
  generating: { label: '生成中', color: '#0f62fe' },
  testing: { label: '测试中', color: '#0f62fe' },
  passed: { label: '已通过', color: '#198038' },
  published: { label: '已发布', color: '#6929c4' },
  archived: { label: '已归档', color: '#6f6f6f' },
};

export default function AppCard({ app, onArchive }) {
  const st = STATUS_MAP[app.status] || { label: app.status, color: '#6f6f6f' };
  const result = app.latest_result || {};
  const hasResult = result.status === 'passed' || result.status === 'failed';

  const handleClick = () => {
    if (app.status !== 'archived') {
      window.location.hash = `app/${app.id}`;
    }
  };

  return (
    <div className="app-card" onClick={handleClick}>
      <div className="app-card-header">
        <div className="app-card-icon" style={{ background: app.color || '#0f62fe' }}>
          <span>{(app.name || '?')[0].toUpperCase()}</span>
        </div>
        <div className="app-card-info">
          <h3 className="app-card-name">{app.name}</h3>
          {app.url && <span className="app-card-url">{app.url}</span>}
        </div>
      </div>
      <div className="app-card-body">
        {app.test_goal && (
          <p className="app-card-goal">{app.test_goal.length > 80 ? app.test_goal.slice(0, 80) + '...' : app.test_goal}</p>
        )}
      </div>
      <div className="app-card-footer">
        <span className="app-card-status" style={{ color: st.color, borderColor: st.color }}>
          {st.label}
        </span>
        {hasResult && (
          <span className="app-card-result">
            {result.passed}/{result.total} passed
          </span>
        )}
        {app.iteration_count > 0 && (
          <span className="app-card-iterations">v{app.iteration_count}</span>
        )}
      </div>
    </div>
  );
}
