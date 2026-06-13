"""
Script Validation Service

Handles Playwright script validation logic with browser automation.
Extracted from endpoints to follow Single Responsibility Principle.
Now with Result wrapper types for better error handling.
"""

import logging
from typing import Dict, Any, Optional, Union

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.core.simple_result_types import (
    service_success, service_error, service_validation_error,
    ServiceSuccess, ServiceError
)
from app.services.interfaces.script_validation_service_interface import IScriptValidationService

logger = logging.getLogger(__name__)


class ScriptValidationService(IScriptValidationService):
    """
    Service for validating Playwright scripts through browser execution.

    Responsible for:
    - Browser lifecycle management
    - Script execution in controlled environment
    - Result extraction and error handling
    - Timeout and safety management
    """

    def __init__(self, headless: bool = True, timeout: int = 120):
        """
        Initialize Script Validation Service.

        Args:
            headless: Run browser in headless mode
            timeout: Default execution timeout in seconds
        """
        self.headless = headless
        self.timeout = timeout

    # ==================== Result-based methods (v2) ====================

    async def validate_script_v2(
        self,
        script: str,
        url: Optional[str] = None
    ) -> ServiceSuccess[Dict[str, Any]] | ServiceError:
        """
        Validate a Playwright script by executing it in a browser.

        Args:
            script: Playwright script source code
            url: Optional URL to navigate to before execution

        Returns:
            ServiceSuccess with validation result dict or ServiceError
            Dict contains:
                - status: "passed", "failed", or "error"
                - step_results: List of step results from script
                - error: Optional error message
        """
        try:
            if not script or not script.strip():
                return service_validation_error("Script cannot be empty")

            from app.agents.test_composer.lib.script_executor import execute_script

            # Browser will be managed by context manager
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context()
                page = await context.new_page()

                try:
                    # Navigate to URL if provided
                    if url:
                        await page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=30000
                        )

                    # Execute the script
                    exec_result = await execute_script(
                        script,
                        page,
                        timeout=self.timeout
                    )

                finally:
                    await browser.close()

            # Extract results
            exec_status = exec_result.get("status", "failed")

            result = {
                "status": exec_status,
                "step_results": exec_result.get("step_results", []),
                "error": exec_result.get("error")
            }

            return service_success(result, metadata={
                "execution_time": self.timeout,
                "headless": self.headless
            })

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return service_validation_error(f"Invalid script: {str(e)}")
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
            return service_error(f"Script execution failed: {str(e)}", "EXECUTION_ERROR")

    async def validate_script_with_metadata_v2(
        self,
        script: str,
        url: Optional[str] = None,
        existing_metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceSuccess[Dict[str, Any]] | ServiceError:
        """
        Validate script and merge results with existing metadata.

        Args:
            script: Playwright script source code
            url: Optional URL to navigate to before execution
            existing_metadata: Existing script metadata to merge with

        Returns:
            ServiceSuccess with dict containing:
                - validation_result: Validation result from validate_script_v2
                - updated_metadata: Merged metadata
        """
        try:
            validation_result = await self.validate_script_v2(script, url)

            if validation_result.is_error():
                return validation_result

            # Merge with existing metadata
            validation_data = validation_result.get_data()
            updated_metadata = {
                **(existing_metadata or {}),
                "validation_error": validation_data.get("error"),
                "last_error": validation_data.get("error"),
                "validation_status": validation_data.get("status"),
            }

            result = {
                "validation_result": validation_data,
                "updated_metadata": updated_metadata
            }

            return service_success(result, metadata={
                "has_existing_metadata": existing_metadata is not None
            })

        except Exception as e:
            logger.error(f"Failed to validate script with metadata: {e}")
            return service_error(f"Failed to validate script with metadata: {str(e)}", "METADATA_ERROR")

    def determine_script_status_v2(self, validation_result: Dict[str, Any]) -> ServiceSuccess[str] | ServiceError:
        """
        Determine script status based on validation result.

        Args:
            validation_result: Result from validate_script_v2()

        Returns:
            ServiceSuccess with "validated" if script passed, "draft" otherwise
        """
        try:
            if not validation_result:
                return service_validation_error("Validation result cannot be empty")

            exec_status = validation_result.get("status", "failed")
            status = "validated" if exec_status == "passed" else "draft"

            return service_success(status, metadata={
                "validation_status": exec_status
            })

        except Exception as e:
            logger.error(f"Failed to determine script status: {e}")
            return service_error(f"Failed to determine script status: {str(e)}", "STATUS_ERROR")

    # ==================== Legacy methods (maintained for backward compatibility) ====================

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

        from app.agents.test_composer.lib.script_executor import execute_script

        # Browser will be managed by context manager
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Navigate to URL if provided
                if url:
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=30000
                    )

                # Execute the script
                exec_result = await execute_script(
                    script,
                    page,
                    timeout=self.timeout
                )

            finally:
                await browser.close()

        # Extract results
        exec_status = exec_result.get("status", "failed")

        return {
            "status": exec_status,
            "step_results": exec_result.get("step_results", []),
            "error": exec_result.get("error")
        }

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
