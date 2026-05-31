#!/bin/bash

# Casdoor SSO Setup Script for Test Runner
# This script configures Casdoor for SSO integration

set -e

CASDOOR_API="http://localhost:8002/api"
ORG_NAME="test-runner"
APP_NAME="test-runner-app"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="Test@2026"

echo "🔧 Casdoor SSO Setup Script"
echo "=========================="
echo ""

# Step 1: Wait for rate limit to expire
echo "⏳ Step 1: Checking if rate limit is still active..."
RESPONSE=$(curl -s -X POST "$CASDOOR_API/login" \
  -H "Content-Type: application/json" \
  -d "{\"organization\": \"built-in\", \"username\": \"$ADMIN_USERNAME\", \"password\": \"$ADMIN_PASSWORD\", \"application\": \"app-built-in\"}")

if echo "$RESPONSE" | grep -q "wait for"; then
  echo "⚠️  Rate limit is still active. Please wait for it to expire."
  echo "   You can check the rate limit status by running:"
  echo "   curl -X POST $CASDOOR_API/login -H 'Content-Type: application/json' -d '{\"organization\": \"built-in\", \"username\": \"admin\", \"password\": \"test\", \"application\": \"app-built-in\"}'"
  exit 1
fi

echo "✅ Rate limit has expired. Proceeding with setup..."
echo ""

# Step 2: Login as built-in admin
echo "🔐 Step 2: Logging in as built-in admin..."
LOGIN_RESPONSE=$(curl -s -X POST "$CASDOOR_API/login" \
  -H "Content-Type: application/json" \
  -d "{\"organization\": \"built-in\", \"username\": \"$ADMIN_USERNAME\", \"password\": \"$ADMIN_PASSWORD\", \"application\": \"app-built-in\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['data'] if data['status']=='ok' else '')" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed. Please check admin credentials."
  echo "   Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✅ Successfully logged in"
echo ""

# Step 3: Create organization
echo "🏢 Step 3: Creating organization '$ORG_NAME'..."
CREATE_ORG_RESPONSE=$(curl -s -X POST "$CASDOOR_API/add-organization" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"owner\": \"admin\",
    \"name\": \"$ORG_NAME\",
    \"displayName\": \"Test Runner\",
    \"websiteUrl\": \"http://localhost:8080\",
    \"passwordType\": \"bcrypt\",
    \"passwordOptions\": [\"AtLeast6\"],
    \"defaultApplication\": \"$APP_NAME\",
    \"enableSignUp\": true,
    \"enableCodeSignin\": false
  }")

if echo "$CREATE_ORG_RESPONSE" | grep -q "\"status\":\"ok\""; then
  echo "✅ Organization created successfully"
else
  echo "ℹ️  Organization might already exist or there was an issue:"
  echo "   $CREATE_ORG_RESPONSE"
fi
echo ""

# Step 4: Create application
echo "📱 Step 4: Creating application '$APP_NAME'..."
CREATE_APP_RESPONSE=$(curl -s -X POST "$CASDOOR_API/add-application" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"owner\": \"$ORG_NAME\",
    \"name\": \"$APP_NAME\",
    \"displayName\": \"Test Runner SSO\",
    \"organization\": \"$ORG_NAME\",
    \"cert\": \"cert-built-in\",
    \"redirectUris\": [
      \"http://localhost:8080/oidc/callback\",
      \"http://localhost:5173/oidc/callback\"
    ],
    \"tokenFormat\": \"JWT\",
    \"expireInHours\": 168,
    \"refreshExpireInHours\": 720,
    \"enablePassword\": true,
    \"enableSignUp\": true,
    \"enableSigninSession\": false,
    \"enableAutoSignin\": false
  }")

if echo "$CREATE_APP_RESPONSE" | grep -q "\"status\":\"ok\""; then
  echo "✅ Application created successfully"

  # Extract client credentials
  CLIENT_ID=$(echo "$CREATE_APP_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['data']['clientId'] if 'data' in data and 'clientId' in data['data'] else '')" 2>/dev/null)
  CLIENT_SECRET=$(echo "$CREATE_APP_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['data']['clientSecret'] if 'data' in data and 'clientSecret' in data['data'] else '')" 2>/dev/null)

  echo ""
  echo "🔑 Client Credentials:"
  echo "   Client ID: $CLIENT_ID"
  echo "   Client Secret: $CLIENT_SECRET"
  echo ""
  echo "📝 Add these to your .env file:"
  echo "   CASDOOR_CLIENT_ID=$CLIENT_ID"
  echo "   CASDOOR_CLIENT_SECRET=$CLIENT_SECRET"
else
  echo "ℹ️  Application might already exist or there was an issue:"
  echo "   $CREATE_APP_RESPONSE"
fi
echo ""

# Step 5: Create test users
echo "👥 Step 5: Creating test users..."

# Create admin user
echo "   Creating admin user..."
curl -s -X POST "$CASDOOR_API/add-user" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"owner\": \"$ORG_NAME\",
    \"name\": \"admin\",
    \"displayName\": \"Test Admin\",
    \"email\": \"admin@testrunner.local\",
    \"type\": \"normal\",
    \"password\": \"admin123\",
    \"isAdmin\": true,
    \"isVerified\": true,
    \"emailVerified\": true
  }" > /dev/null

# Create regular user
echo "   Creating regular user..."
curl -s -X POST "$CASDOOR_API/add-user" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"owner\": \"$ORG_NAME\",
    \"name\": \"testuser\",
    \"displayName\": \"Test User\",
    \"email\": \"user@testrunner.local\",
    \"type\": \"normal\",
    \"password\": \"user123\",
    \"isAdmin\": false,
    \"isVerified\": true,
    \"emailVerified\": true
  }" > /dev/null

echo "✅ Test users created"
echo "   Admin: admin / admin123"
echo "   User:  testuser / user123"
echo ""

# Step 6: Get OAuth authorization URL
echo "🔗 Step 6: OAuth/OIDC Configuration"
echo "   Authorization Endpoint: http://localhost:8002/login/oauth/authorize"
echo "   Token Endpoint: http://localhost:8002/api/login/oauth/access_token"
echo "   User Info Endpoint: http://localhost:8002/api/get-user-info"
echo ""

echo "✅ Casdoor SSO setup complete!"
echo ""
echo "📚 Next Steps:"
echo "   1. Update .env with CASDOOR_CLIENT_ID and CASDOOR_CLIENT_SECRET"
echo "   2. Restart services: docker compose restart"
echo "   3. Test SSO login flow at: http://localhost:8080"
echo "   4. Access Casdoor admin UI at: http://localhost:8002"
