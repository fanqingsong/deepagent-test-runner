"""
Service Adapter

Provides adapter pattern implementation for gradual migration
to standardized service interfaces.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, List, Callable
from functools import wraps
from datetime import datetime

from app.services.base_service_interface import (
    IService,
    ServiceError,
    ValidationError,
    NotFoundError,
    PermissionError,
    ServiceResponse,
    ListResponse
)

logger = logging.getLogger(__name__)


# ============================================================================
# Service Adapter Base
# ============================================================================

class ServiceAdapter:
    """
    Base adapter for standardizing service interfaces.

    Provides wrapper methods to convert existing service calls
    to standardized format.
    """

    def __init__(self, service: Any, service_name: Optional[str] = None):
        """
        Initialize service adapter.

        Args:
            service: Service instance to adapt
            service_name: Optional service name (defaults to class name)
        """
        self.service = service
        self.service_name = service_name or service.__class__.__name__
        self._adapted_methods: Dict[str, Callable] = {}

    def adapt_method(
        self,
        method_name: str,
        adapter_func: Callable,
        original_method: Optional[Callable] = None
    ) -> None:
        """
        Register a method adapter.

        Args:
            method_name: Name of the method to adapt
            adapter_func: Adapter function that transforms the call
            original_method: Optional original method (defaults to getattr)
        """
        if original_method is None:
            original_method = getattr(self.service, method_name)

        self._adapted_methods[method_name] = adapter_func

        # Create wrapper method
        @wraps(original_method)
        async def wrapper(*args, **kwargs):
            return await adapter_func(original_method, *args, **kwargs)

        setattr(self, method_name, wrapper)

    def __getattr__(self, name: str) -> Any:
        """Proxy undefined attributes to wrapped service."""
        return getattr(self.service, name)


# ============================================================================
# Method Adapter Decorators
# ============================================================================

def adapt_return_none_to_not_found(resource: str = "Resource"):
    """
    Adapt methods that return None to raise NotFoundError.

    Args:
        resource: Resource name for error message
    """
    def decorator(method: Callable) -> Callable:
        @wraps(method)
        async def wrapper(self, *args, **kwargs):
            result = await method(self.service, *args, **kwargs)
            if result is None:
                # Try to extract ID from args
                entity_id = args[1] if len(args) > 1 else kwargs.get('id', 'unknown')
                raise NotFoundError(resource, entity_id)
            return result
        return wrapper
    return decorator


def adapt_tuple_to_dict(method: Callable) -> Callable:
    """
    Adapt methods that return tuples to return dicts.

    Converts (entity, metadata) tuples to standardized dict format.
    """
    @wraps(method)
    async def wrapper(*args, **kwargs):
        result = await method(*args, **kwargs)

        if isinstance(result, tuple):
            # Convert tuple to dict
            return {
                "value": result[0],
                "metadata": result[1] if len(result) > 1 else {},
                "success": True
            }

        return result

    return wrapper


def adapt_error_handling(method: Callable) -> Callable:
    """
    Adapt error handling to use standard exceptions.

    Converts ValueError to ValidationError, etc.
    """
    @wraps(method)
    async def wrapper(*args, **kwargs):
        try:
            return await method(*args, **kwargs)
        except ValueError as e:
            raise ValidationError(str(e)) from e
        except PermissionError as e:
            raise  # Re-raise PermissionError as-is
        except Exception as e:
            logger.error(f"Unexpected error in {method.__name__}: {str(e)}")
            raise ServiceError(f"Operation failed: {str(e)}") from e

    return wrapper


# ============================================================================
# CRUD Service Adapter
# ============================================================================

class CrudServiceAdapter(ServiceAdapter):
    """
    Adapter for CRUD services.

    Standardizes CRUD operations to match ICrudService interface.
    """

    def __init__(self, service: Any, service_name: Optional[str] = None):
        super().__init__(service, service_name)
        self._setup_crud_adapters()

    def _setup_crud_adapters(self):
        """Setup CRUD method adapters if they exist."""
        # Adapt get_by_id to return Optional
        if hasattr(self.service, 'get_by_id'):
            self.adapt_method('get_by_id', self._adapt_get_by_id)

        # Adapt create to validate input
        if hasattr(self.service, 'create'):
            self.adapt_method('create', self._adapt_create)

        # Adapt update to handle not found
        if hasattr(self.service, 'update'):
            self.adapt_method('update', self._adapt_update)

        # Adapt delete to return bool
        if hasattr(self.service, 'delete'):
            self.adapt_method('delete', self._adapt_delete)

    async def _adapt_get_by_id(self, original_method, id: int, **kwargs):
        """Adapt get_by_id to return Optional."""
        try:
            return await original_method(id, **kwargs)
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise

    async def _adapt_create(self, original_method, *args, **kwargs):
        """Adapt create to validate input."""
        # Extract data from args/kwargs
        data = kwargs.get('data') or (args[0] if args else None)
        if not data:
            raise ValidationError("Data is required for creation")

        return await original_method(*args, **kwargs)

    async def _adapt_update(self, original_method, *args, **kwargs):
        """Adapt update to handle not found."""
        try:
            return await original_method(*args, **kwargs)
        except Exception as e:
            if "not found" in str(e).lower():
                entity_id = kwargs.get('id') or (args[1] if len(args) > 1 else 'unknown')
                raise NotFoundError(self.service_name, entity_id) from e
            raise

    async def _adapt_delete(self, original_method, *args, **kwargs):
        """Adapt delete to return bool."""
        try:
            result = await original_method(*args, **kwargs)
            return bool(result)
        except Exception as e:
            if "not found" in str(e).lower():
                entity_id = kwargs.get('id') or (args[1] if len(args) > 1 else 'unknown')
                raise NotFoundError(self.service_name, entity_id) from e
            return False


# ============================================================================
# Execution Service Adapter
# ============================================================================

class ExecutionServiceAdapter(ServiceAdapter):
    """
    Adapter for execution services.

    Standardizes execution operations to match IExecutionService interface.
    """

    def __init__(self, service: Any, service_name: Optional[str] = None):
        super().__init__(service, service_name)
        self._setup_execution_adapters()

    def _setup_execution_adapters(self):
        """Setup execution method adapters if they exist."""
        if hasattr(self.service, 'execute'):
            self.adapt_method('execute', self._adapt_execute_result)

        if hasattr(self.service, 'get_status'):
            # Alias get_status to get_execution_status
            self.adapt_method('get_status', self._adapt_get_status)
            # Create alias
            self.get_execution_status = self.get_status

    async def _adapt_execute_result(self, original_method, *args, **kwargs):
        """
        Adapt execute result to standard format.

        Ensures result contains: task_id, status, result, error, duration_ms, timestamp
        """
        task_id = kwargs.get('task_id') or (args[0] if args else 'unknown')
        start_time = datetime.utcnow()

        try:
            result = await original_method(*args, **kwargs)

            # If result is not a dict, convert it
            if not isinstance(result, dict):
                result = {"result": result}

            # Add standard fields
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            result.setdefault('task_id', task_id)
            result.setdefault('status', 'completed')
            result.setdefault('error', None)
            result.setdefault('duration_ms', duration_ms)
            result.setdefault('timestamp', datetime.utcnow().isoformat())

            return result

        except Exception as e:
            return {
                "task_id": task_id,
                "status": "failed",
                "result": None,
                "error": str(e),
                "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _adapt_get_status(self, original_method, *args, **kwargs):
        """Adapt get_status to standard format."""
        execution_id = kwargs.get('execution_id') or kwargs.get('run_id') or (args[0] if args else 'unknown')

        try:
            status = await original_method(*args, **kwargs)

            # If status is not a dict, convert it
            if not isinstance(status, dict):
                status = {"status": status}

            # Add standard fields
            status.setdefault('execution_id', execution_id)
            status.setdefault('progress', 1.0 if status.get('status') == 'completed' else 0.0)
            status.setdefault('started_at', datetime.utcnow().isoformat())
            status.setdefault('updated_at', datetime.utcnow().isoformat())
            status.setdefault('estimated_completion', None)

            return status

        except Exception as e:
            return {
                "execution_id": execution_id,
                "status": "unknown",
                "progress": 0.0,
                "error": str(e),
                "started_at": None,
                "updated_at": datetime.utcnow().isoformat(),
                "estimated_completion": None
            }


# ============================================================================
# Query Service Adapter
# ============================================================================

class QueryServiceAdapter(ServiceAdapter):
    """
    Adapter for query services.

    Standardizes query operations to match IQueryService interface.
    """

    def __init__(self, service: Any, service_name: Optional[str] = None):
        super().__init__(service, service_name)
        self._setup_query_adapters()

    def _setup_query_adapters(self):
        """Setup query method adapters if they exist."""
        if hasattr(self.service, 'list'):
            self.adapt_method('list', self._adapt_list)

        if hasattr(self.service, 'search'):
            self.adapt_method('search', self._adapt_search)

    async def _adapt_list(self, original_method, *args, **kwargs):
        """
        Adapt list to standard format.

        Ensures consistent parameter names and returns list.
        """
        # Normalize parameters
        params = {
            'skip': kwargs.get('skip', kwargs.get('offset', 0)),
            'limit': kwargs.get('limit', 50),
            'filters': kwargs.get('filters'),
            'sort_by': kwargs.get('sort_by'),
            'sort_order': kwargs.get('sort_order', 'desc')
        }

        result = await original_method(*args, **params)

        # Ensure result is a list
        if not isinstance(result, list):
            result = list(result) if result is not None else []

        return result

    async def _adapt_search(self, original_method, *args, **kwargs):
        """
        Adapt search to standard format.

        Ensures consistent parameter names and returns list.
        """
        # Normalize parameters
        query = kwargs.get('query') or kwargs.get('q') or (args[0] if args else '')
        params = {
            'query': query,
            'skip': kwargs.get('skip', 0),
            'limit': kwargs.get('limit', 50),
            'filters': kwargs.get('filters')
        }

        result = await original_method(**params)

        # Ensure result is a list
        if not isinstance(result, list):
            result = list(result) if result is not None else []

        return result


# ============================================================================
# Health Check Adapter
# ============================================================================

class HealthCheckAdapter(ServiceAdapter):
    """
    Adapter for health check methods.

    Standardizes health check responses across services.
    """

    def __init__(self, service: Any, service_name: Optional[str] = None):
        super().__init__(service, service_name)
        self._setup_health_check()

    def _setup_health_check(self):
        """Setup health check adapter if it exists."""
        if hasattr(self.service, 'health_check'):
            self.adapt_method('health_check', self._adapt_health_check)

    async def _adapt_health_check(self, original_method, *args, **kwargs):
        """
        Adapt health check to standard format.

        Ensures response contains: healthy, status, checks, timestamp
        """
        try:
            result = await original_method(*args, **kwargs)

            # If result is not a dict, convert it
            if not isinstance(result, dict):
                result = {"healthy": bool(result)}

            # Add standard fields
            result.setdefault('healthy', True)
            result.setdefault('status', 'healthy' if result.get('healthy') else 'unhealthy')
            result.setdefault('checks', {})
            result.setdefault('timestamp', datetime.utcnow().isoformat())

            return result

        except Exception as e:
            return {
                "healthy": False,
                "status": "unhealthy",
                "checks": {},
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# ============================================================================
# Universal Service Adapter
# ============================================================================

class UniversalServiceAdapter(
    HealthCheckAdapter,
    CrudServiceAdapter,
    ExecutionServiceAdapter,
    QueryServiceAdapter
):
    """
    Universal adapter that combines all adapters.

    Automatically adapts any service to match standard interfaces.
    """

    def __init__(self, service: Any, service_name: Optional[str] = None):
        """
        Initialize universal adapter.

        Args:
            service: Service instance to adapt
            service_name: Optional service name
        """
        # Initialize all parent adapters
        self.service = service
        self.service_name = service_name or service.__class__.__name__
        self._adapted_methods: Dict[str, Callable] = {}

        # Setup all adapters
        self._setup_health_check()
        self._setup_crud_adapters()
        self._setup_execution_adapters()
        self._setup_query_adapters()


# ============================================================================
# Adapter Factory
# ============================================================================

def create_adapter(
    service: Any,
    adapter_type: str = "universal",
    service_name: Optional[str] = None
) -> ServiceAdapter:
    """
    Create appropriate adapter for a service.

    Args:
        service: Service instance to adapt
        adapter_type: Type of adapter ("universal", "crud", "execution", "query", "health")
        service_name: Optional service name

    Returns:
        Appropriate adapter instance
    """
    adapters = {
        "universal": UniversalServiceAdapter,
        "crud": CrudServiceAdapter,
        "execution": ExecutionServiceAdapter,
        "query": QueryServiceAdapter,
        "health": HealthCheckAdapter
    }

    adapter_class = adapters.get(adapter_type, UniversalServiceAdapter)
    return adapter_class(service, service_name)


# ============================================================================
# Adapter Context Manager
# ============================================================================

class AdapterContext:
    """
    Context manager for temporary service adaptation.

    Usage:
        async with AdapterContext(my_service) as adapted:
            result = await adapted.get_by_id(1)
            # Returns Optional[T] instead of raising NotFoundError
    """

    def __init__(
        self,
        service: Any,
        adapter_type: str = "universal",
        service_name: Optional[str] = None
    ):
        self.service = service
        self.adapter_type = adapter_type
        self.service_name = service_name
        self.adapter = None

    async def __aenter__(self) -> ServiceAdapter:
        """Enter context and create adapter."""
        self.adapter = create_adapter(
            self.service,
            self.adapter_type,
            self.service_name
        )
        return self.adapter

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context and cleanup."""
        self.adapter = None
        return False


# ============================================================================
# Migration Helper
# ============================================================================

class ServiceMigrationHelper:
    """
    Helper for migrating services to standard interfaces.

    Provides utilities to:
    - Analyze current service interfaces
    - Generate migration reports
    - Create adapter instances
    """

    @staticmethod
    def analyze_service(service: Any) -> Dict[str, Any]:
        """
        Analyze a service's current interface.

        Args:
            service: Service instance to analyze

        Returns:
            Analysis report with methods and signatures
        """
        import inspect

        methods = {}
        for name, method in inspect.getmembers(service, predicate=inspect.ismethod):
            if not name.startswith('_'):
                sig = inspect.signature(method)
                methods[name] = {
                    "signature": str(sig),
                    "parameters": list(sig.parameters.keys()),
                    "is_async": inspect.iscoroutinefunction(method)
                }

        return {
            "service_name": service.__class__.__name__,
            "methods": methods,
            "total_methods": len(methods)
        }

    @staticmethod
    def generate_migration_report(
        old_service: Any,
        standard_interface: Any
    ) -> Dict[str, Any]:
        """
        Generate migration report comparing old and new interfaces.

        Args:
            old_service: Current service instance
            standard_interface: Standard interface class

        Returns:
            Migration report with differences and recommendations
        """
        old_analysis = ServiceMigrationHelper.analyze_service(old_service)

        # Get expected methods from interface
        expected_methods = set()
        for base in standard_interface.__mro__:
            if hasattr(base, '__abstractmethods__'):
                expected_methods.update(base.__abstractmethods__)

        current_methods = set(old_analysis["methods"].keys())

        missing = expected_methods - current_methods
        extra = current_methods - expected_methods
        matching = current_methods & expected_methods

        return {
            "service_name": old_analysis["service_name"],
            "matching_methods": list(matching),
            "missing_methods": list(missing),
            "extra_methods": list(extra),
            "migration_required": len(missing) > 0,
            "adapter_recommended": True
        }
