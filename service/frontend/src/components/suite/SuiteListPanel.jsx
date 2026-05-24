import SuiteListFilterBar from './SuiteListFilterBar';
import SuiteListItem from './SuiteListItem';
import './SuiteListPanel.css';

export default function SuiteListPanel({
  suites,
  loading,
  error,
  selectedSuiteId,
  onSelect,
  search,
  onSearchChange,
  modeFilter,
  onModeFilterChange,
  onCreateClick,
  onDelete,
}) {
  return (
    <div className="suite-list-panel">
      <SuiteListFilterBar
        search={search}
        onSearchChange={onSearchChange}
        modeFilter={modeFilter}
        onModeFilterChange={onModeFilterChange}
      />

      {error && <div className="suite-list-error">{error}</div>}

      <div className="suite-list-items">
        {loading ? (
          <div className="suite-list-loading">Loading...</div>
        ) : suites.length === 0 ? (
          <div className="suite-list-empty">
            {search || modeFilter ? 'No matching test suites' : 'No test suites yet'}
          </div>
        ) : (
          suites.map((suite) => (
            <SuiteListItem
              key={suite.id}
              suite={suite}
              isSelected={selectedSuiteId === suite.id}
              onSelect={onSelect}
              onDelete={onDelete}
            />
          ))
        )}
      </div>

      <div className="suite-list-create">
        <button className="suite-list-create-btn" onClick={onCreateClick}>
          + New Suite
        </button>
      </div>
    </div>
  );
}
