-- Create RBAC tables for unified backend service
-- This creates the roles, permissions, and junction tables needed for role-based access control

BEGIN;

-- Create permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for permissions
CREATE INDEX IF NOT EXISTS idx_permissions_name ON permissions(name);
CREATE INDEX IF NOT EXISTS idx_permissions_resource ON permissions(resource);
CREATE INDEX IF NOT EXISTS idx_permissions_action ON permissions(action);

-- Create roles table
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for roles
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);

-- Create user_roles junction table (many-to-many: users <-> roles)
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- Create role_permissions junction table (many-to-many: roles <-> permissions)
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Insert default permissions
INSERT INTO permissions (name, description, resource, action) VALUES
    ('create:user', 'Create new users', 'user', 'create'),
    ('read:user', 'View users', 'user', 'read'),
    ('update:user', 'Update users', 'user', 'update'),
    ('delete:user', 'Delete users', 'user', 'delete'),
    ('create:test', 'Create test definitions', 'test', 'create'),
    ('read:test', 'View test definitions', 'test', 'read'),
    ('update:test', 'Update test definitions', 'test', 'update'),
    ('delete:test', 'Delete test definitions', 'test', 'delete'),
    ('create:schedule', 'Create schedules', 'schedule', 'create'),
    ('read:schedule', 'View schedules', 'schedule', 'read'),
    ('update:schedule', 'Update schedules', 'schedule', 'update'),
    ('delete:schedule', 'Delete schedules', 'schedule', 'delete'),
    ('execute:test', 'Execute tests', 'test', 'execute')
ON CONFLICT (name) DO NOTHING;

-- Insert default roles
INSERT INTO roles (name, description, is_system) VALUES
    ('admin', 'Administrator with full access', TRUE),
    ('tester', 'Tester who can run tests', TRUE),
    ('viewer', 'Read-only access', TRUE)
ON CONFLICT (name) DO NOTHING;

-- Assign all permissions to admin role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'admin'
ON CONFLICT DO NOTHING;

-- Assign test-related permissions to tester role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'tester' AND p.action IN ('read', 'execute')
ON CONFLICT DO NOTHING;

-- Assign read-only permissions to viewer role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.name = 'viewer' AND p.action = 'read'
ON CONFLICT DO NOTHING;

-- Assign admin role to admin user (user_id=1)
INSERT INTO user_roles (user_id, role_id)
SELECT 1, r.id
FROM roles r
WHERE r.name = 'admin'
ON CONFLICT DO NOTHING;

COMMIT;

-- Verify the setup
SELECT 'RBAC tables created successfully!' AS status;
SELECT COUNT(*) AS permission_count FROM permissions;
SELECT COUNT(*) AS role_count FROM roles;
SELECT COUNT(*) AS user_role_count FROM user_roles;
SELECT COUNT(*) AS role_permission_count FROM role_permissions;
