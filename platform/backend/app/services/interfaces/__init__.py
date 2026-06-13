"""
Service Interfaces Package

This package contains interfaces for all major services, following the
Dependency Inversion Principle of SOLID design.

High-level modules should not depend on low-level modules. Both should
depend on abstractions (interfaces).

Available Interfaces:
- IExecutionService: Test execution service interface
- IAnalyticsService: Analytics and dashboard service interface
- IScriptValidationService: Script validation service interface
- ISuiteService: Suite execution service interface
"""

from app.services.interfaces.execution_service_interface import IExecutionService
from app.services.interfaces.analytics_service_interface import IAnalyticsService
from app.services.interfaces.script_validation_service_interface import IScriptValidationService
from app.services.interfaces.suite_service_interface import ISuiteService

__all__ = [
    "IExecutionService",
    "IAnalyticsService",
    "IScriptValidationService",
    "ISuiteService",
]
