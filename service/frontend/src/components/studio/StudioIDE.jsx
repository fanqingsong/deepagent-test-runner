import { useState, useEffect, useCallback } from 'react';
import { listStudios, createStudio, archiveStudio } from '../../api';
import { useAuth } from '../../contexts/AuthContext';
import PermissionGate from '../PermissionGate';
import StudioListPanel from './StudioListPanel';
import StudioEditorPanel from './StudioEditorPanel';
import StudioAuxPanel from './StudioAuxPanel';
import './StudioIDE.css';

export default function StudioIDE() {
  const [studios, setStudios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedStudioId, setSelectedStudioId] = useState(null);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);

  // Initialize selected studio from hash
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    const match = hash.match(/^studios?\/(\d+)/);
    if (match) {
      setSelectedStudioId(parseInt(match[1]));
    }
  }, []);

  // Sync hash when selection changes
  useEffect(() => {
    if (selectedStudioId) {
      const currentHash = window.location.hash.slice(1);
      const newHash = `studios/${selectedStudioId}`;
      if (currentHash !== newHash) {
        window.history.replaceState(null, '', `#${newHash}`);
      }
    }
  }, [selectedStudioId]);

  const loadStudios = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listStudios({
        status: statusFilter || undefined,
        search: search || undefined,
      });
      setStudios(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search]);

  useEffect(() => { loadStudios(); }, [loadStudios]);

  const handleSelect = useCallback((id) => {
    setSelectedStudioId(id);
  }, []);

  const handleCreate = async () => {
    try {
      const studio = await createStudio({});
      await loadStudios();
      setSelectedStudioId(studio.id);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleArchive = async (studioId) => {
    try {
      await archiveStudio(studioId);
      if (selectedStudioId === studioId) {
        setSelectedStudioId(null);
      }
      loadStudios();
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
    <div className="studio-ide">
      <div className="studio-ide-sidebar">
        <StudioListPanel
          studios={studios}
          loading={loading}
          error={error}
          selectedStudioId={selectedStudioId}
          onSelect={handleSelect}
          search={search}
          onSearchChange={handleSearchChange}
          statusFilter={statusFilter}
          onStatusFilterChange={handleStatusFilterChange}
          onCreateClick={handleCreate}
          onArchive={handleArchive}
        />
      </div>

      <div className="studio-ide-main">
        <StudioEditorPanel
          studioId={selectedStudioId}
          onToggleAuxPanel={() => setRightPanelOpen(prev => !prev)}
          auxPanelOpen={rightPanelOpen}
          onStudioChanged={loadStudios}
        />
      </div>

      <div className={`studio-ide-aux ${rightPanelOpen ? '' : 'studio-ide-aux--collapsed'}`}>
        {rightPanelOpen && (
          <StudioAuxPanel
            studioId={selectedStudioId}
            onClose={() => setRightPanelOpen(false)}
          />
        )}
      </div>
    </div>
  );
}
