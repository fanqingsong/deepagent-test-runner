import { useAuth } from '../contexts/AuthContext';
import { MenuIcon } from './Icons';
import UserDropdown from './UserDropdown';

function AppHeader({ onMenuToggle, isMobileMenuOpen }) {
  const { user } = useAuth();

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      height: 'var(--cds-nav-height)',
      backgroundColor: 'var(--cds-background-inverse)',
      padding: '0 16px',
      borderBottom: '1px solid var(--cds-border-subtle)',
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      zIndex: 1001
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button
          onClick={onMenuToggle}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--cds-text-on-color)',
            cursor: 'pointer',
            padding: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          aria-label="Toggle menu"
        >
          <MenuIcon size={20} />
        </button>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span style={{
            fontSize: '18px',
            fontWeight: 'var(--cds-font-weight-semibold)',
            color: 'var(--cds-text-on-color)',
            letterSpacing: '0.32px'
          }}>
            DeepAgent
          </span>
          <span style={{
            fontSize: '12px',
            color: 'var(--cds-border-subtle)',
            fontWeight: 'var(--cds-font-weight-regular)'
          }}>
            Test Runner
          </span>
        </div>
      </div>

      <UserDropdown />
    </header>
  );
}

export default AppHeader;
