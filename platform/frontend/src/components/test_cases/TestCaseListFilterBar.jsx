const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'draft', label: 'Draft' },
  { value: 'testing', label: 'Testing' },
  { value: 'passed', label: 'Passed' },
  { value: 'pending_review', label: 'Pending Review' },
  { value: 'published', label: 'Published' },
];

export default function TestCaseListFilterBar({ search, onSearchChange, statusFilter, onStatusFilterChange }) {
  return (
    <div className="test-case-list-filter-bar">
      <input
        className="test-case-list-search"
        type="text"
        placeholder="Search..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
      />
      <div className="test-case-list-status-tabs">
        {STATUS_OPTIONS.map(opt => (
          <button
            key={opt.value}
            className={`test-case-list-tab ${statusFilter === opt.value ? 'test-case-list-tab--active' : ''}`}
            onClick={() => onStatusFilterChange(opt.value)}
            title={opt.label}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
