import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import settings

logger = structlog.get_logger("app.telemetry")

_telemetry_initialized = False


def setup_telemetry(service_name: str) -> None:
    """Configure OpenTelemetry tracing and auto-instrumentation."""
    global _telemetry_initialized
    if _telemetry_initialized or settings.is_test:
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "3.0.0",
            "deployment.environment": settings.ENVIRONMENT,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_ENDPOINT,
        insecure=True,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    CeleryInstrumentor().instrument()
    RedisInstrumentor().instrument()

    from app.db.session import engine, read_engine

    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine,
        enable_commenter=True,
    )
    SQLAlchemyInstrumentor().instrument(
        engine=read_engine.sync_engine,
        enable_commenter=True,
    )

    _telemetry_initialized = True
    logger.info(
        "OpenTelemetry initialized",
        service_name=service_name,
        exporter_endpoint=settings.OTEL_EXPORTER_ENDPOINT,
    )


def instrument_fastapi(app) -> None:
    """Attach FastAPI auto-instrumentation to the application."""
    if settings.is_test:
        return
    setup_telemetry("expense-tracker-api")
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/api/v1/health,/",
    )
