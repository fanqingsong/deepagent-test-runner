/**
 * UserList Component
 *
 * Displays a list of users with actions for management.
 * Follows IBM Carbon Design System principles.
 */

import { useState, useEffect } from 'react';
import './UserList.css';

const UserList = ({ refreshKey, onEditUser }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchUsers();
  }, [refreshKey]);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/users', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch users');
      }

      const data = await response.json();
      setUsers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (userId, currentStatus) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_active: !currentStatus }),
      });

      if (!response.ok) {
        throw new Error('Failed to update user');
      }

      fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!confirm(`确定要删除用户 "${username}" 吗？`)) {
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete user');
      }

      fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = (user.username || user.email || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (user.email || '').toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSearch;
  });

  if (loading) {
    return (
      <div className="user-list">
        <div className="empty-state">
          <div className="empty-icon">👥</div>
          <p className="empty-title">加载用户中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="user-list">
        <h2 className="list-title">用户管理</h2>
        <div className="user-list-error">错误: {error}</div>
      </div>
    );
  }

  return (
    <div className="user-list">
      <h2 className="list-title">用户 ({users.length})</h2>

      <div className="list-controls">
        <input
          type="text"
          className="search-input"
          placeholder="搜索用户名或邮箱..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {filteredUsers.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🔍</div>
          <p className="empty-title">没有找到用户</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="user-table">
            <thead>
              <tr>
                <th>用户名</th>
                <th>邮箱</th>
                <th>角色</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
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
                    <div className="user-roles">
                      {user.roles && user.roles.length > 0 ? (
                        user.roles.map((role) => (
                          <span key={role.id} className="role-badge">
                            {role.name}
                          </span>
                        ))
                      ) : (
                        <span className="no-roles">无角色</span>
                      )}
                    </div>
                  </td>
                  <td className="status-cell">
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? '活跃' : '停用'}
                    </span>
                  </td>
                  <td className="created-cell">
                    {new Date(user.created_at).toLocaleDateString('zh-CN')}
                  </td>
                  <td className="actions-cell">
                    <div className="action-buttons">
                      <button
                        onClick={() => onEditUser && onEditUser(user)}
                        className="action-btn edit-btn"
                        title="编辑用户"
                        aria-label="编辑用户"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                        </svg>
                      </button>
                      <button
                        onClick={() => handleToggleActive(user.id, user.is_active)}
                        className={`action-btn ${user.is_active ? 'deactivate-btn' : 'activate-btn'}`}
                        title={user.is_active ? '停用用户' : '激活用户'}
                        aria-label={user.is_active ? '停用用户' : '激活用户'}
                      >
                        {user.is_active ? (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                          </svg>
                        ) : (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4 11H8v-2h8v2z"/>
                          </svg>
                        )}
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user.id, user.username || user.email || 'Unknown')}
                        className="action-btn delete-btn"
                        title="删除用户"
                        aria-label="删除用户"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                        </svg>
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

export default UserList;
