import PermissionGate from '../PermissionGate';
import StudioListFilterBar from './StudioListFilterBar';
import StudioListItem from './StudioListItem';
import './StudioListPanel.css';

export default function StudioListPanel({
  studios,
  loading,
  error,
  selectedStudioId,
  onSelect,
  search,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  onCreateClick,
  onArchive,
}) {
  return (
    <div className="studio-list-panel">
      <StudioListFilterBar
        search={search}
        onSearchChange={onSearchChange}
        statusFilter={statusFilter}
        onStatusFilterChange={onStatusFilterChange}
      />

      {error && <div className="studio-list-error">{error}</div>}

      <div className="studio-list-items">
        {loading ? (
          <div className="studio-list-loading">Loading...</div>
        ) : studios.length === 0 ? (
          <div className="studio-list-empty">
            {search || statusFilter ? 'No matching test cases' : 'No test cases yet'}
          </div>
        ) : (
          studios.map(studio => (
            <StudioListItem
              key={studio.id}
              studio={studio}
              isSelected={selectedStudioId === studio.id}
              onSelect={onSelect}
              onArchive={onArchive}
            />
          ))
        )}
      </div>

      <PermissionGate permission="create:app">
        <div className="studio-list-create">
          <button className="studio-list-create-btn" onClick={onCreateClick}>
            + New Test
          </button>
        </div>
      </PermissionGate>
    </div>
  );
}
