#!/bin/bash

# Authentication Setup Script for Claude Code Test Runner
# This script sets up initial admin user and configures Casdoor

set -e

echo "======================================"
echo "Claude Code Test Runner - Auth Setup"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker compose is running
echo "📋 Checking if services are running..."
if ! docker compose ps | grep -q "Up"; then
    echo -e "${YELLOW}Services are not running. Starting services...${NC}"
    docker compose up -d
    echo "Waiting for services to be ready..."
    sleep 10
else
    echo -e "${GREEN}✓ Services are running${NC}"
fi

echo ""
echo "======================================"
echo "Step 1: Create Local Admin User"
echo "======================================"
echo ""

# Generate a secure random password
ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
ADMIN_USERNAME="admin"
ADMIN_EMAIL="admin@example.com"

echo "Creating local admin user..."
echo "Username: $ADMIN_USERNAME"
echo "Email: $ADMIN_EMAIL"
echo "Password: $ADMIN_PASSWORD"
echo ""

# Create admin user in PostgreSQL
docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db << EOF
-- Insert admin user (password: 'Admin123!' - bcrypt hash)
INSERT INTO users (username, email, hashed_password, is_admin, is_active, created_at, updated_at)
VALUES (
    '$ADMIN_USERNAME',
    '$ADMIN_EMAIL',
    '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzW5qHl9CC',
    true,
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (username) DO NOTHING
ON CONFLICT (email) DO NOTHING;
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Local admin user created successfully${NC}"
else
    echo -e "${RED}✗ Failed to create admin user${NC}"
    exit 1
fi

echo ""
echo "======================================"
echo "Step 2: Migrate Existing Data"
echo "======================================"
echo ""

echo "Migrating existing test definitions, test runs, and test cases to admin user..."

# Migrate test_definitions
docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db << EOF
-- Update test_definitions created_by to admin (user_id=1)
UPDATE test_definitions
SET created_by = 1
WHERE created_by IS NULL;

-- Update test_runs user_id to admin (user_id=1)
UPDATE test_runs
SET user_id = 1
WHERE user_id IS NULL;

-- Update test_cases user_id to admin (user_id=1)
UPDATE test_cases
SET user_id = 1
WHERE user_id IS NULL;
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Existing data migrated to admin user${NC}"
else
    echo -e "${RED}✗ Failed to migrate data${NC}"
fi

echo ""
echo "======================================"
echo "Step 3: Casdoor Configuration"
echo "======================================"
echo ""

echo "Please configure Casdoor by following these steps:"
echo ""
echo "1. Access Casdoor Admin UI:"
echo "   URL: http://localhost:8002"
echo "   Default admin: admin / admin"
echo ""
echo "2. Create Organization:"
echo "   - Go to 'Organizations' → 'Add Organization'"
echo "   - Name: test-runner"
echo "   - Display Name: Test Runner"
echo ""
echo "3. Create Application:"
echo "   - Go to 'Applications' → 'Add Application'"
echo "   - Name: test-runner-app"
echo "   - Organization: test-runner"
echo "   - Redirect URLs: http://localhost:8080/oidc/callback"
echo "   - Copy the Client ID and Client Secret"
echo ""
echo "4. Update .env file:"
echo "   - Edit docker-compose/.env"
echo "   - Update CASDOOR_CLIENT_ID with the Client ID from Casdoor"
echo "   - Update CASDOOR_CLIENT_SECRET with the Client Secret from Casdoor"
echo ""
echo "5. Create Admin User in Casdoor (optional):"
echo "   - Go to 'Users' → 'Add User'"
echo "   - Create admin user with same credentials as local admin"
echo "   - Add 'admin' role to the user"
echo ""
echo -e "${YELLOW}⚠️  After updating .env, restart services:${NC}"
echo "   docker compose restart test-case-service scheduler-service dashboard-service"

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "📝 Save these credentials:"
echo "================================"
echo "Local Admin Login:"
echo "  Username: $ADMIN_USERNAME"
echo "  Password: $ADMIN_PASSWORD"
echo "  Login URL: http://localhost:8080#login"
echo ""
echo "Casdoor Admin UI:"
echo "  URL: http://localhost:8002"
echo "  Default: admin / admin"
echo ""
echo "======================================"
echo ""
echo -e "${GREEN}✓ Authentication system is ready!${NC}"
echo ""
echo "Next steps:"
echo "1. Configure Casdoor (optional, for SSO)"
echo "2. Test login at http://localhost:8080"
echo "3. Create additional users via registration or Casdoor UI"
echo ""
