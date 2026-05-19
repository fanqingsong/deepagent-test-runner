"""
Test Definitions API Endpoints

CRUD operations for test case definitions.
"""

from typing import List, Optional

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import TestDefinition, TestStep, TestVersion, User
from app.schemas import (
    TestDefinitionCreate,
    TestDefinitionResponse,
    TestDefinitionUpdate,
    TestDefinitionListResponse,
    TestVersionSnapshot,
)
from app.services.unified_auth import verify_token
from app.services.regression_service import RegressionService

router = APIRouter()


@router.get("/", response_model=TestDefinitionListResponse)
async def list_test_definitions(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=500, description="Number of items to return"),
    search: Optional[str] = Query(None, description="Search in name, description, or test_id"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    List all test definitions with pagination and filtering.

    Admin users see all test definitions, regular users only see their own.

    - **skip**: Number of items to skip (for pagination)
    - **limit**: Number of items to return (max 500)
    - **search**: Search term for name, description, or test_id
    - **tags**: Filter by tags (comma-separated)
    - **is_active**: Filter by active status
    """
    filters = []

    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local":
        filters.append(TestDefinition.created_by == int(current_user["sub"]))

    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                TestDefinition.name.ilike(search_pattern),
                TestDefinition.description.ilike(search_pattern),
                TestDefinition.test_id.ilike(search_pattern),
            )
        )

    if tags:
        filters.append(TestDefinition.tags.overlap(tags))

    if is_active is not None:
        filters.append(TestDefinition.is_active == is_active)

    count_query = select(func.count()).select_from(TestDefinition)
    if filters:
        count_query = count_query.where(*filters)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = select(TestDefinition)
    if filters:
        query = query.where(*filters)
    query = query.order_by(TestDefinition.created_at.desc()).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query.options(selectinload(TestDefinition.test_steps)))
    test_definitions = result.scalars().all()

    # Calculate pagination metadata
    page = skip // limit + 1
    total_pages = (total + limit - 1) // limit

    return TestDefinitionListResponse(
        items=test_definitions,
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages
    )


@router.post("/", response_model=TestDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_test_definition(
    test_def: TestDefinitionCreate,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new test definition.

    - **name**: Test name
    - **description**: Test description
    - **test_id**: Unique test identifier
    - **url**: Base URL for test
    - **environment**: Environment variables
    - **tags**: Test tags
    - **test_steps**: List of test steps
    """
    # Check if test_id already exists
    existing = await db.execute(
        select(TestDefinition).where(TestDefinition.test_id == test_def.test_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Test definition with test_id '{test_def.test_id}' already exists"
        )

    # Get user ID from token (for development, allow None when unauthenticated)
    user_id = None
    if current_user.get("provider") == "local" and current_user.get("sub"):
        try:
            user_id = int(current_user["sub"])
        except (ValueError, TypeError):
            user_id = None

    # Create test definition
    db_test_def = TestDefinition(
        name=test_def.name,
        description=test_def.description,
        test_id=test_def.test_id,
        url=test_def.url,
        environment=test_def.environment,
        tags=test_def.tags,
        created_by=user_id,
        test_goal=test_def.test_goal,
        test_context=test_def.test_context,
    )

    # Add test steps
    for step_data in test_def.test_steps:
        step = TestStep(
            step_number=step_data.step_number,
            description=step_data.description,
            type=step_data.type,
            params=step_data.params,
            expected_result=step_data.expected_result
        )
        db_test_def.test_steps.append(step)

    db.add(db_test_def)
    await db.commit()
    await db.refresh(db_test_def)

    # Load test steps for response
    result = await db.execute(
        select(TestDefinition)
        .options(selectinload(TestDefinition.test_steps))
        .where(TestDefinition.id == db_test_def.id)
    )
    return result.scalar_one()


class RegressionSaveRequest(BaseModel):
    """Request body for saving a passed run as a regression test."""
    run_id: str = Field(..., min_length=1, description="Run ID of the passed test run")
    user_id: int = Field(..., description="ID of the user creating the regression test")


@router.get("/regression", response_model=TestDefinitionListResponse)
async def list_regression_tests(
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    List all regression test definitions.

    Returns all test definitions where is_regression is True,
    ordered by creation date (newest first).
    """
    regression_service = RegressionService()

    items = await regression_service.list_regression_tests(db=db)

    total = len(items)
    return TestDefinitionListResponse(
        items=items,
        total=total,
        page=1,
        page_size=total,
        total_pages=1,
    )


@router.post("/regression/save", response_model=TestDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def save_regression_test(
    request: RegressionSaveRequest,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Save a passed test run as a reusable regression test definition.

    Creates a new test definition based on the original test, marked as a
    regression test, with steps derived from the passing test cases.

    - **run_id**: The string run identifier of the passed test run
    - **user_id**: ID of the user creating the regression test
    """
    regression_service = RegressionService()

    try:
        new_definition = await regression_service.save_as_regression(
            db=db,
            run_id=request.run_id,
            user_id=request.user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return new_definition


@router.get("/{test_id}", response_model=TestDefinitionResponse)
async def get_test_definition(
    test_id: str,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific test definition by test_id.

    - **test_id**: Unique test identifier
    """
    result = await db.execute(
        select(TestDefinition)
        .options(selectinload(TestDefinition.test_steps))
        .where(TestDefinition.test_id == test_id)
    )
    test_def = result.scalar_one_or_none()

    if not test_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test definition with test_id '{test_id}' not found"
        )

    # Check permission: regular users can only view their own test definitions
    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local":
        if test_def.created_by != int(current_user["sub"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this test definition"
            )

    return test_def


@router.put("/{test_id}", response_model=TestDefinitionResponse)
async def update_test_definition(
    test_id: str,
    test_def_update: TestDefinitionUpdate,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Update a test definition.

    Creates a version snapshot before updating.

    - **test_id**: Unique test identifier
    - **name**: Updated test name
    - **description**: Updated test description
    - **url**: Updated base URL
    - **environment**: Updated environment variables
    - **tags**: Updated test tags
    - **is_active**: Updated active status
    """
    # Get existing test definition
    result = await db.execute(
        select(TestDefinition)
        .options(selectinload(TestDefinition.test_steps))
        .where(TestDefinition.test_id == test_id)
    )
    test_def = result.scalar_one_or_none()

    if not test_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test definition with test_id '{test_id}' not found"
        )

    # Check permission: regular users can only update their own test definitions
    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local":
        if test_def.created_by != int(current_user["sub"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this test definition"
            )

    # Get user ID for version tracking (convert to string for database)
    user_id_str = str(current_user["sub"]) if current_user.get("provider") == "local" else "system"

    # Create version snapshot
    snapshot_data = TestDefinitionResponse.model_validate(test_def).model_dump(mode='json')
    version = TestVersion(
        test_definition_id=test_def.id,
        version=test_def.version,
        snapshot=snapshot_data,
        change_description="Update before modification",
        created_by=user_id_str
    )
    db.add(version)

    # Update fields
    update_data = test_def_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(test_def, field, value)

    # Increment version
    test_def.version += 1

    await db.commit()
    await db.refresh(test_def)

    # Reload with test steps
    result = await db.execute(
        select(TestDefinition)
        .options(selectinload(TestDefinition.test_steps))
        .where(TestDefinition.id == test_def.id)
    )
    return result.scalar_one()


@router.delete("/{test_id}", response_model=TestDefinitionResponse)
async def delete_test_definition(
    test_id: str,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete a test definition (sets is_active=False).

    - **test_id**: Unique test identifier
    """
    # Get existing test definition
    result = await db.execute(
        select(TestDefinition)
        .options(selectinload(TestDefinition.test_steps))
        .where(TestDefinition.test_id == test_id)
    )
    test_def = result.scalar_one_or_none()

    if not test_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test definition with test_id '{test_id}' not found"
        )

    # Check permission: regular users can only delete their own test definitions
    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local":
        if test_def.created_by != int(current_user["sub"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this test definition"
            )

    # Soft delete
    test_def.is_active = False
    await db.commit()
    await db.refresh(test_def)

    return test_def


@router.get("/{test_id}/versions", response_model=List[TestVersionSnapshot])
async def list_test_definition_versions(
    test_id: str,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    List all versions of a test definition.

    - **test_id**: Unique test identifier
    """
    # Get test definition
    result = await db.execute(
        select(TestDefinition).where(TestDefinition.test_id == test_id)
    )
    test_def = result.scalar_one_or_none()

    if not test_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test definition with test_id '{test_id}' not found"
        )

    # Check permission: regular users can only view versions of their own test definitions
    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local":
        if test_def.created_by != int(current_user["sub"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view versions of this test definition"
            )

    # Get versions
    result = await db.execute(
        select(TestVersion)
        .where(TestVersion.test_definition_id == test_def.id)
        .order_by(TestVersion.version.desc())
    )
    versions = result.scalars().all()

    return versions


# ---------------------------------------------------------------------------
# Regression Test Endpoints (kept for backwards compat — see top of file for
# the actual route definitions that must come before /{test_id})
# ---------------------------------------------------------------------------
