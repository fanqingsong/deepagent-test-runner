# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Code Test Runner is an AI-powered E2E testing framework with two deployment models:

1. **CLI Tool** (`cli/`): Standalone test runner using Claude Code SDK + Playwright
2. **Microservices** (`service/`): Multi-service architecture with PostgreSQL, Redis, and web dashboard

The system executes natural language test definitions using Claude Code's AI to perform browser automation through Playwright MCP.

## Architecture

### CLI Architecture
```
CLI (Bun) → Claude Code SDK → Anthropic API
                ↓
         Playwright MCP → Browser
                ↓
         Test State MCP (local HTTP server)
```

### Microservices Architecture (current: unified backend)
```
Frontend (React/Vite :5173) → Nginx (:8080) → Unified Backend (FastAPI :8001, host :8011)
                                                    ↓
                              PostgreSQL (:5432) ← Celery Worker + Beat ← Redis
```

**Service Interactions:**
- **Unified Backend** (`service/backend/`): test definitions, schedules, jobs, analytics, auth (MFA, sessions), SSO config
- **Celery Workers** execute tests via Playwright + Claude Agent SDK; load test data from PostgreSQL (not HTTP self-calls)
- **Job metadata** stored in Redis (`app/core/job_store.py`) for status polling across API restarts
- Frontend uses hash-based routing: `#dashboard`, `#tests`, `#schedules`
- Use `docker compose` (not `docker-compose`) from `service/`

## Development Commands

### CLI Development
```bash
cd cli
bun install                    # Install dependencies
./init.dev.sh                 # Initialize development environment
bun run build                 # Build CLI
./dist/cc-test-runner -t ./samples/pdca-e2e-tests.json -v
bun test                      # Run tests
```

### Microservices Development
```bash
cd service
docker compose up -d          # Start all services with hot-reload
docker compose ps             # Check service status
docker compose logs -f [service]  # View logs
docker compose restart [service]  # Restart specific service
```

**Hot-reload is enabled for:**
- `backend/app:/app/app` (API and Celery worker)
- `frontend/src:/app/frontend` (Vite dev server)

Changes to these directories are automatically reflected without rebuilding.

### Service-Specific Commands

**Dashboard Service:**
```bash
cd service/dashboard-service
npm run dev                    # Backend hot-reload
npm run frontend:dev           # Frontend dev server
npm run dev:full               # Both backend and frontend
```

**Test Case Service:**
```bash
docker-compose exec test-case-service pytest
docker-compose exec test-case-service pytest tests/test_endpoints.py -v
```

**Scheduler Service:**
```bash
docker-compose exec scheduler-service pytest
docker-compose exec scheduler-worker celery -A app.core.celery_app inspect active
```

### Database Operations
```bash
# Connect to PostgreSQL
docker exec -it cc-test-postgres psql -U cc_test_user -d cc_test_db

# Check specific table
docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db -c "\d test_runs"
docker exec cc-test-postgres psql -U cc_test_user -d cc_test_db -c "SELECT COUNT(*) FROM test_cases"

# Backup
docker exec cc-test-postgres pg_dump -U cc_test_user cc_test_db > backup.sql
```

## Database Schema Relationships

**Core Tables:**
- `test_definitions`: Test case definitions (the "what")
- `test_steps`: Sequential steps for each test definition
- `test_runs`: Execution instances with status and timestamps
- `test_cases`: Individual test step results (linked to test_runs)
- `schedules`: Cron-based test scheduling configurations

**Important Relationships:**
- `test_runs.test_definition_id` → `test_definitions.id`
- `test_cases.run_id` → `test_runs.id` (execution details)
- `test_cases.test_definition_id` → `test_definitions.id`
- `schedules.test_definition_id` → `test_definitions.id` (single test)
- `schedules.test_suite_id` → `test_suites.id` (multiple tests)

**Critical Field Distinction:**
- `test_runs.total_tests`: Number of test steps in this run (cumulative)
- `test_runs.total_duration_ms`: Execution duration in milliseconds
- `test_cases.duration`: Individual step duration in milliseconds
- Use `test_definitions` count for "test case总数" not `test_runs.total_tests`

## Frontend Development

**⚠️ IMPORTANT: Always consult DESIGN.md before writing UI code**

This project uses an IBM Carbon-inspired design system. Before creating or modifying any UI components:

1. **Read DESIGN.md** - Complete design system specifications
2. **Follow the design tokens** - Use `--cds-*` naming convention for CSS variables
3. **Apply Carbon principles** - 0px border-radius, flat design, IBM Plex Sans typography
4. **Use the color palette** - IBM Blue 60 (#0f62fe) as the sole accent color

**Design System Highlights:**
- **Border-radius**: 0px on buttons, inputs, cards (24px only for tags/labels)
- **Colors**: Monochromatic grays + IBM Blue 60 (#0f62fe)
- **Typography**: IBM Plex Sans (weight 300/400/600 - NO weight 700)
- **Spacing**: 8px base unit, 16px component padding, 48px button height
- **Depth**: Background-color layering, not shadows (flat design)
- **Inputs**: Bottom-border only, #f4f4f4 background

**Routing:** Hash-based (`#dashboard`, `#tests`, `#schedules`)

**API Calls:** Via Nginx on port 8080 (or Vite dev with same-origin `/api/v1`)
- Unified API: `http://localhost:8080/api/v1/` (or `http://localhost:8011/api/v1/` direct to backend)
- Analytics: `http://localhost:8080/api/v1/analytics/`

**Component Patterns:**
- Table layouts for lists (TestList, ScheduleList, RecentTests)
- Modal popups for create/edit forms
- Pagination for large datasets
- Status badges with color coding (passed=green, failed=red, running=blue)

**State Management:**
- `refreshKey` pattern to trigger list refreshes after CRUD operations
- `on*Created` callbacks to close modals and refresh lists
- Direct state updates, no Redux/context for simple cases

**Current UI Migration Status:**
The existing UI components were built using Material Design patterns and need to be migrated to the IBM Carbon-inspired design system:

- ❌ **Border-radius**: Currently uses 4-8px (should be 0px)
- ❌ **Colors**: Uses Material Design palette (#1976d2 blue, #4caf50 green) - needs IBM Blue 60
- ❌ **Typography**: Uses Arial fallback - needs IBM Plex Sans
- ❌ **Shadows**: Cards have box-shadows - should be flat with background-color layering
- ❌ **Buttons**: Rounded with gradients - should be rectangular, flat colors

**Migration Priority:**
1. Create global CSS design token system (`--cds-*` variables)
2. Update App.jsx with IBM Plex Sans and design tokens
3. Migrate shared components (Modal, Button, Input, Table)
4. Update page-specific components to use new design system

**When modifying UI:**
- Always check DESIGN.md first for the correct patterns
- Prefer creating new components following the design system over patching old ones
- Test responsive behavior at 320px, 672px, 1056px, and 1312px breakpoints

## Backend Development

**Scheduler Service (FastAPI):**
- `app/api/v1/endpoints/`: REST endpoints
- `app/services/`: Business logic (execution_service.py, schedule_manager.py)
- `app/tasks/`: Celery tasks (test_execution.py, schedule_sync.py)
- `app/models/`: SQLAlchemy ORM models (test_run.py, schedule.py, test_case.py)

**Dashboard Service (Express):**
- `src/db.js`: Database queries using pg
- `src/server.js`: Express server with API routes
- `frontend/src/`: React frontend

**Authentication Service (FastAPI):**
- `app/api/v1/endpoints/`: REST endpoints (auth.py, mfa.py, password.py, admin.py)
- `app/services/`: Business logic (auth_service.py, mfa_service.py, session_service.py, audit_service.py)
- `app/models/`: SQLAlchemy ORM models (user_account.py, user_session.py, mfa_secret.py, recovery_code.py, email_token.py, audit_log.py)
- `app/tasks/`: Celery tasks (email_tasks.py, maintenance_tasks.py)
- `app/core/`: Configuration and security (config.py, security.py, rate_limit.py, celery_app.py)

**Authentication Flow:**
1. **Registration:** User submits email/password → AuthService.register_user() → creates user_account → queues verification email via Celery
2. **Email Verification:** User clicks email link → token validation → user_account.is_verified = True
3. **Login:** User submits credentials → AuthService.authenticate_user() → validates password → creates user_session → returns JWT tokens
4. **MFA Setup:** Authenticated user requests setup → MFAService.setup_mfa() → generates TOTP secret + QR code + 10 backup codes
5. **MFA Enable:** User verifies TOTP code → MFAService.enable_mfa() → marks MFA enabled
6. **Password Reset:** User requests reset → generates token → emails link → token validation → password update → invalidate all sessions

**Security Architecture:**
- **Rate Limiting:** Sliding window using Redis sorted sets (5 login attempts/15min, 3 password resets/hour, 10 MFA verifications/5min)
- **Account Lockout:** 5 failed login attempts triggers 15-minute lock (user_account.failed_login_attempts, account_locked_until)
- **Session Management:** Max 5 concurrent sessions, oldest inactive terminated on 6th (session_service.create_user_session())
- **MFA:** TOTP secrets (160-bit Base32), 10 single-use backup codes (bcrypt hashed), 30-second window with ±1 step skew tolerance
- **Audit Logging:** All security events logged to audit_logs table with IP address, user agent, auto-deletion after 90 days
- **Email Queue:** Celery tasks with exponential backoff retry (30s, 5m, 15m), failure tracking after 3 attempts

**Critical Authentication Service Methods:**
- `AuthService.register_user()`: Creates user, validates password strength, queues verification email
- `AuthService.authenticate_user()`: Validates credentials, checks account status, enforces lockout, tracks failed attempts
- `SessionService.create_user_session()`: Creates session, enforces concurrent limit, sets remember_me expiry (30 days vs 24 hours)
- `MFAService.setup_mfa()`: Generates TOTP secret (pyotp), QR code (otpauth URI), 10 backup codes (bcrypt hashed)
- `MFAService.verify_mfa()`: Validates TOTP code with ±1 step tolerance, updates last_verified_at
- `AuditService.log_security_event()`: Logs security events with IP, user agent, details, 90-day retention

**Authentication Database Schema:**
- `user_accounts`: id, email, password_hash (bcrypt), is_verified, status (active/suspended), failed_login_attempts, account_locked_until, mfa_enabled
- `user_sessions`: id, user_id, session_token, ip_address, user_agent, expires_at, remember_me, created_at, last_active
- `mfa_secrets`: id, user_id, secret (bcrypt), enabled, verified_at, last_verified_at
- `recovery_codes`: id, user_id, code (bcrypt), used_at, created_at
- `email_tokens`: id, user_id, token (SHA256 hash), token_type (verification/password_reset), expires_at, used_at
- `audit_logs`: id, user_id, event_type, details (JSON), ip_address, user_agent, created_at, auto_delete_at

**Critical Service Methods:**
- `ExecutionService.save_test_results()`: Saves both test_runs summary AND test_cases details
- `ScheduleManager.parse_cron_expression()`: Validates cron expressions
- `DatabaseManager.getRecentTestRuns()`: Must JOIN with test_definitions to get test names

## Test Execution Flow

1. **Schedule Trigger:** Celery Beat detects due schedule → calls `schedule_sync.execute_scheduled_tests()`
2. **Job Creation:** Creates TestRun record with status='pending'
3. **Test Execution:** Worker calls `test_execution.execute_test()` with test_definition_id
4. **Browser Automation:** Playwright executes steps using AI interpretation
5. **Result Saving:** `ExecutionService.save_test_results()` saves:
   - Summary to `test_runs` table
   - Individual step results to `test_cases` table
6. **Dashboard Update:** Frontend queries PostgreSQL for latest results

**Key Timing Fields:**
- All timestamps in PostgreSQL are naive datetime (no timezone)
- Use `datetime.utcnow()` for consistency, not `datetime.now(timezone.utc)`
- JavaScript timestamps are milliseconds, PostgreSQL timestamps are seconds

## Common Issues and Solutions

**Issue:** Scheduled tests not executing
- **Solution:** Check Celery Beat logs, verify schedule is_active=true, ensure cron expression is valid

**Issue:** Test results not showing in dashboard
- **Solution:** Verify `test_cases` records are created (check `run_id` foreign key), ensure JOIN includes test_definitions table

**Issue:** Hot-reload not working
- **Solution:** Volume mounts are in docker-compose.yml, changes should auto-apply. If not, restart the specific service.

**Issue:** "测试用例总数" mismatch (72 vs 4)
- **Solution:** Use `COUNT(*) FROM test_definitions` for test count, not `SUM(total_tests) FROM test_runs`

**Issue:** Invalid Date in frontend
- **Solution:** Database timestamps are milliseconds, use `new Date(parseInt(timestamp))` in JavaScript

## Configuration Files

**CLI:** `cli/cc-test.yaml` (YAML configuration with environment detection)
**Microservices:** `service/.env` (PostgreSQL, Redis, API keys)

**Environment Variables:**
- `ANTTHROPIC_API_KEY`: Required for Claude Code access
- `POSTGRES_PASSWORD`: Database credentials
- `SECRET_KEY`: JWT signing key

## Testing Strategy

**Unit Tests:** Co-located with source files
**Integration Tests:** `cli/tests/integration/`
**E2E Tests:** Use the CLI itself to test the framework

**Test Execution Verification:**
1. Check test_runs table for summary records
2. Check test_cases table for step-by-step results
3. Verify status transitions: pending → running → passed/failed
4. Confirm timestamps and durations are saved correctly

## Performance Considerations

**Dashboard Queries:**
- Use `created_at` for filtering (always populated), not `start_time` (often NULL)
- Index on `test_runs.created_at` for time-based queries
- Join with test_definitions to get test names (add test_definition_id to queries)

**Celery Workers:**
- Default concurrency: 2 workers
- Scale with: `docker-compose up -d --scale scheduler-worker=4`
- Task routing: test_execution tasks go to workers, schedule_sync to beat

## API Port Mappings

- **8080:** Nginx reverse proxy (routes to backend services)
- **8010:** Authentication Service (FastAPI)
- **8011:** Test Case Service (FastAPI)
- **8012:** Scheduler Service (FastAPI)
- **8013:** Dashboard Service (Express + Vite)
- **5173:** Vite dev server (for React frontend hot-reload)
- **5433:** PostgreSQL (external access)
- **6380:** Redis (external access)

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
specs/001-user-auth-mfa/plan.md
<!-- SPECKIT END -->
