import { useState, useEffect } from 'react';
import { listPublishedSuites } from '../api';
import SuiteMarketplaceCard from '../components/marketplace/SuiteMarketplaceCard';
import './SuiteMarketplacePage.css';

export default function SuiteMarketplacePage() {
  const [suites, setSuites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  const loadSuites = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listPublishedSuites({
        search: search || undefined,
        skip: 0,
        limit: 100,
      });
      setSuites(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSuites();
  }, []);

  const handleSearch = () => {
    loadSuites();
  };

  const handleCopy = (copiedSuite) => {
    loadSuites();
  };

  return (
    <div className="suite-marketplace-page">
      <div className="suite-marketplace-header">
        <h1 className="suite-marketplace-title">Test Suite Marketplace</h1>
        <p className="suite-marketplace-subtitle">
          Browse and use approved test suites created by the community
        </p>
      </div>

      <div className="suite-marketplace-filters">
        <div className="suite-marketplace-search-row">
          <input
            className="suite-marketplace-search"
            type="text"
            placeholder="Search test suites..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            className="suite-marketplace-search-btn"
            onClick={handleSearch}
          >
            Search
          </button>
        </div>
      </div>

      {error && <div className="suite-marketplace-error">{error}</div>}

      {loading ? (
        <div className="suite-marketplace-loading">Loading...</div>
      ) : suites.length === 0 ? (
        <div className="suite-marketplace-empty">
          <div className="suite-marketplace-empty-icon">📦</div>
          <h3>No approved test suites yet</h3>
          <p>
            Approved test suites will appear here for the community to discover and use.
          </p>
        </div>
      ) : (
        <div className="suite-marketplace-grid">
          {suites.map(suite => (
            <SuiteMarketplaceCard
              key={suite.id}
              suite={suite}
              onCopy={handleCopy}
            />
          ))}
        </div>
      )}
    </div>
  );
}
