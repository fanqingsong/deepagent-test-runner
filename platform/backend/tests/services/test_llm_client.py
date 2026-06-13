"""
Unit tests for LLMClient
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_client import LLMClient


class TestLLMClient:
    """Test suite for LLMClient component."""

    @pytest.fixture
    def llm_client(self):
        """Create LLMClient instance for testing."""
        return LLMClient(
            api_key="test_key",
            base_url="https://test.api.com",
            model="test-model",
            timeout=60.0,
            max_retries=2
        )

    def test_init_with_parameters(self, llm_client):
        """Test initialization with custom parameters."""
        assert llm_client.api_key == "test_key"
        assert llm_client.base_url == "https://test.api.com"
        assert llm_client.model == "test-model"
        assert llm_client.timeout == 60.0
        assert llm_client.max_retries == 2

    def test_init_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="LLM_API_KEY is required"):
                LLMClient(api_key=None)

    @pytest.mark.asyncio
    async def test_generate_test_case_success(self, llm_client):
        """Test successful test case generation."""
        # Mock LangChain LLM
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.generations[0][0].text = '{"name": "Test", "steps": []}'
        mock_llm.agenerate.return_value = mock_response

        with patch('app.services.llm_client.get_llm', return_value=mock_llm):
            result = await llm_client.generate_test_case("test prompt")

            assert result == '{"name": "Test", "steps": []}'
            mock_llm.agenerate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_test_case_with_custom_model(self, llm_client):
        """Test generation with custom model override."""
        mock_llm = AsyncMock()
        mock_response = MagicMock()
        mock_response.generations[0][0].text = "test response"
        mock_llm.agenerate.return_value = mock_response

        with patch('app.services.llm_client.get_llm', return_value=mock_llm) as mock_get_llm:
            await llm_client.generate_test_case("prompt", model="custom-model")

            # Verify get_llm was called with custom model
            mock_get_llm.assert_called_once()
            call_kwargs = mock_get_llm.call_args[1]
            assert call_kwargs['model_name'] == "custom-model"

    @pytest.mark.asyncio
    async def test_generate_test_case_fallback_to_direct_call(self, llm_client):
        """Test fallback to direct HTTP call when LangChain fails."""
        # Mock LangChain to fail
        mock_llm = AsyncMock()
        mock_llm.agenerate.side_effect = Exception("LangChain failed")

        # Mock httpx for direct call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "direct response"}}]
        }

        with patch('app.services.llm_client.get_llm', return_value=mock_llm):
            with patch('httpx.AsyncClient') as mock_client:
                async_mock_client = AsyncMock()
                async_mock_client.post.return_value = mock_response
                async_mock_client.__aenter__.return_value = async_mock_client
                mock_client.return_value = async_mock_client

                result = await llm_client.generate_test_case("test prompt")

                assert result == "direct response"

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, llm_client):
        """Test retry mechanism on timeout."""
        from httpx import TimeoutException

        # Mock httpx to timeout twice then succeed
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "success"}}]
        }

        with patch('app.services.llm_client.get_llm') as mock_get_llm:
            # LangChain fails, triggering direct call
            mock_get_llm.side_effect = Exception("LangChain failed")

            with patch('httpx.AsyncClient') as mock_client:
                async_mock_client = AsyncMock()
                # First two calls timeout, third succeeds
                async_mock_client.post.side_effect = [
                    TimeoutException("Timeout"),
                    TimeoutException("Timeout"),
                    mock_response
                ]
                async_mock_client.__aenter__.return_value = async_mock_client
                mock_client.return_value = async_mock_client

                result = await llm_client.generate_test_case("test")

                assert result == "success"
                assert async_mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, llm_client):
        """Test that 4xx errors are not retried."""
        from httpx import HTTPStatusError

        mock_response = MagicMock()
        mock_response.status_code = 400
        error = HTTPStatusError(
            "Bad Request",
            request=MagicMock(),
            response=mock_response
        )

        with patch('app.services.llm_client.get_llm') as mock_get_llm:
            mock_get_llm.side_effect = Exception("LangChain failed")

            with patch('httpx.AsyncClient') as mock_client:
                async_mock_client = AsyncMock()
                async_mock_client.post.side_effect = error
                async_mock_client.__aenter__.return_value = async_mock_client
                mock_client.return_value = async_mock_client

                with pytest.raises(HTTPStatusError):
                    await llm_client.generate_test_case("test")

                # Should only be called once (no retries for 4xx)
                assert async_mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, llm_client):
        """Test that max retries limit is respected."""
        from httpx import TimeoutException

        with patch('app.services.llm_client.get_llm') as mock_get_llm:
            mock_get_llm.side_effect = Exception("LangChain failed")

            with patch('httpx.AsyncClient') as mock_client:
                async_mock_client = AsyncMock()
                async_mock_client.post.side_effect = TimeoutException("Timeout")
                async_mock_client.__aenter__.return_value = async_mock_client
                mock_client.return_value = async_mock_client

                with pytest.raises(Exception):
                    await llm_client.generate_test_case("test")

                # Should be called max_retries times
                assert async_mock_client.post.call_count == llm_client.max_retries

    @pytest.mark.asyncio
    async def test_health_check_success(self, llm_client):
        """Test health check returns True when API is healthy."""
        with patch.object(llm_client, 'generate_test_case', return_value="OK"):
            result = await llm_client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, llm_client):
        """Test health check returns False when API is unhealthy."""
        with patch.object(llm_client, 'generate_test_case', side_effect=Exception("API down")):
            result = await llm_client.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_with_ok_response(self, llm_client):
        """Test health check recognizes OK response."""
        with patch.object(llm_client, 'generate_test_case', return_value="OK, system operational"):
            result = await llm_client.health_check()
            assert result is True
