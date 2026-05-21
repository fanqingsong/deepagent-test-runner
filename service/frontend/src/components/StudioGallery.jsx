import { useState, useEffect } from 'react';
import { listStudios, createStudio, archiveStudio } from '../api';
import StudioCard from './StudioCard';
import Modal from './Modal';
import './StudioGallery.css';

const STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'draft', label: '草稿' },
  { value: 'testing', label: '测试中' },
  { value: 'passed', label: '已通过' },
  { value: 'published', label: '已发布' },
];

export default function StudioGallery() {
  const [studios, setStudios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  // Create form state
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formGoal, setFormGoal] = useState('');

  const loadStudios = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listStudios({ status: statusFilter || undefined, search: search || undefined });
      setStudios(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadStudios(); }, [statusFilter]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!formName.trim() || !formUrl.trim() || !formGoal.trim()) return;
    try {
      const studio = await createStudio({
        name: formName.trim(),
        url: formUrl.trim(),
        test_goal: formGoal.trim(),
      });
      setShowCreate(false);
      setFormName('');
      setFormUrl('');
      setFormGoal('');
      window.location.hash = `studio/${studio.id}`;
    } catch (e) {
      setError(e.message);
    }
  };

  const handleArchive = async (studioId) => {
    try {
      await archiveStudio(studioId);
      loadStudios();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="studio-gallery">
      <div className="studio-gallery-header">
        <div className="studio-gallery-title-row">
          <h1 className="studio-gallery-title">Studio Workspace</h1>
          <button className="studio-gallery-create-btn" onClick={() => setShowCreate(true)}>
            + Create Studio
          </button>
        </div>
        <div className="studio-gallery-filters">
          <input
            className="studio-gallery-search"
            type="text"
            placeholder="Search studios..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadStudios()}
          />
          <div className="studio-gallery-status-tabs">
            {STATUS_OPTIONS.map(opt => (
              <button
                key={opt.value}
                className={`studio-gallery-tab ${statusFilter === opt.value ? 'active' : ''}`}
                onClick={() => setStatusFilter(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <div className="studio-gallery-error">{error}</div>}

      {loading ? (
        <div className="studio-gallery-loading">Loading...</div>
      ) : studios.length === 0 ? (
        <div className="studio-gallery-empty">
          <div className="studio-gallery-empty-icon">+</div>
          <h3>No studios yet</h3>
          <p>Create your first Studio to start testing</p>
          <button className="studio-gallery-create-btn" onClick={() => setShowCreate(true)}>
            + Create Studio
          </button>
        </div>
      ) : (
        <div className="studio-gallery-grid">
          {studios.map(studio => (
            <StudioCard key={studio.id} studio={studio} onArchive={handleArchive} />
          ))}
        </div>
      )}

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create Studio">
        <form className="studio-create-form" onSubmit={handleCreate}>
          <div className="studio-create-field">
            <label>Studio Name *</label>
            <input
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="e.g. Login Test"
              required
            />
          </div>
          <div className="studio-create-field">
            <label>Target URL *</label>
            <input
              type="url"
              value={formUrl}
              onChange={(e) => setFormUrl(e.target.value)}
              placeholder="https://example.com"
              required
            />
          </div>
          <div className="studio-create-field">
            <label>Test Goal *</label>
            <textarea
              value={formGoal}
              onChange={(e) => setFormGoal(e.target.value)}
              placeholder="Describe what you want to test in natural language..."
              rows={4}
              required
            />
          </div>
          <div className="studio-create-actions">
            <button type="button" className="studio-btn-secondary" onClick={() => setShowCreate(false)}>
              Cancel
            </button>
            <button type="submit" className="studio-btn-primary">
              Create & Start
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
