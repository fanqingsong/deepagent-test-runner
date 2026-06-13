"""
Script Validation API Endpoints

Handles Playwright script validation endpoints.
Refactored to follow SOLID principles - validation concerns only.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.test_definition import ScriptResponse
from app.services.script_validation_service import ScriptValidationService
from app.services.script_management_service import ScriptManagementService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/test-definitions/{test_definition_id}/validate-script",
    response_model=ScriptResponse,
    summary="Validate Playwright script",
    description="Run script validation by executing it in a browser and report results"
)
async def validate_script(
    test_definition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScriptResponse:
    """Run script validation (execute and report result)."""
    management_service = ScriptManagementService(db)
    validation_service = ScriptValidationService()

    try:
        # Load test definition
        test_def = await management_service.get_test_definition_or_404(
            test_definition_id
        )
        if not test_def:
            raise HTTPException(
                status_code=404,
                detail="Test definition not found"
            )

        if not test_def.playwright_script:
            raise HTTPException(
                status_code=400,
                detail="No script to validate"
            )

        # Validate script through browser execution
        validation_result = await validation_service.validate_script(
            script=test_def.playwright_script,
            url=test_def.url
        )

        # Determine new status based on validation result
        new_status = validation_service.determine_script_status(
            validation_result
        )

        # Update test definition with validation results
        response = await management_service.update_script_status(
            test_definition_id=test_definition_id,
            new_status=new_status,
            metadata_updates={
                "validation_error": validation_result.get("error"),
                "last_error": validation_result.get("error"),
            }
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Script validation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Script validation failed: {str(e)}"
        )
