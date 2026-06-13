"""
Browser Automation Implementations

This package provides implementations of the IBrowserAutomation interface.

Implementations:
- PlaywrightAutomation: Production implementation using Playwright
- MockBrowserAutomation: Mock implementation for testing

Usage:
    from app.core.browser.playwright_automation import PlaywrightAutomation
    from app.core.browser.mock_browser_automation import MockBrowserAutomation
"""

from app.core.browser.playwright_automation import PlaywrightAutomation
from app.core.browser.mock_browser_automation import MockBrowserAutomation

__all__ = [
    "PlaywrightAutomation",
    "MockBrowserAutomation",
]
