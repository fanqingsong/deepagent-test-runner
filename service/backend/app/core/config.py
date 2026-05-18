"""
Application Configuration

Uses pydantic-settings for environment-based configuration.
All settings can be overridden via environment variables.
"""

import re
from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET_DEFAULTS = frozenset({
    "changeme-in-production",
    "changeme",
    "your-jwt-secret-key-change-this-in-production",
    "your-jwt-secret-key",
    "your-secret-key",
    "secret",
})

_WEAK_SECRET_PATTERNS = re.compile(
    r"changeme|secret|password|1234|your.*secret|jwt.*key",
    re.IGNORECASE,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = Field(default="Test Case Service", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8001, description="Server port")
    FRONTEND_BASE_URL: str = Field(
        default="http://localhost:8080",
        description="Public frontend base URL for email links and redirects",
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://cc_test_user:changeme@localhost:5432/claude_code_tests",
        description="PostgreSQL database URL"
    )

    # Security
    SECRET_KEY: str = Field(
        default="changeme-in-production",
        description="Secret key for JWT token signing"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )

    # Authentication Service Settings
    JWT_SECRET_KEY: str = Field(
        default="your-jwt-secret-key-change-this-in-production",
        description="Secret key for auth JWT tokens"
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        description="Auth access token expiration time in minutes"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        description="Auth refresh token expiration time in days"
    )

    # SMTP Configuration (for email verification)
    SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USER: str = Field(default="", description="SMTP username")
    SMTP_PASSWORD: str = Field(default="", description="SMTP password")
    EMAIL_FROM: str = Field(
        default="noreply@example.com",
        description="From email address for sent emails"
    )

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REDIS_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Redis URL for rate limiting"
    )

    # Session Management
    MAX_CONCURRENT_SESSIONS: int = Field(
        default=5,
        description="Maximum concurrent sessions per user"
    )
    SESSION_EXPIRE_HOURS: int = Field(
        default=24,
        description="Session expiration time in hours"
    )
    SESSION_REMEMBER_ME_DAYS: int = Field(
        default=30,
        description="Remember-me session expiration time in days"
    )

    # MFA Configuration
    MFA_TOTP_ISSUER: str = Field(
        default="CC-Test-Runner",
        description="TOTP issuer name"
    )
    MFA_RECOVERY_CODE_COUNT: int = Field(
        default=10,
        description="Number of MFA recovery codes"
    )

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://localhost:8013"],
        description="Allowed CORS origins"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(",")]
        return v

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for caching and Celery"
    )

    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )

    # Anthropic API
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Anthropic API key for Claude"
    )
    ANTHROPIC_BASE_URL: str = Field(
        default="https://api.anthropic.com",
        description="Anthropic API base URL"
    )
    ANTHROPIC_MODEL: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Anthropic model to use"
    )
    API_TIMEOUT_MS: int = Field(
        default=300000,
        description="API timeout in milliseconds"
    )

    # Playwright
    PLAYWRIGHT_HEADLESS: bool = Field(
        default=True,
        description="Run Playwright in headless mode"
    )
    TEST_TIMEOUT: int = Field(
        default=30000,
        description="Test execution timeout in milliseconds"
    )
    SCREENSHOT_DIR: str = Field(
        default="/tmp/screenshots",
        description="Directory to store test screenshots"
    )

    # Observability - Prometheus
    PROMETHEUS_PORT: int = Field(default=9090, description="Prometheus metrics port")
    PROMETHEUS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")

    # Observability - Loki
    LOKI_ENABLED: bool = Field(default=False, description="Enable Loki logging")
    LOKI_ENDPOINT: str = Field(
        default="http://loki:3100/loki/api/v1/push",
        description="Loki push endpoint"
    )

    # Observability - Jaeger
    JAEGER_ENABLED: bool = Field(default=False, description="Enable Jaeger tracing")
    JAEGER_AGENT_HOST: str = Field(default="jaeger", description="Jaeger agent hostname")
    JAEGER_AGENT_PORT: int = Field(default=6831, description="Jaeger agent port")
    TRACE_SAMPLE_RATE: float = Field(
        default=0.1,
        description="Trace sampling rate (0.0-1.0)"
    )

    # Observability - Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json or text)")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Reject default/weak secrets when not in debug mode."""
        if self.DEBUG:
            return self
        for name, value in (
            ("SECRET_KEY", self.SECRET_KEY),
            ("JWT_SECRET_KEY", self.JWT_SECRET_KEY),
        ):
            if not value or value in _INSECURE_SECRET_DEFAULTS or len(value) < 32:
                raise ValueError(
                    f"{name} must be set to a secure value (>= 32 chars) when DEBUG=false"
                )
            if _WEAK_SECRET_PATTERNS.search(value):
                raise ValueError(
                    f"{name} contains a weak/placeholder pattern — generate a random secret"
                )
            if len(set(value)) < 16:
                raise ValueError(
                    f"{name} has low entropy (< 16 unique chars) — use a more random string"
                )
        return self


# Global settings instance
settings = Settings()
