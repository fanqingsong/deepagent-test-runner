import PermissionGate from '../PermissionGate';

const STATUS_COLORS = {
  draft: '#a8a8a8',
  generating: '#0f62fe',
  testing: '#0f62fe',
  passed: '#198038',
  published: '#6929c4',
  archived: '#6f6f6f',
};

export default function TestCaseListItem({ testCase, isSelected, onSelect, onArchive }) {
  const statusColor = STATUS_COLORS[testCase.status] || '#6f6f6f';

  const handleClick = (e) => {
    e.stopPropagation();
    if (testCase.status !== 'archived') {
      onSelect(testCase.id);
    }
  };

  const handleArchive = (e) => {
    e.stopPropagation();
    onArchive(testCase.id);
  };

  return (
    <div
      className={`test-case-list-item ${isSelected ? 'test-case-list-item--active' : ''}`}
      onClick={handleClick}
    >
      <div className="test-case-list-item-color" style={{ background: testCase.color || '#0f62fe' }}>
        {(testCase.name || '?')[0].toUpperCase()}
      </div>
      <div className="test-case-list-item-content">
        <div className="test-case-list-item-name">{testCase.name}</div>
        {testCase.url && (
          <div className="test-case-list-item-url">{testCase.url}</div>
        )}
      </div>
      <span className="test-case-list-item-dot" style={{ background: statusColor }} title={testCase.status} />
      {isSelected && testCase.status !== 'archived' && (
        <PermissionGate permission="delete:app">
          <button
            className="test-case-list-item-archive"
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
