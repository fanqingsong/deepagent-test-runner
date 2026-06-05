"""
Script Generation API Endpoints

Generate, validate, and manage Playwright test scripts for test definitions.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from playwright.async_api import async_playwright
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.test_definition import TestDefinition
from app.models.user import User
from app.schemas.test_definition import (
    ScriptGenerationRequest,
    ScriptResponse,
    ScriptUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_test_def_or_404(test_definition_id: int, db: AsyncSession, user: User):
    """Helper to load a test definition or raise 404."""
    return select(TestDefinition).where(
        TestDefinition.id == test_definition_id,
        TestDefinition.is_active == True,
    )


@router.post("/test-definitions/{test_definition_id}/generate-script", response_model=ScriptResponse)
async def generate_script(
    test_definition_id: int,
    body: ScriptGenerationRequest = ScriptGenerationRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a Playwright script for a test definition."""
    from app.agents.deepagents_test_runner.page_fetcher import fetch_page_context
    from app.agents.deepagents_test_runner.script_generator import generate_playwright_script
    from app.agents.deepagents_test_runner.script_executor import execute_script

    result = await db.execute(
        _get_test_def_or_404(test_definition_id, db, current_user)
    )
    test_def = result.scalar_one_or_none()
    if not test_def:
        raise HTTPException(status_code=404, detail="Test definition not found")

    if not test_def.url or not test_def.test_goal:
        raise HTTPException(status_code=400, detail="Test definition must have url and test_goal")

    if test_def.playwright_script and test_def.script_status == "validated" and not body.force_regenerate:
        return ScriptResponse(
            playwright_script=test_def.playwright_script,
            script_status=test_def.script_status,
            script_metadata=test_def.script_metadata,
            execution_mode=test_def.execution_mode,
        )

    test_def.script_status = "generating"
    await db.commit()

    script = None
    script_error = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            page_context = await fetch_page_context(page, test_def.url)

            for attempt in range(body.max_retries):
                gen_result = await generate_playwright_script(
                    goal=test_def.test_goal,
                    url=test_def.url,
                    page_context=page_context.get("context_text", ""),
                    previous_error=script_error,
                    previous_script=script,
                )

                script = gen_result.get("script")
                if not script:
                    script_error = gen_result.get("error", "Script generation failed")
                    continue

                exec_result = await execute_script(script, page, timeout=60)
                if exec_result.get("status") == "passed":
                    test_def.playwright_script = script
                    test_def.script_status = "validated"
                    test_def.script_metadata = {
                        "attempts": attempt + 1,
                        "last_error": None,
                    }
                    await db.commit()
                    await db.refresh(test_def)
                    return ScriptResponse(
                        playwright_script=script,
                        script_status="validated",
                        script_metadata=test_def.script_metadata,
                        execution_mode=test_def.execution_mode,
                    )

                script_error = exec_result.get("error", "Unknown error")
                logger.info("Script attempt %d failed: %s", attempt + 1, script_error)

        finally:
            await browser.close()

    test_def.playwright_script = script
    test_def.script_status = "draft" if script else "failed"
    test_def.script_metadata = {
        "attempts": body.max_retries,
        "last_error": script_error,
    }
    await db.commit()
    await db.refresh(test_def)

    return ScriptResponse(
        playwright_script=script,
        script_status=test_def.script_status,
        script_metadata=test_def.script_metadata,
        execution_mode=test_def.execution_mode,
    )


@router.get("/test-definitions/{test_definition_id}/script", response_model=ScriptResponse)
async def get_script(
    test_definition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current script and its status."""
    result = await db.execute(
        _get_test_def_or_404(test_definition_id, db, current_user)
    )
    test_def = result.scalar_one_or_none()
    if not test_def:
        raise HTTPException(status_code=404, detail="Test definition not found")

    return ScriptResponse(
        playwright_script=test_def.playwright_script,
        script_status=test_def.script_status,
        script_metadata=test_def.script_metadata,
        execution_mode=test_def.execution_mode,
    )


@router.put("/test-definitions/{test_definition_id}/script", response_model=ScriptResponse)
async def update_script(
    test_definition_id: int,
    body: ScriptUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update script content (user edits)."""
    result = await db.execute(
        _get_test_def_or_404(test_definition_id, db, current_user)
    )
    test_def = result.scalar_one_or_none()
    if not test_def:
        raise HTTPException(status_code=404, detail="Test definition not found")

    test_def.playwright_script = body.playwright_script
    test_def.script_status = "draft"
    await db.commit()
    await db.refresh(test_def)

    return ScriptResponse(
        playwright_script=test_def.playwright_script,
        script_status=test_def.script_status,
        script_metadata=test_def.script_metadata,
        execution_mode=test_def.execution_mode,
    )


@router.post("/test-definitions/{test_definition_id}/validate-script", response_model=ScriptResponse)
async def validate_script(
    test_definition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run script validation (execute and report result)."""
    from app.agents.deepagents_test_runner.script_executor import execute_script

    result = await db.execute(
        _get_test_def_or_404(test_definition_id, db, current_user)
    )
    test_def = result.scalar_one_or_none()
    if not test_def:
        raise HTTPException(status_code=404, detail="Test definition not found")

    if not test_def.playwright_script:
        raise HTTPException(status_code=400, detail="No script to validate")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            if test_def.url:
                await page.goto(test_def.url, wait_until="domcontentloaded", timeout=30000)

            exec_result = await execute_script(test_def.playwright_script, page, timeout=120)
        finally:
            await browser.close()

    exec_status = exec_result.get("status", "failed")
    test_def.script_status = "validated" if exec_status == "passed" else "draft"
    test_def.script_metadata = {
        **(test_def.script_metadata or {}),
        "validation_error": exec_result.get("error"),
        "last_error": exec_result.get("error"),
    }
    await db.commit()
    await db.refresh(test_def)

    return ScriptResponse(
        playwright_script=test_def.playwright_script,
        script_status=test_def.script_status,
        script_metadata=test_def.script_metadata,
        execution_mode=test_def.execution_mode,
    )


@router.post("/test-definitions/{test_definition_id}/approve-script", response_model=ScriptResponse)
async def approve_script(
    test_definition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve script for regression testing."""
    result = await db.execute(
        _get_test_def_or_404(test_definition_id, db, current_user)
    )
    test_def = result.scalar_one_or_none()
    if not test_def:
        raise HTTPException(status_code=404, detail="Test definition not found")

    if not test_def.playwright_script:
        raise HTTPException(status_code=400, detail="No script to approve")

    if test_def.script_status != "validated":
        raise HTTPException(status_code=400, detail="Script must be validated before approval")

    test_def.script_status = "approved"
    test_def.execution_mode = "script"
    await db.commit()
    await db.refresh(test_def)

    return ScriptResponse(
        playwright_script=test_def.playwright_script,
        script_status=test_def.script_status,
        script_metadata=test_def.script_metadata,
        execution_mode=test_def.execution_mode,
    )


@router.post("/test-definitions/{test_definition_id}/generate-description")
async def generate_description(
    test_definition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a concise description based on test goal using LLM."""
    from app.core.agent_config import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.core.llm_context import llm_usage_context

    result = await db.execute(
        _get_test_def_or_404(test_definition_id, db, current_user)
    )
    test_def = result.scalar_one_or_none()
    if not test_def:
        raise HTTPException(status_code=404, detail="Test definition not found")

    if not test_def.test_goal:
        raise HTTPException(status_code=400, detail="Test definition must have test_goal")

    system_prompt = """You are a technical writing assistant. Generate a concise, clear description for a test case based on its goal.

Rules:
1. Output ONLY the description text, no explanations or markdown
2. Keep it under 100 characters
3. Use active voice and present tense
4. Focus on what is being tested, not how
5. Be specific but brief
6. Do NOT add any introductory or concluding text"""

    user_prompt = f"""Generate a concise description for this test goal:

Test Goal: {test_def.test_goal}

Generate the description now."""

    try:
        llm = get_llm(temperature=0.3, max_tokens=150)
        async with llm_usage_context("description_generator", test_run_id=f"test_def_{test_definition_id}"):
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
    except Exception as e:
        logger.error(f"Error generating description: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate description: {str(e)}"
        )

    content = response.content if hasattr(response, 'content') else str(response)
    generated_description = content.strip()

    # Clean up common LLM artifacts
    generated_description = generated_description.rstrip('."')

    return {"description": generated_description}
