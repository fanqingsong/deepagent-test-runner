"""
Browser Automation Interface

Defines the contract for browser automation providers.
Following SOLID Dependency Inversion Principle - high-level modules depend on abstractions.

This interface enables:
- Easy swapping of browser automation tools (Playwright, Puppeteer, Selenium)
- Mock implementations for testing
- Consistent API across different providers
- Screenshot and content extraction capabilities
- Safe script execution in sandboxed environment
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class BrowserType(Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


@dataclass
class BrowserConfig:
    """
    Browser configuration options.

    Attributes:
        headless: Run browser in headless mode (no GUI)
        timeout: Default timeout for operations in milliseconds
        viewport: Viewport dimensions (width, height)
        user_agent: Custom user agent string
        locale: Browser locale (e.g., 'en-US', 'zh-CN')
        timezone: Timezone identifier (e.g., 'America/New_York')
        geolocation: Geolocation coordinates (latitude, longitude)
        permissions: List of permissions to grant
        ignore_https_errors: Whether to ignore HTTPS certificate errors
        slow_mo: Slow down operations by specified milliseconds
    """
    headless: bool = True
    timeout: int = 30000
    viewport: Optional[Dict[str, int]] = None
    user_agent: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    geolocation: Optional[Dict[str, float]] = None
    permissions: Optional[List[str]] = None
    ignore_https_errors: bool = False
    slow_mo: int = 0

    def __post_init__(self):
        if self.viewport is None:
            self.viewport = {"width": 1280, "height": 720}
        if self.permissions is None:
            self.permissions = []


@dataclass
class ScriptExecutionResult:
    """
    Result of browser script execution.

    Attributes:
        status: Execution status ('passed', 'failed', 'error')
        step_results: List of individual step results
        screenshots: Base64-encoded screenshots taken during execution
        console_logs: Console logs collected during execution
        errors: List of errors encountered
        duration_ms: Execution duration in milliseconds
        metadata: Additional execution metadata
    """
    status: str
    step_results: List[Dict[str, Any]] = None
    screenshots: List[str] = None
    console_logs: List[Dict[str, str]] = None
    errors: List[str] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.step_results is None:
            self.step_results = []
        if self.screenshots is None:
            self.screenshots = []
        if self.console_logs is None:
            self.console_logs = []
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PageContent:
    """
    Extracted page content and metadata.

    Attributes:
        url: Current page URL
        title: Page title
        html: Full HTML content
        text: Extracted text content
        links: List of links found on page
        forms: List of forms found on page
        buttons: List of buttons found on page
        inputs: List of input fields found on page
        metadata: Additional page metadata
    """
    url: str
    title: str
    html: str
    text: str
    links: List[Dict[str, str]] = None
    forms: List[Dict[str, Any]] = None
    buttons: List[Dict[str, str]] = None
    inputs: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.links is None:
            self.links = []
        if self.forms is None:
            self.forms = []
        if self.buttons is None:
            self.buttons = []
        if self.inputs is None:
            self.inputs = []
        if self.metadata is None:
            self.metadata = {}


class IBrowserAutomation(ABC):
    """
    Interface for browser automation providers.

    This abstraction allows switching between different browser automation
    tools (Playwright, Puppeteer, Selenium) without changing application code.
    """

    @abstractmethod
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
            ConnectionError: If connection to browser fails
        """
        pass

    @abstractmethod
    async def stop_browser(self) -> None:
        """
        Stop the browser instance and cleanup resources.

        Raises:
            BrowserError: If browser fails to stop properly
        """
        pass

    @abstractmethod
    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation succeeded
                ('load', 'domcontentloaded', 'networkidle')

        Raises:
            NavigationError: If navigation fails
            TimeoutError: If navigation times out
        """
        pass

    @abstractmethod
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
            timeout: Execution timeout in milliseconds (uses default if None)

        Returns:
            ScriptExecutionResult: Execution result with status and metadata

        Raises:
            ScriptValidationError: If script validation fails
            ScriptExecutionError: If script execution fails
            TimeoutError: If script execution times out
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def click(self, selector: str) -> None:
        """
        Click an element matching the selector.

        Args:
            selector: CSS selector of element to click

        Raises:
            ElementNotFoundError: If element is not found
            ClickError: If click operation fails
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def is_visible(self, selector: str) -> bool:
        """
        Check if an element is visible.

        Args:
            selector: CSS selector of element

        Returns:
            bool: True if element is visible
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the current page/context.

        Raises:
            BrowserError: If close operation fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if browser automation is working properly.

        Returns:
            bool: True if browser automation is healthy

        Raises:
            Exception: If health check fails
        """
        pass

    @abstractmethod
    def is_browser_started(self) -> bool:
        """
        Check if browser is currently started.

        Returns:
            bool: True if browser is started
        """
        pass


class BrowserError(Exception):
    """Base exception for browser automation errors."""

    def __init__(self, message: str, provider: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(self.message)


class BrowserLaunchError(BrowserError):
    """Exception raised when browser fails to launch."""

    pass


class NavigationError(BrowserError):
    """Exception raised when navigation fails."""

    pass


class ScriptValidationError(BrowserError, ValueError):
    """Exception raised when script validation fails."""

    pass


class ScriptExecutionError(BrowserError):
    """Exception raised when script execution fails."""

    pass


class ElementNotFoundError(BrowserError):
    """Exception raised when element is not found."""

    pass


class ClickError(BrowserError):
    """Exception raised when click operation fails."""

    pass


class FillError(BrowserError):
    """Exception raised when fill operation fails."""

    pass


class ScreenshotError(BrowserError):
    """Exception raised when screenshot fails."""

    pass


class ContentExtractionError(BrowserError):
    """Exception raised when content extraction fails."""

    pass
