"""
Tests for LLM Client Interface and Implementations

Comprehensive tests for ILLMClient interface, GLMClient, and MockLLMClient.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.core.interfaces.llm_client_interface import (
    ILLMClient,
    LLMResponse,
    LLMMessage,
    LLMStreamChunk,
    LLMClientException,
    LLMConnectionError,
    LLMTimeoutError,
    LLMValidationError,
    LLMRateLimitError,
    LLMTokenLimitError
)
from app.core.llm.glm_client import GLMClient
from app.core.llm.mock_llm_client import MockLLMClient


class TestLLMClientInterface:
    """Test ILLMClient interface contract."""

    def test_interface_cannot_be_instantiated(self):
        """Test that ILLMClient interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ILLMClient()

    def test_interface_methods_are_abstract(self):
        """Test that ILLMClient methods are abstract."""
        # Check that abstract methods raise NotImplementedError
        assert ILLMClient.generate_response.__isabstractmethod__
        assert ILLMClient.generate_chat_response.__isabstractmethod__
        assert ILLMClient.generate_structured_response.__isabstractmethod__
        assert ILLMClient.stream_response.__isabstractmethod__
        assert ILLMClient.stream_chat_response.__isabstractmethod__
        assert ILLMClient.get_model_info.__isabstractmethod__
        assert ILLMClient.estimate_tokens.__isabstractmethod__
        assert ILLMClient.health_check.__isabstractmethod__
        assert ILLMClient.get_default_model.__isabstractmethod__
        assert ILLMClient.list_available_models.__isabstractmethod__


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_llm_response_creation(self):
        """Test LLMResponse can be created with all fields."""
        response = LLMResponse(
            content="Test response",
            model="test-model",
            tokens_used=100,
            duration_ms=1000,
            finish_reason="stop",
            metadata={"key": "value"}
        )

        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.tokens_used == 100
        assert response.duration_ms == 1000
        assert response.finish_reason == "stop"
        assert response.metadata == {"key": "value"}

    def test_llm_response_default_metadata(self):
        """Test LLMResponse creates empty metadata dict by default."""
        response = LLMResponse(
            content="Test",
            model="test",
            tokens_used=50,
            duration_ms=500,
            finish_reason="stop"
        )

        assert response.metadata == {}


class TestLLMMessage:
    """Test LLMMessage dataclass."""

    def test_llm_message_creation(self):
        """Test LLMMessage can be created with all fields."""
        message = LLMMessage(
            role="user",
            content="Hello",
            name="test_user",
            tool_calls=None,
            tool_id=None
        )

        assert message.role == "user"
        assert message.content == "Hello"
        assert message.name == "test_user"


class TestGLMClient:
    """Test GLMClient implementation."""

    @pytest.fixture
    def glm_client(self):
        """Create GLMClient instance for testing."""
        return GLMClient(
            api_key="test-api-key",
            base_url="https://test.api.com",
            model="glm-4-plus",
            timeout=10.0
        )

    def test_glm_client_initialization(self, glm_client):
        """Test GLMClient initializes correctly."""
        assert glm_client.api_key == "test-api-key"
        assert glm_client.base_url == "https://test.api.com"
        assert glm_client.model == "glm-4-plus"
        assert glm_client.timeout == 10.0

    def test_glm_client_requires_api_key(self):
        """Test GLMClient raises error without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(LLMValidationError):
                GLMClient(api_key=None)

    def test_estimate_tokens(self, glm_client):
        """Test token estimation."""
        text = "This is a test message with some words"
        tokens = glm_client.estimate_tokens(text)

        # Should be approximately 0.3 * len(text)
        expected = int(len(text) * 0.3)
        assert tokens == expected

    def test_estimate_empty_text(self, glm_client):
        """Test token estimation for empty text."""
        assert glm_client.estimate_tokens("") == 0
        assert glm_client.estimate_tokens(None) == 0

    def test_get_model_info(self, glm_client):
        """Test getting model information."""
        info = glm_client.get_model_info("glm-4-plus")

        assert info["name"] == "glm-4-plus"
        assert info["provider"] == "GLM"
        assert info["max_tokens"] == 128000
        assert info["supports_streaming"] is True
        assert info["supports_structured"] is True

    def test_get_model_info_unknown_model(self, glm_client):
        """Test getting info for unknown model returns generic info."""
        info = glm_client.get_model_info("unknown-model")

        assert info["name"] == "unknown-model"
        assert info["provider"] == "GLM"
        assert info["max_tokens"] == 128000

    def test_get_default_model(self, glm_client):
        """Test getting default model name."""
        assert glm_client.get_default_model() == "glm-4-plus"

    def test_list_available_models(self, glm_client):
        """Test listing available models."""
        models = glm_client.list_available_models()

        assert "glm-4-plus" in models
        assert "glm-4" in models
        assert "glm-4-flash" in models

    @pytest.mark.asyncio
    async def test_generate_response_empty_prompt(self, glm_client):
        """Test generate_response raises error for empty prompt."""
        with pytest.raises(LLMValidationError):
            await glm_client.generate_response("")

    @pytest.mark.asyncio
    async def test_generate_chat_response_empty_messages(self, glm_client):
        """Test generate_chat_response raises error for empty messages."""
        with pytest.raises(LLMValidationError):
            await glm_client.generate_chat_response([])

    @pytest.mark.asyncio
    async def test_health_check(self, glm_client):
        """Test health check with mocked response."""
        with patch.object(glm_client, 'generate_response', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = LLMResponse(
                content="OK",
                model="test",
                tokens_used=10,
                duration_ms=100,
                finish_reason="stop"
            )

            result = await glm_client.health_check()
            assert result is True


class TestMockLLMClient:
    """Test MockLLMClient implementation."""

    @pytest.fixture
    def mock_client(self):
        """Create MockLLMClient instance for testing."""
        return MockLLMClient(
            model="mock-model",
            delay_ms=0,  # No delay for tests
            simulate_errors=False
        )

    def test_mock_client_initialization(self, mock_client):
        """Test MockLLMClient initializes correctly."""
        assert mock_client.model == "mock-model"
        assert mock_client.delay_ms == 0
        assert mock_client.simulate_errors is False

    @pytest.mark.asyncio
    async def test_generate_response(self, mock_client):
        """Test generate_response returns mock response."""
        response = await mock_client.generate_response("Test prompt")

        assert isinstance(response, LLMResponse)
        assert response.content != ""
        assert response.model == "mock-model"
        assert response.tokens_used > 0
        assert response.duration_ms >= 0
        assert response.finish_reason == "stop"
        assert response.metadata["mock"] is True

    @pytest.mark.asyncio
    async def test_generate_response_empty_prompt(self, mock_client):
        """Test generate_response raises error for empty prompt."""
        with pytest.raises(LLMValidationError):
            await mock_client.generate_response("")

    @pytest.mark.asyncio
    async def test_generate_chat_response(self, mock_client):
        """Test generate_chat_response returns mock response."""
        messages = [
            LLMMessage(role="user", content="Hello"),
            LLMMessage(role="assistant", content="Hi there!")
        ]

        response = await mock_client.generate_chat_response(messages)

        assert isinstance(response, LLMResponse)
        assert response.content != ""
        assert response.metadata["conversation_length"] == 2

    @pytest.mark.asyncio
    async def test_generate_structured_response(self, mock_client):
        """Test generate_structured_response returns mock data."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "active": {"type": "boolean"}
            }
        }

        response = await mock_client.generate_structured_response(
            "Generate user data",
            schema
        )

        assert isinstance(response, dict)
        assert "name" in response
        assert "age" in response
        assert "active" in response

    @pytest.mark.asyncio
    async def test_stream_response(self, mock_client):
        """Test stream_response yields chunks."""
        chunks = []
        async for chunk in mock_client.stream_response("Test prompt"):
            chunks.append(chunk)

        assert len(chunks) > 1
        assert any(chunk.is_complete for chunk in chunks)
        assert all(isinstance(chunk.content, str) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_stream_chat_response(self, mock_client):
        """Test stream_chat_response yields chunks."""
        messages = [LLMMessage(role="user", content="Hello")]

        chunks = []
        async for chunk in mock_client.stream_chat_response(messages):
            chunks.append(chunk)

        assert len(chunks) > 1
        assert any(chunk.is_complete for chunk in chunks)

    def test_estimate_tokens(self, mock_client):
        """Test token estimation."""
        text = "Test message"
        tokens = mock_client.estimate_tokens(text)

        expected = int(len(text) * 0.3)
        assert tokens == expected

    def test_get_model_info(self, mock_client):
        """Test getting model information."""
        info = mock_client.get_model_info("any-model")

        assert info["name"] == "any-model"
        assert info["provider"] == "Mock"
        assert info["mock"] is True

    @pytest.mark.asyncio
    async def test_health_check(self, mock_client):
        """Test health check always returns True."""
        assert await mock_client.health_check() is True

    def test_get_default_model(self, mock_client):
        """Test getting default model name."""
        assert mock_client.get_default_model() == "mock-model"

    def test_list_available_models(self, mock_client):
        """Test listing available models."""
        models = mock_client.list_available_models()

        assert "mock-model" in models
        assert isinstance(models, list)


class TestMockLLMClientWithErrorSimulation:
    """Test MockLLMClient error simulation."""

    @pytest.fixture
    def error_client(self):
        """Create MockLLMClient with error simulation."""
        return MockLLMClient(
            simulate_errors=True,
            delay_ms=0
        )

    @pytest.mark.asyncio
    async def test_simulate_timeout_error(self, error_client):
        """Test timeout error simulation."""
        with patch('random.random', return_value=0.05):  # Trigger timeout
            with pytest.raises(LLMTimeoutError):
                await error_client.generate_response("Test")

    @pytest.mark.asyncio
    async def test_simulate_validation_error(self, error_client):
        """Test validation error simulation."""
        with patch('random.random', return_value=0.15):  # Trigger validation error
            with pytest.raises(LLMValidationError):
                await error_client.generate_response("Test")

    @pytest.mark.asyncio
    async def test_simulate_rate_limit_error(self, error_client):
        """Test rate limit error simulation."""
        with patch('random.random', return_value=0.12):  # Trigger rate limit
            with pytest.raises(LLMRateLimitError):
                await error_client.generate_response("Test")

    @pytest.mark.asyncio
    async def test_successful_call_without_error(self, error_client):
        """Test successful call when error not triggered."""
        with patch('random.random', return_value=0.5):  # No error
            response = await error_client.generate_response("Test")
            assert isinstance(response, LLMResponse)


class TestLLMClientExceptions:
    """Test LLM client exceptions."""

    def test_llm_client_exception(self):
        """Test base LLMClientException."""
        exc = LLMClientException("Test error", provider="GLM", details={"key": "value"})

        assert str(exc) == "Test error"
        assert exc.provider == "GLM"
        assert exc.details == {"key": "value"}

    def test_llm_connection_error_inherits(self):
        """Test LLMConnectionError inherits from both."""
        exc = LLMConnectionError("Connection failed")

        assert isinstance(exc, LLMClientException)
        assert isinstance(exc, ConnectionError)

    def test_llm_timeout_error_inherits(self):
        """Test LLMTimeoutError inherits from both."""
        exc = LLMTimeoutError("Timeout")

        assert isinstance(exc, LLMClientException)
        assert isinstance(exc, TimeoutError)

    def test_llm_validation_error_inherits(self):
        """Test LLMValidationError inherits from both."""
        exc = LLMValidationError("Invalid input")

        assert isinstance(exc, LLMClientException)
        assert isinstance(exc, ValueError)

    def test_llm_rate_limit_error(self):
        """Test LLMRateLimitError has retry_after."""
        exc = LLMRateLimitError("Rate limited", retry_after=60)

        assert exc.retry_after == 60

    def test_llm_token_limit_error(self):
        """Test LLMTokenLimitError has token_limit."""
        exc = LLMTokenLimitError("Token limit exceeded", token_limit=128000)

        assert exc.token_limit == 128000
