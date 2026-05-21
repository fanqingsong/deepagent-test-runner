import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { parseApiError } from './api';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './components/LoginPage';
import OidcCallback from './components/OidcCallback';
import DashboardView from './components/DashboardView';
import ScheduleList from './components/ScheduleList';
import ScheduleForm from './components/ScheduleForm';
import UserList from './components/UserList';
import UserForm from './components/UserForm';
import Modal from './components/Modal';
import StudioGallery from './components/StudioGallery';
import StudioWorkspace from './components/StudioWorkspace';
import authService from './services/authService';

function AppContent() {
  const { user, logout, isAuthenticated, isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [currentView, setCurrentView] = useState('dashboard');

  // Schedule states
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(null);
  // User management states
  const [showUserForm, setShowUserForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);


  // 从hash初始化视图
  useEffect(() => {
    const hash = window.location.hash.slice(1); // 去掉#号
    if (hash.startsWith('studio/')) {
      setCurrentView(hash);
    } else if (hash === 'dashboard' || hash === 'schedules' || hash === 'users' || hash === 'studios') {
      setCurrentView(hash);
    }
  }, []);

  // 监听hash变化
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1);
      if (hash.startsWith('studio/')) {
        setCurrentView(hash);
      } else if (hash === 'dashboard' || hash === 'schedules' || hash === 'users' || hash === 'studios') {
        setCurrentView(hash);
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);


  const getAuthHeadersSafe = () => {
    const token = typeof authService?.getAccessToken === 'function' ? authService.getAccessToken() : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  };




  // Schedule handlers
  const handleScheduleCreated = () => {
    queryClient.invalidateQueries({ queryKey: ['schedules'] });
  };

  const handleEditSchedule = (schedule) => {
    setEditingSchedule(schedule);
    setShowScheduleForm(true);
  };

  const handleTriggerSchedule = async (scheduleId) => {
    try {
      const response = await fetch(`/api/v1/schedules/${scheduleId}/trigger`, {
        method: 'POST',
        headers: {
          ...getAuthHeadersSafe()
        }
      });
      if (response.ok) {
        alert('调度已触发！');
      } else {
        alert(await parseApiError(response, '触发失败'));
      }
    } catch (err) {
      alert('错误: ' + err.message);
    }
  };

  const handleToggleSchedule = async (scheduleId, isActive) => {
    try {
      const response = await fetch(`/api/v1/schedules/${scheduleId}/toggle`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeadersSafe()
        },
        body: JSON.stringify({ is_active: isActive })
      });
      if (response.ok) {
        handleScheduleCreated();
      } else {
        throw new Error('Failed to toggle schedule');
      }
    } catch (err) {
      alert('错误: ' + err.message);
    }
  };

  // User management handlers
  const handleEditUser = (user) => {
    setEditingUser(user);
    setShowUserForm(true);
  };

  const navStyle = {
    display: 'flex',
    background: 'var(--cds-background-inverse)',
    padding: 'var(--cds-nav-padding)',
    height: 'var(--cds-nav-height)',
    alignItems: 'center',
    justifyContent: 'space-between'
  };

  const navButtonStyle = (isActive) => ({
    padding: '16px 20px',
    background: 'none',
    border: 'none',
    color: isActive ? 'var(--cds-background)' : 'var(--cds-border-subtle)',
    cursor: 'pointer',
    fontSize: 'var(--cds-body-short-01)',
    fontWeight: 'var(--cds-font-weight-regular)',
    borderBottom: isActive ? '2px solid var(--cds-background)' : '2px solid transparent',
    transition: 'all var(--cds-transition-normal)',
    height: '100%',
    display: 'flex',
    alignItems: 'center'
  });

  // Check if user is on login page or OIDC callback
  const isAuthPage = window.location.hash === '#login' || window.location.hash.startsWith('#/oidc/callback');

  if (!isAuthenticated && !isAuthPage) {
    // Redirect to login
    window.location.hash = 'login';
    return null;
  }

  if (isAuthPage) {
    if (window.location.hash.startsWith('#/oidc/callback')) {
      return <OidcCallback />;
    }
    return <LoginPage />;
  }

  return (
    <div style={{minHeight: '100vh', display: 'flex', flexDirection: 'column'}}>
      {/* 导航栏 */}
      <nav style={navStyle}>
        <div style={{display: 'flex'}}>
          <button
            onClick={() => window.location.hash = 'dashboard'}
            style={navButtonStyle(currentView === 'dashboard')}
          >
            仪表板
          </button>
          <button
            onClick={() => window.location.hash = 'studios'}
            style={navButtonStyle(currentView === 'studios')}
          >
            Studio
          </button>
          <button
