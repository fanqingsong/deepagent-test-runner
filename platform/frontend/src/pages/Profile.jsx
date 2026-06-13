import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import authService from '../services/authService';
import Toast from '../components/Toast';

function Profile() {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [profileData, setProfileData] = useState({
    username: '',
    email: ''
  });
  const [toast, setToast] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      setIsLoading(true);
      try {
        const data = await authService.getCurrentUser();
        setProfileData({
          username: data.username || '',
          email: data.email || ''
        });
      } catch (error) {
        showToast('error', 'Failed to load profile');
      } finally {
        setIsLoading(false);
      }
    };

    fetchProfile();
  }, []);

  const showToast = (type, message) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3000);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);

    try {
      await authService.updateProfile({
        username: profileData.username
      });

      showToast('success', 'Profile updated successfully');
      setIsEditing(false);
    } catch (error) {
      const errorMsg = error.message || 'Failed to update profile';
      showToast('error', errorMsg);
    } finally {
      setIsSaving(false);
    }
  };

  const handleEditClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsEditing(true);
  };

  const handleCancel = () => {
    // Reset to original values
    setProfileData({
      username: user?.username || '',
      email: user?.email || ''
    });
    setIsEditing(false);
  };

  if (isLoading) {
    return (
      <div style={{
        padding: 'var(--cds-layout-sm)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '400px'
      }}>
        <div style={{ color: 'var(--cds-text-secondary)' }}>Loading...</div>
      </div>
    );
  }

  return (
    <div style={{
      padding: 'var(--cds-layout-sm)',
      background: 'var(--cds-background)',
      minHeight: 'calc(100vh - 48px)'
    }}>
      {toast && (
        <Toast
          type={toast.type}
          message={toast.message}
          onClose={() => setToast(null)}
        />
      )}

      <div style={{
        maxWidth: '600px',
        margin: '0 auto'
      }}>
        <h1 style={{
          fontSize: 'var(--cds-heading-01)',
          fontWeight: 'var(--cds-font-weight-light)',
          lineHeight: 'var(--cds-display-line-height)',
          marginBottom: 'var(--cds-layout-md)',
          color: 'var(--cds-text-primary)'
        }}>
          My Profile
        </h1>

        <div style={{
          background: 'var(--cds-layer-01)',
          padding: 'var(--cds-layout-md)',
          border: 'none'
        }}>
          <form onSubmit={handleSave}>
            <div style={{ marginBottom: 'var(--cds-layout-md)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--cds-label-01)',
                fontWeight: 'var(--cds-font-weight-regular)',
                letterSpacing: '0.32px',
                color: 'var(--cds-text-secondary)',
                marginBottom: '8px'
              }}>
                Username
              </label>
              <input
                type="text"
                name="username"
                value={profileData.username}
                onChange={handleInputChange}
                disabled={!isEditing}
                required
                style={{
                  width: '100%',
                  height: 'var(--cds-input-height, 40px)',
                  padding: '0 16px',
                  background: 'var(--cds-field, #f4f4f4)',
                  color: 'var(--cds-text-primary, #161616)',
                  border: 'none',
                  borderBottom: isEditing
                    ? '2px solid var(--cds-focus, #0f62fe)'
                    : '2px solid var(--cds-border-subtle, #c6c6c6)',
                  fontSize: 'var(--cds-body-long-01, 16px)',
                  borderRadius: '0',
                  cursor: isEditing ? 'text' : 'not-allowed'
                }}
              />
            </div>

            <div style={{ marginBottom: 'var(--cds-layout-md)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--cds-label-01)',
                fontWeight: 'var(--cds-font-weight-regular)',
                letterSpacing: '0.32px',
                color: 'var(--cds-text-secondary)',
                marginBottom: '8px'
              }}>
                Email
              </label>
              <input
                type="email"
                value={profileData.email}
                disabled
                style={{
                  width: '100%',
                  height: 'var(--cds-input-height, 40px)',
                  padding: '0 16px',
                  background: 'var(--cds-field, #f4f4f4)',
                  color: 'var(--cds-text-primary, #161616)',
                  border: 'none',
                  borderBottom: '2px solid var(--cds-border-subtle, #c6c6c6)',
                  fontSize: 'var(--cds-body-long-01, 16px)',
                  borderRadius: '0',
                  cursor: 'not-allowed'
                }}
              />
              <p style={{
                fontSize: 'var(--cds-helper-text, 12px)',
                color: 'var(--cds-text-secondary, #525252)',
                marginTop: '4px'
              }}>
                Contact administrator to change email
              </p>
            </div>

            <div style={{ marginBottom: 'var(--cds-layout-md)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--cds-label-01)',
                fontWeight: 'var(--cds-font-weight-regular)',
                letterSpacing: '0.32px',
                color: 'var(--cds-text-secondary)',
                marginBottom: '8px'
              }}>
                Roles
              </label>
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '8px'
              }}>
                {user?.roles && user.roles.length > 0 ? (
                  user.roles.map((role) => (
                    <span
                      key={role}
                      style={{
                        padding: '4px 8px',
                        background: 'var(--cds-tag-blue, #edf5ff)',
                        color: 'var(--cds-link-primary, #0f62fe)',
                        borderRadius: '24px',
                        fontSize: 'var(--cds-caption-01, 12px)',
                        fontWeight: 'var(--cds-font-weight-regular, 400)'
                      }}
                    >
                      {role}
                    </span>
                  ))
                ) : (
                  <span style={{
                    fontSize: 'var(--cds-body-short-01, 14px)',
                    color: 'var(--cds-text-secondary, #525252)'
                  }}>
                    No roles assigned
                  </span>
                )}
              </div>
            </div>

            <div style={{ marginBottom: 'var(--cds-layout-md)' }}>
              <label style={{
                display: 'block',
                fontSize: 'var(--cds-label-01)',
                fontWeight: 'var(--cds-font-weight-regular)',
                letterSpacing: '0.32px',
                color: 'var(--cds-text-secondary)',
                marginBottom: '8px'
              }}>
                Account Status
              </label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: user?.is_active ? 'var(--cds-support-success, #24a148)' : 'var(--cds-support-error, #da1e28)'
                }} />
                <span style={{
                  fontSize: 'var(--cds-body-short-01, 14px)',
                  color: 'var(--cds-text-primary, #161616)'
                }}>
                  {user?.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>

            <div style={{
              display: 'flex',
              gap: '16px',
              marginTop: 'var(--cds-layout-lg)'
            }}>
              {!isEditing ? (
                <button
                  type="button"
                  onClick={handleEditClick}
                  style={{
                    padding: 'var(--cds-button-padding-sm, 14px 16px)',
                    background: 'var(--cds-button-primary, #0f62fe)',
                    color: 'var(--cds-text-on-color, #ffffff)',
                    border: 'none',
                    borderRadius: '0',
                    cursor: 'pointer',
                    fontSize: 'var(--cds-body-short-01, 14px)',
                    fontWeight: 'var(--cds-font-weight-regular, 400)',
                    height: 'var(--cds-button-height, 48px)'
                  }}
                >
                  Edit Profile
                </button>
              ) : (
                <>
                  <button
                    type="submit"
                    disabled={isSaving}
                    style={{
                      padding: 'var(--cds-button-padding-sm, 14px 16px)',
                      background: isSaving
                        ? 'var(--cds-button-primary-disabled, #8d8d8d)'
                        : 'var(--cds-button-primary, #0f62fe)',
                      color: 'var(--cds-text-on-color, #ffffff)',
                      border: 'none',
                      borderRadius: '0',
                      cursor: isSaving ? 'not-allowed' : 'pointer',
                      fontSize: 'var(--cds-body-short-01, 14px)',
                      fontWeight: 'var(--cds-font-weight-regular, 400)',
                      height: 'var(--cds-button-height, 48px)'
                    }}
                  >
                    {isSaving ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    type="button"
                    onClick={handleCancel}
                    disabled={isSaving}
                    style={{
                      padding: 'var(--cds-button-padding-sm, 14px 16px)',
                      background: 'transparent',
                      color: 'var(--cds-link-primary, #0f62fe)',
                      border: 'none',
                      cursor: isSaving ? 'not-allowed' : 'pointer',
                      fontSize: 'var(--cds-body-short-01, 14px)',
                      fontWeight: 'var(--cds-font-weight-regular, 400)',
                      height: 'var(--cds-button-height, 48px)'
                    }}
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Profile;
