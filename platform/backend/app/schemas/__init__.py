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
    TestStepsReplaceRequest,
)
from app.schemas.test_generation import (
    TestCaseGenerateRequest,
    TestCaseGenerateResponse,
    GeneratedTestStep,
    GeneratedTestCase,
    BatchGenerateRequest,
    BatchGenerateResponse,
)
from app.schemas.jobs import (
    JobCreate,
    JobResponse,
    JobStatusResponse,
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
    "TestStepsReplaceRequest",
    # Test Generation
    "TestCaseGenerateRequest",
    "TestCaseGenerateResponse",
    "GeneratedTestStep",
    "GeneratedTestCase",
    "BatchGenerateRequest",
    "BatchGenerateResponse",
    # Jobs
    "JobCreate",
    "JobResponse",
    "JobStatusResponse",
    # Common
    "Error",
    "MessageResponse",
]
