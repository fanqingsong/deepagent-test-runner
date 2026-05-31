const STATUS_MAP = {
  draft: { label: 'Draft', color: '#a8a8a8' },
  generating: { label: 'Generating', color: '#0f62fe' },
  testing: { label: 'Testing', color: '#0f62fe' },
  passed: { label: 'Passed', color: '#198038' },
  published: { label: 'Published', color: '#6929c4' },
  archived: { label: 'Archived', color: '#6f6f6f' },
};

export default function StudioCard({ studio, onArchive }) {
  const st = STATUS_MAP[studio.status] || { label: studio.status, color: '#6f6f6f' };
  const result = studio.latest_result || {};
  const hasResult = result.status === 'passed' || result.status === 'failed';

  const handleClick = () => {
    if (studio.status !== 'archived') {
      window.location.hash = `studio/${studio.id}`;
    }
  };

  return (
    <div className="studio-card" onClick={handleClick}>
      <div className="studio-card-header">
        <div className="studio-card-icon" style={{ background: studio.color || '#0f62fe' }}>
          <span>{(studio.name || '?')[0].toUpperCase()}</span>
        </div>
        <div className="studio-card-info">
          <h3 className="studio-card-name">{studio.name}</h3>
          {studio.url && <span className="studio-card-url">{studio.url}</span>}
        </div>
      </div>
      <div className="studio-card-body">
        {studio.test_goal && (
          <p className="studio-card-goal">{studio.test_goal.length > 80 ? studio.test_goal.slice(0, 80) + '...' : studio.test_goal}</p>
        )}
      </div>
      <div className="studio-card-footer">
        <span className="studio-card-status" style={{ color: st.color, borderColor: st.color }}>
          {st.label}
        </span>
        {hasResult && (
          <span className="studio-card-result">
            {result.passed}/{result.total} passed
          </span>
        )}
        {studio.iteration_count > 0 && (
          <span className="studio-card-iterations">v{studio.iteration_count}</span>
        )}
      </div>
    </div>
  );
}
