"""
Metrics Decorators

Provides decorators for automatic metrics collection on functions and methods.
Simplifies instrumentation of code for performance monitoring.
"""

import time
import functools
import logging
from typing import Callable, Any, Optional, TypeVar
from contextlib import contextmanager

from app.core.interfaces.metrics_collector_interface import IMetricsCollector

logger = logging.getLogger(__name__)

T = TypeVar('T')


def track_timing(
    operation_name: Optional[str] = None,
    metrics_collector: Optional[IMetricsCollector] = None
):
    """
    Decorator to track function execution time.

    Args:
        operation_name: Custom operation name (default: function qualified name)
        metrics_collector: Custom metrics collector (default: from dependency injection)

    Example:
        >>> from app.core.metrics.metrics_decorators import track_timing
        >>>
        >>> @track_timing("database.user.create")
        >>> async def create_user(user_data):
        >>>     # ... implementation
        >>>     pass

    The decorator works with both sync and async functions.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            # Get operation name
            op_name = operation_name or func.__qualname__

            # Start timing
            start_time = time.perf_counter()

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Record timing if collector available
                if metrics_collector:
                    metrics_collector.record_timing(op_name, duration_ms)
                else:
                    # Try to get from container
                    try:
                        from app.core.container import get_container
                        container = get_container()
                        if hasattr(container, 'metrics_collector'):
                            container.metrics_collector().record_timing(op_name, duration_ms)
                    except Exception:
                        logger.debug(f"Metrics collector not available for {op_name}")

                return result

            except Exception as e:
                # Record error timing
                duration_ms = (time.perf_counter() - start_time) * 1000

                if metrics_collector:
                    metrics_collector.record_timing(op_name, duration_ms)
                    metrics_collector.record_error(op_name, type(e).__name__, str(e))

                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # Get operation name
            op_name = operation_name or func.__qualname__

            # Start timing
            start_time = time.perf_counter()

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Record timing if collector available
                if metrics_collector:
                    metrics_collector.record_timing(op_name, duration_ms)
                else:
                    # Try to get from container
                    try:
                        from app.core.container import get_container
                        container = get_container()
                        if hasattr(container, 'metrics_collector'):
                            container.metrics_collector().record_timing(op_name, duration_ms)
                    except Exception:
                        logger.debug(f"Metrics collector not available for {op_name}")

                return result

            except Exception as e:
                # Record error timing
                duration_ms = (time.perf_counter() - start_time) * 1000

                if metrics_collector:
                    metrics_collector.record_timing(op_name, duration_ms)
                    metrics_collector.record_error(op_name, type(e).__name__, str(e))

                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_errors(
    operation_name: Optional[str] = None,
    metrics_collector: Optional[IMetricsCollector] = None
):
    """
    Decorator to track function errors.

    Args:
        operation_name: Custom operation name (default: function qualified name)
        metrics_collector: Custom metrics collector (default: from dependency injection)

    Example:
        >>> from app.core.metrics.metrics_decorators import track_errors
        >>>
        >>> @track_errors("service.llm.call")
        >>> async def call_llm(prompt):
        >>>     # ... implementation
        >>>     pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            op_name = operation_name or func.__qualname__

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Record error
                if metrics_collector:
                    metrics_collector.record_error(op_name, type(e).__name__, str(e))
                else:
                    # Try to get from container
                    try:
                        from app.core.container import get_container
                        container = get_container()
                        if hasattr(container, 'metrics_collector'):
                            container.metrics_collector().record_error(
                                op_name, type(e).__name__, str(e)
                            )
                    except Exception:
                        logger.debug(f"Metrics collector not available for {op_name}")

                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            op_name = operation_name or func.__qualname__

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Record error
                if metrics_collector:
                    metrics_collector.record_error(op_name, type(e).__name__, str(e))
                else:
                    # Try to get from container
                    try:
                        from app.core.container import get_container
                        container = get_container()
                        if hasattr(container, 'metrics_collector'):
                            container.metrics_collector().record_error(
                                op_name, type(e).__name__, str(e)
                            )
                    except Exception:
                        logger.debug(f"Metrics collector not available for {op_name}")

                raise

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_metrics(
    operation_name: Optional[str] = None,
    metrics_collector: Optional[IMetricsCollector] = None
):
    """
    Decorator to track both timing and errors.

    Combines track_timing and track_errors functionality.

    Args:
        operation_name: Custom operation name (default: function qualified name)
        metrics_collector: Custom metrics collector (default: from dependency injection)

    Example:
        >>> from app.core.metrics.metrics_decorators import track_metrics
        >>>
        >>> @track_metrics("service.execution.create_test_run")
        >>> async def create_test_run(test_definition_id):
        >>>     # ... implementation
        >>>     pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Apply both decorators
        timed_func = track_timing(operation_name, metrics_collector)(func)
        error_tracked_func = track_errors(operation_name, metrics_collector)(timed_func)
        return error_tracked_func

    return decorator


def track_counter(
    metric_name: Optional[str] = None,
    value: int = 1,
    metrics_collector: Optional[IMetricsCollector] = None
):
    """
    Decorator to track function call count.

    Args:
        metric_name: Custom metric name (default: function qualified name + .calls)
        value: Counter increment value (default: 1)
        metrics_collector: Custom metrics collector (default: from dependency injection)

    Example:
        >>> from app.core.metrics.metrics_decorators import track_counter
        >>>
        >>> @track_counter("http.requests.get", 1)
        >>> async def get_test(test_id):
        >>>     # ... implementation
        >>>     pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            # Get metric name
            metric = metric_name or f"{func.__qualname__}.calls"

            # Record counter
            if metrics_collector:
                metrics_collector.record_counter(metric, value)
            else:
                # Try to get from container
                try:
                    from app.core.container import get_container
                    container = get_container()
                    if hasattr(container, 'metrics_collector'):
                        container.metrics_collector().record_counter(metric, value)
                except Exception:
                    logger.debug(f"Metrics collector not available for {metric}")

            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # Get metric name
            metric = metric_name or f"{func.__qualname__}.calls"

            # Record counter
            if metrics_collector:
                metrics_collector.record_counter(metric, value)
            else:
                # Try to get from container
                try:
                    from app.core.container import get_container
                    container = get_container()
                    if hasattr(container, 'metrics_collector'):
                        container.metrics_collector().record_counter(metric, value)
                except Exception:
                    logger.debug(f"Metrics collector not available for {metric}")

            return func(*args, **kwargs)

        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@contextmanager
def track_operation(
    operation_name: str,
    metrics_collector: Optional[IMetricsCollector] = None
):
    """
    Context manager for tracking operation timing and errors.

    Useful for timing code blocks without decorating functions.

    Args:
        operation_name: Operation name to track
        metrics_collector: Custom metrics collector (default: from dependency injection)

    Example:
        >>> from app.core.metrics.metrics_decorators import track_operation
        >>>
        >>> with track_operation("custom.operation"):
        >>>     # ... code to time
        >>>     pass
    """
    start_time = time.perf_counter()

    try:
        yield

    except Exception as e:
        # Record error
        duration_ms = (time.perf_counter() - start_time) * 1000

        if metrics_collector:
            metrics_collector.record_timing(operation_name, duration_ms)
            metrics_collector.record_error(operation_name, type(e).__name__, str(e))
        else:
            # Try to get from container
            try:
                from app.core.container import get_container
                container = get_container()
                if hasattr(container, 'metrics_collector'):
                    collector = container.metrics_collector()
                    collector.record_timing(operation_name, duration_ms)
                    collector.record_error(operation_name, type(e).__name__, str(e))
            except Exception:
                logger.debug(f"Metrics collector not available for {operation_name}")

        raise

    else:
        # Record successful timing
        duration_ms = (time.perf_counter() - start_time) * 1000

        if metrics_collector:
            metrics_collector.record_timing(operation_name, duration_ms)
        else:
            # Try to get from container
            try:
                from app.core.container import get_container
                container = get_container()
                if hasattr(container, 'metrics_collector'):
                    container.metrics_collector().record_timing(operation_name, duration_ms)
            except Exception:
                logger.debug(f"Metrics collector not available for {operation_name}")


# Import asyncio for function type checking
import asyncio
