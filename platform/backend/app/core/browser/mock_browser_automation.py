"""
Mock Browser Automation Implementation

Provides a mock implementation of IBrowserAutomation for testing purposes.
Supports deterministic behavior and configurable responses.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

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


logger = logging.getLogger(__name__)


class MockBrowserAutomation(IBrowserAutomation):
    """
    Mock browser automation for testing.

    Provides deterministic browser behavior without actual browser.
    Useful for unit tests and integration tests.
    """

    def __init__(
        self,
        config: Optional[BrowserConfig] = None,
        delay_ms: int = 100,
        simulate_errors: bool = False
    ):
        """
        Initialize mock browser automation.

        Args:
            config: Browser configuration options
            delay_ms: Artificial delay for operations in milliseconds
            simulate_errors: Whether to simulate errors randomly
        """
        self.config = config or BrowserConfig()
        self.delay_ms = delay_ms
        self.simulate_errors = simulate_errors

        # Mock state
        self._browser_started = False
        self._current_url = "about:blank"
        self._page_content = self._create_default_page_content()

    def _create_default_page_content(self) -> Dict[str, Any]:
        """Create default mock page content."""
        return {
            "url": "https://example.com",
            "title": "Example Page",
            "html": "<html><body><h1>Mock Page</h1></body></html>",
            "text": "Mock Page Content",
            "links": [
                {"text": "Home", "href": "/"},
                {"text": "About", "href": "/about"},
            ],
            "forms": [
                {
                    "action": "/submit",
                    "method": "POST",
                    "inputs": [
                        {"name": "username", "type": "text", "id": "username"},
                        {"name": "password", "type": "password", "id": "password"},
                    ]
                }
            ],
            "buttons": [
                {"text": "Submit", "type": "submit", "id": "submit-btn"},
            ],
            "inputs": [
                {"name": "username", "type": "text", "id": "username", "value": ""},
                {"name": "password", "type": "password", "id": "password", "value": ""},
            ],
        }

    async def _simulate_delay(self):
        """Simulate operation delay."""
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000.0)

    def _maybe_simulate_error(self, error_class=BrowserError):
        """Simulate random errors if enabled."""
        if not self.simulate_errors:
            return

        import random
        if random.random() < 0.1:  # 10% chance of error
            raise error_class("Mock browser error", provider="Mock")

    async def start_browser(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        config: Optional[BrowserConfig] = None
    ) -> None:
        """
        Start the mock browser.

        Args:
            browser_type: Type of browser (ignored in mock)
            config: Browser configuration options

        Raises:
            BrowserLaunchError: If launch fails (simulated)
        """
        await self._simulate_delay()
        self._maybe_simulate_error(BrowserLaunchError)

        if self._browser_started:
            logger.warning("Mock browser already started")
            return

        self._browser_started = True
        self._current_url = "about:blank"
        logger.info(f"Mock browser started: {browser_type.value}")

    async def stop_browser(self) -> None:
        """
        Stop the mock browser.

        Raises:
            BrowserError: If stop fails (simulated)
        """
        await self._simulate_delay()
        self._maybe_simulate_error(BrowserError)

        if not self._browser_started:
            logger.warning("Mock browser not started")
            return

        self._browser_started = False
        logger.info("Mock browser stopped")

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """
        Navigate to a URL (mock).

        Args:
            url: URL to navigate to
            wait_until: Wait condition (ignored in mock)

        Raises:
            NavigationError: If navigation fails (simulated)
        """
        if not self._browser_started:
            raise BrowserError("Mock browser not started", provider="Mock")

        await self._simulate_delay()
        self._maybe_simulate_error(NavigationError)

        self._current_url = url
        logger.info(f"Mock navigation to: {url}")

    async def execute_script(
        self,
        script: str,
        page_context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> ScriptExecutionResult:
        """
        Execute a mock script.

        Args:
            script: Script source code (not actually executed)
            page_context: Optional context variables
            timeout: Execution timeout (ignored in mock)

        Returns:
            ScriptExecutionResult: Mock execution result

        Raises:
            ScriptValidationError: If script is empty
            ScriptExecutionError: If execution fails (simulated)
        """
        if not self._browser_started:
            raise BrowserError("Mock browser not started", provider="Mock")

        if not script or not script.strip():
            raise ScriptValidationError("Script cannot be empty", provider="Mock")

        await self._simulate_delay()
        self._maybe_simulate_error(ScriptExecutionError)

        # Return successful mock result
        logger.info(f"Mock script execution: {len(script)} chars")

        return ScriptExecutionResult(
            status="passed",
            step_results=[
                {"step": 1, "action": "navigate", "status": "passed"},
                {"step": 2, "action": "click", "status": "passed"},
                {"step": 3, "action": "verify", "status": "passed"},
            ],
            screenshots=["base64_mock_screenshot_1"],
            console_logs=[
                {"level": "info", "message": "Mock console log"},
            ],
            errors=[],
            duration_ms=self.delay_ms,
            metadata={"mock": True, "script_length": len(script)}
        )

    async def take_screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False
    ) -> bytes:
        """
        Take a mock screenshot.

        Args:
            path: Optional path to save screenshot (ignored in mock)
            full_page: Whether to capture full page (ignored in mock)

        Returns:
            bytes: Mock screenshot data

        Raises:
            ScreenshotError: If screenshot fails (simulated)
        """
        if not self._browser_started:
            raise BrowserError("Mock browser not started", provider="Mock")

        await self._simulate_delay()
        self._maybe_simulate_error(ScreenshotError)

        # Return mock screenshot data
        mock_screenshot = b"MOCK_SCREENSHOT_DATA"
        logger.info(f"Mock screenshot taken: {len(mock_screenshot)} bytes")

        return mock_screenshot

    async def get_page_content(self, include_html: bool = True) -> PageContent:
        """
        Extract mock page content.

        Args:
            include_html: Whether to include HTML content

        Returns:
            PageContent: Mock page content

        Raises:
            ContentExtractionError: If extraction fails (simulated)
        """
        if not self._browser_started:
            raise BrowserError("Mock browser not started", provider="Mock")

        await self._simulate_delay()
        self._maybe_simulate_error(ContentExtractionError)

        # Return mock page content
        logger.info("Mock page content extracted")

        return PageContent(
            url=self._page_content["url"],
            title=self._page_content["title"],
            html=self._page_content["html"] if include_html else "",
            text=self._page_content["text"],
            links=self._page_content["links"],
            forms=self._page_content["forms"],
            buttons=self._page_content["buttons"],
            inputs=self._page_content["inputs"],
            metadata={"mock": True}
        )

    async def wait_for_selector(
        self,
        selector: str,
        timeout: Optional[int] = None
    ) -> None:
        """
        Mock wait for selector.

        Args:
            selector: CSS selector (ignored in mock)
            timeout: Maximum wait time (uses delay_ms in mock)

        Raises:
            TimeoutError: If timeout occurs (simulated)
        """
        if not self._browser_started:
            raise BrowserError("Mock browser not started", provider="Mock")

        await self._simulate_delay()
        self._maybe_simulate_error()

        logger.info(f"Mock wait for selector: {selector}")

    async def click(self, selector: str) -> None:
        """
        Mock click an element.

        Args:
            selector: CSS selector of element

        Raises:
            ElementNotFoundError: If element not found (simulated)
            ClickError: If click fails (simulated)
        """
        if not self._browser_started:
            raise BrowserError("Mock browser not started", provider="Mock")

        await self._simulate_delay()
        self._maybe_simulate_error(ClickError)

        logger.info(f"Mock click: {selector}")

    async def fill(self, selector: str, value: str) -> None:
        """
        Mock fill an input.

        Args:
            selector: CSS selector of input
            value: Text to fill

        Raises:
            ElementNotFoundError: If element not found (simulated)
            FillError: If fill fails (simulated)
        """
        if not self._browser_started:
            raise BrowserError("Mock browser not started", provider="Mock")

        await self._simulate_delay()
        self._maybe_simulate_error(FillError)

        logger.info(f"Mock fill: {selector} = {value}")

    async def get_text(self, selector: str) -> str:
        """
        Mock get text content.

        Args:
            selector: CSS selector of element

        Returns:
            str: Mock text content

        Raises:
            ElementNotFoundError: If element not found (simulated)
        """
        if not self._browser_started:
            raise BrowserError("Mock browser not started", provider="Mock")

        await self._simulate_delay()
        self._maybe_simulate_error(ElementNotFoundError)

        mock_text = f"Mock text for {selector}"
        logger.info(f"Mock get text: {selector}")
        return mock_text

    async def is_visible(self, selector: str) -> bool:
        """
        Mock check element visibility.

        Args:
            selector: CSS selector of element

        Returns:
            bool: Mock visibility (always True in mock)
        """
        if not self._browser_started:
            return False

        await self._simulate_delay()
        return True

    async def close(self) -> None:
        """
        Mock close current page.

        Raises:
            BrowserError: If close fails (simulated)
        """
        if not self._browser_started:
            logger.warning("Mock browser not started")
            return

        await self._simulate_delay()
        self._maybe_simulate_error(BrowserError)

        logger.info("Mock page closed")

    async def health_check(self) -> bool:
        """
        Mock health check - always returns True.

        Returns:
            bool: True if mock browser is healthy
        """
        await self._simulate_delay()
        logger.debug("Mock browser health check: HEALTHY")
        return True

    def is_browser_started(self) -> bool:
        """
        Check if mock browser is started.

        Returns:
            bool: True if mock browser is started
        """
        return self._browser_started

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_browser()
