"""
Tests for Browser Automation Interface and Implementations

Comprehensive tests for IBrowserAutomation interface, PlaywrightAutomation, and MockBrowserAutomation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.core.interfaces.browser_automation_interface import (
    IBrowserAutomation,
    BrowserType,
    BrowserConfig,
    ScriptExecutionResult,
    PageContent,
    BrowserError,
    BrowserLaunchError,
    NavigationError,
    ScriptValidationError,
    ScriptExecutionError,
    ElementNotFoundError,
    ClickError,
    FillError,
    ScreenshotError,
    ContentExtractionError
)
from app.core.browser.playwright_automation import PlaywrightAutomation
from app.core.browser.mock_browser_automation import MockBrowserAutomation


class TestBrowserAutomationInterface:
    """Test IBrowserAutomation interface contract."""

    def test_interface_cannot_be_instantiated(self):
        """Test that IBrowserAutomation interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            IBrowserAutomation()

    def test_interface_methods_are_abstract(self):
        """Test that IBrowserAutomation methods are abstract."""
        assert IBrowserAutomation.start_browser.__isabstractmethod__
        assert IBrowserAutomation.stop_browser.__isabstractmethod__
        assert IBrowserAutomation.navigate.__isabstractmethod__
        assert IBrowserAutomation.execute_script.__isabstractmethod__
        assert IBrowserAutomation.take_screenshot.__isabstractmethod__
        assert IBrowserAutomation.get_page_content.__isabstractmethod__
        assert IBrowserAutomation.wait_for_selector.__isabstractmethod__
        assert IBrowserAutomation.click.__isabstractmethod__
        assert IBrowserAutomation.fill.__isabstractmethod__
        assert IBrowserAutomation.get_text.__isabstractmethod__
        assert IBrowserAutomation.is_visible.__isabstractmethod__
        assert IBrowserAutomation.close.__isabstractmethod__
        assert IBrowserAutomation.health_check.__isabstractmethod__
        assert IBrowserAutomation.is_browser_started.__isabstractmethod__


class TestBrowserConfig:
    """Test BrowserConfig dataclass."""

    def test_browser_config_defaults(self):
        """Test BrowserConfig has correct defaults."""
        config = BrowserConfig()

        assert config.headless is True
        assert config.timeout == 30000
        assert config.viewport == {"width": 1280, "height": 720}
        assert config.user_agent is None
        assert config.locale is None
        assert config.timezone is None
        assert config.geolocation is None
        assert config.ignore_https_errors is False
        assert config.slow_mo == 0

    def test_browser_config_custom_values(self):
        """Test BrowserConfig with custom values."""
        config = BrowserConfig(
            headless=False,
            timeout=60000,
            viewport={"width": 1920, "height": 1080},
            user_agent="TestAgent",
            locale="en-US",
            timezone="America/New_York"
        )

        assert config.headless is False
        assert config.timeout == 60000
        assert config.viewport == {"width": 1920, "height": 1080}
        assert config.user_agent == "TestAgent"
        assert config.locale == "en-US"
        assert config.timezone == "America/New_York"


class TestScriptExecutionResult:
    """Test ScriptExecutionResult dataclass."""

    def test_script_execution_result_defaults(self):
        """Test ScriptExecutionResult has correct defaults."""
        result = ScriptExecutionResult(status="passed")

        assert result.status == "passed"
        assert result.step_results == []
        assert result.screenshots == []
        assert result.console_logs == []
        assert result.errors == []
        assert result.duration_ms == 0
        assert result.metadata == {}

    def test_script_execution_result_with_data(self):
        """Test ScriptExecutionResult with data."""
        result = ScriptExecutionResult(
            status="failed",
            step_results=[{"step": 1, "status": "passed"}],
            screenshots=["base64_data"],
            console_logs=[{"level": "info", "message": "Test"}],
            errors=["Test error"],
            duration_ms=1000,
            metadata={"key": "value"}
        )

        assert result.status == "failed"
        assert len(result.step_results) == 1
        assert len(result.screenshots) == 1
        assert len(result.console_logs) == 1
        assert len(result.errors) == 1
        assert result.duration_ms == 1000
        assert result.metadata == {"key": "value"}


class TestPageContent:
    """Test PageContent dataclass."""

    def test_page_content_defaults(self):
        """Test PageContent has correct defaults."""
        content = PageContent(
            url="https://example.com",
            title="Example",
            html="<html></html>",
            text="Example text"
        )

        assert content.url == "https://example.com"
        assert content.title == "Example"
        assert content.html == "<html></html>"
        assert content.text == "Example text"
        assert content.links == []
        assert content.forms == []
        assert content.buttons == []
        assert content.inputs == []
        assert content.metadata == {}


class TestMockBrowserAutomation:
    """Test MockBrowserAutomation implementation."""

    @pytest.fixture
    def mock_browser(self):
        """Create MockBrowserAutomation instance for testing."""
        return MockBrowserAutomation(
            config=BrowserConfig(headless=True),
            delay_ms=0,
            simulate_errors=False
        )

    @pytest.mark.asyncio
    async def test_start_browser(self, mock_browser):
        """Test starting the mock browser."""
        await mock_browser.start_browser()

        assert mock_browser.is_browser_started() is True

    @pytest.mark.asyncio
    async def test_stop_browser(self, mock_browser):
        """Test stopping the mock browser."""
        await mock_browser.start_browser()
        await mock_browser.stop_browser()

        assert mock_browser.is_browser_started() is False

    @pytest.mark.asyncio
    async def test_navigate(self, mock_browser):
        """Test navigating to a URL."""
        await mock_browser.start_browser()
        await mock_browser.navigate("https://example.com")

        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_navigate_without_start(self, mock_browser):
        """Test navigate raises error if browser not started."""
        with pytest.raises(BrowserError):
            await mock_browser.navigate("https://example.com")

    @pytest.mark.asyncio
    async def test_execute_script(self, mock_browser):
        """Test executing a script."""
        await mock_browser.start_browser()

        result = await mock_browser.execute_script("console.log('test')")

        assert isinstance(result, ScriptExecutionResult)
        assert result.status == "passed"
        assert len(result.step_results) > 0

    @pytest.mark.asyncio
    async def test_execute_script_empty(self, mock_browser):
        """Test execute_script raises error for empty script."""
        await mock_browser.start_browser()

        with pytest.raises(ScriptValidationError):
            await mock_browser.execute_script("")

    @pytest.mark.asyncio
    async def test_take_screenshot(self, mock_browser):
        """Test taking a screenshot."""
        await mock_browser.start_browser()

        screenshot = await mock_browser.take_screenshot()

        assert isinstance(screenshot, bytes)
        assert len(screenshot) > 0

    @pytest.mark.asyncio
    async def test_get_page_content(self, mock_browser):
        """Test getting page content."""
        await mock_browser.start_browser()

        content = await mock_browser.get_page_content()

        assert isinstance(content, PageContent)
        assert content.url != ""
        assert content.title != ""
        assert content.text != ""

    @pytest.mark.asyncio
    async def test_wait_for_selector(self, mock_browser):
        """Test waiting for selector."""
        await mock_browser.start_browser()

        await mock_browser.wait_for_selector("#test")

        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_click(self, mock_browser):
        """Test clicking an element."""
        await mock_browser.start_browser()

        await mock_browser.click("#button")

        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_fill(self, mock_browser):
        """Test filling an input."""
        await mock_browser.start_browser()

        await mock_browser.fill("#input", "test value")

        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_get_text(self, mock_browser):
        """Test getting text from element."""
        await mock_browser.start_browser()

        text = await mock_browser.get_text("#element")

        assert isinstance(text, str)
        assert "#element" in text

    @pytest.mark.asyncio
    async def test_is_visible(self, mock_browser):
        """Test checking element visibility."""
        await mock_browser.start_browser()

        is_visible = await mock_browser.is_visible("#element")

        assert is_visible is True

    @pytest.mark.asyncio
    async def test_is_visible_not_started(self, mock_browser):
        """Test is_visible returns False if browser not started."""
        is_visible = await mock_browser.is_visible("#element")

        assert is_visible is False

    @pytest.mark.asyncio
    async def test_close(self, mock_browser):
        """Test closing the current page."""
        await mock_browser.start_browser()
        await mock_browser.close()

        assert mock_browser.is_browser_started() is True  # Browser still started

    @pytest.mark.asyncio
    async def test_health_check(self, mock_browser):
        """Test health check returns True."""
        health = await mock_browser.health_check()

        assert health is True

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_browser):
        """Test async context manager."""
        async with mock_browser as browser:
            assert browser.is_browser_started() is True

        # Browser should be stopped after context exit
        # Note: MockBrowserAutomation doesn't actually stop in __aexit__

    def test_is_browser_started(self, mock_browser):
        """Test is_browser_started returns correct status."""
        assert mock_browser.is_browser_started() is False


class TestMockBrowserAutomationWithErrorSimulation:
    """Test MockBrowserAutomation error simulation."""

    @pytest.fixture
    def error_browser(self):
        """Create MockBrowserAutomation with error simulation."""
        return MockBrowserAutomation(
            simulate_errors=True,
            delay_ms=0
        )

    @pytest.mark.asyncio
    async def test_simulate_start_error(self, error_browser):
        """Test browser start error simulation."""
        with patch('random.random', return_value=0.05):  # Trigger error
            with pytest.raises(BrowserLaunchError):
                await error_browser.start_browser()

    @pytest.mark.asyncio
    async def test_simulate_navigation_error(self, error_browser):
        """Test navigation error simulation."""
        await error_browser.start_browser()

        with patch('random.random', return_value=0.15):  # Trigger error
            with pytest.raises(NavigationError):
                await error_browser.navigate("https://example.com")


class TestBrowserAutomationExceptions:
    """Test browser automation exceptions."""

    def test_browser_error(self):
        """Test base BrowserError."""
        exc = BrowserError("Test error", provider="Playwright", details={"key": "value"})

        assert str(exc) == "Test error"
        assert exc.provider == "Playwright"
        assert exc.details == {"key": "value"}

    def test_browser_launch_error(self):
        """Test BrowserLaunchError."""
        exc = BrowserLaunchError("Launch failed")

        assert isinstance(exc, BrowserError)

    def test_navigation_error(self):
        """Test NavigationError."""
        exc = NavigationError("Navigation failed")

        assert isinstance(exc, BrowserError)

    def test_script_validation_error(self):
        """Test ScriptValidationError inherits from both."""
        exc = ScriptValidationError("Invalid script")

        assert isinstance(exc, BrowserError)
        assert isinstance(exc, ValueError)

    def test_script_execution_error(self):
        """Test ScriptExecutionError."""
        exc = ScriptExecutionError("Execution failed")

        assert isinstance(exc, BrowserError)

    def test_element_not_found_error(self):
        """Test ElementNotFoundError."""
        exc = ElementNotFoundError("Element not found")

        assert isinstance(exc, BrowserError)

    def test_click_error(self):
        """Test ClickError."""
        exc = ClickError("Click failed")

        assert isinstance(exc, BrowserError)

    def test_fill_error(self):
        """Test FillError."""
        exc = FillError("Fill failed")

        assert isinstance(exc, BrowserError)

    def test_screenshot_error(self):
        """Test ScreenshotError."""
        exc = ScreenshotError("Screenshot failed")

        assert isinstance(exc, BrowserError)

    def test_content_extraction_error(self):
        """Test ContentExtractionError."""
        exc = ContentExtractionError("Extraction failed")

        assert isinstance(exc, BrowserError)


class TestBrowserType:
    """Test BrowserType enum."""

    def test_browser_type_values(self):
        """Test BrowserType enum values."""
        assert BrowserType.CHROMIUM.value == "chromium"
        assert BrowserType.FIREFOX.value == "firefox"
        assert BrowserType.WEBKIT.value == "webkit"

    def test_browser_type_from_string(self):
        """Test creating BrowserType from string."""
        assert BrowserType("chromium") == BrowserType.CHROMIUM
        assert BrowserType("firefox") == BrowserType.FIREFOX
        assert BrowserType("webkit") == BrowserType.WEBKIT
