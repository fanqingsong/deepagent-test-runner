"""
Unified Backend Service - FastAPI Application

This service combines test-case-service and scheduler-service into a single
unified backend with a single JWT verification system, RBAC, and database
connection pool.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.observability import setup_observability
from app.api.v1.endpoints.browser_stream import browser_stream_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Lifespan event handler for FastAPI application.
    Manages application startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    from app.core.rbac_seed import ensure_rbac_seeded
    await ensure_rbac_seeded()

    yield
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Unified Backend Service for Test Management and Scheduling",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Setup observability FIRST (before CORS)
    setup_observability(app)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        max_age=600,
    )

    # Include API router
    app.include_router(api_router, prefix="/api/v1")

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        body = await request.body()
        logger.error(f"Validation error on {request.method} {request.url}: {exc.errors()} | body={body.decode()[:500]}")
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    # Include authentication routers
    from app.api.v1.endpoints import (
        auth,
        mfa,
        password,
        sessions,
        admin
    )

    app.include_router(auth.router, prefix="/api/v1/auth")
    app.include_router(mfa.router, prefix="/api/v1/auth/mfa")
    app.include_router(password.router, prefix="/api/v1/auth/password")
    app.include_router(sessions.router, prefix="/api/v1/auth/sessions")
    app.include_router(admin.router, prefix="/api/v1/admin")

    # Include feature routers
    from app.api.v1.endpoints import (
        users,
        roles,
    )

    app.include_router(users.router, prefix="/api/v1/users")
    app.include_router(roles.router, prefix="/api/v1/roles")

    @app.get("/")
    async def root():
        """Root endpoint with service information."""
        return {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running"
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    # WebSocket endpoint for live browser stream
    app.websocket("/ws/browser-stream/{job_id}")(browser_stream_handler)

    return app


app = create_application()
