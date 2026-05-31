import { useState, useEffect } from 'react';
import { listPublishedTestCases } from '../api';
import TestCasesMarketplaceCard from '../components/marketplace/TestCasesMarketplaceCard';
import './TestCasesMarketplacePage.css';

export default function TestCasesMarketplacePage() {
  const [testCases, setTestCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [tags, setTags] = useState('');

  const loadTestCases = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listPublishedTestCases({
        search: search || undefined,
        skip: 0,
        limit: 100,
      });
      setTestCases(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTestCases();
  }, []);

  const handleSearch = () => {
    loadTestCases();
  };

  const handleCopy = (copiedTestCase) => {
    loadTestCases();
  };

  return (
    <div className="test-cases-marketplace-page">
      <div className="test-cases-marketplace-header">
        <h1 className="test-cases-marketplace-title">Test Case Marketplace</h1>
        <p className="test-cases-marketplace-subtitle">
          Browse and use published test cases created by the community
        </p>
      </div>

      <div className="test-cases-marketplace-filters">
        <div className="test-cases-marketplace-search-row">
          <input
            className="test-cases-marketplace-search"
            type="text"
            placeholder="Search test cases..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            className="test-cases-marketplace-search-btn"
            onClick={handleSearch}
          >
            Search
          </button>
        </div>
      </div>

      {error && <div className="test-cases-marketplace-error">{error}</div>}

      {loading ? (
        <div className="test-cases-marketplace-loading">Loading...</div>
      ) : testCases.length === 0 ? (
        <div className="test-cases-marketplace-empty">
          <div className="test-cases-marketplace-empty-icon">📦</div>
          <h3>No published test cases yet</h3>
          <p>
            Published test cases will appear here for the community to discover and use.
          </p>
        </div>
      ) : (
        <div className="test-cases-marketplace-grid">
          {testCases.map(testCase => (
            <TestCasesMarketplaceCard
              key={testCase.id}
              testCase={testCase}
              onCopy={handleCopy}
            />
          ))}
        </div>
      )}
    </div>
  );
}
