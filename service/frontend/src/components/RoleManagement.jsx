/**
 * RoleManagement Component
 *
 * CRUD page for roles and permissions.
 * Follows IBM Carbon Design System principles.
 */

import { useState, useEffect, useCallback } from 'react';
import { getRoles, getPermissions, createRole, updateRole, deleteRole } from '../api';
import Modal from './Modal';
import PermissionGate from './PermissionGate';
import './RoleManagement.css';

const RoleManagement = () => {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showRoleForm, setShowRoleForm] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);
  const [formError, setFormError] = useState(null);
  const [formLoading, setFormLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [rolesData, permsData] = await Promise.all([getRoles(), getPermissions()]);
      setRoles(Array.isArray(rolesData) ? rolesData : []);
      setPermissions(Array.isArray(permsData) ? permsData : []);
    } catch (err) {
      setError(err.message || 'Failed to load role data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateRole = () => {
    setEditingRole(null);
    setFormError(null);
    setShowRoleForm(true);
  };

  const handleEditRole = (role) => {
    setEditingRole(role);
    setFormError(null);
    setShowRoleForm(true);
  };

  const handleDeleteRole = (role) => {
    setShowDeleteConfirm(role);
  };

  const confirmDeleteRole = async () => {
    if (!showDeleteConfirm) return;
    try {
      setDeleteLoading(true);
      await deleteRole(showDeleteConfirm.id);
      setShowDeleteConfirm(null);
      await loadData();
    } catch (err) {
      alert(err.message || 'Failed to delete role');
    } finally {
      setDeleteLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="role-management">
        <div className="role-management-loading">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="role-management">
        <div className="role-form-alert">{error}</div>
      </div>
    );
  }

  return (
    <div className="role-management">
      <div className="role-management-header">
        <h2 className="role-management-title">Role Management</h2>
        <PermissionGate permission="create:role">
          <button className="role-create-btn" onClick={handleCreateRole}>
            <span>+</span>
            <span>Create Role</span>
          </button>
        </PermissionGate>
      </div>

      <div className="role-table-container">
        <table className="role-table">
          <thead>
            <tr>
              <th>Role Name</th>
              <th>Description</th>
              <th>Permissions</th>
              <th>Type</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {roles.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--cds-text-secondary)' }}>
                  No roles
                </td>
              </tr>
            ) : (
              roles.map((role) => (
                <tr key={role.id}>
                  <td className="role-name-cell">{role.name}</td>
                  <td className="role-desc-cell">{role.description || '-'}</td>
                  <td className="role-perm-count-cell">
                    <span className="role-perm-count">
                      {role.permissions ? role.permissions.length : 0}
                    </span>
                  </td>
                  <td className="role-system-cell">
                    {role.is_system ? (
                      <span className="role-system-badge">System Role</span>
                    ) : (
                      <span style={{ color: 'var(--cds-text-secondary)' }}>Custom</span>
                    )}
                  </td>
                  <td className="role-actions-cell">
                    <div className="role-action-buttons">
                      <PermissionGate permission="update:role">
                        <button
                          className="role-action-btn edit-btn"
                          onClick={() => handleEditRole(role)}
                          title="Edit"
                        >
                          Edit
                        </button>
                      </PermissionGate>
                      <PermissionGate permission="delete:role">
                        {!role.is_system && (
                          <button
                            className="role-action-btn delete-btn"
                            onClick={() => handleDeleteRole(role)}
                            title="Delete"
                          >
                            Delete
                          </button>
                        )}
                      </PermissionGate>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Role Create/Edit Modal */}
      <Modal
        isOpen={showRoleForm}
        onClose={() => {
          setShowRoleForm(false);
          setEditingRole(null);
          setFormError(null);
        }}
        title={editingRole ? `Edit Role: ${editingRole.name}` : 'Create Role'}
      >
        <RoleForm
          role={editingRole}
          permissions={permissions}
          loading={formLoading}
          error={formError}
          onSubmit={async (data) => {
            try {
              setFormLoading(true);
              setFormError(null);
              if (editingRole) {
                await updateRole(editingRole.id, data);
              } else {
                await createRole(data);
              }
              setShowRoleForm(false);
              setEditingRole(null);
              await loadData();
            } catch (err) {
              setFormError(err.message || 'Failed to save role');
            } finally {
              setFormLoading(false);
            }
          }}
          onCancel={() => {
            setShowRoleForm(false);
            setEditingRole(null);
            setFormError(null);
          }}
        />
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={Boolean(showDeleteConfirm)}
        onClose={() => setShowDeleteConfirm(null)}
        title="Delete Role"
      >
        <div className="role-delete-confirm">
          <p className="role-delete-confirm-text">
            Are you sure you want to delete role &quot;{showDeleteConfirm?.name}&quot;? This action cannot be undone.
          </p>
          <div className="role-delete-confirm-actions">
            <button
              className="role-cancel-btn"
              onClick={() => setShowDeleteConfirm(null)}
              disabled={deleteLoading}
            >
              Cancel
            </button>
            <button
              className="role-delete-confirm-btn"
              onClick={confirmDeleteRole}
              disabled={deleteLoading}
            >
              {deleteLoading ? 'Deleting...' : 'Confirm Delete'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

/**
 * RoleForm - sub-component for creating/editing roles
 */
function RoleForm({ role, permissions, loading, error, onSubmit, onCancel }) {
  const isEdit = Boolean(role);
  const isSystem = role?.is_system ?? false;

  const [name, setName] = useState(role?.name || '');
  const [description, setDescription] = useState(role?.description || '');
  const [selectedPermIds, setSelectedPermIds] = useState(() => {
    if (role?.permissions) {
      return role.permissions.map((p) => p.id);
    }
    return [];
  });

  const [expandedGroups, setExpandedGroups] = useState(() => {
    const groups = groupPermissionsByResource(permissions);
    const expanded = {};
    groups.forEach((g) => {
      expanded[g.resource] = true;
    });
    return expanded;
  });

  const handleTogglePerm = (permId) => {
    setSelectedPermIds((prev) =>
      prev.includes(permId)
        ? prev.filter((id) => id !== permId)
        : [...prev, permId]
    );
  };

  const handleToggleGroup = (resource) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [resource]: !prev[resource],
    }));
  };

  const handleSelectAllGroup = (resource, groupPerms) => {
    const groupIds = groupPerms.map((p) => p.id);
    const allSelected = groupIds.every((id) => selectedPermIds.includes(id));
    if (allSelected) {
      setSelectedPermIds((prev) => prev.filter((id) => !groupIds.includes(id)));
    } else {
      setSelectedPermIds((prev) => {
        const newSet = new Set(prev);
        groupIds.forEach((id) => newSet.add(id));
        return [...newSet];
      });
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      name: name.trim(),
      description: description.trim() || null,
      permission_ids: selectedPermIds,
    });
  };

  const grouped = groupPermissionsByResource(permissions);

  return (
    <div className="role-form">
      {error && <div className="role-form-alert">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="role-form-group">
          <label className={`role-form-label ${isSystem ? '' : 'required'}`}>
            Role Name
          </label>
          <input
            type="text"
            className="role-form-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={isSystem}
            required={!isSystem}
            minLength={2}
            maxLength={100}
            placeholder="Enter role name"
          />
        </div>

        <div className="role-form-group" style={{ marginTop: 'var(--cds-spacing-xl)' }}>
          <label className="role-form-label">Description</label>
          <textarea
            className="role-form-textarea"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter role description (optional)"
            rows={3}
          />
        </div>

        <div className="role-form-group" style={{ marginTop: 'var(--cds-spacing-xl)' }}>
          <label className="role-form-label">Permission Configuration</label>
          <div className="permission-selector">
            {grouped.map((group) => (
              <PermissionGroup
                key={group.resource}
                group={group}
                selectedPermIds={selectedPermIds}
                expanded={expandedGroups[group.resource] ?? true}
                onToggleGroup={() => handleToggleGroup(group.resource)}
                onTogglePerm={handleTogglePerm}
                onSelectAll={() => handleSelectAllGroup(group.resource, group.permissions)}
              />
            ))}
          </div>
        </div>

        <div className="role-form-actions">
          <button type="submit" className="role-save-btn" disabled={loading}>
            {loading ? 'Saving...' : isEdit ? 'Update' : 'Create'}
          </button>
          <button type="button" className="role-cancel-btn" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

/**
 * PermissionGroup - renders a collapsible group of permissions by resource
 */
function PermissionGroup({ group, selectedPermIds, expanded, onToggleGroup, onTogglePerm, onSelectAll }) {
  const allSelected = group.permissions.every((p) => selectedPermIds.includes(p.id));

  return (
    <div className="permission-group">
      <div className="permission-group-header" onClick={onToggleGroup}>
        <span>{group.resource}</span>
        <div className="permission-group-header-actions">
          <button
            type="button"
            className="permission-select-all-btn"
            onClick={(e) => {
              e.stopPropagation();
              onSelectAll();
            }}
          >
            {allSelected ? 'Deselect All' : 'Select All'}
          </button>
          <span className={`permission-group-arrow ${expanded ? 'expanded' : ''}`}>
            &#9654;
          </span>
        </div>
      </div>
      {expanded && (
        <div className="permission-group-body">
          {group.permissions.map((perm) => (
            <label key={perm.id} className="permission-checkbox-row">
              <input
                type="checkbox"
                className="permission-checkbox"
                checked={selectedPermIds.includes(perm.id)}
                onChange={() => onTogglePerm(perm.id)}
              />
              <span className="permission-checkbox-label">
                {formatPermission(perm)}
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Group permissions by their resource field.
 * Each permission is expected to have: id, action, resource
 */
function groupPermissionsByResource(perms) {
  if (!Array.isArray(perms)) return [];

  const map = new Map();
  for (const perm of perms) {
    const resource = perm.resource || 'other';
    if (!map.has(resource)) {
      map.set(resource, []);
    }
    map.get(resource).push(perm);
  }

  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([resource, permissions]) => ({
      resource,
      permissions: permissions.sort((x, y) => x.action.localeCompare(y.action)),
    }));
}

/**
 * Format a permission as "action:resource" for display.
 */
function formatPermission(perm) {
  return `${perm.action}:${perm.resource}`;
}

export default RoleManagement;
