/**
 * PermissionGate
 *
 * Conditionally renders children based on user permissions.
 * Admins always see everything.
 *
 * Usage:
 *   <PermissionGate permission="create:test">
 *     <button>Create Test</button>
 *   </PermissionGate>
 *
 *   <PermissionGate anyPermission={["update:test", "delete:test"]}>
 *     <button>Manage Tests</button>
 *   </PermissionGate>
 *
 *   <PermissionGate role="admin">
 *     <AdminPanel />
 *   </PermissionGate>
 */

import { useAuth } from '../contexts/AuthContext';

function PermissionGate({ children, permission, anyPermission, role, fallback = null }) {
  const { hasPermission, hasAnyPermission, hasRole, isAdmin } = useAuth();

  if (isAdmin) return children;

  if (permission && hasPermission(permission)) return children;
  if (anyPermission && hasAnyPermission(...anyPermission)) return children;
  if (role && hasRole(role)) return children;

  if (!permission && !anyPermission && !role) return children;

  return fallback;
}

export default PermissionGate;
