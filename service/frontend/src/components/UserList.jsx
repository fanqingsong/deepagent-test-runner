/**
 * UserList Component
 *
 * Displays a list of users with actions for management,
 * including inline role assignment/removal.
 */

import { useState, useEffect, useRef } from 'react';
import { useUsers } from '../hooks/useUsers';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRoles, assignUserRole, removeUserRole } from '../api';
import './UserList.css';

const UserList = ({ onEditUser }) => {
  const { users, isLoading, isError, error, updateUser, deleteUser, isDeleting } = useUsers();
  const [searchTerm, setSearchTerm] = useState('');

  const handleToggleActive = async (userId, currentStatus) => {
    try {
      await updateUser({ userId, userData: { is_active: !currentStatus } });
    } catch (err) {
      alert(err.message || 'Failed to update user');
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!confirm(`Are you sure you want to delete user "${username}"?`)) {
      return;
    }
    try {
      await deleteUser(userId);
    } catch (err) {
      alert(err.message || 'Failed to delete user');
    }
  };

  const filteredUsers = users.filter((user) => {
    const q = searchTerm.toLowerCase();
    return (
      (user.username || '').toLowerCase().includes(q) ||
      (user.email || '').toLowerCase().includes(q)
    );
  });

  if (isLoading) {
    return (
      <div className="user-list">
        <div className="empty-state">
          <div className="empty-icon">&#128101;</div>
          <p className="empty-title">Loading users...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="user-list">
        <h2 className="list-title">User Management</h2>
        <div className="user-list-error">Error: {error?.message || String(error)}</div>
      </div>
    );
  }

  return (
    <div className="user-list">
      <h2 className="list-title">Users ({users.length})</h2>

      <div className="list-controls">
        <input
          type="text"
          className="search-input"
          placeholder="Search username or email..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {filteredUsers.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">&#128269;</div>
          <p className="empty-title">No users found</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="user-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Email</th>
                <th>Roles</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr key={user.id} className="user-row">
                  <td className="username-cell">
                    <div className="user-username">{user.username || user.email || 'Unknown'}</div>
                  </td>
                  <td className="email-cell">
                    <div className="user-email">{user.email}</div>
                  </td>
                  <td className="roles-cell">
                    <UserRoleCell userId={user.id} roles={user.roles || []} />
                  </td>
                  <td className="status-cell">
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="created-cell">
                    {user.created_at
                      ? new Date(user.created_at).toLocaleDateString('en-US')
                      : '-'}
                  </td>
                  <td className="actions-cell">
                    <div className="action-buttons">
                      <button
                        type="button"
                        className="action-btn edit-btn"
                        onClick={() => onEditUser(user)}
                        title="Edit"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="action-btn toggle-btn"
                        onClick={() => handleToggleActive(user.id, user.is_active)}
                        title={user.is_active ? 'Deactivate' : 'Activate'}
                      >
                        {user.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                      <button
                        type="button"
                        className="action-btn delete-btn"
                        onClick={() => handleDeleteUser(user.id, user.username || user.email)}
                        disabled={isDeleting}
                        title="Delete"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

/**
 * UserRoleCell - displays role badges and provides inline role management
 */
function UserRoleCell({ userId, roles }) {
  const queryClient = useQueryClient();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [operating, setOperating] = useState(false);
  const dropdownRef = useRef(null);

  const rolesQuery = useQuery({
    queryKey: ['all-roles'],
    queryFn: getRoles,
    staleTime: 30000,
  });

  const assignMutation = useMutation({
    mutationFn: ({ userId, roleId }) => assignUserRole(userId, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: ({ userId, roleId }) => removeUserRole(userId, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  // Close dropdown on outside click
  useEffect(() => {
    if (!dropdownOpen) return;
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [dropdownOpen]);

  const allRoles = Array.isArray(rolesQuery.data) ? rolesQuery.data : [];
  const assignedRoleIds = new Set(roles.map((r) => r.id));

  const handleAssign = async (roleId) => {
    try {
      setOperating(true);
      await assignMutation.mutateAsync({ userId, roleId });
    } catch (err) {
      alert(err.message || 'Failed to assign role');
    } finally {
      setOperating(false);
    }
  };

  const handleRemove = async (roleId) => {
    try {
      setOperating(true);
      await removeMutation.mutateAsync({ userId, roleId });
    } catch (err) {
      alert(err.message || 'Failed to remove role');
    } finally {
      setOperating(false);
    }
  };

  return (
    <div className="user-roles" ref={dropdownRef}>
      {roles.length > 0 ? (
        roles.map((role) => (
          <span key={role.id} className="role-badge">
            {role.name}
          </span>
        ))
      ) : (
        <span className="no-roles">No roles</span>
      )}
      <div className="user-role-dropdown">
        <button
          type="button"
          className="user-role-dropdown-btn"
          onClick={() => setDropdownOpen((prev) => !prev)}
          disabled={operating}
          title="Assign roles"
        >
          {dropdownOpen ? '▲' : '▼'}
        </button>
        {dropdownOpen && (
          <div className="user-role-dropdown-menu">
            {allRoles.length === 0 ? (
              <div style={{ padding: '8px 12px', color: 'var(--cds-text-placeholder)', fontSize: '12px' }}>
                No available roles
              </div>
            ) : (
              allRoles.map((role) => {
                const isAssigned = assignedRoleIds.has(role.id);
                return (
                  <div key={role.id} className={`user-role-dropdown-item ${isAssigned ? 'has-role' : ''}`}>
                    <span>{role.name}</span>
                    {isAssigned ? (
                      <button
                        type="button"
                        className="user-role-remove-btn"
                        onClick={() => handleRemove(role.id)}
                        disabled={operating}
                      >
                        Remove
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="user-role-assign-btn"
                        onClick={() => handleAssign(role.id)}
                        disabled={operating}
                      >
                        Assign
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default UserList;
