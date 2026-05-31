export default function SuiteListItem({ suite, isSelected, onSelect, onDelete }) {
  const handleClick = () => {
    onSelect(suite.id);
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this suite?')) {
      onDelete(suite.id);
    }
  };

  const testCount = suite.suite_entries?.length || suite.test_definition_ids?.length || 0;
  const modeLabel = suite.is_dynamic ? 'Dynamic' : suite.execution_mode === 'parallel' ? 'Parallel' : 'Sequential';

  return (
    <div
      className={`suite-list-item ${isSelected ? 'suite-list-item--active' : ''}`}
      onClick={handleClick}
    >
      <div className="suite-list-item-icon">
        {(suite.name || '?')[0].toUpperCase()}
      </div>
      <div className="suite-list-item-content">
        <div className="suite-list-item-name">{suite.name}</div>
        <div className="suite-list-item-meta">{testCount} tests · {modeLabel}</div>
      </div>
      <span className="suite-list-item-dot" style={{ background: suite.is_dynamic ? '#6929c4' : '#0f62fe' }} />
      {isSelected && (
        <button
          className="suite-list-item-delete"
          onClick={handleDelete}
          title="Delete"
        >
          x
        </button>
      )}
    </div>
  );
}
