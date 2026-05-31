/**
 * UserForm Component
 *
 * Form for creating and editing users, including role assignment.
 * Follows IBM Carbon Design System principles.
 */

import { useState, useEffect } from 'react';
import { getRoles } from '../api';
import './UserForm.css';

const UserForm = ({ user = null, onSuccess, onCancel }) => {
  const isEdit = Boolean(user);
  const [formData, setFormData] = useState({
    username: user?.username || '',
    email: user?.email || '',
    password: '',
    is_active: user?.is_active ?? true,
  });
  const [selectedRoleIds, setSelectedRoleIds] = useState(() => {
    if (user?.roles) {
      return user.roles.map((r) => r.id);
    }
    return [];
  });
  const [availableRoles, setAvailableRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const loadRoles = async () => {
      try {
        const rolesData = await getRoles();
        if (!cancelled) {
          setAvailableRoles(Array.isArray(rolesData) ? rolesData : []);
        }
      } catch {
        // Non-critical: roles will just be empty
      }
    };
    loadRoles();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleToggleRole = (roleId) => {
    setSelectedRoleIds((prev) =>
      prev.includes(roleId)
        ? prev.filter((id) => id !== roleId)
        : [...prev, roleId]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const url = user
        ? `/api/v1/users/${user.id}`
        : '/api/v1/users';
      const method = user ? 'PUT' : 'POST';

      const payload = {
        ...formData,
        role_ids: selectedRoleIds,
      };

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save user');
      }

      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="user-form">
      {error && (
        <div className="form-alert error">
          <span className="form-alert-icon">&#9888;</span>
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Account Information */}
        <div className="user-form-section">
          <h3 className="user-form-section-title">Account Information</h3>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="username" className="form-label required">
                Username
              </label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleChange}
                required
                minLength={3}
                maxLength={100}
                className="form-input"
                disabled={isEdit}
                placeholder="e.g. johndoe"
              />
            </div>

            <div className="form-group">
              <label htmlFor="email" className="form-label required">
                Email
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                className="form-input"
                placeholder="e.g. john@example.com"
              />
            </div>
          </div>

          {!isEdit && (
            <div className="form-group" style={{ marginTop: 'var(--cds-spacing-lg)' }}>
              <label htmlFor="password" className="form-label required">
                Password
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                minLength={8}
                maxLength={100}
                className="form-input"
                placeholder="At least 8 characters"
              />
            </div>
          )}

          <label className="form-toggle" style={{ marginTop: 'var(--cds-spacing-lg)' }}>
            <input
              type="checkbox"
              name="is_active"
              checked={formData.is_active}
              onChange={handleChange}
            />
            <span className={`form-toggle-track ${formData.is_active ? 'active' : ''}`} />
            <div>
              <div className="form-toggle-label">
                {formData.is_active ? 'Active' : 'Inactive'}
              </div>
              <div className="form-toggle-helper">
                {formData.is_active
                  ? 'User can log in and use the system'
                  : 'User account is disabled'}
              </div>
            </div>
          </label>
        </div>

        {/* Role Assignment */}
        <div className="user-form-section">
          <h3 className="user-form-section-title">Role Assignment</h3>
          {availableRoles.length === 0 ? (
            <span style={{ color: 'var(--cds-text-placeholder)', fontSize: 'var(--cds-body-short-02)' }}>
              No available roles
            </span>
          ) : (
            <div className="user-form-roles">
              {availableRoles.map((role) => (
                <label key={role.id} className="user-form-role-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedRoleIds.includes(role.id)}
                    onChange={() => handleToggleRole(role.id)}
                  />
                  <span className="user-form-role-name">{role.name}</span>
                  {role.is_system && (
                    <span className="user-form-role-system">System</span>
                  )}
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="form-actions">
          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Saving...' : isEdit ? 'Update' : 'Create'}
          </button>
          {onCancel && (
            <button type="button" onClick={onCancel} className="cancel-button">
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  );
};

export default UserForm;
