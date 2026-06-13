"""
Token Decorator Tests

Comprehensive tests for token limitation decorators:
- @check_token_budget
- @track_token_usage
- @enforce_token_limits
- TokenLimiter context manager
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.decorators.token_decorators import (
    check_token_budget,
    track_token_usage,
    enforce_token_limits,
    TokenLimiter
)
from app.core.exceptions.token_exceptions import TokenBudgetExceeded, TokenQuotaExceeded
from app.services.token_budget_service import TokenBudgetService
from app.services.token_quota_service import TokenQuotaService


class TestCheckTokenBudgetDecorator:
    """Test suite for @check_token_budget decorator."""

    @pytest.fixture
    def mock_budget_service(self):
        """Mock budget service."""
        service = Mock(spec=TokenBudgetService)
        service.check_token_availability = AsyncMock()
        return service

    @pytest.fixture
    def test_db_session(self):
        """Mock database session."""
        return Mock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_check_allows_sufficient_budget(self, mock_budget_service, test_db_session):
        """Test that decorator allows execution when budget is sufficient."""
        # Mock successful check
        from app.core.result_helpers import service_success
        mock_budget_service.check_token_availability.return_value = service_success({
            "available": True,
            "remaining_tokens": 500000,
            "budget_id": 1
        })

        @check_token_budget(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            enforcement_mode="soft"
        )
        async def test_function(prompt: str, scope_type: str, scope_id: int, **kwargs):
            return {"result": "success"}

        result = await test_function(
            prompt="Test prompt",
            scope_type="test",
            scope_id=123,
            token_budget_service=mock_budget_service,
            db=test_db_session
        )

        assert result["result"] == "success"
        mock_budget_service.check_token_availability.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_blocks_insufficient_budget_hard_mode(self, mock_budget_service, test_db_session):
        """Test that decorator blocks execution in hard mode when budget exceeded."""
        from app.core.result_helpers import service_success

        # Mock failed check
        mock_budget_service.check_token_availability.return_value = service_success({
            "available": False,
            "reason": "insufficient_tokens",
            "enforcement_action": "blocked",
            "budget_id": 1,
            "available_tokens": 1000,
            "requested_tokens": 5000
        })

        @check_token_budget(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            enforcement_mode="hard",
            on_exceeded="raise"
        )
        async def test_function(prompt: str, scope_type: str, scope_id: int, **kwargs):
            return {"result": "should not execute"}

        with pytest.raises(TokenBudgetExceeded):
            await test_function(
                prompt="Test prompt",
                scope_type="test",
                scope_id=123,
                token_budget_service=mock_budget_service,
                db=test_db_session
            )

    @pytest.mark.asyncio
    async def test_check_warns_insufficient_budget_soft_mode(self, mock_budget_service, test_db_session):
        """Test that decorator warns but allows execution in soft mode."""
        from app.core.result_helpers import service_success

        # Mock failed check
        mock_budget_service.check_token_availability.return_value = service_success({
            "available": False,
            "reason": "insufficient_tokens",
            "enforcement_action": "warning",
            "budget_id": 1
        })

        @check_token_budget(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            enforcement_mode="soft",
            on_exceeded="warn"
        )
        async def test_function(prompt: str, scope_type: str, scope_id: int, **kwargs):
            return {"result": "executed with warning"}

        result = await test_function(
            prompt="Test prompt",
            scope_type="test",
            scope_id=123,
            token_budget_service=mock_budget_service,
            db=test_db_session
        )

        # Should still execute in soft mode
        assert result["result"] == "executed with warning"

    @pytest.mark.asyncio
    async def test_check_returns_early_on_exceeded(self, mock_budget_service, test_db_session):
        """Test that decorator returns early when configured."""
        from app.core.result_helpers import service_success

        mock_budget_service.check_token_availability.return_value = service_success({
            "available": False,
            "enforcement_action": "blocked",
            "budget_id": 1,
            "available_tokens": 1000,
            "requested_tokens": 5000
        })

        @check_token_budget(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            enforcement_mode="hard",
            on_exceeded="return"
        )
        async def test_function(prompt: str, scope_type: str, scope_id: int, **kwargs):
            return {"result": "should not execute"}

        result = await test_function(
            prompt="Test prompt",
            scope_type="test",
            scope_id=123,
            token_budget_service=mock_budget_service,
            db=test_db_session
        )

        assert result["error"] == "token_budget_exceeded"
        assert result["available_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_check_skips_when_missing_parameters(self, mock_budget_service, test_db_session):
        """Test that decorator skips check when required parameters are missing."""
        @check_token_budget()
        async def test_function(prompt: str, **kwargs):
            return {"result": "executed without check"}

        result = await test_function(prompt="Test prompt")

        # Should execute without check
        assert result["result"] == "executed without check"
        mock_budget_service.check_token_availability.assert_not_called()


class TestTrackTokenUsageDecorator:
    """Test suite for @track_token_usage decorator."""

    @pytest.fixture
    def mock_budget_service(self):
        """Mock budget service."""
        service = Mock(spec=TokenBudgetService)
        service.record_token_usage = AsyncMock()
        return service

    @pytest.fixture
    def mock_quota_service(self):
        """Mock quota service."""
        service = Mock(spec=TokenQuotaService)
        service.record_quota_usage = AsyncMock()
        return service

    @pytest.fixture
    def test_db_session(self):
        """Mock database session."""
        return Mock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_track_usage_from_dict_result(self, mock_budget_service, mock_quota_service, test_db_session):
        """Test tracking usage when function returns dict with tokens_used."""
        @track_token_usage(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            user_id_param="user_id"
        )
        async def test_function(prompt: str, scope_type: str, scope_id: int, user_id: int, **kwargs):
            return {"tokens_used": 1500, "result": "success"}

        result = await test_function(
            prompt="Test prompt",
            scope_type="test",
            scope_id=123,
            user_id=456,
            token_budget_service=mock_budget_service,
            token_quota_service=mock_quota_service,
            db=test_db_session
        )

        assert result["tokens_used"] == 1500
        mock_budget_service.record_token_usage.assert_called_once()
        mock_quota_service.record_quota_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_usage_from_object_result(self, mock_budget_service, mock_quota_service, test_db_session):
        """Test tracking usage when function returns object with tokens_used attribute."""
        @track_token_usage()
        async def test_function(prompt: str, **kwargs):
            result_obj = Mock()
            result_obj.tokens_used = 2000
            return result_obj

        result = await test_function(
            prompt="Test prompt",
            scope_type="test",
            scope_id=123,
            user_id=456,
            token_budget_service=mock_budget_service,
            token_quota_service=mock_quota_service,
            db=test_db_session
        )

        assert result.tokens_used == 2000
        mock_budget_service.record_token_usage.assert_called_once()
        mock_quota_service.record_quota_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_track_usage_skips_when_no_tokens(self, mock_budget_service, mock_quota_service, test_db_session):
        """Test that tracking skips when no tokens_used in result."""
        @track_token_usage()
        async def test_function(prompt: str, **kwargs):
            return {"result": "success"}  # No tokens_used field

        result = await test_function(
            prompt="Test prompt",
            scope_type="test",
            scope_id=123,
            user_id=456,
            token_budget_service=mock_budget_service,
            token_quota_service=mock_quota_service,
            db=test_db_session
        )

        assert result["result"] == "success"
        mock_budget_service.record_token_usage.assert_not_called()
        mock_quota_service.record_quota_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_usage_handles_errors_gracefully(self, mock_budget_service, mock_quota_service, test_db_session):
        """Test that tracking errors don't break function execution."""
        # Make budget service raise error
        mock_budget_service.record_token_usage = AsyncMock(side_effect=Exception("Database error"))

        @track_token_usage()
        async def test_function(prompt: str, **kwargs):
            return {"tokens_used": 1500, "result": "success"}

        result = await test_function(
            prompt="Test prompt",
            scope_type="test",
            scope_id=123,
            user_id=456,
            token_budget_service=mock_budget_service,
            token_quota_service=mock_quota_service,
            db=test_db_session
        )

        # Should still return result despite tracking error
        assert result["result"] == "success"


class TestEnforceTokenLimitsDecorator:
    """Test suite for @enforce_token_limits decorator."""

    @pytest.fixture
    def mock_budget_service(self):
        """Mock budget service."""
        service = Mock(spec=TokenBudgetService)
        service.check_token_availability = AsyncMock()
        service.record_token_usage = AsyncMock()
        return service

    @pytest.fixture
    def mock_quota_service(self):
        """Mock quota service."""
        service = Mock(spec=TokenQuotaService)
        service.record_quota_usage = AsyncMock()
        return service

    @pytest.fixture
    def test_db_session(self):
        """Mock database session."""
        return Mock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_enforce_limits_combined_functionality(self, mock_budget_service, mock_quota_service, test_db_session):
        """Test that combined decorator provides both checking and tracking."""
        from app.core.result_helpers import service_success

        # Mock check passes
        mock_budget_service.check_token_availability.return_value = service_success({
            "available": True,
            "remaining_tokens": 500000
        })

        @enforce_token_limits(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            user_id_param="user_id",
            enforcement_mode="soft"
        )
        async def test_function(prompt: str, scope_type: str, scope_id: int, user_id: int, **kwargs):
            return {"tokens_used": 2500, "result": "success"}

        result = await test_function(
            prompt="Test prompt",
            scope_type="test",
            scope_id=123,
            user_id=456,
            token_budget_service=mock_budget_service,
            token_quota_service=mock_quota_service,
            db=test_db_session
        )

        assert result["result"] == "success"
        # Both check and track should be called
        mock_budget_service.check_token_availability.assert_called_once()
        mock_budget_service.record_token_usage.assert_called_once()
        mock_quota_service.record_quota_usage.assert_called_once()


class TestTokenLimiterContextManager:
    """Test suite for TokenLimiter context manager."""

    @pytest.fixture
    def mock_budget_service(self):
        """Mock budget service."""
        service = Mock(spec=TokenBudgetService)
        service.check_token_availability = AsyncMock()
        service.record_token_usage = AsyncMock()
        return service

    @pytest.fixture
    def mock_quota_service(self):
        """Mock quota service."""
        service = Mock(spec=TokenQuotaService)
        service.record_quota_usage = AsyncMock()
        return service

    @pytest.fixture
    def test_db_session(self):
        """Mock database session."""
        return Mock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_context_manager_check_and_track(self, mock_budget_service, mock_quota_service, test_db_session):
        """Test context manager for check and track workflow."""
        from app.core.result_helpers import service_success

        # Mock check passes
        mock_budget_service.check_token_availability.return_value = service_success({
            "allowed": True,
            "remaining_tokens": 500000
        })

        async with TokenLimiter(
            budget_service=mock_budget_service,
            quota_service=mock_quota_service,
            scope_type="test",
            scope_id=123,
            user_id=456,
            db=test_db_session,
            enforcement_mode="soft"
        ) as limiter:
            # Check availability
            check_result = await limiter.check_availability(
                prompt="Test prompt",
                model="glm-4-plus"
            )
            assert check_result["allowed"] is True

            # Track usage
            await limiter.track_usage(tokens_used=3000)

        # Verify services were called
        mock_budget_service.check_token_availability.assert_called_once()
        mock_budget_service.record_token_usage.assert_called_once()
        mock_quota_service.record_quota_usage.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_without_budget_service(self, test_db_session):
        """Test context manager works without budget service."""
        async with TokenLimiter(
            budget_service=None,
            scope_type="test",
            scope_id=123,
            db=test_db_session
        ) as limiter:
            check_result = await limiter.check_availability(
                prompt="Test prompt",
                model="glm-4-plus"
            )

            # Should allow when no budget service
            assert check_result["allowed"] is True
            assert check_result["reason"] == "No budget service configured"

    @pytest.mark.asyncio
    async def test_context_manager_handles_errors(self, mock_budget_service, test_db_session):
        """Test context manager handles check errors gracefully."""
        # Mock check fails with exception
        mock_budget_service.check_token_availability = AsyncMock(side_effect=Exception("API error"))

        async with TokenLimiter(
            budget_service=mock_budget_service,
            scope_type="test",
            scope_id=123,
            db=test_db_session
        ) as limiter:
            check_result = await limiter.check_availability(
                prompt="Test prompt",
                model="glm-4-plus"
            )

            # Should allow on check failure
            assert check_result["allowed"] is True
            assert check_result["reason"] == "Check failed"

    @pytest.mark.asyncio
    async def test_context_manager_track_without_db(self, mock_budget_service, mock_quota_service):
        """Test that tracking warns when no database session."""
        async with TokenLimiter(
            budget_service=mock_budget_service,
            quota_service=mock_quota_service,
            scope_type="test",
            scope_id=123,
            user_id=456,
            db=None
        ) as limiter:
            # Should not raise error
            await limiter.track_usage(tokens_used=3000)

        # Services should not be called
        mock_budget_service.record_token_usage.assert_not_called()
        mock_quota_service.record_quota_usage.assert_not_called()

    @pytest.mark.asyncio
    async def test_context_manager_concurrent_tracking(self, mock_budget_service, mock_quota_service, test_db_session):
        """Test that budget and quota tracking happen concurrently."""
        async with TokenLimiter(
            budget_service=mock_budget_service,
            quota_service=mock_quota_service,
            scope_type="test",
            scope_id=123,
            user_id=456,
            db=test_db_session
        ) as limiter:
            await limiter.track_usage(tokens_used=5000)

        # Both should be called
        mock_budget_service.record_token_usage.assert_called_once()
        mock_quota_service.record_quota_usage.assert_called_once()
