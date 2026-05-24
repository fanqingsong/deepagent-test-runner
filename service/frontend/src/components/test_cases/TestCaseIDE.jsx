import { useState, useEffect, useCallback } from 'react';
import { listTestCases, createTestCase, archiveTestCase } from '../../api';
import { useAuth } from '../../contexts/AuthContext';
import PermissionGate from '../PermissionGate';
import TestCaseListPanel from './TestCaseListPanel';
import TestCaseEditorPanel from './TestCaseEditorPanel';
import TestCaseAuxPanel from './TestCaseAuxPanel';
import './TestCaseIDE.css';

export default function TestCasesIDE() {
  const [testCases, setTestCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedTestCaseId, setSelectedTestCaseId] = useState(null);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  // Initialize selected test case from hash
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    const match = hash.match(/^test-cases?\/(\d+)/);
    if (match) {
      setSelectedTestCaseId(parseInt(match[1]));
    }
  }, []);

  // Sync hash when selection changes
  useEffect(() => {
    if (selectedTestCaseId) {
      const currentHash = window.location.hash.slice(1);
      const newHash = `test-cases/${selectedTestCaseId}`;
      if (currentHash !== newHash) {
        window.history.replaceState(null, '', `#${newHash}`);
      }
    }
  }, [selectedTestCaseId]);

  const loadTestCases = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listTestCases({
        status: statusFilter || undefined,
        search: search || undefined,
      });
      setTestCases(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search]);

  useEffect(() => { loadTestCases(); }, [loadTestCases]);

  const handleSelect = useCallback((id) => {
    setSelectedTestCaseId(id);
  }, []);

  const handleCreate = async () => {
    try {
      const testCase = await createTestCase({});
      await loadTestCases();
      setSelectedTestCaseId(testCase.id);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleArchive = async (testCaseId) => {
    try {
      await archiveTestCase(testCaseId);
      if (selectedTestCaseId === testCaseId) {
        setSelectedTestCaseId(null);
      }
      loadTestCases();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleSearchChange = (value) => {
    setSearch(value);
  };

  const handleStatusFilterChange = (value) => {
    setStatusFilter(value);
  };

  return (
    <div className="test-cases-ide">
      <div className="test-cases-ide-sidebar">
        <TestCaseListPanel
          testCases={testCases}
          loading={loading}
          error={error}
          selectedTestCaseId={selectedTestCaseId}
          onSelect={handleSelect}
          search={search}
          onSearchChange={handleSearchChange}
          statusFilter={statusFilter}
          onStatusFilterChange={handleStatusFilterChange}
          onCreateClick={handleCreate}
          onArchive={handleArchive}
        />
      </div>

      <div className="test-cases-ide-main">
        <TestCaseEditorPanel
          testCaseId={selectedTestCaseId}
          onToggleAuxPanel={() => setRightPanelOpen(prev => !prev)}
          auxPanelOpen={rightPanelOpen}
          onTestCaseChanged={loadTestCases}
        />
      </div>

      <div className={`test-cases-ide-aux ${rightPanelOpen ? '' : 'test-cases-ide-aux--collapsed'}`}>
        {rightPanelOpen && (
          <TestCaseAuxPanel
            testCaseId={selectedTestCaseId}
            onClose={() => setRightPanelOpen(false)}
          />
        )}
      </div>
    </div>
  );
}
