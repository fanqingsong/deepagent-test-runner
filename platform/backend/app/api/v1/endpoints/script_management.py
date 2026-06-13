"""
Script Management API Endpoints

Handles Playwright script lifecycle management endpoints.
Refactored to follow SOLID principles - management concerns only.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.test_definition import ScriptResponse, ScriptUpdateRequest
from app.services.script_management_service import ScriptManagementService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/test-definitions/{test_definition_id}/script",
    response_model=ScriptResponse,
    summary="Get Playwright script",
    description="Get the current script and its status for a test definition"
)
async def get_script(
    test_definition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScriptResponse:
    """Get the current script and its status."""
    service = ScriptManagementService(db)

    try:
        return await service.get_script(test_definition_id)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get script: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get script: {str(e)}"
        )


@router.put(
    "/test-definitions/{test_definition_id}/script",
    response_model=ScriptResponse,
    summary="Update Playwright script",
    description="Update script content (user edits). Status resets to draft."
)
async def update_script(
    test_definition_id: int,
    body: ScriptUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScriptResponse:
    """Update script content (user edits)."""
    service = ScriptManagementService(db)

    try:
        return await service.update_script(test_definition_id, body)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update script: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update script: {str(e)}"
        )


@router.post(
    "/test-definitions/{test_definition_id}/approve-script",
    response_model=ScriptResponse,
    summary="Approve Playwright script",
    description="Approve script for regression testing. Must be validated first."
)
async def approve_script(
    test_definition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScriptResponse:
    """Approve script for regression testing."""
    service = ScriptManagementService(db)

    try:
        return await service.approve_script(test_definition_id)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to approve script: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve script: {str(e)}"
        )


@router.post(
    "/test-definitions/{test_definition_id}/generate-description",
    summary="Generate test description",
    description="Generate a concise description based on test goal using LLM"
)
async def generate_description(
    test_definition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a concise description based on test goal using LLM."""
    from app.services.script_generation_service import ScriptGenerationService

    service = ScriptGenerationService(db)

    try:
        # Load test definition
        test_def = await service.get_test_definition_or_404(test_definition_id)
        if not test_def:
            raise HTTPException(
                status_code=404,
                detail="Test definition not found"
            )

        if not test_def.test_goal:
            raise HTTPException(
                status_code=400,
                detail="Test definition must have test_goal"
            )

        # Generate description
        description = await service.generate_description(
            test_goal=test_def.test_goal,
            test_definition_id=test_definition_id
        )

        return {"description": description}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Description generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate description: {str(e)}"
        )
