"""
External Dependency Interfaces

This package provides interface abstractions for external dependencies following SOLID principles.

Interfaces:
- ILLMClient: LLM provider abstraction (GLM, OpenAI, Anthropic, etc.)
- IBrowserAutomation: Browser automation abstraction (Playwright, Puppeteer, Selenium, etc.)
- IHealthChecker: Health check abstraction for system components

Usage:
    from app.core.interfaces.llm_client_interface import ILLMClient, LLMResponse
    from app.core.interfaces.browser_automation_interface import IBrowserAutomation, BrowserConfig
    from app.core.interfaces.health_check_interface import IHealthChecker
"""

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

from app.core.interfaces.health_check_interface import (
    IHealthChecker
)

__all__ = [
    # LLM Interface
    "ILLMClient",
    "LLMResponse",
    "LLMMessage",
    "LLMStreamChunk",
    "LLMClientException",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMValidationError",
    "LLMRateLimitError",
    "LLMTokenLimitError",

    # Browser Automation Interface
    "IBrowserAutomation",
    "BrowserType",
    "BrowserConfig",
    "ScriptExecutionResult",
    "PageContent",
    "BrowserError",
    "BrowserLaunchError",
    "NavigationError",
    "ScriptValidationError",
    "ScriptExecutionError",
    "ElementNotFoundError",
    "ClickError",
    "FillError",
    "ScreenshotError",
    "ContentExtractionError",

    # Health Check Interface
    "IHealthChecker",
]
