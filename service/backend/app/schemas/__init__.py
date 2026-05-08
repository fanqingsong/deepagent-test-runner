# Auth schemas (from auth-service migration)
from app.schemas.auth import (
    RegistrationRequest,
    RegistrationResponse,
    EmailVerificationRequest,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
)
from app.schemas.mfa import (
    MFAVerificationRequest,
    MFASetupResponse,
    MFAEnableRequest,
    MFAEnabledResponse,
    MFADisableRequest,
)
from app.schemas.password import (
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    PasswordChangeRequest,
)
from app.schemas.auth_user import User as AuthUser
from app.schemas.user import Session, SessionsListResponse

# Backend schemas (original)
from app.schemas.test_definition import (
    TestDefinitionCreate,
    TestDefinitionResponse,
    TestDefinitionUpdate,
    TestDefinitionListResponse,
    TestVersionSnapshot,
    TestStepCreate,
    TestStepResponse,
    TestStepUpdate,
)
from app.schemas.test_generation import (
    TestCaseGenerateRequest,
    TestCaseGenerateResponse,
    GeneratedTestStep,
    GeneratedTestCase,
    BatchGenerateRequest,
    BatchGenerateResponse,
)
from app.schemas.schedules import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleToggle,
    SchedulePreset,
    SchedulePresetsResponse,
    ScheduleTriggerResponse,
)
from app.schemas.jobs import (
    JobCreate,
    JobResponse,
    JobStatusResponse,
)
from app.schemas.sso_config import (
    SSOConfigCreate,
    SSOConfigResponse,
    SSOConfigUpdate,
    SSOConfigListResponse,
)
from app.schemas.common import Error, MessageResponse

__all__ = [
    # Auth (from auth-service)
    "RegistrationRequest",
    "RegistrationResponse",
    "EmailVerificationRequest",
    "LoginRequest",
    "LoginResponse",
    "LogoutResponse",
    # MFA
    "MFAVerificationRequest",
    "MFASetupResponse",
    "MFAEnableRequest",
    "MFAEnabledResponse",
    "MFADisableRequest",
    # Password
    "PasswordResetRequest",
    "PasswordResetConfirmRequest",
    "PasswordChangeRequest",
    # User
    "AuthUser",
    "Session",
    "SessionsListResponse",
    # Test Definitions
    "TestDefinitionCreate",
    "TestDefinitionResponse",
    "TestDefinitionUpdate",
    "TestDefinitionListResponse",
    "TestVersionSnapshot",
    "TestStepCreate",
    "TestStepResponse",
    "TestStepUpdate",
    # Test Generation
    "TestCaseGenerateRequest",
    "TestCaseGenerateResponse",
    "GeneratedTestStep",
    "GeneratedTestCase",
    "BatchGenerateRequest",
    "BatchGenerateResponse",
    # Schedules
    "ScheduleCreate",
    "ScheduleResponse",
    "ScheduleUpdate",
    "ScheduleToggle",
    "SchedulePreset",
    "SchedulePresetsResponse",
    "ScheduleTriggerResponse",
    # Jobs
    "JobCreate",
    "JobResponse",
    "JobStatusResponse",
    # SSO Config
    "SSOConfigCreate",
    "SSOConfigResponse",
    "SSOConfigUpdate",
    "SSOConfigListResponse",
    # Common
    "Error",
    "MessageResponse",
]
