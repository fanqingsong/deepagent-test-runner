"""
Pydantic Schemas for Schedule Management
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing_extensions import Literal


class ScheduleCreate(BaseModel):
    """Schema for creating a new schedule"""
    name: str = Field(..., min_length=1, max_length=255, description="Schedule name")
    schedule_type: Literal["single", "suite", "tag_filter"] = Field(
        ...,
        description="Type of schedule target"
    )

    # Target configuration (based on schedule_type)
    test_definition_ids: Optional[List[int]] = Field(None, description="List of test definition IDs")
    test_definition_id: Optional[int] = Field(None, description="Test definition ID for single type")
    test_suite_id: Optional[int] = Field(None, description="Test suite ID for suite type")
    tag_filter: Optional[str] = Field(None, description="Tag filter for dynamic grouping")

    # Schedule configuration
    preset_type: Optional[str] = Field(
        None,
        description="Preset schedule type (hourly, daily, weekly, etc.)"
    )
    cron_expression: str = Field(
        ...,
        description="Cron expression for scheduling",
        pattern=r"^[\d\*\/\-,]+\s+[\d\*\/\-,]+\s+[\d\*\/\-,]+\s+[\d\*\/\-,]+\s+[\d\*\/\-,]+$"
    )
    timezone: str = Field(default="UTC", description="Timezone for schedule")

    # Environment and execution configuration
    environment_overrides: dict = Field(
        default_factory=dict,
        description="Environment variable overrides"
    )
    is_active: bool = Field(default=True, description="Whether schedule is active")
    allow_concurrent: bool = Field(default=False, description="Allow concurrent executions")
    max_retries: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Maximum number of retries"
    )
    retry_interval_seconds: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="Seconds between retries"
    )
    run_config_id: Optional[int] = Field(None, description="Run config template ID")

    @model_validator(mode='after')
    def validate_target_config(self):
        """Validate that appropriate target field is provided based on schedule_type"""
        if self.schedule_type == 'single':
            if self.test_definition_id is None:
                raise ValueError('schedule_type=single requires test_definition_id')
        elif self.schedule_type == 'suite':
            if self.test_suite_id is None:
                raise ValueError('schedule_type=suite requires test_suite_id')
        elif self.schedule_type == 'tag_filter':
            if self.tag_filter is None:
                raise ValueError('schedule_type=tag_filter requires tag_filter')
        return self


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    schedule_type: Optional[Literal["single", "suite", "tag_filter"]] = None
    test_definition_id: Optional[int] = None
    test_suite_id: Optional[int] = None
    tag_filter: Optional[str] = None
    preset_type: Optional[str] = None
    cron_expression: Optional[str] = Field(
        None,
        pattern=r"^[\d\*\/\-,]+\s+[\d\*\/\-,]+\s+[\d\*\/\-,]+\s+[\d\*\/\-,]+\s+[\d\*\/\-,]+$"
    )
    timezone: Optional[str] = None
    environment_overrides: Optional[dict] = None
    is_active: Optional[bool] = None
    allow_concurrent: Optional[bool] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_interval_seconds: Optional[int] = Field(None, ge=10, le=3600)
    run_config_id: Optional[int] = None


class ScheduleResponse(BaseModel):
    """Schema for schedule response"""
    id: int
    name: str
    schedule_type: str
    test_definition_ids: List[int]
    test_definition_id: Optional[int]
    test_suite_id: Optional[int]
    tag_filter: Optional[str]
    preset_type: Optional[str]
    cron_expression: str
    timezone: str
    environment_overrides: dict
    is_active: bool
    allow_concurrent: bool
    max_retries: int
    retry_interval_seconds: int
    run_config_id: Optional[int]
    next_run_time: Optional[datetime]
    last_run_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = ConfigDict(from_attributes=True)


class ScheduleToggle(BaseModel):
    """Schema for toggling schedule active status"""
    is_active: bool = Field(..., description="New active status")


class SchedulePreset(BaseModel):
    """Schema for schedule preset option"""
    type: str = Field(..., description="Preset type identifier")
    name: str = Field(..., description="Human-readable name")
    cron: str = Field(..., description="Cron expression")
    description: str = Field(..., description="Description of what this preset does")


class SchedulePresetsResponse(BaseModel):
    """Schema for presets list response"""
    presets: List[SchedulePreset]


class ScheduleTriggerResponse(BaseModel):
    """Schema for manual trigger response"""
    run_id: str = Field(..., description="Generated run ID")
    status: str = Field(..., description="Initial status")
