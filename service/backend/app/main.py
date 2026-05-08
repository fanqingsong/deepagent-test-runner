"""
Unified Backend Service - FastAPI Application

This service combines test-case-service and scheduler-service into a single
unified backend with a single JWT verification system, RBAC, and database
connection pool.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Lifespan event handler for FastAPI application.
    Manages application startup and shutdown events.
    """
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    # Shutdown
    print(f"Shutting down {settings.APP_NAME}")


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

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix="/api/v1")

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

    return app


app = create_application()
