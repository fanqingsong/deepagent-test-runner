"""
Script Validation Service (Refactored)

Refactored to use IBrowserAutomation interface for flexibility.
Maintains backward compatibility with existing code.
"""

import logging
from typing import Dict, Any, Optional

from app.core.interfaces.browser_automation_interface import IBrowserAutomation, BrowserConfig
from app.core.browser.playwright_automation import PlaywrightAutomation


logger = logging.getLogger(__name__)


class ScriptValidationService:
    """
    Service for validating Playwright scripts through browser automation.

    Responsible for:
    - Browser lifecycle management
    - Script execution in controlled environment
    - Result extraction and error handling
    - Timeout and safety management

    Refactored to use IBrowserAutomation interface for flexibility.
    """

    def __init__(
        self,
        browser_automation: Optional[IBrowserAutomation] = None,
        headless: bool = True,
        timeout: int = 120
    ):
        """
        Initialize Script Validation Service.

        Args:
            browser_automation: IBrowserAutomation implementation (creates PlaywrightAutomation if None)
            headless: Run browser in headless mode (only used if browser_automation is None)
            timeout: Default execution timeout in seconds (only used if browser_automation is None)
        """
        if browser_automation is not None:
            self._browser_automation = browser_automation
        else:
            # Create Playwright automation with provided parameters
            config = BrowserConfig(
                headless=headless,
                timeout=timeout * 1000  # Convert to milliseconds
            )
            self._browser_automation = PlaywrightAutomation(config=config)

        # Expose properties for backward compatibility
        self.headless = headless
        self.timeout = timeout

    async def validate_script(
        self,
        script: str,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate a Playwright script by executing it in a browser.

        Args:
            script: Playwright script source code
            url: Optional URL to navigate to before execution

        Returns:
            Dict with keys:
                - status: "passed", "failed", or "error"
                - step_results: List of step results from script
                - error: Optional error message

        Raises:
            ValueError: If script is empty or invalid
        """
        if not script or not script.strip():
            raise ValueError("Script cannot be empty")

        logger.info(f"Validating script ({len(script)} chars)")

        try:
            # Start browser
            await self._browser_automation.start_browser()

            # Navigate to URL if provided
            if url:
                await self._browser_automation.navigate(url)

            # Execute the script
            exec_result = await self._browser_automation.execute_script(script)

            logger.info(f"Script validation completed: {exec_result.status}")

            return {
                "status": exec_result.status,
                "step_results": exec_result.step_results,
                "error": exec_result.errors[0] if exec_result.errors else None
            }

        finally:
            # Always stop browser
            await self._browser_automation.stop_browser()

    async def validate_script_with_metadata(
        self,
        script: str,
        url: Optional[str] = None,
        existing_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate script and merge results with existing metadata.

        Args:
            script: Playwright script source code
            url: Optional URL to navigate to before execution
            existing_metadata: Existing script metadata to merge with

        Returns:
            Updated metadata dictionary with validation results
        """
        validation_result = await self.validate_script(script, url)

        # Merge with existing metadata
        updated_metadata = {
            **(existing_metadata or {}),
            "validation_error": validation_result.get("error"),
            "last_error": validation_result.get("error"),
            "validation_status": validation_result.get("status"),
        }

        return {
            "validation_result": validation_result,
            "updated_metadata": updated_metadata
        }

    def determine_script_status(self, validation_result: Dict[str, Any]) -> str:
        """
        Determine script status based on validation result.

        Args:
            validation_result: Result from validate_script()

        Returns:
            "validated" if script passed, "draft" otherwise
        """
        exec_status = validation_result.get("status", "failed")
        return "validated" if exec_status == "passed" else "draft"

    async def take_screenshot(self, url: str) -> bytes:
        """
        Take a screenshot of a webpage.

        Args:
            url: URL to navigate to

        Returns:
            bytes: Screenshot image data

        Raises:
            Exception: If screenshot fails
        """
        logger.info(f"Taking screenshot of: {url}")

        try:
            await self._browser_automation.start_browser()
            await self._browser_automation.navigate(url)
            screenshot = await self._browser_automation.take_screenshot()
            return screenshot

        finally:
            await self._browser_automation.stop_browser()

    async def extract_page_content(self, url: str) -> Dict[str, Any]:
        """
        Extract content from a webpage.

        Args:
            url: URL to navigate to

        Returns:
            Dict with page content including links, forms, buttons, etc.

        Raises:
            Exception: If extraction fails
        """
        logger.info(f"Extracting content from: {url}")

        try:
            await self._browser_automation.start_browser()
            await self._browser_automation.navigate(url)
            page_content = await self._browser_automation.get_page_content()

            return {
                "url": page_content.url,
                "title": page_content.title,
                "text": page_content.text,
                "links": page_content.links,
                "forms": page_content.forms,
                "buttons": page_content.buttons,
                "inputs": page_content.inputs,
            }

        finally:
            await self._browser_automation.stop_browser()

    async def health_check(self) -> bool:
        """
        Check if browser automation is working properly.

        Returns:
            bool: True if browser automation is healthy
        """
        try:
            return await self._browser_automation.health_check()
        except Exception as e:
            logger.error(f"Browser automation health check failed: {str(e)}")
            return False

    # Property access to underlying automation for advanced usage

    @property
    def browser(self) -> IBrowserAutomation:
        """Get the underlying IBrowserAutomation instance."""
        return self._browser_automation
