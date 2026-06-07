import { useState, useEffect, useCallback, useRef } from 'react';
import {
  getSuitePermissions, addSuitePermission,
  updateSuitePermission, removeSuitePermission,
  searchUsers,
} from '../../api';
import PermissionGate from '../PermissionGate';
import '../test_cases/test-cases-shared.css';

const PERMISSION_LABELS = {
  view: 'View',
  edit: 'Edit',
  execute: 'Execute',
  admin: 'Admin',
};

const PERMISSION_TYPES = ['view', 'edit', 'execute', 'admin'];

export default function SuitePermissionTab({ suiteId }) {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [addPermType, setAddPermType] = useState('view');
  const [adding, setAdding] = useState(false);

  // User search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const searchRef = useRef(null);
  const dropdownRef = useRef(null);
  const debounceRef = useRef(null);

  const loadPermissions = useCallback(async () => {
    if (!suiteId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getSuitePermissions(suiteId);
      setPermissions(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [suiteId]);

  useEffect(() => { loadPermissions(); }, [loadPermissions]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        searchRef.current && !searchRef.current.contains(e.target) &&
        dropdownRef.current && !dropdownRef.current.contains(e.target)
      ) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchChange = (value) => {
    setSearchQuery(value);
    setSelectedUser(null);

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!value.trim()) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      try {
        setSearching(true);
        const users = await searchUsers(value.trim());
        setSearchResults(users);
        setHighlightIndex(-1);
        setShowDropdown(true);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
  };

  const handleSelectUser = (user) => {
    setSelectedUser(user);
    setSearchQuery(`${user.username} (${user.email})`);
    setShowDropdown(false);
  };

  const handleAdd = async () => {
    if (!selectedUser) return;
    try {
      setAdding(true);
      setError(null);
      await addSuitePermission(suiteId, {
        userId: selectedUser.id,
        permissionType: addPermType,
      });
      setSelectedUser(null);
      setSearchQuery('');
      setSearchResults([]);
      setAddPermType('view');
      await loadPermissions();
    } catch (e) {
      setError(e.message);
    } finally {
      setAdding(false);
    }
  };

  const handleUpdate = async (userId, newType) => {
    try {
      setError(null);
      await updateSuitePermission(suiteId, userId, { permissionType: newType });
      await loadPermissions();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleRemove = async (userId) => {
    try {
      setError(null);
      await removeSuitePermission(suiteId, userId);
      await loadPermissions();
    } catch (e) {
      setError(e.message);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '48px', color: '#525252' }}>
        Loading permissions...
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      {error && (
        <div className="test-case-workspace-msg-error">{error}</div>
      )}

      {/* Add permission */}
      <PermissionGate permission="update:suite">
        <div className="test-case-section">
          <h3 className="test-case-section-title">Add Collaborator</h3>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
            <div style={{ position: 'relative', flex: 1, maxWidth: '280px' }}>
              <input
                type="text"
                placeholder="Search by username or email..."
                value={searchQuery}
                onChange={(e) => handleSearchChange(e.target.value)}
                onFocus={() => { if (searchResults.length > 0) setShowDropdown(true); }}
                onKeyDown={(e) => {
                  if (!showDropdown || searchResults.length === 0) return;
                  if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    setHighlightIndex((i) => (i + 1) % searchResults.length);
                  } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    setHighlightIndex((i) => (i - 1 + searchResults.length) % searchResults.length);
                  } else if (e.key === 'Enter' && highlightIndex >= 0) {
                    e.preventDefault();
                    handleSelectUser(searchResults[highlightIndex]);
                  } else if (e.key === 'Escape') {
                    setShowDropdown(false);
                  }
                }}
                ref={searchRef}
                className="test-case-workspace-field-input"
                style={{ width: '100%', boxSizing: 'border-box' }}
              />
              {showDropdown && (
                <div
                  ref={dropdownRef}
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    background: '#fff',
                    border: '1px solid #e0e0e0',
                    borderTop: 'none',
                    maxHeight: '200px',
                    overflowY: 'auto',
                    zIndex: 100,
                  }}
                >
                  {searching && (
                    <div style={{ padding: '8px 12px', color: '#8d8d8d', fontSize: '13px' }}>
                      Searching...
                    </div>
                  )}
                  {!searching && searchResults.length === 0 && (
                    <div style={{ padding: '8px 12px', color: '#8d8d8d', fontSize: '13px' }}>
                      No users found
                    </div>
                  )}
                  {searchResults.map((user, idx) => (
                    <div
                      key={user.id}
                      onClick={() => handleSelectUser(user)}
                      style={{
                        padding: '8px 12px',
                        cursor: 'pointer',
                        fontSize: '13px',
                        borderBottom: '1px solid #f4f4f4',
                        background: idx === highlightIndex ? '#f4f4f4' : 'transparent',
                      }}
                      onMouseEnter={() => setHighlightIndex(idx)}
                      onMouseLeave={() => setHighlightIndex(-1)}
                    >
                      <div style={{ fontWeight: 600, color: '#161616' }}>{user.username}</div>
                      <div style={{ fontSize: '11px', color: '#8d8d8d' }}>{user.email}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <select
              value={addPermType}
              onChange={(e) => setAddPermType(e.target.value)}
              className="test-case-workspace-field-input"
              style={{ width: 'auto' }}
            >
              {PERMISSION_TYPES.map(t => (
                <option key={t} value={t}>{PERMISSION_LABELS[t]}</option>
              ))}
            </select>
            <button
              className="test-case-workspace-run-btn"
              onClick={handleAdd}
              disabled={!selectedUser || adding}
            >
              {adding ? 'Adding...' : 'Add'}
            </button>
          </div>
          {selectedUser && (
            <div style={{ marginTop: '6px', fontSize: '12px', color: '#198038' }}>
              Selected: {selectedUser.username} (ID: {selectedUser.id})
            </div>
          )}
        </div>
      </PermissionGate>

      {/* Permissions list */}
      <div className="test-case-section">
        <h3 className="test-case-section-title">
          Collaborators
          <span style={{ fontWeight: 400, color: '#525252', fontSize: '13px', marginLeft: '8px' }}>
            {permissions.length} members
          </span>
        </h3>

        {permissions.length === 0 ? (
          <p style={{ color: '#8d8d8d', fontSize: '13px' }}>
            No collaborators yet. Search for a user above to add them.
          </p>
        ) : (
          <table className="test-case-workspace-steps-table">
            <thead>
              <tr>
                <th className="th-desc">User</th>
                <th className="th-type">Permission</th>
                <th style={{ width: '80px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {permissions.map((perm) => (
                <tr key={perm.id}>
                  <td className="td-desc">
                    <div>{perm.username || `User ${perm.user_id}`}</div>
                    <div style={{ fontSize: '11px', color: '#8d8d8d' }}>{perm.email || ''}</div>
                  </td>
                  <td className="td-type">
                    <PermissionGate permission="update:suite" fallback={
                      <span style={{ fontSize: '13px', color: '#525252' }}>{PERMISSION_LABELS[perm.permission_type]}</span>
                    }>
                      <select
                        value={perm.permission_type}
                        onChange={(e) => handleUpdate(perm.user_id, e.target.value)}
                        style={{
                          background: 'transparent',
                          border: '1px solid #e0e0e0',
                          padding: '2px 8px',
                          fontSize: '13px',
                          fontFamily: 'inherit',
                          cursor: 'pointer',
                        }}
                      >
                        {PERMISSION_TYPES.map(t => (
                          <option key={t} value={t}>{PERMISSION_LABELS[t]}</option>
                        ))}
                      </select>
                    </PermissionGate>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <PermissionGate permission="update:suite">
                      <button
                        className="test-case-workspace-secondary-btn"
                        onClick={() => handleRemove(perm.user_id)}
                        style={{ color: '#da1e28', borderColor: '#da1e28' }}
                      >
                        Remove
                      </button>
                    </PermissionGate>
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
