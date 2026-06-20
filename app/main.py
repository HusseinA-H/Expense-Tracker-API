from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.core.exceptions import AppException
from app.core.error_handlers import (
    app_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.core.middleware import LoggingAndRequestIdMiddleware
from app.core.telemetry import instrument_fastapi, setup_telemetry
from app.utils.logging import setup_logging
from app.api.v1.router import api_router
from app.api.health import router as health_router
from app.events.handlers import register_event_handlers

logger = structlog.get_logger("app.main")

_docs_url = "/docs" if settings.OPENAPI_ENABLED else None
_redoc_url = "/redoc" if settings.OPENAPI_ENABLED else None
_openapi_url = "/openapi.json" if settings.OPENAPI_ENABLED else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(log_level="DEBUG" if settings.is_dev else "INFO")
    setup_telemetry("expense-tracker-api")
    logger.info(
        "Starting Expense Tracker API...",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
    )

    register_event_handlers()

    yield

    logger.info("Stopping Expense Tracker API...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-ready expense Tracker API.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

if settings.is_prod or settings.is_staging:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts_list,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

app.add_middleware(LoggingAndRequestIdMiddleware)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(health_router, prefix=f"{settings.API_V1_STR}/health")


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Expense Tracker API.",
        "docs_url": _docs_url,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/api/v1/health", tags=["Health"], include_in_schema=settings.OPENAPI_ENABLED)
async def health_check():
    """Backward-compatible liveness endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}

instrument_fastapi(app)


def _configure_openapi() -> None:
    """Document OAuth2 password flow for Swagger UI (email as username)."""
    if not settings.OPENAPI_ENABLED:
        return

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        from fastapi.openapi.utils import get_openapi

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        openapi_schema["components"]["securitySchemes"]["OAuth2PasswordBearer"] = {
            "type": "oauth2",
            "description": (
                "OAuth2 password grant. Use your account **email** as the username "
                "and your password. Token URL: POST /api/v1/auth/token "
                "(application/x-www-form-urlencoded)."
            ),
            "flows": {
                "password": {
                    "tokenUrl": f"{settings.API_V1_STR}/auth/token",
                    "scopes": {},
                }
            },
        }
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi


_configure_openapi()
