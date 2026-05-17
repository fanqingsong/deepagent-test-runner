# Casdoor SSO Configuration - Current Status

**Date:** 2026-05-01
**Status:** ⏳ Pending Rate Limit Expiration

## What's Been Done

### ✅ Casdoor Service Running
- **Status:** Healthy
- **URL:** http://localhost:8002
- **Database:** PostgreSQL (casdoor)
- **Configuration:** Custom app.conf with PostgreSQL connection

### ✅ Database Configuration
- **Organization:** "built-in" (default)
- **Application:** "app-built-in" (default)
- **Admin User:** Created in database (pending rate limit for login)
  - **Username:** admin
  - **Password:** admin123
  - **Email:** admin@example.com
  - **Is Admin:** true

### ⚠️ Current Blocker
**Rate Limit Active:** The Casdoor API has a 15-minute rate limit on failed login attempts.
- **Current Status:** ~14 minutes remaining
- **Reason:** Multiple failed password verification attempts during user creation
- **Impact:** Cannot test login or create new organization/application via API

## Next Steps

### Option 1: Wait for Rate Limit (Recommended)
1. Wait ~14 minutes for rate limit to expire
2. Run the setup script: `./setup-casdoor.sh`
3. Test SSO login flow

### Option 2: Manual Configuration via Web UI
1. Access http://localhost:8002
2. Try signing up with verification disabled (isDemo=true in config)
3. Configure organization and application manually

### Option 3: Direct Database Access (Advanced)
1. Clear rate limit counters in database
2. Test with different password hash format
3. Verify bcrypt compatibility between Python and Go

## Configuration Files

### Casdoor Config
**File:** `casdoor/conf/app.conf`
```ini
appname = casdoor
httpport = 8000
runmode = prod
driverName = postgres
dataSourceName = postgres://casdoor:casdoor_password_123@casdoor-postgres:5432/casdoor?sslmode=disable
authState = false
isDemo = true
enableEmailCode = false
enablePhoneCode = false
```

### Environment Variables (To Be Added)
**File:** `.env`
```bash
# Casdoor Configuration
CASDOOR_ENDPOINT=http://casdoor:8000
CASDOOR_CLIENT_ID=<generate-in-casdoor>
CASDOOR_CLIENT_SECRET=<generate-in-casdoor>
CASDOOR_ORGANIZATION=test-runner
CASDOOR_APPLICATION=test-runner-app
CASDOOR_CERTIFICATE=
```

## Testing Checklist

Once rate limit expires:

- [ ] Login to Casdoor admin UI (http://localhost:8002)
- [ ] Create "test-runner" organization
- [ ] Create "test-runner-app" application
- [ ] Configure OAuth redirect URIs
- [ ] Generate client credentials
- [ ] Update .env with client ID and secret
- [ ] Test password login via API
- [ ] Test OIDC authorization flow
- [ ] Test token refresh mechanism
- [ ] Verify role-based access control

## Setup Script

**Location:** `setup-casdoor.sh`

This script automates the entire Casdoor setup process:
- Creates organization and application
- Generates OAuth client credentials
- Creates test users (admin and regular user)
- Provides configuration for .env file

**Usage:**
```bash
./setup-casdoor.sh
```

## API Endpoints

### Login
```bash
curl -X POST http://localhost:8002/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "organization": "built-in",
    "username": "admin",
    "password": "admin123",
    "application": "app-built-in"
  }'
```

### OAuth Authorization
- **URL:** http://localhost:8002/login/oauth/authorize
- **Params:** client_id, redirect_uri, scope, response_type, state

### Token Exchange
- **URL:** http://localhost:8002/api/login/oauth/access_token
- **Method:** POST

## Known Issues

### 1. Bcrypt Hash Compatibility
**Issue:** Python bcrypt hashes ($2a$) may not be compatible with Go's bcrypt implementation used by Casdoor.

**Workaround:** Use Casdoor API to create users instead of direct database insertion.

### 2. Signup Page Empty
**Issue:** The signup page at /signup/built-in appears empty despite enable_sign_up=true.

**Workaround:** Use admin API to create users once logged in.

### 3. Rate Limiting
**Issue:** IP-based rate limiting (15 minutes) blocks multiple failed login attempts.

**Workaround:** Wait for expiration or use different IP/network.

## References

- **Casdoor Docs:** https://casdoor.org/docs
- **OAuth 2.0:** https://oauth.net/2/
- **OIDC:** https://openid.net/connect/
- **Setup Script:** `./setup-casdoor.sh`

## Current Service Status

```
cc-test-casdoor             Up (healthy) ✅
cc-test-casdoor-postgres    Up (healthy) ✅
```

Casdoor is ready for configuration once rate limit expires.
