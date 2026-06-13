"""
Tests for Health Checkers

Tests individual health checker implementations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.health.checkers import (
    DatabaseHealthChecker,
    RedisHealthChecker,
    LLMHealthChecker,
    TemporalHealthChecker,
    FileSystemHealthChecker,
)
from app.core.health_check_types import HealthStatus


class TestDatabaseHealthChecker:
    """Test DatabaseHealthChecker."""

    @pytest.mark.asyncio
    async def test_check_type(self):
        """Test checker type identifier."""
        checker = DatabaseHealthChecker()
        assert checker.get_check_type() == "database"

    @pytest.mark.asyncio
    async def test_is_critical(self):
        """Test if checker is critical."""
        checker = DatabaseHealthChecker()
        assert checker.is_critical() is True

    @pytest.mark.asyncio
    async def test_get_timeout(self):
        """Test timeout value."""
        checker = DatabaseHealthChecker(timeout=10.0)
        assert checker.get_timeout_seconds() == 10.0

    @pytest.mark.asyncio
    async def test_should_run_default(self):
        """Test default should_run behavior."""
        checker = DatabaseHealthChecker()
        assert checker.should_run() is True

    @pytest.mark.asyncio
    async def test_should_run_critical_only(self):
        """Test should_run with critical_only config."""
        checker = DatabaseHealthChecker()
        assert checker.should_run({"critical_only": True}) is True

    @pytest.mark.asyncio
    async def test_check_health_success(self):
        """Test successful health check."""
        checker = DatabaseHealthChecker()

        # Mock database session
        with patch('app.health.checkers.database_health_checker.async_session_maker') as mock_session_maker:
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            # Mock query result
            mock_result = Mock()
            mock_result.fetchone.return_value = [1]
            mock_session.execute.return_value = mock_result

            # Mock second query for performance
            mock_session.execute.return_value = Mock(scalar=Mock(return_value="10MB"))

            result = await checker.check_health()

            assert result.status == HealthStatus.HEALTHY
            assert result.component_name == "database"
            assert "successful" in result.details.lower()
            assert result.is_critical is True

    @pytest.mark.asyncio
    async def test_check_health_failure(self):
        """Test health check with database failure."""
        checker = DatabaseHealthChecker()

        with patch('app.health.checkers.database_health_checker.async_session_maker') as mock_session_maker:
            mock_session_maker.side_effect = Exception("Connection failed")

            result = await checker.check_health()

            assert result.status == HealthStatus.UNHEALTHY
            assert "failed" in result.details.lower()

    @pytest.mark.asyncio
    async def test_safe_check_error_handling(self):
        """Test safe_check error handling."""
        checker = DatabaseHealthChecker()

        # Force an exception
        with patch('app.health.checkers.database_health_checker.async_session_maker') as mock_session_maker:
            mock_session_maker.side_effect = Exception("Test error")

            result = await checker.safe_check()

            assert result.status == HealthStatus.UNHEALTHY
            assert "Test error" in result.details
            assert result.response_time_ms is not None


class TestRedisHealthChecker:
    """Test RedisHealthChecker."""

    @pytest.mark.asyncio
    async def test_check_type(self):
        """Test checker type identifier."""
        checker = RedisHealthChecker()
        assert checker.get_check_type() == "redis"

    @pytest.mark.asyncio
    async def test_is_critical(self):
        """Test if checker is critical."""
        checker = RedisHealthChecker()
        assert checker.is_critical() is True

    @pytest.mark.asyncio
    async def test_check_health_success(self):
        """Test successful health check."""
        checker = RedisHealthChecker()

        with patch('app.health.checkers.redis_health_checker.get_redis') as mock_get_redis:
            mock_redis = Mock()
            mock_redis.ping.return_value = True
            mock_redis.info.return_value = {
                "redis_version": "7.0.0",
                "used_memory_human": "100MB",
                "connected_clients": 5,
            }
            mock_get_redis.return_value = mock_redis

            result = await checker.check_health()

            assert result.status == HealthStatus.HEALTHY
            assert result.component_name == "redis"
            assert "successful" in result.details.lower()

    @pytest.mark.asyncio
    async def test_check_health_failure(self):
        """Test health check with Redis failure."""
        checker = RedisHealthChecker()

        with patch('app.health.checkers.redis_health_checker.get_redis') as mock_get_redis:
            mock_get_redis.side_effect = Exception("Connection failed")

            result = await checker.check_health()

            assert result.status == HealthStatus.UNHEALTHY
            assert "failed" in result.details.lower()


class TestLLMHealthChecker:
    """Test LLMHealthChecker."""

    @pytest.mark.asyncio
    async def test_check_type(self):
        """Test checker type identifier."""
        checker = LLMHealthChecker()
        assert checker.get_check_type() == "llm"

    @pytest.mark.asyncio
    async def test_is_critical(self):
        """Test if checker is critical."""
        checker = LLMHealthChecker()
        assert checker.is_critical() is False  # LLM is not critical

    @pytest.mark.asyncio
    async def test_check_health_no_api_key(self):
        """Test health check without API key."""
        checker = LLMHealthChecker()

        with patch.dict('os.environ', {}, clear=False):
            import os
            if 'LLM_API_KEY' in os.environ:
                del os.environ['LLM_API_KEY']

            result = await checker.check_health()

            assert result.status == HealthStatus.UNHEALTHY
            assert "not configured" in result.details.lower()

    @pytest.mark.asyncio
    async def test_check_health_success(self):
        """Test successful health check."""
        checker = LLMHealthChecker()

        # Mock environment
        with patch.dict('os.environ', {
            'LLM_API_KEY': 'test-key',
            'LLM_MODEL': 'test-model',
            'LLM_BASE_URL': 'http://test.com',
        }):
            # Mock LLM
            mock_response = Mock()
            mock_response.content = "OK"

            mock_llm = AsyncMock()
            mock_llm.ainvoke.return_value = mock_response

            with patch('app.health.checkers.llm_health_checker.get_llm') as mock_get_llm:
                mock_get_llm.return_value = mock_llm

                result = await checker.check_health()

                assert result.status == HealthStatus.HEALTHY
                assert result.component_name == "llm"


class TestTemporalHealthChecker:
    """Test TemporalHealthChecker."""

    @pytest.mark.asyncio
    async def test_check_type(self):
        """Test checker type identifier."""
        checker = TemporalHealthChecker()
        assert checker.get_check_type() == "temporal"

    @pytest.mark.asyncio
    async def test_is_critical(self):
        """Test if checker is critical."""
        checker = TemporalHealthChecker()
        assert checker.is_critical() is False  # Temporal is not critical

    @pytest.mark.asyncio
    async def test_check_health_success(self):
        """Test successful health check."""
        checker = TemporalHealthChecker()

        # Mock Temporal client
        mock_client = Mock()
        mock_client.service_name = "test-cluster"

        with patch('app.health.checkers.temporal_health_checker.get_temporal_client') as mock_get_client:
            mock_get_client.return_value = mock_client

            result = await checker.check_health()

            assert result.status == HealthStatus.HEALTHY
            assert result.component_name == "temporal"

    @pytest.mark.asyncio
    async def test_check_health_failure(self):
        """Test health check with Temporal failure."""
        checker = TemporalHealthChecker()

        with patch('app.health.checkers.temporal_health_checker.get_temporal_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")

            result = await checker.check_health()

            assert result.status == HealthStatus.UNHEALTHY
            assert "failed" in result.details.lower()


class TestFileSystemHealthChecker:
    """Test FileSystemHealthChecker."""

    @pytest.mark.asyncio
    async def test_check_type(self):
        """Test checker type identifier."""
        checker = FileSystemHealthChecker()
        assert checker.get_check_type() == "filesystem"

    @pytest.mark.asyncio
    async def test_is_critical(self):
        """Test if checker is critical."""
        checker = FileSystemHealthChecker()
        assert checker.is_critical() is True  # File system is critical

    @pytest.mark.asyncio
    async def test_check_health_success(self):
        """Test successful health check."""
        checker = FileSystemHealthChecker()

        # Mock os.statvfs and os.makedirs
        with patch('os.statvfs') as mock_statvfs:
            mock_stat = Mock()
            mock_stat.f_blocks = 1000000
            mock_stat.f_frsize = 4096
            mock_stat.f_bavail = 800000
            mock_statvfs.return_value = mock_stat

            with patch('os.makedirs'):
                with patch('builtins.open', create=False):
                    with patch('os.remove'):
                        result = await checker.check_health()

                        assert result.status == HealthStatus.HEALTHY
                        assert result.component_name == "filesystem"

    @pytest.mark.asyncio
    async def test_check_health_disk_full(self):
        """Test health check with full disk."""
        checker = FileSystemHealthChecker()

        with patch('os.statvfs') as mock_statvfs:
            # Simulate 99% disk usage
            mock_stat = Mock()
            mock_stat.f_blocks = 1000000
            mock_stat.f_frsize = 4096
            mock_stat.f_bavail = 10000  # Only 1% free
            mock_statvfs.return_value = mock_stat

            with patch('os.makedirs'):
                with patch('builtins.open', create=False):
                    with patch('os.remove'):
                        result = await checker.check_health()

                        assert result.status == HealthStatus.UNHEALTHY
                        assert "critically full" in result.details.lower()
