import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { UserIcon, LogoutIcon, CaretDownIcon } from './Icons';

function UserDropdown() {
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const displayName = user?.username || user?.email || 'User';

  const handleProfileClick = () => {
    window.location.hash = 'profile';
    setIsOpen(false);
  };

  const handleLogout = async () => {
    await logout();
    setIsOpen(false);
  };

  return (
    <div ref={dropdownRef} style={{ position: 'relative' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          background: 'transparent',
          color: 'var(--cds-text-on-color)',
          border: 'none',
          cursor: 'pointer',
          fontSize: 'var(--cds-body-short-01)',
          fontWeight: 'var(--cds-font-weight-regular)',
          transition: 'all var(--cds-transition-normal)',
          borderRadius: '0'
        }}
        onMouseEnter={(e) => {
          if (!isOpen) {
            e.target.style.background = 'rgba(255, 255, 255, 0.1)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isOpen) {
            e.target.style.background = 'transparent';
          }
        }}
      >
        <UserIcon size={16} />
        <span>{displayName}</span>
        <CaretDownIcon size={12} style={{
          transition: 'transform var(--cds-transition-normal)',
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)'
        }} />
      </button>

      {isOpen && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 4px)',
          right: 0,
          minWidth: '180px',
          background: 'var(--cds-layer-01, #ffffff)',
          border: '1px solid var(--cds-border-subtle, #e0e0e0)',
          boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
          borderRadius: '0',
          padding: '4px 0',
          zIndex: 1002
        }}>
          <button
            onClick={handleProfileClick}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '10px 16px',
              background: 'transparent',
              color: 'var(--cds-text-primary, #161616)',
              border: 'none',
              cursor: 'pointer',
              fontSize: 'var(--cds-body-short-01, 14px)',
              fontWeight: 'var(--cds-font-weight-regular, 400)',
              textAlign: 'left',
              transition: 'background var(--cds-transition-fast)'
            }}
            onMouseEnter={(e) => {
              e.target.style.background = 'var(--cds-layer-01-hover, #e8e8e8)';
            }}
            onMouseLeave={(e) => {
              e.target.style.background = 'transparent';
            }}
          >
            <UserIcon size={16} />
            <span>My Profile</span>
          </button>

          <div style={{
            height: '1px',
            background: 'var(--cds-border-subtle, #e0e0e0)',
            margin: '4px 0'
          }} />

          <button
            onClick={handleLogout}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '10px 16px',
              background: 'transparent',
              color: 'var(--cds-text-primary, #161616)',
              border: 'none',
              cursor: 'pointer',
              fontSize: 'var(--cds-body-short-01, 14px)',
              fontWeight: 'var(--cds-font-weight-regular, 400)',
              textAlign: 'left',
              transition: 'background var(--cds-transition-fast)'
            }}
            onMouseEnter={(e) => {
              e.target.style.background = 'var(--cds-layer-01-hover, #e8e8e8)';
            }}
            onMouseLeave={(e) => {
              e.target.style.background = 'transparent';
            }}
          >
            <LogoutIcon size={16} />
            <span>Logout</span>
          </button>
        </div>
      )}
    </div>
  );
}

export default UserDropdown;
