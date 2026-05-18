from app.core.celery_app import celery_app

# Lazy initialization - instances created when first accessed
_schedule_manager = None
_execution_service = None
_test_case_generator = None


def get_schedule_manager():
    """Get or create ScheduleManager instance"""
    global _schedule_manager
    if _schedule_manager is None:
        from app.services.schedule_manager import ScheduleManager
        from app.core.celery_app import celery_app
        _schedule_manager = ScheduleManager(None, celery_app)
    return _schedule_manager


def get_execution_service():
    """Get or create ExecutionService instance"""
    global _execution_service
    if _execution_service is None:
        from app.services.execution_service import ExecutionService
        _execution_service = ExecutionService()
    return _execution_service


def get_test_case_generator():
    """Get or create TestCaseGenerator instance"""
    global _test_case_generator
    if _test_case_generator is None:
        from app.services.test_case_generator import TestCaseGenerator
        _test_case_generator = TestCaseGenerator()
    return _test_case_generator


# Property-style accessors for backwards compatibility
class ServiceContainer:
    """Container for service instances"""
    @property
    def schedule_manager(self):
        return get_schedule_manager()

    @property
    def execution_service(self):
        return get_execution_service()

    @property
    def test_case_generator(self):
        return get_test_case_generator()


# Global container instance - properties are lazy, no instantiation at import time
services = ServiceContainer()

__all__ = [
    "get_schedule_manager",
    "get_execution_service",
    "get_test_case_generator",
    "services"
]
