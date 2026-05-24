import { useState, useEffect, useCallback } from 'react';
import {
  getStudioPermissions, addStudioPermission,
  updateStudioPermission, removeStudioPermission,
} from '../../api';
import PermissionGate from '../PermissionGate';
import './studio-shared.css';

const PERMISSION_LABELS = {
  view: 'View',
  edit: 'Edit',
  execute: 'Execute',
  admin: 'Admin',
};

const PERMISSION_TYPES = ['view', 'edit', 'execute', 'admin'];

export default function StudioPermissionTab({ studioId }) {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [addUserId, setAddUserId] = useState('');
  const [addPermType, setAddPermType] = useState('view');
  const [adding, setAdding] = useState(false);

  const loadPermissions = useCallback(async () => {
    if (!studioId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getStudioPermissions(studioId);
      setPermissions(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [studioId]);

  useEffect(() => { loadPermissions(); }, [loadPermissions]);

  const handleAdd = async () => {
    if (!addUserId.trim()) return;
    try {
      setAdding(true);
      setError(null);
      await addStudioPermission(studioId, {
        userId: parseInt(addUserId),
        permissionType: addPermType,
      });
      setAddUserId('');
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
      await updateStudioPermission(studioId, userId, { permissionType: newType });
      await loadPermissions();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleRemove = async (userId) => {
    try {
      setError(null);
      await removeStudioPermission(studioId, userId);
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
        <div className="studio-workspace-msg-error">{error}</div>
      )}

      {/* Add permission */}
      <PermissionGate permission="update:app">
        <div className="studio-section">
          <h3 className="studio-section-title">Add Collaborator</h3>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input
              type="number"
              placeholder="User ID"
              value={addUserId}
              onChange={(e) => setAddUserId(e.target.value)}
              style={{
                background: '#f4f4f4',
                border: 'none',
                borderBottom: '1px solid #8d8d8d',
                padding: '8px 12px',
                fontSize: '14px',
                width: '120px',
                outline: 'none',
                fontFamily: 'inherit',
              }}
            />
            <select
              value={addPermType}
              onChange={(e) => setAddPermType(e.target.value)}
              style={{
                background: '#f4f4f4',
                border: 'none',
                borderBottom: '1px solid #8d8d8d',
                padding: '8px 12px',
                fontSize: '14px',
                outline: 'none',
                fontFamily: 'inherit',
              }}
            >
              {PERMISSION_TYPES.map(t => (
                <option key={t} value={t}>{PERMISSION_LABELS[t]}</option>
              ))}
            </select>
            <button
              className="studio-workspace-run-btn"
              onClick={handleAdd}
              disabled={!addUserId.trim() || adding}
            >
              {adding ? 'Adding...' : 'Add'}
            </button>
          </div>
        </div>
      </PermissionGate>

      {/* Permissions list */}
      <div className="studio-section">
        <h3 className="studio-section-title">
          Collaborators
          <span style={{ fontWeight: 400, color: '#525252', fontSize: '13px', marginLeft: '8px' }}>
            {permissions.length} members
          </span>
        </h3>

        {permissions.length === 0 ? (
          <p style={{ color: '#8d8d8d', fontSize: '13px' }}>
            No collaborators yet. Add a user by their ID above.
          </p>
        ) : (
          <table className="studio-workspace-steps-table">
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
                    <PermissionGate permission="update:app" fallback={
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
                    <PermissionGate permission="update:app">
                      <button
                        className="studio-workspace-secondary-btn"
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
