import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import authClient from './services/auth';
import LoginPage from './components/LoginPage';
import DashboardView from './components/DashboardView';
import UserList from './components/UserList';
import UserForm from './components/UserForm';
import Modal from './components/Modal';
import PermissionGate from './components/PermissionGate';
import RoleManagement from './components/RoleManagement';
import TestCasesIDE from './components/test_cases/TestCaseIDE';
import SuiteIDE from './components/suite/SuiteIDE';
import ReviewPanel from './components/admin/ReviewPanel';
import ChatMonitorPage from './components/admin/ChatMonitorPage';
import Sidebar from './components/Sidebar';
import AppHeader from './components/AppHeader';
import Profile from './pages/Profile';
import TestCasesMarketplacePage from './pages/TestCasesMarketplacePage';
import SuiteMarketplacePage from './pages/SuiteMarketplacePage';
import NanjingWeatherPage from './pages/NanjingWeatherPage';
import MonitoringPage from './pages/MonitoringPage';
import RootCauseAnalysisPage from './pages/RootCauseAnalysisPage';
import TokenUsageDashboard from './components/token/TokenUsageDashboard';
import BudgetManagement from './components/token/BudgetManagement';
import QuotaManagement from './components/token/QuotaManagement';
import AlertManagement from './components/token/AlertManagement';
import TokenAnalytics from './components/token/TokenAnalytics';
import ChatFab from './components/ChatFab';
import ChatModal from './components/ChatModal';

function AppContent() {
  const { user, logout, isAuthenticated, loading } = useAuth();
  const queryClient = useQueryClient();

  // Email verification from URL
  const [verifyResult, setVerifyResult] = useState(null);

  useEffect(() => {
    const path = window.location.pathname;
    if (path === '/auth/verify-email') {
      const params = new URLSearchParams(window.location.search);
      const token = params.get('token');
      if (token) {
        authClient.verifyEmail(token)
          .then(() => setVerifyResult('success'))
          .catch((err) => setVerifyResult(err.response?.data?.detail || 'Verification failed, link may have expired'));
      }
    }
  }, []);

  const [currentView, setCurrentView] = useState(() => {
    const hash = window.location.hash.slice(1);
    if (['dashboard', 'users', 'roles', 'reviews', 'profile', 'chat-monitor', 'nanjing-weather', 'monitoring', 'root-cause', 'token-usage', 'token-budget', 'token-quota', 'token-alert', 'token-analytics'].includes(hash)) {
      return hash;
    } else if (hash.startsWith('test-cases')) {
      return hash === 'test-cases-marketplace' ? 'test-cases-marketplace' : 'test-cases';
    } else if (hash.startsWith('suites')) {
      return hash === 'suites-marketplace' ? 'suites-marketplace' : 'suites';
    }
    return 'dashboard';
  });

  const [showUserForm, setShowUserForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isDesktop, setIsDesktop] = useState(() => window.innerWidth >= 1056);
  const [isChatOpen, setIsChatOpen] = useState(false);

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1);
      if (hash.startsWith('test-cases')) {
        setCurrentView(hash === 'test-cases-marketplace' ? 'test-cases-marketplace' : 'test-cases');
      } else if (hash.startsWith('suites')) {
        setCurrentView(hash === 'suites-marketplace' ? 'suites-marketplace' : 'suites');
      } else if (hash === 'dashboard' || hash === 'users' || hash === 'roles' || hash === 'reviews' || hash === 'profile' || hash === 'chat-monitor' || hash === 'nanjing-weather' || hash === 'monitoring' || hash === 'root-cause' || hash === 'token-usage' || hash === 'token-budget' || hash === 'token-quota' || hash === 'token-alert' || hash === 'token-analytics') {
        setCurrentView(hash);
      }
    };

    const handleResize = () => {
      const desktop = window.innerWidth >= 1056;
      setIsDesktop(desktop);
      if (!desktop) {
        setIsMobileMenuOpen(false);
      }
    };

    window.addEventListener('hashchange', handleHashChange);
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const handleEditUser = (user) => {
    setEditingUser(user);
    setShowUserForm(true);
  };

  const handleSidebarToggle = () => {
    if (!isDesktop) {
      setIsMobileMenuOpen(!isMobileMenuOpen);
    } else {
      setIsSidebarCollapsed(!isSidebarCollapsed);
    }
  };

  const handleMobileMenuClose = () => {
    setIsMobileMenuOpen(false);
  };

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--cds-background, #f4f4f4)',
        color: 'var(--cds-text-primary, #161616)',
        fontSize: '14px'
      }}>
        Loading...
      </div>
    );
  }

  // Show email verification result, then redirect to login
  if (verifyResult !== null) {
    const isSuccess = verifyResult === 'success';
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'var(--cds-background, #f4f4f4)'
      }}>
        <div style={{
          background: '#fff', padding: '48px', maxWidth: '400px', width: '100%', textAlign: 'center'
        }}>
          <div style={{
            fontSize: '48px', marginBottom: '16px',
            color: isSuccess ? '#42be65' : '#da1e28'
          }}>
            {isSuccess ? '✓' : '✗'}
          </div>
          <h2 style={{ fontWeight: 300, marginBottom: '8px' }}>
            {isSuccess ? 'Email verification successful' : 'Verification failed'}
          </h2>
          <p style={{ color: '#525252', marginBottom: '24px' }}>
            {isSuccess ? 'Your email has been verified, you can now log in.' : typeof verifyResult === 'string' ? verifyResult : 'The link may have expired or is invalid.'}
          </p>
          <button
            onClick={() => { setVerifyResult(null); window.location.href = window.location.origin + '#login'; }}
            style={{
              padding: '12px 24px', background: '#0f62fe', color: '#fff',
              border: 'none', cursor: 'pointer', fontSize: '14px', width: '100%'
            }}
          >
            Go to login
          </button>
        </div>
      </div>
    );
  }

  const isAuthPage = window.location.hash === '#login';

  if (!isAuthenticated && !isAuthPage) {
    window.location.hash = 'login';
    return null;
  }

  if (isAuthPage) {
    return <LoginPage />;
  }

  const contentMarginLeft = isSidebarCollapsed ? '48px' : '250px';

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AppHeader
        onMenuToggle={handleSidebarToggle}
        isMobileMenuOpen={isMobileMenuOpen}
      />
      <Sidebar
        isOpen={!isSidebarCollapsed || isMobileMenuOpen}
        isCollapsed={isSidebarCollapsed}
        onToggle={handleSidebarToggle}
        onMobileClose={handleMobileMenuClose}
        isDesktop={isDesktop}
      />

      <div style={{
        marginLeft: isDesktop ? contentMarginLeft : '0',
        marginTop: '48px',
        minHeight: 'calc(100vh - 48px)',
        transition: 'margin-left var(--cds-transition-normal) ease'
      }}>
        {currentView === 'test-cases' ? (
          <TestCasesIDE />
        ) : currentView === 'suites' ? (
          <SuiteIDE />
        ) : currentView === 'users' ? (
          <div style={{padding: 'var(--cds-layout-sm)', background: 'var(--cds-background)'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--cds-layout-md)'}}>
              <h2 style={{
                margin: 0,
                fontSize: 'var(--cds-heading-01)',
                fontWeight: 'var(--cds-font-weight-light)',
                lineHeight: 'var(--cds-display-line-height)'
              }}>User Management</h2>
              <PermissionGate permission="create:user">
              <button
                onClick={() => {
                  setEditingUser(null);
                  setShowUserForm(true);
                }}
                style={{
                  padding: 'var(--cds-button-padding-sm)',
                  background: 'var(--cds-button-primary)',
                  color: 'var(--cds-text-on-color)',
                  border: 'none',
                  borderRadius: 'var(--cds-border-radius)',
                  cursor: 'pointer',
                  fontWeight: 'var(--cds-font-weight-regular)',
                  fontSize: 'var(--cds-body-short-01)',
                  height: 'var(--cds-button-height-compact)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--cds-spacing-sm)'
                }}
              >
                <span>+</span>
                <span>Create User</span>
              </button>
              </PermissionGate>
            </div>

            <UserList onEditUser={handleEditUser} />

            <Modal
              isOpen={showUserForm}
              onClose={() => {
                setEditingUser(null);
                setShowUserForm(false);
              }}
              title={editingUser ? `Edit User: ${editingUser.username}` : 'Create New User'}
            >
              <UserForm
                user={editingUser}
                onSuccess={() => {
                  queryClient.invalidateQueries({ queryKey: ['users'] });
                  setShowUserForm(false);
                  setEditingUser(null);
                }}
                onCancel={() => {
                  setShowUserForm(false);
                  setEditingUser(null);
                }}
              />
            </Modal>
          </div>
        ) : currentView === 'roles' ? (
          <div style={{padding: 'var(--cds-layout-sm)', background: 'var(--cds-background)'}}>
            <RoleManagement />
          </div>
        ) : currentView === 'reviews' ? (
          <div style={{padding: 'var(--cds-layout-sm)', background: 'var(--cds-background)'}}>
            <ReviewPanel />
          </div>
        ) : currentView === 'profile' ? (
          <Profile />
        ) : currentView === 'test-cases-marketplace' ? (
          <TestCasesMarketplacePage />
        ) : currentView === 'suites-marketplace' ? (
          <SuiteMarketplacePage />
        ) : currentView === 'chat-monitor' ? (
          <ChatMonitorPage />
        ) : currentView === 'nanjing-weather' ? (
          <NanjingWeatherPage />
        ) : currentView === 'monitoring' ? (
          <MonitoringPage />
        ) : currentView === 'root-cause' ? (
          <RootCauseAnalysisPage />
        ) : currentView === 'token-usage' ? (
          <TokenUsageDashboard />
        ) : currentView === 'token-budget' ? (
          <BudgetManagement />
        ) : currentView === 'token-quota' ? (
          <QuotaManagement />
        ) : currentView === 'token-alert' ? (
          <AlertManagement />
        ) : currentView === 'token-analytics' ? (
          <TokenAnalytics />
        ) : (
          <DashboardView />
        )}
      </div>

      {/* Chat Components */}
      <ChatFab
        onClick={() => {
          setIsChatOpen(true);
        }}
        className={isChatOpen ? 'hidden' : ''}
      />
      <ChatModal
        isOpen={isChatOpen}
        onClose={() => {
          setIsChatOpen(false);
        }}
      />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
