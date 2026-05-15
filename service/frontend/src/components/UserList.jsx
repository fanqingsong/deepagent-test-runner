/**
 * UserList Component
 *
 * Displays a list of users with actions for management.
 */

import { useState } from 'react';
import { useUsers } from '../hooks/useUsers';
import './UserList.css';

const UserList = ({ onEditUser }) => {
  const { users, isLoading, isError, error, updateUser, deleteUser, isDeleting } = useUsers();
  const [searchTerm, setSearchTerm] = useState('');

  const handleToggleActive = async (userId, currentStatus) => {
    try {
      await updateUser({ userId, userData: { is_active: !currentStatus } });
    } catch (err) {
      alert(err.message || '更新用户失败');
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!confirm(`确定要删除用户 "${username}" 吗？`)) {
      return;
    }
    try {
      await deleteUser(userId);
    } catch (err) {
      alert(err.message || '删除用户失败');
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
          <div className="empty-icon">👥</div>
          <p className="empty-title">加载用户中...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="user-list">
        <h2 className="list-title">用户管理</h2>
        <div className="user-list-error">错误: {error?.message || String(error)}</div>
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
                    {user.created_at
                      ? new Date(user.created_at).toLocaleDateString('zh-CN')
                      : '-'}
                  </td>
                  <td className="actions-cell">
                    <div className="action-buttons">
                      <button
                        type="button"
                        className="action-btn edit-btn"
                        onClick={() => onEditUser(user)}
                        title="编辑"
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        className="action-btn toggle-btn"
                        onClick={() => handleToggleActive(user.id, user.is_active)}
                        title={user.is_active ? '停用' : '启用'}
                      >
                        {user.is_active ? '停用' : '启用'}
                      </button>
                      <button
                        type="button"
                        className="action-btn delete-btn"
                        onClick={() => handleDeleteUser(user.id, user.username || user.email)}
                        disabled={isDeleting}
                        title="删除"
                      >
                        删除
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
