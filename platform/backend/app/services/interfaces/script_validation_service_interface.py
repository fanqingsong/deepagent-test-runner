"""
Script Validation Service Interface

Defines the contract for Playwright script validation services.
Following the Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union

from app.core.simple_result_types import ServiceSuccess, ServiceError


class IScriptValidationService(ABC):
    """
    Interface for script validation services.

    This interface defines the contract for services that validate
    Playwright scripts through browser execution.
    """

    @abstractmethod
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
            ServiceSuccess with validation result dict containing:
                - status: "passed", "failed", or "error"
                - step_results: List of step results from script
                - error: Optional error message
            or ServiceError if validation fails

        Raises:
            None - errors are wrapped in ServiceError
        """
        pass

    @abstractmethod
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
            or ServiceError if validation fails

        Raises:
            None - errors are wrapped in ServiceError
        """
        pass

    @abstractmethod
    def determine_script_status_v2(self, validation_result: Dict[str, Any]) -> ServiceSuccess[str] | ServiceError:
        """
        Determine script status based on validation result.

        Args:
            validation_result: Result from validate_script_v2()

        Returns:
            ServiceSuccess with "validated" if script passed, "draft" otherwise
            or ServiceError if determination fails

        Raises:
            None - errors are wrapped in ServiceError
        """
        pass
