"""
Pydantic Schemas for AI Test Case Generation
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict


class TestCaseGenerateRequest(BaseModel):
    """Request schema for generating test cases"""
    app_url: str = Field(..., description="Application URL to test")
    app_description: str = Field(..., min_length=10, description="Application description")
    requirements: str = Field(..., min_length=20, description="Test requirements in natural language")
    test_type: str = Field(
        default="functional",
        description="Type of test: functional, ui, api, e2e, performance, security"
    )
    credentials: Optional[Dict[str, str]] = Field(
        None,
        description="Optional test credentials"
    )
    test_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional test data for generation"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags to categorize the test"
    )
    generate_negative_cases: bool = Field(
        default=True,
        description="Whether to generate negative test cases"
    )
    max_steps: int = Field(
        default=10,
        ge=5,
        le=20,
        description="Maximum number of steps to generate"
    )

    @field_validator('test_type')
    @classmethod
    def validate_test_type(cls, v):
        allowed_types = ['functional', 'ui', 'api', 'e2e', 'performance', 'security', 'smoke', 'regression']
        if v not in allowed_types:
            raise ValueError(f'test_type must be one of {", ".join(allowed_types)}')
        return v


class GeneratedTestStep(BaseModel):
    """Generated test step"""
    step_number: int = Field(..., ge=1, description="Step sequence number")
    description: str = Field(..., description="Natural language description of the step")
    type: str = Field(..., description="Action type: navigate, click, input, verify, wait, etc.")
    params: Dict[str, Any] = Field(default_factory=dict, description="Step parameters")
    expected_result: str = Field(..., description="Expected result of this step")


class GeneratedTestCase(BaseModel):
    """Generated test case"""
    name: str = Field(..., description="Test case name")
    description: str = Field(..., description="Test case description")
    test_id: Optional[str] = Field(None, description="Test case ID")
    url: str = Field(..., description="Application URL")
    tags: List[str] = Field(default_factory=list, description="Test tags")
    steps: List[GeneratedTestStep] = Field(..., description="Test steps")
    estimated_duration: Optional[str] = Field(None, description="Estimated execution time")


class TestCaseGenerateResponse(BaseModel):
    """Response schema for test generation"""
    test_definition_id: int = Field(..., description="Created test definition ID")
    test_case: GeneratedTestCase = Field(..., description="Generated test case")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Generation metadata")

    model_config = ConfigDict(from_attributes=True)


class BatchGenerateRequest(BaseModel):
    """Request for generating multiple test cases"""
    app_url: str = Field(..., description="Application base URL")
    app_description: str = Field(..., description="Application description")
    test_requirements: List[Dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="List of test requirement objects"
    )

    @field_validator('test_requirements')
    @classmethod
    def validate_requirements(cls, v):
        for req in v:
            if 'requirements' not in req or 'test_type' not in req:
                raise ValueError('Each requirement must have "requirements" and "test_type" fields')
        return v


class BatchGenerateResponse(BaseModel):
    """Response for batch generation"""
    generated_tests: List[TestCaseGenerateResponse] = Field(..., description="Generated test cases")
    summary: Dict[str, Any] = Field(..., description="Generation summary")
    failed: List[Dict[str, Any]] = Field(default_factory=list, description="Failed generations")


class PromptTemplate(BaseModel):
    """Prompt template for test generation"""
    name: str = Field(..., description="Template name")
    test_type: str = Field(..., description="Test type this template is for")
    description: str = Field(..., description="Template description")
    template: str = Field(..., description="Prompt template with placeholders")
    variables: List[str] = Field(default_factory=list, description="Template variables")


class GenerationOptions(BaseModel):
    """Options for test generation"""
    include_positive_cases: bool = True
    include_negative_cases: bool = True
    include_edge_cases: bool = False
    include_performance_tests: bool = False
    max_steps_per_test: int = 10
    detail_level: str = Field(default="medium", pattern="^(low|medium|high)$")
