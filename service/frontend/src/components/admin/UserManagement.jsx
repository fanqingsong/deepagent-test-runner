/**
 * UserManagement Component
 *
 * Admin interface for managing user accounts.
 * Provides user list with suspend/reactivate controls.
 * WCAG 2.1 Level AA compliant.
 */

import { useState, useEffect } from 'react';
import { SuspendIcon, ReactivateIcon } from '../Icons';
import './UserManagement.css';

function UserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const sessionToken = localStorage.getItem('session_token');
      const response = await fetch('/api/v1/admin/users', {
        headers: { 'X-Session-Token': sessionToken },
      });
      if (!response.ok) throw new Error('Failed to fetch users');
      const data = await response.json();
      setUsers(data.users || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const handleSuspend = async (userId, userEmail) => {
    const reason = prompt(`Enter reason for suspending ${userEmail}:`);
    if (!reason || !reason.trim()) return;
    try {
      const sessionToken = localStorage.getItem('session_token');
      const response = await fetch(`/api/v1/admin/users/${userId}/suspend`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': sessionToken,
        },
        body: JSON.stringify({ reason: reason.trim() }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to suspend user');
      }
      setSuccess(`User ${userEmail} has been suspended`);
      setTimeout(() => setSuccess(''), 3000);
      fetchUsers();
    } catch (err) {
      setError(err.message || 'Failed to suspend user');
    }
  };

  const handleReactivate = async (userId, userEmail) => {
    if (!confirm(`Reactivate ${userEmail}?`)) return;
    try {
      const sessionToken = localStorage.getItem('session_token');
      const response = await fetch(`/api/v1/admin/users/${userId}/reactivate`, {
        method: 'POST',
        headers: { 'X-Session-Token': sessionToken },
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to reactivate user');
      }
      setSuccess(`User ${userEmail} has been reactivated`);
      setTimeout(() => setSuccess(''), 3000);
      fetchUsers();
    } catch (err) {
      setError(err.message || 'Failed to reactivate user');
    }
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === 'all' || 
      (filterStatus === 'active' && user.status === 'active') ||
      (filterStatus === 'suspended' && user.status !== 'active');
    return matchesSearch && matchesStatus;
  });

  if (loading) {
    return (
      <div className="user-management-loading" aria-live="polite">
        <div className="spinner" aria-hidden="true"></div>
        <span>Loading users...</span>
      </div>
    );
  }

  return (
    <div className="user-management">
      <div className="user-management-header">
        <h1>User Management</h1>
        <p>Manage user accounts and permissions</p>
      </div>

      {error && (
        <div className="error-message" role="alert" aria-live="assertive">{error}</div>
      )}

      {success && (
        <div className="success-message" role="status" aria-live="polite">{success}</div>
      )}

      <div className="user-management-controls">
        <div className="search-box">
          <label htmlFor="user-search">Search Users</label>
          <input
            id="user-search"
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by email..."
          />
        </div>

        <div className="filter-box">
          <label htmlFor="status-filter">Status</label>
          <select
            id="status-filter"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="all">All Users</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
      </div>

      <div className="users-table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Status</th>
              <th>Created</th>
              <th>Last Login</th>
              <th>MFA</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.length === 0 ? (
              <tr><td colSpan="6" className="no-users">
                {searchTerm || filterStatus !== 'all' ? 'No users match your filters' : 'No users found'}
              </td></tr>
            ) : (
              filteredUsers.map((user) => (
                <tr key={user.id}>
                  <td>{user.email}</td>
                  <td>
                    <span className={`status-badge ${user.status === 'active' ? 'status-active' : 'status-suspended'}`}>
                      {user.status === 'active' ? 'Active' : 'Suspended'}
                    </span>
                  </td>
                  <td>{new Date(user.created_at).toLocaleDateString()}</td>
                  <td>{user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}</td>
                  <td>{user.mfa_enabled ? 'Enabled' : 'Disabled'}</td>
                  <td>
                    <div className="action-buttons">
                      {user.status === 'active' ? (
                        <button
                          className="btn-icon btn-suspend"
                          onClick={() => handleSuspend(user.id, user.email)}
                          title="Suspend"
                          aria-label={`Suspend ${user.email}`}
                        >
                          <SuspendIcon size={16} />
                        </button>
                      ) : (
                        <button
                          className="btn-icon btn-reactivate"
                          onClick={() => handleReactivate(user.id, user.email)}
                          title="Reactivate"
                          aria-label={`Reactivate ${user.email}`}
                        >
                          <ReactivateIcon size={16} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default UserManagement;
