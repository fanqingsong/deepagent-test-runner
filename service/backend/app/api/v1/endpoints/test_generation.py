"""
Test Generation API Endpoints

AI-powered test case generation from natural language requirements.
"""

from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.test_generation import (
    TestCaseGenerateRequest,
    TestCaseGenerateResponse,
    BatchGenerateRequest,
    BatchGenerateResponse,
    PromptTemplate,
    GenerationOptions
)
from app.services import get_test_case_generator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=TestCaseGenerateResponse, status_code=status.HTTP_201_CREATED)
async def generate_test_case(
    request: TestCaseGenerateRequest,
    current_user: User = Depends(RequirePermission("create:test")),
):
    """
    Generate a test case from natural language requirements.

    - **app_url**: Application URL to test
    - **app_description**: Detailed application description
    - **requirements**: Test requirements in natural language
    - **test_type**: Type of test (functional, ui, api, e2e, etc.)
    - **credentials**: Optional test credentials
    - **test_data**: Optional test data
    - **tags**: Tags for categorization
    - **generate_negative_cases**: Include negative test scenarios
    - **max_steps**: Maximum number of steps (5-20)

    Returns:
        Generated test case with steps saved to database
    """
    try:
        result = await get_test_case_generator().generate_test_case(request)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating test case: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test case: {str(e)}"
        )


@router.post("/generate-batch", response_model=BatchGenerateResponse)
async def generate_test_cases_batch(
    batch_request: BatchGenerateRequest,
    current_user: User = Depends(RequirePermission("create:test")),
):
    """
    Generate multiple test cases in batch.

    - **app_url**: Application base URL
    - **app_description**: Application description
    - **test_requirements**: List of requirement objects

    Each requirement object should contain:
        - requirements: Test requirements text
        - test_type: Type of test
        - credentials: Optional credentials
        - tags: Optional tags

    Returns:
        Summary of generated test cases and any failures
    """
    try:
        # Convert batch request to list of individual requests
        requests = []
        for req in batch_request.test_requirements:
            request = TestCaseGenerateRequest(
                app_url=batch_request.app_url,
                app_description=batch_request.app_description,
                requirements=req["requirements"],
                test_type=req.get("test_type", "functional"),
                credentials=req.get("credentials"),
                test_data=req.get("test_data"),
                tags=req.get("tags", [])
            )
            requests.append(request)

        result = await get_test_case_generator().generate_batch(requests)

        return BatchGenerateResponse(
            generated_tests=result["generated_tests"],
            summary=result["summary"],
            failed=result["failed"]
        )

    except Exception as e:
        logger.error(f"Error in batch generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch generation failed: {str(e)}"
        )


@router.get("/templates", response_model=List[PromptTemplate])
async def get_prompt_templates(
    current_user: User = Depends(get_current_user),
):
    """
    Get available prompt templates for different test types.

    Returns:
        List of prompt templates with their descriptions
    """
    templates = get_test_case_generator()._get_templates()
    return list(templates.values())


@router.get("/templates/{test_type}", response_model=PromptTemplate)
async def get_prompt_template(
    test_type: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific prompt template by test type.

    - **test_type**: Type of test (functional, ui, api, e2e)

    Returns:
        Prompt template for the specified test type
    """
    try:
        template = get_test_case_generator().get_prompt_template(test_type)
        return template
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No template found for test type: {test_type}"
        )


@router.post("/options", response_model=GenerationOptions)
async def get_generation_options(
    options: GenerationOptions,
    current_user: User = Depends(get_current_user),
):
    """
    Validate and return generation options.

    - **include_positive_cases**: Include happy path tests
    - **include_negative_cases**: Include negative scenarios
    - **include_edge_cases**: Include boundary tests
    - **include_performance_tests**: Include performance tests
    - **max_steps_per_test**: Maximum steps per test case
    - **detail_level**: Level of detail (low, medium, high)

    Returns:
        Validated generation options
    """
    return options


@router.get("/health")
async def health_check():
    """
    Health check endpoint for test generation service.

    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "service": "test-generation",
        "ai_enabled": bool(get_test_case_generator().llm_api_key)
    }
