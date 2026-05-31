import PermissionGate from '../PermissionGate';
import TestCaseListFilterBar from './TestCaseListFilterBar';
import TestCaseListItem from './TestCaseListItem';
import './TestCaseListPanel.css';

export default function TestCaseListPanel({
  testCases,
  loading,
  error,
  selectedTestCaseId,
  onSelect,
  search,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  onCreateClick,
  onArchive,
}) {
  return (
    <div className="test-case-list-panel">
      <TestCaseListFilterBar
        search={search}
        onSearchChange={onSearchChange}
        statusFilter={statusFilter}
        onStatusFilterChange={onStatusFilterChange}
      />

      {error && <div className="test-case-list-error">{error}</div>}

      <div className="test-case-list-items">
        {loading ? (
          <div className="test-case-list-loading">Loading...</div>
        ) : testCases.length === 0 ? (
          <div className="test-case-list-empty">
            {search || statusFilter ? 'No matching test cases' : 'No test cases yet'}
          </div>
        ) : (
          testCases.map(testCase => (
            <TestCaseListItem
              key={testCase.id}
              testCase={testCase}
              isSelected={selectedTestCaseId === testCase.id}
              onSelect={onSelect}
              onArchive={onArchive}
            />
          ))
        )}
      </div>

      <PermissionGate permission="create:app">
        <div className="test-case-list-create">
          <button className="test-case-list-create-btn" onClick={onCreateClick}>
            + New Test
          </button>
        </div>
      </PermissionGate>
    </div>
  );
}
