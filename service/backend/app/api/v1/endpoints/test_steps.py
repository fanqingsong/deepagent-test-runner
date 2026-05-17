"""
Test Steps API Endpoints

CRUD operations for test steps within test definitions.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import TestStep, TestDefinition
from app.schemas import TestStepCreate, TestStepResponse, TestStepUpdate, TestStepsReplaceRequest
from app.services.unified_auth import verify_token

router = APIRouter()


@router.get("/test-definition/{test_definition_id}", response_model=List[TestStepResponse])
async def list_test_steps(
    test_definition_id: int,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    List all test steps for a test definition.

    - **test_definition_id**: Test definition internal ID
    """
    # Verify test definition exists
    result = await db.execute(
        select(TestDefinition).where(TestDefinition.id == test_definition_id)
    )
    test_def = result.scalar_one_or_none()

    if not test_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test definition with id {test_definition_id} not found"
        )

    # Check permission: regular users can only view test steps for their own test definitions
    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local" and current_user.get("sub"):
        if test_def.created_by != int(current_user["sub"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view test steps for this test definition"
            )

    # Get test steps
    result = await db.execute(
        select(TestStep)
        .where(TestStep.test_definition_id == test_definition_id)
        .order_by(TestStep.step_number)
    )
    test_steps = result.scalars().all()

    return test_steps


@router.post("/test-definition/{test_definition_id}", response_model=TestStepResponse, status_code=status.HTTP_201_CREATED)
async def create_test_step(
    test_definition_id: int,
    step: TestStepCreate,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Add a test step to a test definition.

    - **test_definition_id**: Test definition internal ID
    - **step_number**: Step order number
    - **description**: Step description
    - **type**: Step type (e.g., 'navigate', 'click', 'fill')
    - **params**: Step parameters
    - **expected_result**: Expected result
    """
    # Verify test definition exists
    result = await db.execute(
        select(TestDefinition).where(TestDefinition.id == test_definition_id)
    )
    test_def = result.scalar_one_or_none()

    if not test_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test definition with id {test_definition_id} not found"
        )

    # Check permission: regular users can only add test steps to their own test definitions
    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local" and current_user.get("sub"):
        if test_def.created_by != int(current_user["sub"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to add test steps to this test definition"
            )

    # Check if step_number already exists
    existing = await db.execute(
        select(TestStep).where(
            TestStep.test_definition_id == test_definition_id,
            TestStep.step_number == step.step_number
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step number {step.step_number} already exists for this test definition"
        )

    # Create test step
    db_step = TestStep(
        test_definition_id=test_definition_id,
        step_number=step.step_number,
        description=step.description,
        type=step.type,
        params=step.params,
        expected_result=step.expected_result
    )

    db.add(db_step)
    await db.commit()
    await db.refresh(db_step)

    return db_step


@router.put(
    "/test-definition/{test_definition_id}",
    response_model=List[TestStepResponse],
)
async def replace_test_steps(
    test_definition_id: int,
    payload: TestStepsReplaceRequest,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db),
):
    """
    Replace ALL test steps for a test definition (full overwrite).

    This endpoint exists to avoid N+1 requests from the frontend.

    - **test_definition_id**: Test definition internal ID
    """
    result = await db.execute(
        select(TestDefinition).where(TestDefinition.id == test_definition_id)
    )
    test_def = result.scalar_one_or_none()
    if not test_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test definition with id {test_definition_id} not found",
        )

    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local" and current_user.get("sub"):
        if test_def.created_by != int(current_user["sub"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update test steps for this test definition",
            )

    # Delete existing steps, then insert new ones (step_number = array order, 1-based)
    await db.execute(delete(TestStep).where(TestStep.test_definition_id == test_definition_id))
    new_steps = [
        TestStep(
            test_definition_id=test_definition_id,
            step_number=idx + 1,
            description=s.description,
            type=s.type,
            params=s.params,
            expected_result=s.expected_result,
        )
        for idx, s in enumerate(payload.test_steps)
    ]
    if new_steps:
        db.add_all(new_steps)
    await db.commit()

    # Return steps in order
    result = await db.execute(
        select(TestStep)
        .where(TestStep.test_definition_id == test_definition_id)
        .order_by(TestStep.step_number)
    )
    return result.scalars().all()


@router.put("/{step_id}", response_model=TestStepResponse)
async def update_test_step(
    step_id: int,
    step_update: TestStepUpdate,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Update a test step.

    - **step_id**: Test step internal ID
    """
    # Get existing step
    result = await db.execute(
        select(TestStep)
        .join(TestDefinition, TestStep.test_definition_id == TestDefinition.id)
        .where(TestStep.id == step_id)
    )
    step = result.scalar_one_or_none()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test step with id {step_id} not found"
        )

    # Get test definition for permission check
    result = await db.execute(
        select(TestDefinition).where(TestDefinition.id == step.test_definition_id)
    )
    test_def = result.scalar_one_or_none()

    # Check permission: regular users can only update test steps for their own test definitions
    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local" and current_user.get("sub"):
        if test_def.created_by != int(current_user["sub"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this test step"
            )

    # Update fields
    update_data = step_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(step, field, value)

    await db.commit()
    await db.refresh(step)

    return step


@router.delete("/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_step(
    step_id: int,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a test step.

    - **step_id**: Test step internal ID
    """
    # Get existing step
    result = await db.execute(
        select(TestStep)
        .join(TestDefinition, TestStep.test_definition_id == TestDefinition.id)
        .where(TestStep.id == step_id)
    )
    step = result.scalar_one_or_none()

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test step with id {step_id} not found"
        )

    # Get test definition for permission check
    result = await db.execute(
        select(TestDefinition).where(TestDefinition.id == step.test_definition_id)
    )
    test_def = result.scalar_one_or_none()

    # Check permission: regular users can only delete test steps for their own test definitions
    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local" and current_user.get("sub"):
        if test_def.created_by != int(current_user["sub"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this test step"
            )

    await db.delete(step)
    await db.commit()

    return None
