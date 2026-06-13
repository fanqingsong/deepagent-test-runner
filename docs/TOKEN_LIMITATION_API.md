# Token Limitation API Documentation

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Budget Endpoints](#budget-endpoints)
4. [Quota Endpoints](#quota-endpoints)
5. [Alert Endpoints](#alert-endpoints)
6. [Analytics Endpoints](#analytics-endpoints)
7. [Error Responses](#error-responses)
8. [Rate Limiting](#rate-limiting)
9. [OpenAPI Specification](#openapi-specification)

## API Overview

The Token Limitation API provides 37 endpoints across 4 main resource categories:

- **Budget Endpoints (10)**: Manage hierarchical token budgets
- **Quota Endpoints (8)**: Manage user-specific token quotas
- **Alert Endpoints (10)**: Handle alert generation and management
- **Analytics Endpoints (9)**: Provide usage analytics and reporting

### Base URL

```
Production: https://api.deepagent.io/api/v1/token
Development: http://localhost:8080/api/v1/token
```

### API Versioning

Current version: `v1`

Include version in URL path: `/api/v1/token/*`

## Authentication

### Bearer Token Authentication

All endpoints require authentication using JWT bearer tokens.

```bash
# Get token from login endpoint
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "password"
}

# Use token in subsequent requests
Authorization: Bearer <jwt_token>
```

### Authorization Levels

- **User**: Can access their own quotas and alerts
- **Admin**: Can manage all budgets, quotas, and alerts

### Example Requests

```bash
# User-level request
curl -X GET "http://localhost:8080/api/v1/token/quotas/my-quota" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Admin-level request
curl -X GET "http://localhost:8080/api/v1/token/budgets" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Budget Endpoints

### 1. Create Budget

```http
POST /api/v1/token/budgets
```

**Description:** Create a new token budget with specified limits and enforcement mode.

**Authentication:** Admin required

**Request Body:**

```json
{
  "name": "Test Suite 1 Budget",
  "description": "Monthly budget for Test Suite 1",
  "scope_type": "suite",
  "scope_id": 1,
  "parent_budget_id": null,
  "period_type": "monthly",
  "period_start": "2026-06-01T00:00:00Z",
  "period_end": "2026-06-30T23:59:59Z",
  "total_tokens": 1000000,
  "priority": 5,
  "enforcement_mode": "soft",
  "inherit_from_parent": false,
  "alert_thresholds": {
    "warning": 80,
    "critical": 90,
    "emergency": 95
  }
}
```

**Response (201 Created):**

```json
{
  "id": 1,
  "name": "Test Suite 1 Budget",
  "description": "Monthly budget for Test Suite 1",
  "scope_type": "suite",
  "scope_id": 1,
  "parent_budget_id": null,
  "period_type": "monthly",
  "period_start": "2026-06-01T00:00:00Z",
  "period_end": "2026-06-30T23:59:59Z",
  "total_tokens": 1000000,
  "used_tokens": 0,
  "remaining_tokens": 1000000,
  "priority": 5,
  "enforcement_mode": "soft",
  "status": "active",
  "inherit_from_parent": false,
  "alert_thresholds": {
    "warning": 80,
    "critical": 90,
    "emergency": 95
  },
  "created_at": "2026-06-13T10:00:00Z",
  "updated_at": "2026-06-13T10:00:00Z",
  "last_reset_at": null
}
```

**Error Responses:**

- `400 Bad Request`: Invalid input data
- `403 Forbidden`: Insufficient permissions (non-admin)
- `422 Unprocessable Entity`: Validation error

**cURL Example:**

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Suite 1 Budget",
    "scope_type": "suite",
    "scope_id": 1,
    "period_type": "monthly",
    "total_tokens": 1000000,
    "enforcement_mode": "soft"
  }'
```

---

### 2. Get Budget by ID

```http
GET /api/v1/token/budgets/{budget_id}
```

**Description:** Retrieve detailed information about a specific token budget.

**Authentication:** User required

**Path Parameters:**

- `budget_id` (integer, required): Budget ID (≥ 1)

**Response (200 OK):**

```json
{
  "id": 1,
  "name": "Test Suite 1 Budget",
  "scope_type": "suite",
  "scope_id": 1,
  "total_tokens": 1000000,
  "used_tokens": 250000,
  "remaining_tokens": 750000,
  "usage_percentage": 25.0,
  "priority": 5,
  "enforcement_mode": "soft",
  "status": "active",
  "period_start": "2026-06-01T00:00:00Z",
  "period_end": "2026-06-30T23:59:59Z",
  "alert_thresholds": {
    "warning": 80,
    "critical": 90,
    "emergency": 95
  },
  "created_at": "2026-06-01T00:00:00Z",
  "updated_at": "2026-06-13T10:00:00Z",
  "last_reset_at": null
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Budget not found

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/budgets/1" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 3. Update Budget

```http
PUT /api/v1/token/budgets/{budget_id}
```

**Description:** Update an existing token budget configuration.

**Authentication:** Admin required

**Path Parameters:**

- `budget_id` (integer, required): Budget ID (≥ 1)

**Request Body:**

```json
{
  "name": "Test Suite 1 Budget (Updated)",
  "total_tokens": 1500000,
  "enforcement_mode": "hard",
  "priority": 7
}
```

**Response (200 OK):**

```json
{
  "id": 1,
  "name": "Test Suite 1 Budget (Updated)",
  "total_tokens": 1500000,
  "used_tokens": 250000,
  "remaining_tokens": 1250000,
  "enforcement_mode": "hard",
  "priority": 7,
  "updated_at": "2026-06-13T12:00:00Z"
}
```

**Error Responses:**

- `400 Bad Request`: Invalid input data
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Budget not found

**cURL Example:**

```bash
curl -X PUT "http://localhost:8080/api/v1/token/budgets/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Suite 1 Budget (Updated)",
    "total_tokens": 1500000,
    "enforcement_mode": "hard"
  }'
```

---

### 4. Delete Budget

```http
DELETE /api/v1/token/budgets/{budget_id}
```

**Description:** Delete a token budget (cascades to child budgets).

**Authentication:** Admin required

**Path Parameters:**

- `budget_id` (integer, required): Budget ID (≥ 1)

**Response (204 No Content):**

No content returned on successful deletion.

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Budget not found

**cURL Example:**

```bash
curl -X DELETE "http://localhost:8080/api/v1/token/budgets/1" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 5. Get Budget Status by Scope

```http
GET /api/v1/token/budgets/status/{scope}/{scope_id}
```

**Description:** Get current status of budget for a specific scope.

**Authentication:** User required

**Path Parameters:**

- `scope` (string, required): Scope type (organization, suite, test, user)
- `scope_id` (integer, required): Scope entity ID

**Response (200 OK):**

```json
{
  "budget_id": 1,
  "name": "Test Suite 1 Budget",
  "scope_type": "suite",
  "scope_id": 1,
  "status": "active",
  "total_tokens": 1000000,
  "used_tokens": 850000,
  "remaining_tokens": 150000,
  "usage_percentage": 85.0,
  "is_exhausted": false,
  "is_near_limit": true,
  "enforcement_mode": "soft",
  "period_start": "2026-06-01T00:00:00Z",
  "period_end": "2026-06-30T23:59:59Z",
  "days_remaining": 17,
  "alert_thresholds": {
    "warning": 80,
    "critical": 90,
    "emergency": 95
  }
}
```

**Error Responses:**

- `404 Not Found`: Budget not found for scope

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/budgets/status/suite/1" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 6. Get Budget Hierarchy

```http
GET /api/v1/token/budgets/hierarchy/{budget_id}
```

**Description:** Get budget hierarchy including parent and child budgets.

**Authentication:** User required

**Path Parameters:**

- `budget_id` (integer, required): Budget ID (≥ 1)

**Query Parameters:**

- `include_children` (boolean, optional): Include child budgets (default: true)

**Response (200 OK):**

```json
{
  "budget": {
    "id": 1,
    "name": "Organization Budget",
    "scope_type": "organization",
    "scope_id": 1,
    "total_tokens": 10000000,
    "used_tokens": 2500000,
    "remaining_tokens": 7500000
  },
  "parent": null,
  "children": [
    {
      "id": 2,
      "name": "Test Suite 1 Budget",
      "scope_type": "suite",
      "scope_id": 1,
      "total_tokens": 1000000,
      "used_tokens": 250000,
      "parent_budget_id": 1
    },
    {
      "id": 3,
      "name": "Test Suite 2 Budget",
      "scope_type": "suite",
      "scope_id": 2,
      "total_tokens": 2000000,
      "used_tokens": 500000,
      "parent_budget_id": 1
    }
  ]
}
```

**Error Responses:**

- `404 Not Found`: Budget not found

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/budgets/hierarchy/1?include_children=true" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 7. List All Budgets

```http
GET /api/v1/token/budgets
```

**Description:** List all token budgets with pagination.

**Authentication:** Admin required

**Query Parameters:**

- `page` (integer, optional): Page number (default: 1, ≥ 1)
- `page_size` (integer, optional): Items per page (default: 20, 1-100)
- `scope_type` (string, optional): Filter by scope type
- `status_filter` (string, optional): Filter by status

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": 1,
      "name": "Organization Budget",
      "scope_type": "organization",
      "total_tokens": 10000000,
      "used_tokens": 2500000,
      "status": "active"
    },
    {
      "id": 2,
      "name": "Test Suite 1 Budget",
      "scope_type": "suite",
      "total_tokens": 1000000,
      "used_tokens": 250000,
      "status": "active"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/budgets?page=1&page_size=20&scope_type=suite" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 8. Check Token Availability

```http
POST /api/v1/token/budgets/{budget_id}/check-availability
```

**Description:** Check if sufficient tokens are available for a request.

**Authentication:** User required

**Path Parameters:**

- `budget_id` (integer, required): Budget ID (≥ 1)

**Query Parameters:**

- `requested_tokens` (integer, required): Number of tokens requested (> 0)

**Response (200 OK):**

```json
{
  "available": true,
  "budget_id": 1,
  "requested_tokens": 15000,
  "available_tokens": 750000,
  "usage_percentage": 25.0,
  "enforcement_action": "allowed"
}
```

**Error Responses:**

- `400 Bad Request`: Availability check failed (budget exceeded)
- `404 Not Found`: Budget not found

**cURL Example:**

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets/1/check-availability?requested_tokens=15000" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 9. Reset Budget

```http
POST /api/v1/token/budgets/{budget_id}/reset
```

**Description:** Reset budget period and usage counters.

**Authentication:** Admin required

**Path Parameters:**

- `budget_id` (integer, required): Budget ID (≥ 1)

**Response (200 OK):**

```json
{
  "budget_id": 1,
  "message": "Budget reset successfully",
  "used_tokens": 0,
  "remaining_tokens": 1000000,
  "last_reset_at": "2026-06-13T12:00:00Z"
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Budget not found

**cURL Example:**

```bash
curl -X POST "http://localhost:8080/api/v1/token/budgets/1/reset" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 10. Get Budget Performance

```http
GET /api/v1/token/analytics/budget-performance
```

**Description:** Analyze budget performance and efficiency metrics.

**Authentication:** User required

**Query Parameters:**

- `budget_id` (integer, required): Budget ID to analyze

**Response (200 OK):**

```json
{
  "budget_id": 1,
  "budget_name": "Test Suite 1 Budget",
  "performance": {
    "usage_rate": 85.0,
    "remaining_percentage": 15.0,
    "is_exhausted": false,
    "is_near_limit": true,
    "days_until_exhaustion": 5,
    "efficiency_score": 85.0
  },
  "period": {
    "start": "2026-06-01T00:00:00Z",
    "end": "2026-06-30T23:59:59Z",
    "days_remaining": 17
  },
  "enforcement": {
    "mode": "soft",
    "status": "active"
  }
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Budget not found

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/budget-performance?budget_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Quota Endpoints

### 1. Get Current User's Quota

```http
GET /api/v1/token/quotas/my-quota
```

**Description:** Retrieve the token quota for the currently authenticated user.

**Authentication:** User required

**Response (200 OK):**

```json
{
  "id": 1,
  "user_id": 5,
  "name": "Daily User Quota",
  "description": "Daily token limit for user",
  "period_type": "daily",
  "reset_strategy": "calendar",
  "period_start": "2026-06-13T00:00:00Z",
  "period_end": "2026-06-13T23:59:59Z",
  "total_tokens": 50000,
  "used_tokens": 25000,
  "remaining_tokens": 25000,
  "usage_percentage": 50.0,
  "priority": 5,
  "enforcement_mode": "soft",
  "status": "active",
  "alert_thresholds": {
    "warning": 80,
    "critical": 90,
    "emergency": 95
  },
  "created_at": "2026-06-01T00:00:00Z",
  "updated_at": "2026-06-13T10:00:00Z",
  "last_reset_at": "2026-06-13T00:00:00Z"
}
```

**Error Responses:**

- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Quota not found for user

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/quotas/my-quota" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 2. Get Quota by ID

```http
GET /api/v1/token/quotas/{quota_id}
```

**Description:** Retrieve detailed information about a specific token quota.

**Authentication:** User required

**Path Parameters:**

- `quota_id` (integer, required): Quota ID (≥ 1)

**Response (200 OK):**

```json
{
  "id": 1,
  "user_id": 5,
  "name": "Daily User Quota",
  "total_tokens": 50000,
  "used_tokens": 25000,
  "remaining_tokens": 25000,
  "usage_percentage": 50.0,
  "status": "active"
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Quota not found

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/quotas/1" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 3. Create Quota

```http
POST /api/v1/token/quotas
```

**Description:** Create a new token quota for a user.

**Authentication:** Admin required

**Request Body:**

```json
{
  "user_id": 5,
  "name": "Daily User Quota",
  "description": "Daily token limit for user",
  "period_type": "daily",
  "reset_strategy": "calendar",
  "total_tokens": 50000,
  "priority": 5,
  "enforcement_mode": "soft",
  "alert_thresholds": {
    "warning": 80,
    "critical": 90,
    "emergency": 95
  }
}
```

**Response (201 Created):**

```json
{
  "id": 1,
  "user_id": 5,
  "name": "Daily User Quota",
  "total_tokens": 50000,
  "used_tokens": 0,
  "remaining_tokens": 50000,
  "status": "active",
  "created_at": "2026-06-13T10:00:00Z"
}
```

**Error Responses:**

- `400 Bad Request`: Invalid input data or user already has quota
- `403 Forbidden`: Insufficient permissions
- `422 Unprocessable Entity`: Validation error

**cURL Example:**

```bash
curl -X POST "http://localhost:8080/api/v1/token/quotas" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 5,
    "name": "Daily User Quota",
    "period_type": "daily",
    "total_tokens": 50000
  }'
```

---

### 4. Update Quota

```http
PUT /api/v1/token/quotas/{quota_id}
```

**Description:** Update an existing token quota configuration.

**Authentication:** Admin required

**Path Parameters:**

- `quota_id` (integer, required): Quota ID (≥ 1)

**Request Body:**

```json
{
  "name": "Daily User Quota (Updated)",
  "total_tokens": 75000,
  "enforcement_mode": "hard"
}
```

**Response (200 OK):**

```json
{
  "id": 1,
  "name": "Daily User Quota (Updated)",
  "total_tokens": 75000,
  "used_tokens": 25000,
  "remaining_tokens": 50000,
  "enforcement_mode": "hard",
  "updated_at": "2026-06-13T12:00:00Z"
}
```

**Error Responses:**

- `400 Bad Request`: Invalid input data
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Quota not found

**cURL Example:**

```bash
curl -X PUT "http://localhost:8080/api/v1/token/quotas/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "total_tokens": 75000,
    "enforcement_mode": "hard"
  }'
```

---

### 5. Reset Quota

```http
POST /api/v1/token/quotas/{quota_id}/reset
```

**Description:** Reset quota usage counters and start new period.

**Authentication:** Admin required

**Path Parameters:**

- `quota_id` (integer, required): Quota ID (≥ 1)

**Response (200 OK):**

```json
{
  "quota_id": 1,
  "user_id": 5,
  "message": "Quota reset successfully",
  "used_tokens": 0,
  "remaining_tokens": 50000,
  "last_reset_at": "2026-06-13T12:00:00Z"
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Quota not found

**cURL Example:**

```bash
curl -X POST "http://localhost:8080/api/v1/token/quotas/1/reset" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 6. Get User's Quota

```http
GET /api/v1/token/quotas/user/{user_id}
```

**Description:** Retrieve the token quota for a specific user.

**Authentication:** User required

**Path Parameters:**

- `user_id` (integer, required): User ID (≥ 1)

**Response (200 OK):**

```json
{
  "id": 1,
  "user_id": 5,
  "name": "Daily User Quota",
  "total_tokens": 50000,
  "used_tokens": 25000,
  "remaining_tokens": 25000,
  "usage_percentage": 50.0,
  "status": "active"
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Quota not found for user

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/quotas/user/5" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 7. List All Quotas

```http
GET /api/v1/token/quotas
```

**Description:** List all token quotas with pagination (admin only).

**Authentication:** Admin required

**Query Parameters:**

- `page` (integer, optional): Page number (default: 1, ≥ 1)
- `page_size` (integer, optional): Items per page (default: 20, 1-100)
- `status_filter` (string, optional): Filter by status

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": 1,
      "user_id": 5,
      "name": "Daily User Quota",
      "total_tokens": 50000,
      "used_tokens": 25000,
      "status": "active"
    },
    {
      "id": 2,
      "user_id": 6,
      "name": "Daily User Quota",
      "total_tokens": 50000,
      "used_tokens": 10000,
      "status": "active"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 20,
  "total_pages": 2
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/quotas?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 8. Get Quota Status

```http
GET /api/v1/token/quotas/{quota_id}/status
```

**Description:** Get detailed status information for a quota.

**Authentication:** User required

**Path Parameters:**

- `quota_id` (integer, required): Quota ID (≥ 1)

**Response (200 OK):**

```json
{
  "quota_id": 1,
  "user_id": 5,
  "name": "Daily User Quota",
  "total_tokens": 50000,
  "used_tokens": 42000,
  "remaining_tokens": 8000,
  "usage_percentage": 84.0,
  "status": "active",
  "is_near_limit": true,
  "is_exhausted": false,
  "period_type": "daily",
  "reset_strategy": "calendar",
  "period_start": "2026-06-13T00:00:00Z",
  "period_end": "2026-06-13T23:59:59Z",
  "last_reset_at": "2026-06-13T00:00:00Z",
  "enforcement_mode": "soft",
  "priority": 5,
  "alert_thresholds": {
    "warning": 80,
    "critical": 90,
    "emergency": 95
  }
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Quota not found

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/quotas/1/status" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Alert Endpoints

### 1. Get Active Alerts

```http
GET /api/v1/token/alerts
```

**Description:** Retrieve active token alerts with optional filtering.

**Authentication:** User required

**Query Parameters:**

- `page` (integer, optional): Page number (default: 1, ≥ 1)
- `page_size` (integer, optional): Items per page (default: 20, 1-100)
- `severity` (string, optional): Filter by severity
- `alert_type` (string, optional): Filter by alert type
- `acknowledged_only` (boolean, optional): Show only acknowledged alerts

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": 1,
      "alert_type": "budget_warning",
      "severity": "warning",
      "budget_id": 1,
      "user_id": 5,
      "threshold_value": 80.0,
      "current_value": 85.0,
      "message": "Budget 'Test Suite 1' exceeded warning threshold",
      "is_acknowledged": false,
      "created_at": "2026-06-13T10:00:00Z"
    },
    {
      "id": 2,
      "alert_type": "quota_warning",
      "severity": "warning",
      "quota_id": 1,
      "user_id": 5,
      "threshold_value": 80.0,
      "current_value": 84.0,
      "message": "Quota 'Daily User Quota' exceeded warning threshold",
      "is_acknowledged": false,
      "created_at": "2026-06-13T09:00:00Z"
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts?page=1&severity=warning" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 2. Get Alert by ID

```http
GET /api/v1/token/alerts/{alert_id}
```

**Description:** Retrieve detailed information about a specific alert.

**Authentication:** User required

**Path Parameters:**

- `alert_id` (integer, required): Alert ID (≥ 1)

**Response (200 OK):**

```json
{
  "id": 1,
  "alert_type": "budget_warning",
  "severity": "warning",
  "budget_id": 1,
  "quota_id": null,
  "user_id": 5,
  "threshold_type": "percentage",
  "threshold_value": 80.0,
  "current_value": 85.0,
  "metrics_snapshot": {
    "budget_id": 1,
    "budget_name": "Test Suite 1",
    "usage_percentage": 85.0,
    "total_tokens": 1000000,
    "used_tokens": 850000
  },
  "message": "Budget 'Test Suite 1' exceeded warning threshold",
  "details": {},
  "is_acknowledged": false,
  "acknowledged_by": null,
  "acknowledged_at": null,
  "created_at": "2026-06-13T10:00:00Z",
  "resolved_at": null
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Alert not found

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/1" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 3. Acknowledge Alert

```http
POST /api/v1/token/alerts/{alert_id}/acknowledge
```

**Description:** Mark an alert as acknowledged.

**Authentication:** User required

**Path Parameters:**

- `alert_id` (integer, required): Alert ID (≥ 1)

**Request Body (optional):**

```json
{
  "acknowledged": true
}
```

**Response (200 OK):**

```json
{
  "alert_id": 1,
  "acknowledged": true,
  "acknowledged_by": 5,
  "acknowledged_at": "2026-06-13T12:00:00Z",
  "message": "Alert acknowledged successfully"
}
```

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Alert not found

**cURL Example:**

```bash
curl -X POST "http://localhost:8080/api/v1/token/alerts/1/acknowledge" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"acknowledged": true}'
```

---

### 4. Get Alert History

```http
GET /api/v1/token/alerts/history
```

**Description:** Retrieve historical alerts including resolved ones.

**Authentication:** User required

**Query Parameters:**

- `page` (integer, optional): Page number (default: 1, ≥ 1)
- `page_size` (integer, optional): Items per page (default: 20, 1-100)
- `days_back` (integer, optional): Number of days to look back (default: 30, 1-365)
- `severity` (string, optional): Filter by severity

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": 15,
      "alert_type": "budget_critical",
      "severity": "critical",
      "budget_id": 2,
      "message": "Budget 'Test Suite 2' exceeded critical threshold",
      "is_acknowledged": true,
      "created_at": "2026-06-01T15:00:00Z",
      "resolved_at": "2026-06-01T16:00:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/history?days_back=30&severity=critical" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 5. Update Alert Configuration

```http
PUT /api/v1/token/alerts/config
```

**Description:** Update global or user-specific alert configuration.

**Authentication:** Admin required

**Query Parameters:**

- `enable_email` (boolean, optional): Enable email notifications
- `enable_webhook` (boolean, optional): Enable webhook notifications
- `webhook_url` (string, optional): Webhook URL

**Response (200 OK):**

```json
{
  "message": "Alert configuration updated successfully",
  "config": {
    "email_notifications_enabled": true,
    "webhook_notifications_enabled": true,
    "webhook_url": "https://hooks.company.com/alerts",
    "updated_at": "2026-06-13T12:00:00Z",
    "updated_by": 1
  }
}
```

**cURL Example:**

```bash
curl -X PUT "http://localhost:8080/api/v1/token/alerts/config?enable_email=true&enable_webhook=true&webhook_url=https://hooks.company.com/alerts" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 6. Get Current User's Alerts

```http
GET /api/v1/token/alerts/my-alerts
```

**Description:** Retrieve alerts for the currently authenticated user.

**Authentication:** User required

**Query Parameters:**

- `page` (integer, optional): Page number (default: 1, ≥ 1)
- `page_size` (integer, optional): Items per page (default: 20, 1-100)
- `severity` (string, optional): Filter by severity
- `acknowledged` (boolean, optional): Filter by acknowledgment status

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": 5,
      "alert_type": "quota_warning",
      "severity": "warning",
      "quota_id": 1,
      "user_id": 5,
      "message": "Your quota is at 84% capacity",
      "is_acknowledged": false,
      "created_at": "2026-06-13T09:00:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/my-alerts?acknowledged=false" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 7. Delete Alert

```http
DELETE /api/v1/token/alerts/{alert_id}
```

**Description:** Delete an alert (admin only).

**Authentication:** Admin required

**Path Parameters:**

- `alert_id` (integer, required): Alert ID (≥ 1)

**Response (204 No Content):**

No content returned on successful deletion.

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Alert not found

**cURL Example:**

```bash
curl -X DELETE "http://localhost:8080/api/v1/token/alerts/15" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 8. Get Alert Statistics

```http
GET /api/v1/token/alerts/stats/summary
```

**Description:** Get summary statistics for alerts.

**Authentication:** Admin required

**Query Parameters:**

- `days_back` (integer, optional): Number of days to analyze (default: 30, 1-365)

**Response (200 OK):**

```json
{
  "period": {
    "days": 30,
    "start_date": "2026-05-14T00:00:00Z",
    "end_date": "2026-06-13T00:00:00Z"
  },
  "total_alerts": 125,
  "by_severity": {
    "info": 20,
    "warning": 65,
    "critical": 30,
    "emergency": 10
  },
  "by_type": {
    "budget_warning": 40,
    "budget_critical": 20,
    "quota_warning": 35,
    "quota_critical": 15,
    "enforcement_action": 15
  },
  "acknowledged": 100,
  "unacknowledged": 25,
  "acknowledgement_rate": 0.8
}
```

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/stats/summary?days_back=30" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 9. Get Alert Stats Summary

```http
GET /api/v1/token/alerts/stats/summary
```

**Description:** Get summary statistics for alerts (same as #8).

**Authentication:** Admin required

**Query Parameters:**

- `days_back` (integer, optional): Number of days to analyze (default: 30, 1-365)

**Response (200 OK):**

Same as endpoint #8 above.

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/alerts/stats/summary?days_back=30" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 10. Delete Quota

```http
DELETE /api/v1/token/quotas/{quota_id}
```

**Description:** Delete a token quota.

**Authentication:** Admin required

**Path Parameters:**

- `quota_id` (integer, required): Quota ID (≥ 1)

**Response (204 No Content):**

No content returned on successful deletion.

**Error Responses:**

- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Quota not found

**cURL Example:**

```bash
curl -X DELETE "http://localhost:8080/api/v1/token/quotas/1" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Analytics Endpoints

### 1. Get Token Costs

```http
GET /api/v1/token/analytics/costs
```

**Description:** Retrieve token cost information and spending analysis.

**Authentication:** User required

**Query Parameters:**

- `start_date` (datetime, optional): Start date filter
- `end_date` (datetime, optional): End date filter
- `scope_type` (string, optional): Filter by scope type
- `scope_id` (integer, optional): Filter by scope ID

**Response (200 OK):**

```json
{
  "period": {
    "start_date": "2026-05-14T00:00:00Z",
    "end_date": "2026-06-13T00:00:00Z"
  },
  "total_tokens": 1500000,
  "total_cost": 45.00,
  "average_cost_per_token": 0.00003,
  "by_scope": {
    "organization": {
      "tokens": 500000,
      "cost": 15.00
    },
    "suite": {
      "tokens": 600000,
      "cost": 18.00
    },
    "test": {
      "tokens": 300000,
      "cost": 9.00
    },
    "user": {
      "tokens": 100000,
      "cost": 3.00
    }
  },
  "cost_trend": "increasing"
}
```

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/costs?start_date=2026-05-01&end_date=2026-06-13" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 2. Get Usage by Scope

```http
GET /api/v1/token/analytics/by-scope/{scope}
```

**Description:** Retrieve token usage statistics grouped by scope type.

**Authentication:** User required

**Path Parameters:**

- `scope` (string, required): Scope type (organization, suite, test, user)

**Query Parameters:**

- `start_date` (datetime, optional): Start date filter
- `end_date` (datetime, optional): End date filter
- `group_by` (string, optional): Grouping period (hour, day, week, month, default: day)

**Response (200 OK):**

```json
{
  "scope_type": "suite",
  "period": {
    "start_date": "2026-05-14T00:00:00Z",
    "end_date": "2026-06-13T00:00:00Z"
  },
  "total_tokens": 600000,
  "total_requests": 150,
  "average_tokens_per_request": 4000,
  "time_series": [
    {
      "date": "2026-06-01",
      "tokens": 45000,
      "requests": 12
    },
    {
      "date": "2026-06-02",
      "tokens": 52000,
      "requests": 15
    }
  ],
  "top_consumers": [
    {
      "scope_id": 1,
      "name": "Test Suite 1",
      "tokens": 150000,
      "percentage": 25.0
    },
    {
      "scope_id": 2,
      "name": "Test Suite 2",
      "tokens": 120000,
      "percentage": 20.0
    }
  ]
}
```

**Error Responses:**

- `400 Bad Request`: Invalid scope type

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/by-scope/suite?group_by=day" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 3. Get Usage Forecasts

```http
GET /api/v1/token/analytics/forecasts
```

**Description:** Get token usage forecasts and budget exhaustion predictions.

**Authentication:** User required

**Query Parameters:**

- `budget_id` (integer, required): Budget ID to forecast
- `forecast_days` (integer, optional): Days to forecast (default: 30, 1-365)

**Response (200 OK):**

```json
{
  "budget_id": 1,
  "budget_name": "Test Suite 1",
  "forecast_period": {
    "start_date": "2026-06-13T00:00:00Z",
    "end_date": "2026-07-13T00:00:00Z",
    "days": 30
  },
  "current_usage": {
    "total_tokens": 1000000,
    "used_tokens": 850000,
    "remaining_tokens": 150000,
    "usage_percentage": 85.0
  },
  "forecast": {
    "average_daily_usage": 28000,
    "projected_total_usage": 980000,
    "days_until_exhaustion": 5,
    "exhaustion_date": "2026-06-18T00:00:00Z",
    "confidence": 0.85
  },
  "recommendations": [
    "Budget will be exhausted in 5 days",
    "Consider increasing budget limit",
    "Review high-consumption tests"
  ]
}
```

**Error Responses:**

- `404 Not Found`: Budget not found

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/forecasts?budget_id=1&forecast_days=30" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 4. Get Usage Trends

```http
GET /api/v1/token/analytics/trends
```

**Description:** Analyze token usage trends over time.

**Authentication:** User required

**Query Parameters:**

- `period` (string, optional): Analysis period (hourly, daily, weekly, monthly, default: daily)
- `days_back` (integer, optional): Number of days to analyze (default: 30, 1-365)
- `scope_type` (string, optional): Filter by scope type

**Response (200 OK):**

```json
{
  "period": "daily",
  "analysis_period": {
    "start_date": "2026-05-14T00:00:00Z",
    "end_date": "2026-06-13T00:00:00Z",
    "days": 30
  },
  "trend": {
    "direction": "increasing",
    "rate": 0.15,
    "change_percentage": 15.0
  },
  "statistics": {
    "total_tokens": 1500000,
    "average_daily": 50000,
    "median_daily": 48000,
    "max_daily": 85000,
    "min_daily": 25000
  },
  "time_series": [
    {
      "date": "2026-06-01",
      "tokens": 45000,
      "change": 0.05
    },
    {
      "date": "2026-06-02",
      "tokens": 52000,
      "change": 0.15
    }
  ]
}
```

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/trends?period=daily&days_back=30" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 5. Get Usage Summary

```http
GET /api/v1/token/analytics/summary
```

**Description:** Get overall token usage summary statistics.

**Authentication:** User required

**Query Parameters:**

- `start_date` (datetime, optional): Start date filter
- `end_date` (datetime, optional): End date filter

**Response (200 OK):**

```json
{
  "period": {
    "start_date": "2026-05-14T00:00:00Z",
    "end_date": "2026-06-13T00:00:00Z"
  },
  "overview": {
    "total_tokens": 1500000,
    "total_requests": 375,
    "average_tokens_per_request": 4000,
    "total_cost": 45.00
  },
  "by_scope_type": {
    "organization": {
      "tokens": 500000,
      "requests": 50,
      "percentage": 33.3
    },
    "suite": {
      "tokens": 600000,
      "requests": 150,
      "percentage": 40.0
    },
    "test": {
      "tokens": 300000,
      "requests": 125,
      "percentage": 20.0
    },
    "user": {
      "tokens": 100000,
      "requests": 50,
      "percentage": 6.7
    }
  },
  "by_agent_type": {
    "test_composer": {
      "tokens": 800000,
      "requests": 200,
      "percentage": 53.3
    },
    "script_generator": {
      "tokens": 500000,
      "requests": 125,
      "percentage": 33.3
    },
    "planner_agent": {
      "tokens": 200000,
      "requests": 50,
      "percentage": 13.3
    }
  }
}
```

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/summary?start_date=2026-05-01&end_date=2026-06-13" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 6. Get Model Usage

```http
GET /api/v1/token/analytics/model-usage
```

**Description:** Retrieve token usage statistics grouped by LLM model.

**Authentication:** User required

**Query Parameters:**

- `start_date` (datetime, optional): Start date filter
- `end_date` (datetime, optional): End date filter

**Response (200 OK):**

```json
{
  "period": {
    "start_date": "2026-05-14T00:00:00Z",
    "end_date": "2026-06-13T00:00:00Z"
  },
  "total_tokens": 1500000,
  "by_model": [
    {
      "model_name": "glm-4-plus",
      "tokens": 1200000,
      "requests": 300,
      "percentage": 80.0,
      "average_cost_per_token": 0.00004
    },
    {
      "model_name": "glm-4",
      "tokens": 250000,
      "requests": 60,
      "percentage": 16.7,
      "average_cost_per_token": 0.00002
    },
    {
      "model_name": "glm-3-turbo",
      "tokens": 50000,
      "requests": 15,
      "percentage": 3.3,
      "average_cost_per_token": 0.00001
    }
  ]
}
```

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/model-usage?start_date=2026-05-01" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 7. Get Agent Usage

```http
GET /api/v1/token/analytics/agent-usage
```

**Description:** Retrieve token usage statistics grouped by agent type.

**Authentication:** User required

**Query Parameters:**

- `start_date` (datetime, optional): Start date filter
- `end_date` (datetime, optional): End date filter

**Response (200 OK):**

```json
{
  "period": {
    "start_date": "2026-05-14T00:00:00Z",
    "end_date": "2026-06-13T00:00:00Z"
  },
  "total_tokens": 1500000,
  "by_agent_type": [
    {
      "agent_type": "test_composer",
      "tokens": 800000,
      "requests": 200,
      "percentage": 53.3,
      "average_tokens_per_request": 4000
    },
    {
      "agent_type": "script_generator",
      "tokens": 500000,
      "requests": 125,
      "percentage": 33.3,
      "average_tokens_per_request": 4000
    },
    {
      "agent_type": "planner_agent",
      "tokens": 200000,
      "requests": 50,
      "percentage": 13.3,
      "average_tokens_per_request": 4000
    }
  ]
}
```

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/agent-usage?start_date=2026-05-01" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 8. Compare Budgets

```http
GET /api/v1/token/analytics/comparisons
```

**Description:** Compare multiple budgets side by side.

**Authentication:** User required

**Query Parameters:**

- `budget_ids` (string, required): Comma-separated budget IDs to compare

**Response (200 OK):**

```json
{
  "budgets": [
    {
      "budget_id": 1,
      "name": "Test Suite 1",
      "scope_type": "suite",
      "scope_id": 1,
      "usage_percentage": 85.0,
      "total_tokens": 1000000,
      "used_tokens": 850000,
      "remaining_tokens": 150000,
      "status": "active",
      "enforcement_mode": "soft"
    },
    {
      "budget_id": 2,
      "name": "Test Suite 2",
      "scope_type": "suite",
      "scope_id": 2,
      "usage_percentage": 50.0,
      "total_tokens": 2000000,
      "used_tokens": 1000000,
      "remaining_tokens": 1000000,
      "status": "active",
      "enforcement_mode": "soft"
    },
    {
      "budget_id": 3,
      "name": "Test Suite 3",
      "scope_type": "suite",
      "scope_id": 3,
      "usage_percentage": 25.0,
      "total_tokens": 5000000,
      "used_tokens": 1250000,
      "remaining_tokens": 3750000,
      "status": "active",
      "enforcement_mode": "monitoring"
    }
  ],
  "total_budgets": 3,
  "generated_at": "2026-06-13T12:00:00Z"
}
```

**Error Responses:**

- `400 Bad Request`: Invalid budget IDs format

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/comparisons?budget_ids=1,2,3" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 9. Compare Budget Performance

```http
GET /api/v1/token/analytics/budget-performance
```

**Description:** Analyze budget performance and efficiency metrics.

**Authentication:** User required

**Query Parameters:**

- `budget_id` (integer, required): Budget ID to analyze

**Response (200 OK):**

(See Budget Endpoints #10 above - same response)

**cURL Example:**

```bash
curl -X GET "http://localhost:8080/api/v1/token/analytics/budget-performance?budget_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request

```json
{
  "detail": "Invalid input data",
  "error_code": "VALIDATION_ERROR"
}
```

### 401 Unauthorized

```json
{
  "detail": "Not authenticated",
  "error_code": "AUTHENTICATION_REQUIRED"
}
```

### 403 Forbidden

```json
{
  "detail": "Insufficient permissions",
  "error_code": "AUTHORIZATION_FAILED"
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found",
  "error_code": "NOT_FOUND"
}
```

### 422 Unprocessable Entity

```json
{
  "detail": "Validation error",
  "error_code": "VALIDATION_ERROR",
  "errors": [
    {
      "field": "total_tokens",
      "message": "Must be greater than 0"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error",
  "error_code": "INTERNAL_ERROR"
}
```

## Rate Limiting

API requests are rate-limited to prevent abuse:

- **Standard Users**: 100 requests per minute
- **Admin Users**: 200 requests per minute

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1623542400
```

When rate limit is exceeded:

```json
{
  "detail": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:

```
http://localhost:8080/api/v1/token/openapi.json
```

Or view the interactive Swagger documentation:

```
http://localhost:8080/api/docs
```

### Example OpenAPI Fragment

```yaml
openapi: 3.0.0
info:
  title: Token Limitation API
  version: 1.0.0
  description: API for managing token budgets, quotas, and alerts

paths:
  /token/budgets:
    post:
      summary: Create a token budget
      tags:
        - token-budgets
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TokenBudgetCreate'
      responses:
        '201':
          description: Budget created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TokenBudgetResponse'
        '400':
          description: Invalid input data
        '403':
          description: Insufficient permissions
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  schemas:
    TokenBudgetCreate:
      type: object
      required:
        - name
        - scope_type
        - total_tokens
      properties:
        name:
          type: string
        scope_type:
          type: string
          enum: [organization, suite, test, user]
        total_tokens:
          type: integer
          minimum: 1
```

---

**Next:** See [User Guide](TOKEN_LIMITATION_USER_GUIDE.md) for practical usage examples and workflows.