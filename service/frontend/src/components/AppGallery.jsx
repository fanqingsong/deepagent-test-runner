import { useState, useEffect } from 'react';
import { listApps, createApp, archiveApp } from '../api';
import AppCard from './AppCard';
import Modal from './Modal';
import './AppGallery.css';

const STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'draft', label: '草稿' },
  { value: 'testing', label: '测试中' },
  { value: 'passed', label: '已通过' },
  { value: 'published', label: '已发布' },
];

export default function AppGallery() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);

  // Create form state
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formGoal, setFormGoal] = useState('');

  const loadApps = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listApps({ status: statusFilter || undefined, search: search || undefined });
      setApps(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadApps(); }, [statusFilter]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!formName.trim() || !formUrl.trim() || !formGoal.trim()) return;
    try {
      const app = await createApp({
        name: formName.trim(),
        url: formUrl.trim(),
        test_goal: formGoal.trim(),
      });
      setShowCreate(false);
      setFormName('');
      setFormUrl('');
      setFormGoal('');
      window.location.hash = `app/${app.id}`;
    } catch (e) {
      setError(e.message);
    }
  };

  const handleArchive = async (appId) => {
    try {
      await archiveApp(appId);
      loadApps();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="app-gallery">
      <div className="app-gallery-header">
        <div className="app-gallery-title-row">
          <h1 className="app-gallery-title">APP Workspace</h1>
          <button className="app-gallery-create-btn" onClick={() => setShowCreate(true)}>
            + Create APP
          </button>
        </div>
        <div className="app-gallery-filters">
          <input
            className="app-gallery-search"
            type="text"
            placeholder="Search apps..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadApps()}
          />
          <div className="app-gallery-status-tabs">
            {STATUS_OPTIONS.map(opt => (
              <button
                key={opt.value}
                className={`app-gallery-tab ${statusFilter === opt.value ? 'active' : ''}`}
                onClick={() => setStatusFilter(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <div className="app-gallery-error">{error}</div>}

      {loading ? (
        <div className="app-gallery-loading">Loading...</div>
      ) : apps.length === 0 ? (
        <div className="app-gallery-empty">
          <div className="app-gallery-empty-icon">+</div>
          <h3>No apps yet</h3>
          <p>Create your first APP to start testing</p>
          <button className="app-gallery-create-btn" onClick={() => setShowCreate(true)}>
            + Create APP
          </button>
        </div>
      ) : (
        <div className="app-gallery-grid">
          {apps.map(app => (
            <AppCard key={app.id} app={app} onArchive={handleArchive} />
          ))}
        </div>
      )}

      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Create APP">
        <form className="app-create-form" onSubmit={handleCreate}>
          <div className="app-create-field">
            <label>APP Name *</label>
            <input
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="e.g. Login Test"
              required
            />
          </div>
          <div className="app-create-field">
            <label>Target URL *</label>
            <input
              type="url"
              value={formUrl}
              onChange={(e) => setFormUrl(e.target.value)}
              placeholder="https://example.com"
              required
            />
          </div>
          <div className="app-create-field">
            <label>Test Goal *</label>
            <textarea
              value={formGoal}
              onChange={(e) => setFormGoal(e.target.value)}
              placeholder="Describe what you want to test in natural language..."
              rows={4}
              required
            />
          </div>
          <div className="app-create-actions">
            <button type="button" className="app-btn-secondary" onClick={() => setShowCreate(false)}>
              Cancel
            </button>
            <button type="submit" className="app-btn-primary">
              Create & Start
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
