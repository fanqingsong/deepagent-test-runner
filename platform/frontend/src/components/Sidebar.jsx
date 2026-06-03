import { useState, useEffect, useRef } from 'react';
import PermissionGate from './PermissionGate';
import {
  DashboardIcon,
  TestCasesIcon,
  TestSuiteIcon,
  SettingsIcon,
  ChevronLeftIcon,
  ChevronRightIcon
} from './Icons';
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
    permission: 'read:app',
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
      }
    ]
  }
];

function SidebarItem({ item, isExpanded, isActive, onClick, onSubmenuToggle, expandedSubmenus }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const itemRef = useRef(null);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0 });

  const hasChildren = item.children && item.children.length > 0;
  const isSubmenuExpanded = expandedSubmenus.has(item.id);

  const handleClick = (e) => {
    e.preventDefault();
    if (hasChildren) {
      onSubmenuToggle(item.id);
    } else {
      onClick(item.path);
    }
  };

  const handleMouseEnter = () => {
    if (!isExpanded && itemRef.current) {
      const rect = itemRef.current.getBoundingClientRect();
      setTooltipPosition({ top: rect.top + rect.height / 2 - 12 });
      setShowTooltip(true);
    }
  };

  const handleMouseLeave = () => {
    setShowTooltip(false);
  };

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
        {showTooltip && !isExpanded && (
          <div
            className="tooltip visible"
            style={{ top: `${tooltipPosition.top}px` }}
          >
            {item.label}
          </div>
        )}
      </li>
      {hasChildren && (
        <ul className={`sidebar-submenu ${isSubmenuExpanded ? 'expanded' : ''}`}>
          {item.children.map((child) => (
            <li key={child.id} className="sidebar-submenu-item">
              <PermissionGate permission={child.permission} anyPermission={child.anyPermission}>
                <a
                  href={child.path}
                  className={`sidebar-item ${isActive ? 'active' : ''}`}
                  onClick={(e) => {
                    e.preventDefault();
                    onClick(child.path);
                  }}
                >
                  <span className="sidebar-item-text">{child.label}</span>
                </a>
              </PermissionGate>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function Sidebar({ isOpen, isCollapsed, onToggle, onMobileClose, isDesktop }) {
  const [activePath, setActivePath] = useState('');
  const [expandedSubmenus, setExpandedSubmenus] = useState(new Set(['admin', 'test-cases', 'suites']));

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1) || 'dashboard';
      setActivePath(hash);

      const parentItem = menuItems.find(item =>
        item.children?.some(child => child.path === `#${hash}`)
      );
      if (parentItem) {
        setExpandedSubmenus(prev => new Set([...prev, parentItem.id]));
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleItemClick = (path) => {
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
      return item.children.some(child => child.path === `#${activePath}`);
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
