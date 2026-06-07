import { useState, useCallback, useEffect, useRef } from 'react';
import { getTestCasePermissions, addTestCasePermission,
         updateTestCasePermission, removeTestCasePermission,
         searchUsers } from '../../api';

const PERMISSION_LABELS = { view: 'View', edit: 'Edit', execute: 'Execute', admin: 'Admin' };
const PERMISSION_TYPES = ['view', 'edit', 'execute', 'admin'];

export default function TestCasePermissionsSection({
  workspaceId, readOnly, onPermissionsChange, initialPermissions = []
}) {
  const [permissions, setPermissions] = useState(initialPermissions);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
    if (!workspaceId) return;
    try {
      setLoading(true);
      const data = await getTestCasePermissions(workspaceId);
      setPermissions(data);
      onPermissionsChange?.(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [workspaceId, onPermissionsChange]);

  useEffect(() => { loadPermissions(); }, [loadPermissions]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target) &&
          dropdownRef.current && !dropdownRef.current.contains(e.target)) {
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
      } catch { setSearchResults([]); }
      finally { setSearching(false); }
    }, 300);
  };

  const handleSelectUser = (user) => {
    setSelectedUser(user);
    setSearchQuery(`${user.username} (${user.email})`);
    setShowDropdown(false);
  };

  const handleAdd = async (permissionType) => {
    if (!selectedUser || readOnly) return;
    try {
      setError(null);
      await addTestCasePermission(workspaceId, {
        userId: selectedUser.id,
        permissionType,
      });
      setSelectedUser(null);
      setSearchQuery('');
      setSearchResults([]);
      await loadPermissions();
    } catch (e) { setError(e.message); }
  };

  const handleUpdate = async (userId, newType) => {
    if (readOnly) return;
    try {
      setError(null);
      await updateTestCasePermission(workspaceId, userId, { permissionType: newType });
      await loadPermissions();
    } catch (e) { setError(e.message); }
  };

  const handleRemove = async (userId) => {
    if (readOnly) return;
    try {
      setError(null);
      await removeTestCasePermission(workspaceId, userId);
      await loadPermissions();
    } catch (e) { setError(e.message); }
  };

  if (loading && permissions.length === 0) {
    return (
      <div className="composer-permissions-section">
        <div className="composer-permissions-header">
          <span className="composer-permissions-title">Permissions</span>
        </div>
        <div style={{ padding: '16px', color: '#8d8d8d', fontSize: '13px' }}>
          Loading permissions...
        </div>
      </div>
    );
  }

  return (
    <div className="composer-permissions-section">
      <div className="composer-permissions-header">
        <span className="composer-permissions-title">Permissions</span>
        <span className="composer-permissions-count">({permissions.length})</span>
      </div>

      {error && <div className="composer-permissions-error">{error}</div>}

      {!readOnly && (
        <div className="composer-permissions-add">
          <div style={{ position: 'relative', display: 'inline-block', width: '100%' }}>
            <input
              type="text"
              placeholder="Search users to add..."
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
              className="composer-config-input"
              disabled={readOnly}
            />
            {showDropdown && (
              <div ref={dropdownRef} className="composer-permissions-dropdown">
                {searching && <div className="dropdown-searching">Searching...</div>}
                {!searching && searchResults.length === 0 && (
                  <div className="dropdown-empty">No users found</div>
                )}
                {searchResults.map((user, idx) => (
                  <div
                    key={user.id}
                    onClick={() => handleSelectUser(user)}
                    className={`dropdown-item ${idx === highlightIndex ? 'dropdown-item--highlight' : ''}`}
                    onMouseEnter={() => setHighlightIndex(idx)}
                  >
                    <div className="dropdown-item-name">{user.username}</div>
                    <div className="dropdown-item-email">{user.email}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
          {selectedUser && (
            <div className="composer-permissions-add-actions">
              {PERMISSION_TYPES.map(type => (
                <button
                  key={type}
                  className="composer-permissions-add-btn"
                  onClick={() => handleAdd(type)}
                >
                  Add as {PERMISSION_LABELS[type]}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="composer-permissions-list">
        {permissions.length === 0 ? (
          <p className="composer-permissions-empty">No permissions set</p>
        ) : (
          permissions.map((perm) => (
            <div key={perm.id} className="composer-permissions-item">
              <div className="composer-permissions-user">
                <div className="composer-permissions-username">{perm.username || `User ${perm.user_id}`}</div>
                <div className="composer-permissions-email">{perm.email || ''}</div>
              </div>
              <div className="composer-permissions-type">
                {readOnly ? (
                  <span>{PERMISSION_LABELS[perm.permission_type]}</span>
                ) : (
                  <select
                    value={perm.permission_type}
                    onChange={(e) => handleUpdate(perm.user_id, e.target.value)}
                    className="composer-permissions-select"
                  >
                    {PERMISSION_TYPES.map(t => (
                      <option key={t} value={t}>{PERMISSION_LABELS[t]}</option>
                    ))}
                  </select>
                )}
              </div>
              {!readOnly && (
                <div className="composer-permissions-actions">
                  <button
                    className="composer-permissions-remove"
                    onClick={() => handleRemove(perm.user_id)}
                  >
                    Remove
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
