"""
Script Generation API Endpoints

Handles Playwright script generation and streaming endpoints.
Refactored to follow SOLID principles - generation concerns only.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.test_definition import (
    ScriptGenerationRequest,
    ScriptResponse,
)
from app.services.script_generation_service import ScriptGenerationService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/test-definitions/{test_definition_id}/generate-script",
    response_model=ScriptResponse,
    summary="Generate Playwright script",
    description="Generate a Playwright script for a test definition using AI"
)
async def generate_script(
    test_definition_id: int,
    body: ScriptGenerationRequest = ScriptGenerationRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScriptResponse:
    """Generate a Playwright script for a test definition."""
    service = ScriptGenerationService(db)

    try:
        # Prepare test definition for generation
        test_def, existing_response = await service.prepare_script_generation(
            test_definition_id,
            force_regenerate=body.force_regenerate
        )

        # Return existing script if available and not forcing regeneration
        if existing_response:
            return existing_response

        # Run generation workflow
        result = await service.run_script_generation_workflow(
            test_definition_id=test_def.id,
            url=test_def.url,
            goal=test_def.test_goal,
            description=test_def.description,
        )

        return ScriptResponse(**result)

    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Script generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Script generation failed: {str(e)}"
        )


@router.post(
    "/test-definitions/{test_definition_id}/generate-script/stream",
    summary="Generate Playwright script with streaming",
    description="Generate a Playwright script with real-time SSE progress events"
)
async def generate_script_stream(
    test_definition_id: int,
    body: ScriptGenerationRequest = ScriptGenerationRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a Playwright script with real-time SSE progress events."""
    from app.agents.test_composer.runners import run_script_generation_stream

    service = ScriptGenerationService(db)

    try:
        # Prepare test definition for generation
        test_def, existing_response = await service.prepare_script_generation(
            test_definition_id,
            force_regenerate=body.force_regenerate
        )

        # Return existing script if available and not forcing regeneration
        if existing_response:
            # For streaming, we need to return the response directly, not as stream
            return existing_response

        # Release DB session — subagent uses its own sessions via run_with_session
        await db.close()

        return StreamingResponse(
            run_script_generation_stream(
                test_definition_id=test_def.id,
                url=test_def.url,
                goal=test_def.test_goal,
                description=test_def.description,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Script generation stream failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Script generation failed: {str(e)}"
        )
