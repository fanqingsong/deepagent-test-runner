import { useState, useEffect, useCallback } from 'react';
import {
  getTestSuites,
  createTestSuite,
  deleteTestSuite,
} from '../../api';
import SuiteListPanel from './SuiteListPanel';
import SuiteEditorPanel from './SuiteEditorPanel';
import Toast from '../Toast';
import './SuiteIDE.css';

export default function SuiteIDE() {
  const [suites, setSuites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [modeFilter, setModeFilter] = useState('');
  const [selectedSuiteId, setSelectedSuiteId] = useState(null);

  // Toast state
  const [toast, setToast] = useState({ message: null, type: 'success', key: 0 });
  const showToast = (message, type = 'success') => {
    setToast(prev => ({ message, type, key: prev.key + 1 }));
  };

  useEffect(() => {
    const hash = window.location.hash.slice(1);
    const match = hash.match(/^suites?\/(\d+)/);
    if (match) {
      setSelectedSuiteId(parseInt(match[1]));
    }
  }, []);

  useEffect(() => {
    if (selectedSuiteId) {
      const currentHash = window.location.hash.slice(1);
      const newHash = `suites/${selectedSuiteId}`;
      if (currentHash !== newHash) {
        window.history.replaceState(null, '', `#${newHash}`);
      }
    }
  }, [selectedSuiteId]);

  const loadSuites = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getTestSuites();
      setSuites(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSuites(); }, [loadSuites]);

  const handleSelect = useCallback((id) => {
    setSelectedSuiteId(id);
  }, []);

  const handleCreate = async () => {
    try {
      const suite = await createTestSuite({ name: 'New Suite' });
      await loadSuites();
      setSelectedSuiteId(suite.id);
      showToast('Suite created');
    } catch (e) {
      setError(e.message);
      showToast(e.message, 'error');
    }
  };

  const handleDelete = async (suiteId) => {
    try {
      await deleteTestSuite(suiteId);
      if (selectedSuiteId === suiteId) {
        setSelectedSuiteId(null);
      }
      loadSuites();
      showToast('Suite deleted');
    } catch (e) {
      setError(e.message);
      showToast(e.message, 'error');
    }
  };

  const filtered = suites.filter((s) => {
    if (search && !s.name.toLowerCase().includes(search.toLowerCase())) return false;
    if (modeFilter === 'sequential' && s.execution_mode !== 'sequential') return false;
    if (modeFilter === 'parallel' && s.execution_mode !== 'parallel') return false;
    if (modeFilter === 'dynamic' && !s.is_dynamic) return false;
    return true;
  });

  return (
    <div className="suite-ide">
      <div className="suite-ide-sidebar">
        <SuiteListPanel
          suites={filtered}
          loading={loading}
          error={error}
          selectedSuiteId={selectedSuiteId}
          onSelect={handleSelect}
          search={search}
          onSearchChange={setSearch}
          modeFilter={modeFilter}
          onModeFilterChange={setModeFilter}
          onCreateClick={handleCreate}
          onDelete={handleDelete}
        />
      </div>

      <div className="suite-ide-main">
        <SuiteEditorPanel
          suiteId={selectedSuiteId}
          onSuiteChanged={loadSuites}
          onDelete={handleDelete}
        />
      </div>
      <Toast key={toast.key} message={toast.message} type={toast.type} onDone={() => setToast(prev => ({ ...prev, message: null }))} />
    </div>
  );
}
