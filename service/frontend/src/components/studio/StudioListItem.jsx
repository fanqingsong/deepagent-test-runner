import PermissionGate from '../PermissionGate';

const STATUS_COLORS = {
  draft: '#a8a8a8',
  generating: '#0f62fe',
  testing: '#0f62fe',
  passed: '#198038',
  published: '#6929c4',
  archived: '#6f6f6f',
};

export default function StudioListItem({ studio, isSelected, onSelect, onArchive }) {
  const statusColor = STATUS_COLORS[studio.status] || '#6f6f6f';

  const handleClick = (e) => {
    e.stopPropagation();
    if (studio.status !== 'archived') {
      onSelect(studio.id);
    }
  };

  const handleArchive = (e) => {
    e.stopPropagation();
    onArchive(studio.id);
  };

  return (
    <div
      className={`studio-list-item ${isSelected ? 'studio-list-item--active' : ''}`}
      onClick={handleClick}
    >
      <div className="studio-list-item-color" style={{ background: studio.color || '#0f62fe' }}>
        {(studio.name || '?')[0].toUpperCase()}
      </div>
      <div className="studio-list-item-content">
        <div className="studio-list-item-name">{studio.name}</div>
        {studio.url && (
          <div className="studio-list-item-url">{studio.url}</div>
        )}
      </div>
      <span className="studio-list-item-dot" style={{ background: statusColor }} title={studio.status} />
      {isSelected && studio.status !== 'archived' && (
        <PermissionGate permission="delete:app">
          <button
            className="studio-list-item-archive"
            onClick={handleArchive}
            title="Archive"
          >
            x
          </button>
        </PermissionGate>
      )}
    </div>
  );
}
