const MODE_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'sequential', label: 'Sequential' },
  { value: 'parallel', label: 'Parallel' },
  { value: 'dynamic', label: 'Dynamic' },
];

export default function SuiteListFilterBar({ search, onSearchChange, modeFilter, onModeFilterChange }) {
  return (
    <div className="suite-list-filter-bar">
      <input
        className="suite-list-search"
        type="text"
        placeholder="Search suites..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
      />
      <div className="suite-list-mode-tabs">
        {MODE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className={`suite-list-tab ${modeFilter === opt.value ? 'suite-list-tab--active' : ''}`}
            onClick={() => onModeFilterChange(opt.value)}
            title={opt.label}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
