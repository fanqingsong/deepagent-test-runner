import { useState, useEffect } from 'react';
import { listTestCases } from '../../api';

export default function SuiteEntriesTab({ suite, onUpdateEntries }) {
  const entries = suite?.suite_entries || [];
  const testDefIds = suite?.test_definition_ids || [];

  const hasEntries = entries.length > 0;
  const items = hasEntries
    ? entries.filter((e) => e.enabled !== false)
    : testDefIds.map((id, idx) => ({ test_definition_id: id, order: idx + 1 }));

  const [availableTests, setAvailableTests] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [showPicker, setShowPicker] = useState(false);

  const usedIds = new Set(items.map((e) => e.test_definition_id));
  const testNameMap = new Map(availableTests.map((t) => [t.id, t.name]));

  // Always load test definitions for name resolution
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await listTestCases({ limit: 200 });
        if (!cancelled) setAvailableTests(Array.isArray(data) ? data : []);
      } catch {
        /* non-critical */
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Re-fetch when picker opens (in case new tests were created)
  useEffect(() => {
    if (!showPicker) return;
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        const data = await listTestCases({ limit: 200 });
        if (!cancelled) setAvailableTests(Array.isArray(data) ? data : []);
      } catch {
        /* non-critical */
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [showPicker]);

  const filtered = availableTests.filter((t) => {
    if (usedIds.has(t.id)) return false;
    if (searchText && !(t.name || '').toLowerCase().includes(searchText.toLowerCase())) return false;
    return true;
  });

  const handleAdd = (testId) => {
    const maxOrder = items.reduce((m, e) => Math.max(m, e.order || 0), 0);
    const newEntries = [
      ...entries,
      {
        test_definition_id: testId,
        order: maxOrder + 1,
        enabled: true,
        depends_on: [],
        condition: 'always',
      },
    ];
    onUpdateEntries(newEntries);
  };

  const handleRemove = (index) => {
    if (hasEntries) {
      const updated = entries.map((e, i) =>
        i === index ? { ...e, enabled: false } : { ...e }
      );
      onUpdateEntries(updated);
    } else {
      const updated = testDefIds.filter((_, i) => i !== index);
      onUpdateEntries(updated.map((id, i) => ({
        test_definition_id: id,
        order: i + 1,
        enabled: true,
        depends_on: [],
        condition: 'always',
      })));
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <div className="studio-section">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h3 className="studio-section-title" style={{ margin: 0 }}>
            Test Entries ({items.length})
          </h3>
          <button
            style={{
              background: '#0f62fe',
              color: '#fff',
              border: 'none',
              borderRadius: 0,
              padding: '0 12px',
              height: '28px',
              fontSize: '12px',
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
            onClick={() => setShowPicker((v) => !v)}
          >
            {showPicker ? 'Close Picker' : '+ Add Test Case'}
          </button>
        </div>

        {/* Test picker */}
        {showPicker && (
          <div style={{
            marginBottom: '16px',
            padding: '12px',
            background: '#fff',
            border: '1px solid #e0e0e0',
          }}>
            <input
              type="text"
              placeholder="Search test cases..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{
                width: '100%',
                border: 'none',
                borderBottom: '1px solid #e0e0e0',
                padding: '6px 0',
                fontSize: '13px',
                fontFamily: 'inherit',
                outline: 'none',
                background: '#f4f4f4',
                marginBottom: '8px',
                boxSizing: 'border-box',
              }}
            />
            {loading ? (
              <div style={{ padding: '8px 0', color: '#8d8d8d', fontSize: '13px' }}>Loading...</div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: '8px 0', color: '#8d8d8d', fontSize: '13px' }}>
                {searchText ? 'No matching results' : 'All test cases added'}
              </div>
            ) : (
              <div style={{ maxHeight: '240px', overflowY: 'auto' }}>
                {filtered.map((test) => (
                  <div
                    key={test.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '6px 8px',
                      borderBottom: '1px solid #f4f4f4',
                      fontSize: '13px',
                    }}
                  >
                    <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span style={{ color: '#0f62fe', fontWeight: 600, marginRight: '6px' }}>#{test.id}</span>
                      {test.name || 'Unnamed'}
                    </span>
                    <button
                      style={{
                        background: 'none',
                        border: '1px solid #0f62fe',
                        color: '#0f62fe',
                        padding: '2px 10px',
                        fontSize: '11px',
                        cursor: 'pointer',
                        fontFamily: 'inherit',
                        flexShrink: 0,
                      }}
                      onClick={() => handleAdd(test.id)}
                    >
                      Add
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Entries table */}
        {items.length === 0 ? (
          <div style={{ padding: '24px 0', textAlign: 'center', color: '#8d8d8d', fontSize: '13px' }}>
            No test entries yet, click "Add Test Case" to start
          </div>
        ) : (
          <table className="studio-workspace-steps-table">
            <thead>
              <tr>
                <th style={{ width: '32px', textAlign: 'center' }}>#</th>
                <th>Test Case</th>
                <th style={{ width: '80px', textAlign: 'center' }}>Condition</th>
                <th style={{ width: '64px', textAlign: 'center' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((entry, idx) => (
                <tr key={entry.test_definition_id || idx}>
                  <td style={{ textAlign: 'center', color: '#0f62fe', fontWeight: 600 }}>
                    {entry.order || idx + 1}
                  </td>
                  <td style={{ fontSize: '13px' }}>
                    <span style={{ color: '#0f62fe', fontWeight: 600, marginRight: '6px' }}>
                      #{entry.test_definition_id}
                    </span>
                    {testNameMap.get(entry.test_definition_id) || (
                      <span style={{ color: '#8d8d8d' }}>Unknown</span>
                    )}
                    {entry.depends_on?.length > 0 && (
                      <span style={{ marginLeft: '8px', fontSize: '11px', color: '#8d8d8d' }}>
                        depends: [{entry.depends_on.join(', ')}]
                      </span>
                    )}
                  </td>
                  <td style={{ textAlign: 'center', fontSize: '12px', color: '#525252' }}>
                    {entry.condition || 'always'}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      style={{
                        background: 'none',
                        border: '1px solid #da1e28',
                        color: '#da1e28',
                        padding: '2px 8px',
                        fontSize: '11px',
                        cursor: 'pointer',
                        fontFamily: 'inherit',
                      }}
                      onClick={() => handleRemove(idx)}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
