import { useState, useEffect, useRef, useCallback } from 'react';
import PermissionGate from './PermissionGate';
import {
  DashboardIcon,
  TestCasesIcon,
  TestSuiteIcon,
  SettingsIcon,
  ChevronLeftIcon,
  ChevronRightIcon
} from './Icons';

// Weather icon for sidebar
const WeatherIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M10 2a4 4 0 0 1 4 4 4 4 0 0 1 4 4 3 3 0 0 1 0 6H6a3 3 0 0 1 0-6 4 4 0 0 1 4-4zm0 2a2 2 0 0 0-2 2 2 2 0 0 0 2 2 2 2 0 0 0 2-2 2 2 0 0 0-2-2z"/>
  </svg>
);

// Monitoring icon for sidebar
const MonitoringIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M10 2a8 8 0 0 1 8 8 8 8 0 0 1-8 8zm0 2a6 6 0 0 0-6 6 6 6 0 0 0 6-6zm1 5H9v-2h2v2zm0-4H9v2h2V5z"/>
  </svg>
);

// Token Management icon for sidebar
const TokenIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 20 20" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M10 2a8 8 0 0 1 8 8 8 8 0 0 1-8 8zm0 2a6 6 0 0 0-6 6 6 6 0 0 0 6-6zm1 5H9v-2h2v2zm0-4H9v2h2V5z"/>
    <circle cx="10" cy="10" r="3" fill="currentColor"/>
    <path d="M10 6a4 4 0 1 0 0 8 4 4 0 0 0 0-8zm0 6a2 2 0 1 1 0-4 2 2 0 0 1 0 4z" fill="currentColor"/>
  </svg>
);

import './Sidebar.css';

const menuItems = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: DashboardIcon,
    path: '#dashboard'
  },
  {
    id: 'test-cases',
    label: 'Test Cases',
    icon: TestCasesIcon,
    permission: 'read:test-case',
    children: [
      {
        id: 'test-cases-marketplace',
        label: 'Marketplace',
        path: '#test-cases-marketplace'
      },
      {
        id: 'test-cases-workspace',
        label: 'My Workspace',
        path: '#test-cases'
      }
    ]
  },
  {
    id: 'suites',
    label: 'Test Suites',
    icon: TestSuiteIcon,
    children: [
      {
        id: 'suites-marketplace',
        label: 'Marketplace',
        path: '#suites-marketplace'
      },
      {
        id: 'suites-workspace',
        label: 'My Workspace',
        path: '#suites'
      }
    ]
  },
  {
    id: 'token-management',
    label: 'Token Management',
    icon: TokenIcon,
    children: [
      {
        id: 'token-usage',
        label: 'Usage Dashboard',
        path: '#token-usage'
      },
      {
        id: 'token-budget',
        label: 'Budget Management',
        path: '#token-budget'
      },
      {
        id: 'token-quota',
        label: 'Quota Management',
        path: '#token-quota'
      },
      {
        id: 'token-alert',
        label: 'Alert Management',
        path: '#token-alert'
      },
      {
        id: 'token-analytics',
        label: 'Token Analytics',
        path: '#token-analytics'
      }
    ]
  },
  {
    id: 'admin',
    label: 'System Management',
    icon: SettingsIcon,
    children: [
      {
        id: 'profile',
        label: 'My Profile',
        path: '#profile'
      },
      {
        id: 'users',
        label: 'User Management',
        path: '#users',
        anyPermission: ['read:user', 'create:user']
      },
      {
        id: 'roles',
        label: 'Role Management',
        path: '#roles',
        anyPermission: ['read:role', 'create:role']
      },
      {
        id: 'reviews',
        label: 'Review Management',
        path: '#reviews',
        anyPermission: ['review:test', 'review:suite']
      },
      {
        id: 'chat-monitor',
        label: 'Chat Monitor',
        path: '#chat-monitor'
      },
      {
        id: 'monitoring',
        label: 'System Monitoring',
        path: '#monitoring'
      },
      {
        id: 'nanjing-weather',
        label: 'Nanjing Weather',
        path: '#nanjing-weather'
      }
    ]
  }
];

function SidebarSubmenuEntry({ child, activePath, onClick, expandedSubmenus, onSubmenuToggle }) {
  const hasNestedChildren = child.children?.length > 0;
  const isNestedExpanded = expandedSubmenus.has(child.id);

  if (hasNestedChildren) {
    return (
      <li className="sidebar-submenu-group">
        <button
          type="button"
          className={`sidebar-submenu-group-header ${isNestedExpanded ? 'expanded' : ''}`}
          onClick={(e) => {
            e.preventDefault();
            onSubmenuToggle(child.id);
          }}
        >
          <span className="sidebar-item-text">{child.label}</span>
          <span className={`sidebar-chevron ${isNestedExpanded ? 'expanded' : ''}`}>
            <ChevronRightIcon size={12} />
          </span>
        </button>
        <ul className={`sidebar-nested-submenu ${isNestedExpanded ? 'expanded' : ''}`}>
          {child.children.map((nested) => (
            <li key={nested.id} className="sidebar-submenu-item nested">
              <PermissionGate permission={nested.permission} anyPermission={nested.anyPermission}>
                <a
                  href={nested.path}
                  className={`sidebar-item ${activePath === nested.path.slice(1) ? 'active' : ''}`}
                  onClick={(e) => {
                    e.preventDefault();
                    onClick(nested.path);
                  }}
                >
                  <span className="sidebar-item-text">{nested.label}</span>
                </a>
              </PermissionGate>
            </li>
          ))}
        </ul>
      </li>
    );
  }

  return (
    <li className="sidebar-submenu-item">
      <PermissionGate permission={child.permission} anyPermission={child.anyPermission}>
        <a
          href={child.path}
          className={`sidebar-item ${activePath === child.path?.slice(1) ? 'active' : ''}`}
          onClick={(e) => {
            e.preventDefault();
            onClick(child.path);
          }}
        >
          <span className="sidebar-item-text">{child.label}</span>
        </a>
      </PermissionGate>
    </li>
  );
}

function SidebarPopupEntry({ child, onClick, onClose }) {
  if (child.children?.length) {
    return (
      <li key={child.id} className="submenu-popup-group">
        <div className="submenu-popup-section-label">{child.label}</div>
        <ul className="submenu-popup-nested-list">
          {child.children.map((nested) => (
            <li key={nested.id}>
              <PermissionGate permission={nested.permission} anyPermission={nested.anyPermission}>
                <a
                  href={nested.path}
                  className={`submenu-popup-item ${nested.path === `#${window.location.hash.slice(1)}` ? 'active' : ''}`}
                  onClick={(e) => {
                    e.preventDefault();
                    onClick(nested.path);
                    onClose();
                  }}
                >
                  {nested.label}
                </a>
              </PermissionGate>
            </li>
          ))}
        </ul>
      </li>
    );
  }

  return (
    <li key={child.id}>
      <PermissionGate permission={child.permission} anyPermission={child.anyPermission}>
        <a
          href={child.path}
          className={`submenu-popup-item ${child.path === `#${window.location.hash.slice(1)}` ? 'active' : ''}`}
          onClick={(e) => {
            e.preventDefault();
            onClick(child.path);
            onClose();
          }}
        >
          {child.label}
        </a>
      </PermissionGate>
    </li>
  );
}

function SidebarItem({ item, isExpanded, isActive, onClick, onSubmenuToggle, expandedSubmenus, activePath }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [showSubmenuPopup, setShowSubmenuPopup] = useState(false);
  const itemRef = useRef(null);
  const popupRef = useRef(null);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0 });
  const [popupPosition, setPopupPosition] = useState({ top: 0 });
  const hideTimeoutRef = useRef(null);

  const hasChildren = item.children && item.children.length > 0;
  const isSubmenuExpanded = expandedSubmenus.has(item.id);

  const handleClick = (e) => {
    e.preventDefault();
    if (hasChildren && isExpanded) {
      onSubmenuToggle(item.id);
    } else if (!hasChildren) {
      onClick(item.path);
    }
  };

  const handleMouseEnter = () => {
    // Clear any pending hide timeout
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }

    if (!isExpanded && itemRef.current) {
      const rect = itemRef.current.getBoundingClientRect();
      setTooltipPosition({ top: rect.top + rect.height / 2 - 12 });
      if (hasChildren) {
        setPopupPosition({ top: rect.top });
        setShowSubmenuPopup(true);
      } else {
        setShowTooltip(true);
      }
    }
  };

  const handleMouseLeave = (e) => {
    // Use a small delay before hiding to allow moving to the popup
    hideTimeoutRef.current = setTimeout(() => {
      setShowTooltip(false);
      setShowSubmenuPopup(false);
    }, 100);
  };

  const handlePopupMouseEnter = () => {
    // Clear the hide timeout when entering the popup
    if (hideTimeoutRef.current) {
      clearTimeout(hideTimeoutRef.current);
      hideTimeoutRef.current = null;
    }
  };

  const handlePopupMouseLeave = () => {
    // Hide the popup after leaving it
    setShowSubmenuPopup(false);
  };

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current);
      }
    };
  }, []);

  const IconComponent = item.icon;

  const content = (
    <>
      <div className="sidebar-item-icon">
        <IconComponent size={20} />
      </div>
      <span className="sidebar-item-text">{item.label}</span>
      {hasChildren && (
        <div className={`sidebar-chevron ${isSubmenuExpanded ? 'expanded' : ''}`}>
          <ChevronRightIcon size={16} />
        </div>
      )}
    </>
  );

  const wrappedContent = item.permission || item.anyPermission ? (
    <PermissionGate permission={item.permission} anyPermission={item.anyPermission}>
      {content}
    </PermissionGate>
  ) : content;

  return (
    <>
      <li className={hasChildren ? 'sidebar-parent-item' : ''}>
        <a
          ref={itemRef}
          href={hasChildren ? undefined : item.path}
          className={`sidebar-item ${isActive ? 'active' : ''}`}
          onClick={handleClick}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          {wrappedContent}
        </a>
        {showTooltip && !isExpanded && !hasChildren && (
          <div
            className="tooltip visible"
            style={{ top: `${tooltipPosition.top}px` }}
          >
            {item.label}
          </div>
        )}
      </li>
      {isExpanded && hasChildren && (
        <ul className={`sidebar-submenu ${isSubmenuExpanded ? 'expanded' : ''}`}>
          {item.children.map((child) => (
            <SidebarSubmenuEntry
              key={child.id}
              child={child}
              activePath={activePath}
              onClick={onClick}
              expandedSubmenus={expandedSubmenus}
              onSubmenuToggle={onSubmenuToggle}
            />
          ))}
        </ul>
      )}
      {!isExpanded && hasChildren && showSubmenuPopup && (
        <div
          ref={popupRef}
          className="submenu-popup"
          style={{ top: `${popupPosition.top}px` }}
          onMouseEnter={handlePopupMouseEnter}
          onMouseLeave={handlePopupMouseLeave}
        >
          <div className="submenu-popup-header">{item.label}</div>
          <ul className="submenu-popup-list">
            {item.children.map((child) => (
              <SidebarPopupEntry
                key={child.id}
                child={child}
                onClick={onClick}
                onClose={() => setShowSubmenuPopup(false)}
              />
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

function Sidebar({ isOpen, isCollapsed, onToggle, onMobileClose, isDesktop }) {
  const [activePath, setActivePath] = useState('');
  const [expandedSubmenus, setExpandedSubmenus] = useState(
    new Set(['test-cases', 'suites', 'token-management'])
  );

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1) || 'dashboard';
      setActivePath(hash);

      const expanded = new Set(['test-cases', 'suites', 'token-management']);

      for (const item of menuItems) {
        if (item.children?.some((child) => child.path === `#${hash}`)) {
          expanded.add(item.id);
        }
        for (const child of item.children || []) {
          if (child.children?.some((nested) => nested.path === `#${hash}`)) {
            expanded.add(item.id);
            expanded.add(child.id);
          }
        }
      }

      setExpandedSubmenus(expanded);
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleItemClick = (path) => {
    if (!path) return;
    window.location.hash = path;
    if (!isDesktop) {
      onMobileClose();
    }
  };

  const handleSubmenuToggle = (itemId) => {
    setExpandedSubmenus(prev => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  const isItemActive = (item) => {
    if (item.children) {
      return item.children.some((child) => {
        if (child.path === `#${activePath}`) return true;
        return child.children?.some((nested) => nested.path === `#${activePath}`);
      });
    }
    return item.path === `#${activePath}`;
  };

  return (
    <>
      <aside
        className={`sidebar ${isOpen ? 'expanded' : 'collapsed'} ${isCollapsed ? 'collapsed' : ''}`}
      >
        <div className="sidebar-header">
          <button
            className={`sidebar-toggle ${isCollapsed ? 'collapsed' : ''}`}
            onClick={onToggle}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <ChevronLeftIcon size={20} />
          </button>
        </div>
        <ul className="sidebar-menu">
          {menuItems.map((item) => (
            <SidebarItem
              key={item.id}
              item={item}
              isExpanded={!isCollapsed}
              isActive={isItemActive(item)}
              activePath={activePath}
              onClick={handleItemClick}
              onSubmenuToggle={handleSubmenuToggle}
              expandedSubmenus={expandedSubmenus}
            />
          ))}
        </ul>
      </aside>
      <div
        className={`sidebar-backdrop ${isOpen && !isDesktop ? 'visible' : ''}`}
        onClick={onMobileClose}
      />
    </>
  );
}

export default Sidebar;
