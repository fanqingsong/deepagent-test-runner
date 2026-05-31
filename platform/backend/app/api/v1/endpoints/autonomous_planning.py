"""
Autonomous Planning API Endpoints

REST API for AI-powered test planning and adaptive execution.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models import TestDefinition
from app.models.user import User
from app.agents.test_runner.planner_agent import generate_test_plan as agent_generate_test_plan

router = APIRouter()


# Request/Response Schemas
class GeneratePlanRequest(BaseModel):
    """Request schema for test plan generation."""
    goal: str = Field(..., description="Natural language test goal/requirement")
    url: str = Field(..., description="Target URL for testing")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    test_definition_id: Optional[int] = Field(None, description="Optional test definition to associate with")


class PlanModification(BaseModel):
    """Schema for plan modifications."""
    step_number: int
    description: Optional[str] = None
    type: Optional[str] = None
    verification: Optional[str] = None


class ApprovePlanRequest(BaseModel):
    """Request schema for plan approval."""
    modifications: List[PlanModification] = Field(default_factory=list, description="Optional step modifications")


class PlanStep(BaseModel):
    """Schema for individual plan step."""
    step_number: int
    description: str
    type: str
    verification: str
    confidence: float
    fallback_strategies: List[str]


class GeneratedPlanResponse(BaseModel):
    """Response schema for generated plan."""
    plan_id: str
    steps: List[PlanStep]
    estimated_duration: int
    risk_factors: List[str]
    success_criteria: List[str]
    test_definition_id: Optional[int] = None


class ExecutionDecisionRequest(BaseModel):
    """Request schema for execution decisions."""
    current_step: Dict[str, Any]
    page_state: Dict[str, Any]
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionDecisionResponse(BaseModel):
    """Response schema for execution decisions."""
    action: str  # "continue" | "retry" | "skip" | "abort"
    reason: str
    modifications: Dict[str, Any]


class ErrorRecoveryRequest(BaseModel):
    """Request schema for error recovery."""
    error: str
    context: Dict[str, Any]
    remaining_steps: List[Dict[str, Any]] = Field(default_factory=list)


class ErrorRecoveryResponse(BaseModel):
    """Response schema for error recovery."""
    error_type: str
    recovery_strategy: Dict[str, Any]
    can_continue: bool
    estimated_recovery_time: int


@router.post("/generate-plan", response_model=GeneratedPlanResponse, status_code=status.HTTP_200_OK)
async def generate_test_plan(
    request: GeneratePlanRequest,
    current_user: User = Depends(RequirePermission("create:test")),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI test plan from user goal.

    - **goal**: Natural language description of what to test
    - **url**: Target URL for testing
    - **context**: Additional context (environment variables, etc.)
    - **test_definition_id**: Optional test definition to associate plan with

    Returns a comprehensive test plan with 3-8 structured steps.
    """
    try:
        # Generate plan using LangGraph planner agent
        plan = await agent_generate_test_plan(
            goal=request.goal,
            url=request.url,
            context=request.context,
        )

        # Associate with test definition if provided
        if request.test_definition_id:
            await _associate_plan_with_test_definition(
                db, request.test_definition_id, plan
            )
            plan["test_definition_id"] = request.test_definition_id

        return plan

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test plan: {str(e)}"
        )


@router.put("/approve-plan/{test_definition_id}", status_code=status.HTTP_200_OK)
async def approve_plan(
    test_definition_id: int,
    request: ApprovePlanRequest,
    current_user: User = Depends(RequirePermission("update:test")),
    db: AsyncSession = Depends(get_db)
):
    """
    Finalize and store approved test plan.

    - **test_definition_id**: Test definition to approve plan for
    - **modifications**: Optional list of step modifications

    Updates the test definition with approved plan and marks it ready for execution.
    """
    try:
        # Get test definition
        result = await db.execute(
            select(TestDefinition).where(TestDefinition.id == test_definition_id)
        )
        test_def = result.scalar_one_or_none()

        if not test_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test definition with id {test_definition_id} not found"
            )

        # Check if plan exists
        if not test_def.ai_generated_plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No AI-generated plan found for this test definition"
            )

        planner = get_autonomous_planner()

        # Apply modifications if provided
        if request.modifications:
            test_def.ai_generated_plan = _apply_plan_modifications(
                test_def.ai_generated_plan,
                request.modifications
            )

        # Update status
        test_def.plan_generation_status = "approved"
        await db.commit()
        await db.refresh(test_def)

        return {
            "plan_id": test_def.ai_generated_plan.get("plan_id"),
            "status": "approved",
            "test_definition_id": test_definition_id,
            "modifications_applied": len(request.modifications)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve plan: {str(e)}"
        )


@router.post("/execution-decision", response_model=ExecutionDecisionResponse)
async def make_execution_decision(
    request: ExecutionDecisionRequest,
    current_user: User = Depends(RequirePermission("execute:test")),
    db: AsyncSession = Depends(get_db)
):
    """
    Make real-time execution decision based on current step result.

    - **current_step**: The step that just executed
    - **page_state**: Current browser/page state
    - **execution_history**: Previous step results

    Returns decision on whether to continue, retry, skip, or abort.
    """
    try:
        planner = get_autonomous_planner()

        decision = await planner.make_execution_decision(
            current_step=request.current_step,
            page_state=request.page_state,
            execution_history=request.execution_history,
            db=db
        )

        return decision

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to make execution decision: {str(e)}"
        )


@router.post("/error-recovery", response_model=ErrorRecoveryResponse)
async def recover_from_error(
    request: ErrorRecoveryRequest,
    current_user: User = Depends(RequirePermission("execute:test")),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate recovery strategy for test execution errors.

    - **error**: Error message or type
    - **context**: Current execution context
    - **remaining_steps**: Steps yet to be executed

    Returns recovery strategy with actions to take.
    """
    try:
        planner = get_autonomous_planner()

        recovery = await planner.recover_from_error(
            error=request.error,
            context=request.context,
            remaining_steps=request.remaining_steps,
            db=db
        )

        return recovery

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recovery strategy: {str(e)}"
        )


async def _associate_plan_with_test_definition(
    db: AsyncSession,
    test_definition_id: int,
    plan: Dict[str, Any]
):
    """Associate generated plan with test definition."""
    result = await db.execute(
        select(TestDefinition).where(TestDefinition.id == test_definition_id)
    )
    test_def = result.scalar_one_or_none()

    if test_def:
        test_def.ai_generated_plan = plan
        test_def.plan_generation_status = "generated"
        await db.commit()


def _apply_plan_modifications(
    plan: Dict[str, Any],
    modifications: List[PlanModification]
) -> Dict[str, Any]:
    """Apply user modifications to generated plan."""
    modified_plan = plan.copy()

    for mod in modifications:
        # Find the step to modify
        for step in modified_plan.get("steps", []):
            if step["step_number"] == mod.step_number:
                if mod.description:
                    step["description"] = mod.description
                if mod.type:
                    step["type"] = mod.type
                if mod.verification:
                    step["verification"] = mod.verification
                break

    return modified_plan
