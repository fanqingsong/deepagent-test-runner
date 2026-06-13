"""
Playwright Browser Automation Implementation

Implements IBrowserAutomation interface using Playwright.
Wraps existing Playwright logic with enhanced error handling and timeout management.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error

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
from app.agents.test_composer.lib.script_executor import execute_script


logger = logging.getLogger(__name__)


class PlaywrightAutomation(IBrowserAutomation):
    """
    Playwright browser automation implementation.

    Provides browser automation using Playwright library.
    Supports Chromium, Firefox, and WebKit browsers.
    """

    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Initialize Playwright automation.

        Args:
            config: Browser configuration options
        """
        self.config = config or BrowserConfig()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def start_browser(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        config: Optional[BrowserConfig] = None
    ) -> None:
        """
        Start the browser instance.

        Args:
            browser_type: Type of browser to launch
            config: Browser configuration options

        Raises:
            BrowserLaunchError: If browser fails to start
        """
        if self.is_browser_started():
            logger.warning("Browser already started, skipping")
            return

        config = config or self.config

        logger.info(f"Starting {browser_type.value} browser (headless={config.headless})")

        try:
            self._playwright = await async_playwright().start()

            # Map browser type to Playwright launch method
            launch_methods = {
                BrowserType.CHROMIUM: self._playwright.chromium,
                BrowserType.FIREFOX: self._playwright.firefox,
                BrowserType.WEBKIT: self._playwright.webkit,
            }

            launch_method = launch_methods.get(browser_type, self._playwright.chromium)

            # Launch browser with configuration
            self._browser = await launch_method.launch(
                headless=config.headless,
                timeout=config.timeout,
                slow_mo=config.slow_mo
            )

            # Create context with configuration
            context_options = {
                "viewport": config.viewport,
                "locale": config.locale,
                "timezone_id": config.timezone,
                "ignore_https_errors": config.ignore_https_errors,
            }

            if config.user_agent:
                context_options["user_agent"] = config.user_agent

            if config.geolocation:
                context_options["geolocation"] = config.geolocation
                context_options["permissions"] = config.permissions or ["geolocation"]

            self._context = await self._browser.new_context(**context_options)

            # Create page
            self._page = await self._context.new_page()

            # Set default timeout
            self._page.set_default_timeout(config.timeout)

            logger.info(f"Browser started successfully: {browser_type.value}")

        except Error as e:
            logger.error(f"Failed to start browser: {str(e)}")
            raise BrowserLaunchError(f"Browser launch failed: {str(e)}", provider="Playwright")

        except Exception as e:
            logger.error(f"Unexpected error starting browser: {str(e)}")
            raise BrowserLaunchError(f"Unexpected error: {str(e)}", provider="Playwright")

    async def stop_browser(self) -> None:
        """
        Stop the browser instance and cleanup resources.

        Raises:
            BrowserError: If browser fails to stop properly
        """
        if not self.is_browser_started():
            logger.warning("Browser not started, nothing to stop")
            return

        logger.info("Stopping browser")

        try:
            # Close page
            if self._page:
                await self._page.close()
                self._page = None

            # Close context
            if self._context:
                await self._context.close()
                self._context = None

            # Close browser
            if self._browser:
                await self._browser.close()
                self._browser = None

            # Stop playwright
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            logger.info("Browser stopped successfully")

        except Error as e:
            logger.error(f"Error stopping browser: {str(e)}")
            raise BrowserError(f"Failed to stop browser: {str(e)}", provider="Playwright")

        except Exception as e:
            logger.error(f"Unexpected error stopping browser: {str(e)}")
            raise BrowserError(f"Unexpected error: {str(e)}", provider="Playwright")

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation succeeded

        Raises:
            NavigationError: If navigation fails
        """
        if not self.is_browser_started():
            raise BrowserError("Browser not started", provider="Playwright")

        logger.info(f"Navigating to: {url}")

        try:
            await self._page.goto(url, wait_until=wait_until)
            logger.info(f"Navigation successful: {url}")

        except Error as e:
            logger.error(f"Navigation failed: {str(e)}")
            raise NavigationError(f"Navigation to {url} failed: {str(e)}", provider="Playwright")

        except Exception as e:
            logger.error(f"Unexpected navigation error: {str(e)}")
            raise NavigationError(f"Unexpected error: {str(e)}", provider="Playwright")

    async def execute_script(
        self,
        script: str,
        page_context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> ScriptExecutionResult:
        """
        Execute a browser automation script in a sandboxed environment.

        Args:
            script: Script source code to execute
            page_context: Optional context variables for script execution
            timeout: Execution timeout in milliseconds

        Returns:
            ScriptExecutionResult: Execution result with status and metadata

        Raises:
            ScriptValidationError: If script validation fails
            ScriptExecutionError: If script execution fails
        """
        if not self.is_browser_started():
            raise BrowserError("Browser not started", provider="Playwright")

        if not script or not script.strip():
            raise ScriptValidationError("Script cannot be empty", provider="Playwright")

        logger.info(f"Executing script ({len(script)} chars)")

        try:
            # Use existing script executor
            exec_timeout = timeout or self.config.timeout
            exec_result = await execute_script(script, self._page, timeout=exec_timeout)

            # Convert to ScriptExecutionResult
            return ScriptExecutionResult(
                status=exec_result.get("status", "failed"),
                step_results=exec_result.get("step_results", []),
                screenshots=exec_result.get("screenshots", []),
                console_logs=exec_result.get("console_logs", []),
                errors=exec_result.get("errors", []),
                duration_ms=exec_result.get("duration_ms", 0),
                metadata=exec_result.get("metadata", {})
            )

        except ScriptValidationError as e:
            raise e

        except Exception as e:
            logger.error(f"Script execution error: {str(e)}")
            raise ScriptExecutionError(f"Script execution failed: {str(e)}", provider="Playwright")

    async def take_screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False
    ) -> bytes:
        """
        Take a screenshot of the current page.

        Args:
            path: Optional path to save screenshot
            full_page: Whether to capture full scrollable page

        Returns:
            bytes: Screenshot image data

        Raises:
            ScreenshotError: If screenshot fails
        """
        if not self.is_browser_started():
            raise BrowserError("Browser not started", provider="Playwright")

        logger.info(f"Taking screenshot (full_page={full_page})")

        try:
            screenshot_bytes = await self._page.screenshot(
                path=path,
                full_page=full_page
            )

            logger.info(f"Screenshot taken: {len(screenshot_bytes)} bytes")

            if path:
                logger.info(f"Screenshot saved to: {path}")

            return screenshot_bytes

        except Error as e:
            logger.error(f"Screenshot failed: {str(e)}")
            raise ScreenshotError(f"Screenshot failed: {str(e)}", provider="Playwright")

        except Exception as e:
            logger.error(f"Unexpected screenshot error: {str(e)}")
            raise ScreenshotError(f"Unexpected error: {str(e)}", provider="Playwright")

    async def get_page_content(self, include_html: bool = True) -> PageContent:
        """
        Extract content and metadata from the current page.

        Args:
            include_html: Whether to include full HTML content

        Returns:
            PageContent: Extracted page content and metadata

        Raises:
            ContentExtractionError: If content extraction fails
        """
        if not self.is_browser_started():
            raise BrowserError("Browser not started", provider="Playwright")

        logger.info("Extracting page content")

        try:
            # Basic page info
            url = self._page.url
            title = await self._page.title()

            # Extract text content
            text = await self._page.inner_text("body")

            # Extract HTML if requested
            html = ""
            if include_html:
                html = await self._page.content()

            # Extract links
            links = await self._page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a')).map(a => ({
                    text: a.textContent?.trim() || '',
                    href: a.href || ''
                }));
            }""")

            # Extract forms
            forms = await self._page.evaluate("""() => {
                return Array.from(document.querySelectorAll('form')).map(form => ({
                    action: form.action || '',
                    method: form.method || 'GET',
                    inputs: Array.from(form.querySelectorAll('input, textarea, select')).map(input => ({
                        name: input.name || '',
                        type: input.type || 'text',
                        id: input.id || ''
                    }))
                }));
            }""")

            # Extract buttons
            buttons = await self._page.evaluate("""() => {
                return Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]')).map(btn => ({
                    text: btn.textContent?.trim() || btn.value || '',
                    type: btn.type || 'button',
                    id: btn.id || ''
                }));
            }""")

            # Extract inputs
            inputs = await self._page.evaluate("""() => {
                return Array.from(document.querySelectorAll('input, textarea, select')).map(input => ({
                    name: input.name || '',
                    type: input.type || 'text',
                    id: input.id || '',
                    value: input.value || ''
                }));
            }""")

            logger.info(f"Page content extracted: {len(text)} chars, {len(links)} links")

            return PageContent(
                url=url,
                title=title,
                html=html,
                text=text,
                links=links,
                forms=forms,
                buttons=buttons,
                inputs=inputs,
                metadata={"provider": "Playwright"}
            )

        except Error as e:
            logger.error(f"Content extraction failed: {str(e)}")
            raise ContentExtractionError(f"Content extraction failed: {str(e)}", provider="Playwright")

        except Exception as e:
            logger.error(f"Unexpected content extraction error: {str(e)}")
            raise ContentExtractionError(f"Unexpected error: {str(e)}", provider="Playwright")

    async def wait_for_selector(
        self,
        selector: str,
        timeout: Optional[int] = None
    ) -> None:
        """
        Wait for a selector to appear in the page.

        Args:
            selector: CSS selector to wait for
            timeout: Maximum wait time in milliseconds

        Raises:
            TimeoutError: If selector doesn't appear within timeout
        """
        if not self.is_browser_started():
            raise BrowserError("Browser not started", provider="Playwright")

        logger.info(f"Waiting for selector: {selector}")

        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            logger.info(f"Selector found: {selector}")

        except Error as e:
            logger.error(f"Selector not found: {selector} - {str(e)}")
            raise

    async def click(self, selector: str) -> None:
        """
        Click an element matching the selector.

        Args:
            selector: CSS selector of element to click

        Raises:
            ElementNotFoundError: If element is not found
            ClickError: If click operation fails
        """
        if not self.is_browser_started():
            raise BrowserError("Browser not started", provider="Playwright")

        logger.info(f"Clicking element: {selector}")

        try:
            await self._page.click(selector)
            logger.info(f"Element clicked: {selector}")

        except Error as e:
            logger.error(f"Click failed: {selector} - {str(e)}")
            if "not found" in str(e).lower():
                raise ElementNotFoundError(f"Element not found: {selector}", provider="Playwright")
            raise ClickError(f"Click failed: {str(e)}", provider="Playwright")

    async def fill(self, selector: str, value: str) -> None:
        """
        Fill a form input with text.

        Args:
            selector: CSS selector of input element
            value: Text to fill

        Raises:
            ElementNotFoundError: If element is not found
            FillError: If fill operation fails
        """
        if not self.is_browser_started():
            raise BrowserError("Browser not started", provider="Playwright")

        logger.info(f"Filling input: {selector}")

        try:
            await self._page.fill(selector, value)
            logger.info(f"Input filled: {selector}")

        except Error as e:
            logger.error(f"Fill failed: {selector} - {str(e)}")
            if "not found" in str(e).lower():
                raise ElementNotFoundError(f"Element not found: {selector}", provider="Playwright")
            raise FillError(f"Fill failed: {str(e)}", provider="Playwright")

    async def get_text(self, selector: str) -> str:
        """
        Get text content of an element.

        Args:
            selector: CSS selector of element

        Returns:
            str: Text content of element

        Raises:
            ElementNotFoundError: If element is not found
        """
        if not self.is_browser_started():
            raise BrowserError("Browser not started", provider="Playwright")

        try:
            text = await self._page.inner_text(selector)
            logger.info(f"Retrieved text from: {selector}")
            return text

        except Error as e:
            logger.error(f"Get text failed: {selector} - {str(e)}")
            if "not found" in str(e).lower():
                raise ElementNotFoundError(f"Element not found: {selector}", provider="Playwright")
            raise

    async def is_visible(self, selector: str) -> bool:
        """
        Check if an element is visible.

        Args:
            selector: CSS selector of element

        Returns:
            bool: True if element is visible
        """
        if not self.is_browser_started():
            raise BrowserError("Browser not started", provider="Playwright")

        try:
            is_visible = await self._page.is_visible(selector)
            logger.debug(f"Element visibility check: {selector} = {is_visible}")
            return is_visible

        except Error:
            return False

    async def close(self) -> None:
        """
        Close the current page/context.

        Raises:
            BrowserError: If close operation fails
        """
        if not self.is_browser_started():
            logger.warning("Browser not started, nothing to close")
            return

        logger.info("Closing current page")

        try:
            if self._page:
                await self._page.close()
                self._page = None

            # Create a new page for subsequent operations
            if self._context:
                self._page = await self._context.new_page()

            logger.info("Page closed")

        except Error as e:
            logger.error(f"Close failed: {str(e)}")
            raise BrowserError(f"Close failed: {str(e)}", provider="Playwright")

    async def health_check(self) -> bool:
        """
        Check if browser automation is working properly.

        Returns:
            bool: True if browser automation is healthy
        """
        try:
            # Try to start browser if not started
            if not self.is_browser_started():
                await self.start_browser()

            # Check if page is accessible
            if self._page:
                # Navigate to a simple page
                await self.navigate("about:blank")

                # Check if we can get page title
                title = await self._page.title()
                is_healthy = title is not None

                logger.info(f"Playwright health check: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
                return is_healthy

            return False

        except Exception as e:
            logger.error(f"Playwright health check failed: {str(e)}")
            return False

    def is_browser_started(self) -> bool:
        """
        Check if browser is currently started.

        Returns:
            bool: True if browser is started
        """
        return self._browser is not None and self._page is not None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop_browser()
