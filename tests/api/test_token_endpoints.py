"""
Token API Endpoint Tests

Comprehensive tests for all token-related API endpoints:
- Budget endpoints (9 endpoints)
- Quota endpoints (9 endpoints)
- Alert endpoints (8 endpoints)
- Analytics endpoints (9 endpoints)
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import status
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.models.token_budget import TokenBudget
from app.models.token_quota import TokenQuota
from app.models.token_alert import TokenAlert


class TestTokenBudgetEndpoints:
    """Test suite for token budget API endpoints."""

    @pytest.fixture
    def client(self):
        """Get test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, test_user):
        """Get authentication headers."""
        # This would normally use JWT token
        return {"Authorization": f"Bearer test-token-{test_user.id}"}

    @pytest.fixture
    def admin_auth_headers(self, test_admin_user):
        """Get admin authentication headers."""
        return {"Authorization": f"Bearer admin-token-{test_admin_user.id}"}

    def test_create_budget_success(self, client: TestClient, admin_auth_headers: dict, sample_token_budget_data: dict):
        """Test successful budget creation."""
        response = client.post(
            "/api/v1/token/budgets/",
            json=sample_token_budget_data,
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == sample_token_budget_data["name"]
        assert data["scope_type"] == sample_token_budget_data["scope_type"]
        assert "id" in data

    def test_create_budget_unauthorized(self, client: TestClient, auth_headers: dict, sample_token_budget_data: dict):
        """Test budget creation without admin privileges fails."""
        response = client.post(
            "/api/v1/token/budgets/",
            json=sample_token_budget_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_budget_validation_error(self, client: TestClient, admin_auth_headers: dict):
        """Test budget creation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name should fail validation
            "scope_type": "invalid_scope",
            "total_tokens": -100  # Negative tokens should fail
        }

        response = client.post(
            "/api/v1/token/budgets/",
            json=invalid_data,
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_budget_by_id(self, client: TestClient, auth_headers: dict, sample_token_budget: TokenBudget):
        """Test retrieving budget by ID."""
        response = client.get(
            f"/api/v1/token/budgets/{sample_token_budget.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_token_budget.id
        assert data["name"] == sample_token_budget.name

    def test_get_budget_not_found(self, client: TestClient, auth_headers: dict):
        """Test retrieving non-existent budget."""
        response = client.get(
            "/api/v1/token/budgets/99999",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_budgets(self, client: TestClient, auth_headers: dict):
        """Test listing all budgets."""
        response = client.get(
            "/api/v1/token/budgets/",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "budgets" in data
        assert isinstance(data["budgets"], list)

    def test_list_budgets_with_filters(self, client: TestClient, auth_headers: dict):
        """Test listing budgets with filters."""
        response = client.get(
            "/api/v1/token/budgets/?scope_type=organization&status=active",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "budgets" in data

    def test_update_budget(self, client: TestClient, admin_auth_headers: dict, sample_token_budget: TokenBudget):
        """Test updating a budget."""
        update_data = {
            "name": "Updated Budget Name",
            "total_tokens": 2000000,
            "priority": 8
        }

        response = client.put(
            f"/api/v1/token/budgets/{sample_token_budget.id}",
            json=update_data,
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Budget Name"
        assert data["total_tokens"] == 2000000

    def test_delete_budget(self, client: TestClient, admin_auth_headers: dict, sample_token_budget: TokenBudget):
        """Test deleting a budget."""
        response = client.delete(
            f"/api/v1/token/budgets/{sample_token_budget.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_get_budget_status(self, client: TestClient, auth_headers: dict, sample_token_budget: TokenBudget):
        """Test getting budget status."""
        response = client.get(
            f"/api/v1/token/budgets/{sample_token_budget.id}/status",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "usage_percentage" in data
        assert "remaining_tokens" in data

    def test_reset_budget_period(self, client: TestClient, admin_auth_headers: dict, sample_token_budget: TokenBudget):
        """Test resetting budget period."""
        reset_data = {
            "new_period_start": "2026-06-13T00:00:00",
            "new_period_end": "2026-07-13T00:00:00"
        }

        response = client.post(
            f"/api/v1/token/budgets/{sample_token_budget.id}/reset",
            json=reset_data,
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["used_tokens"] == 0
        assert data["status"] == "active"


class TestTokenQuotaEndpoints:
    """Test suite for token quota API endpoints."""

    @pytest.fixture
    def client(self):
        """Get test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, test_user):
        """Get authentication headers."""
        return {"Authorization": f"Bearer test-token-{test_user.id}"}

    @pytest.fixture
    def admin_auth_headers(self, test_admin_user):
        """Get admin authentication headers."""
        return {"Authorization": f"Bearer admin-token-{test_admin_user.id}"}

    def test_create_quota_success(self, client: TestClient, admin_auth_headers: dict, sample_token_quota_data: dict):
        """Test successful quota creation."""
        response = client.post(
            "/api/v1/token/quotas/",
            json=sample_token_quota_data,
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == sample_token_quota_data["name"]
        assert data["user_id"] == sample_token_quota_data["user_id"]

    def test_get_quota_by_id(self, client: TestClient, auth_headers: dict, sample_token_quota: TokenQuota):
        """Test retrieving quota by ID."""
        response = client.get(
            f"/api/v1/token/quotas/{sample_token_quota.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_token_quota.id

    def test_list_user_quotas(self, client: TestClient, auth_headers: dict, test_user):
        """Test listing user quotas."""
        response = client.get(
            f"/api/v1/token/quotas/user/{test_user.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "quotas" in data

    def test_update_quota(self, client: TestClient, admin_auth_headers: dict, sample_token_quota: TokenQuota):
        """Test updating a quota."""
        update_data = {
            "name": "Updated Quota Name",
            "total_tokens": 200000
        }

        response = client.put(
            f"/api/v1/token/quotas/{sample_token_quota.id}",
            json=update_data,
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Quota Name"

    def test_delete_quota(self, client: TestClient, admin_auth_headers: dict, sample_token_quota: TokenQuota):
        """Test deleting a quota."""
        response = client.delete(
            f"/api/v1/token/quotas/{sample_token_quota.id}",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_get_quota_status(self, client: TestClient, auth_headers: dict, sample_token_quota: TokenQuota):
        """Test getting quota status."""
        response = client.get(
            f"/api/v1/token/quotas/{sample_token_quota.id}/status",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "usage_percentage" in data

    def test_reset_quota_period(self, client: TestClient, admin_auth_headers: dict, sample_token_quota: TokenQuota):
        """Test resetting quota period."""
        reset_data = {
            "new_period_start": "2026-06-13T00:00:00"
        }

        response = client.post(
            f"/api/v1/token/quotas/{sample_token_quota.id}/reset",
            json=reset_data,
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["used_tokens"] == 0

    def test_list_active_quotas(self, client: TestClient, auth_headers: dict):
        """Test listing active quotas."""
        response = client.get(
            "/api/v1/token/quotas/active/list",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "quotas" in data

    def test_reset_user_quotas(self, client: TestClient, admin_auth_headers: dict, test_user):
        """Test resetting all user quotas."""
        response = client.post(
            f"/api/v1/token/quotas/user/{test_user.id}/reset-all",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK


class TestTokenAlertEndpoints:
    """Test suite for token alert API endpoints."""

    @pytest.fixture
    def client(self):
        """Get test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, test_user):
        """Get authentication headers."""
        return {"Authorization": f"Bearer test-token-{test_user.id}"}

    @pytest.fixture
    def admin_auth_headers(self, test_admin_user):
        """Get admin authentication headers."""
        return {"Authorization": f"Bearer admin-token-{test_admin_user.id}"}

    def test_list_alerts(self, client: TestClient, auth_headers: dict):
        """Test listing all alerts."""
        response = client.get(
            "/api/v1/token/alerts/",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "alerts" in data

    def test_get_alert_by_id(self, client: TestClient, auth_headers: dict, sample_token_alert: TokenAlert):
        """Test retrieving alert by ID."""
        response = client.get(
            f"/api/v1/token/alerts/{sample_token_alert.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_token_alert.id

    def test_acknowledge_alert(self, client: TestClient, auth_headers: dict, sample_token_alert: TokenAlert):
        """Test acknowledging an alert."""
        response = client.post(
            f"/api/v1/token/alerts/{sample_token_alert.id}/acknowledge",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_acknowledged"] is True

    def test_list_unacknowledged_alerts(self, client: TestClient, auth_headers: dict):
        """Test listing unacknowledged alerts."""
        response = client.get(
            "/api/v1/token/alerts/unacknowledged",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "alerts" in data

    def test_list_critical_alerts(self, client: TestClient, auth_headers: dict):
        """Test listing critical alerts."""
        response = client.get(
            "/api/v1/token/alerts/critical",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "alerts" in data

    def test_list_budget_alerts(self, client: TestClient, auth_headers: dict, sample_token_budget: TokenBudget):
        """Test listing alerts for a budget."""
        response = client.get(
            f"/api/v1/token/alerts/budget/{sample_token_budget.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "alerts" in data

    def test_list_quota_alerts(self, client: TestClient, auth_headers: dict, sample_token_quota: TokenQuota):
        """Test listing alerts for a quota."""
        response = client.get(
            f"/api/v1/token/alerts/quota/{sample_token_quota.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "alerts" in data

    def test_mark_notification_sent(self, client: TestClient, admin_auth_headers: dict, sample_token_alert: TokenAlert):
        """Test marking notification as sent."""
        notification_data = {
            "channel": "email",
            "success": True
        }

        response = client.post(
            f"/api/v1/token/alerts/{sample_token_alert.id}/notification",
            json=notification_data,
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK


class TestTokenAnalyticsEndpoints:
    """Test suite for token analytics API endpoints."""

    @pytest.fixture
    def client(self):
        """Get test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, test_user):
        """Get authentication headers."""
        return {"Authorization": f"Bearer test-token-{test_user.id}"}

    def test_get_system_overview(self, client: TestClient, auth_headers: dict):
        """Test getting system overview."""
        response = client.get(
            "/api/v1/token/analytics/system-overview",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_budgets" in data
        assert "total_quotas" in data

    def test_get_budget_report(self, client: TestClient, auth_headers: dict, sample_token_budget: TokenBudget):
        """Test getting budget report."""
        response = client.get(
            f"/api/v1/token/analytics/budget/{sample_token_budget.id}/report",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "budget_info" in data

    def test_get_user_report(self, client: TestClient, auth_headers: dict, test_user):
        """Test getting user report."""
        response = client.get(
            f"/api/v1/token/analytics/user/{test_user.id}/report",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "user_id" in data
        assert "quotas" in data

    def test_get_usage_trends(self, client: TestClient, auth_headers: dict):
        """Test getting usage trends."""
        response = client.get(
            "/api/v1/token/analytics/trends?days=7",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "trends" in data

    def test_get_top_consumers(self, client: TestClient, auth_headers: dict):
        """Test getting top consumers."""
        response = client.get(
            "/api/v1/token/analytics/top-consumers?limit=10",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "consumers" in data

    def test_get_forecast_data(self, client: TestClient, auth_headers: dict, sample_token_budget: TokenBudget):
        """Test getting forecast data."""
        response = client.get(
            f"/api/v1/token/analytics/budget/{sample_token_budget.id}/forecast",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "forecast_data" in data

    def test_get_exhausted_budgets(self, client: TestClient, auth_headers: dict):
        """Test getting exhausted budgets."""
        response = client.get(
            "/api/v1/token/analytics/exhausted-budgets",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "budgets" in data

    def test_get_near_limit_budgets(self, client: TestClient, auth_headers: dict):
        """Test getting budgets near limit."""
        response = client.get(
            "/api/v1/token/analytics/near-limit?threshold=80",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "budgets" in data

    def test_get_alert_summary(self, client: TestClient, auth_headers: dict):
        """Test getting alert summary."""
        response = client.get(
            "/api/v1/token/analytics/alerts/summary",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "summary" in data


# Test authentication and authorization
class TestTokenEndpointAuth:
    """Test authentication and authorization for token endpoints."""

    @pytest.fixture
    def client(self):
        """Get test client."""
        return TestClient(app)

    def test_endpoints_require_authentication(self, client: TestClient):
        """Test that endpoints require authentication."""
        endpoints = [
            "/api/v1/token/budgets/",
            "/api/v1/token/quotas/",
            "/api/v1/token/alerts/",
            "/api/v1/token/analytics/system-overview"
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_endpoints_require_admin_privileges(self, client: TestClient, auth_headers: dict):
        """Test that admin endpoints require admin privileges."""
        admin_endpoints = [
            ("POST", "/api/v1/token/budgets/", {}),
            ("PUT", "/api/v1/token/budgets/1", {}),
            ("DELETE", "/api/v1/token/budgets/1", {}),
        ]

        for method, endpoint, data in admin_endpoints:
            if method == "POST":
                response = client.post(endpoint, json=data, headers=auth_headers)
            elif method == "PUT":
                response = client.put(endpoint, json=data, headers=auth_headers)
            elif method == "DELETE":
                response = client.delete(endpoint, headers=auth_headers)

            # Should fail for non-admin user
            assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
