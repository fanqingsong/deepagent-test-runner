"""
OpenTelemetry distributed tracing middleware with Jaeger exporter.
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from fastapi import FastAPI
from app.core.config import settings


def setup_tracing(app: FastAPI) -> None:
    """Configure OpenTelemetry tracing with Jaeger exporter."""
    if not settings.JAEGER_ENABLED:
        return

    # Create resource with service name
    resource = Resource(attributes={
        SERVICE_NAME: settings.APP_NAME,
        "service.version": settings.APP_VERSION,
    })

    # Configure tracer provider
    tracer_provider = TracerProvider(resource=resource)
    jaeger_exporter = JaegerExporter(
        agent_host_name=settings.JAEGER_AGENT_HOST,
        agent_port=settings.JAEGER_AGENT_PORT,
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    # Instrument HTTPX (for external API calls)
    HTTPXClientInstrumentor().instrument()

    # Instrument SQLAlchemy (for database queries)
    from app.core.database import engine
    SQLAlchemyInstrumentor().instrument(engine=engine)

    # Log trace setup
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Tracing enabled: Jaeger agent at {settings.JAEGER_AGENT_HOST}:{settings.JAEGER_AGENT_PORT}")
    logger.info(f"Trace sampling rate: {settings.TRACE_SAMPLE_RATE}")
