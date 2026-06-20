from datetime import datetime, timezone

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException

logger = structlog.get_logger("app.errors")


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all custom application exceptions and format them per the spec."""
    request_id = structlog.contextvars.get_contextvars().get("request_id", "unknown")

    error_content = {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }

    logger.warning(
        "Application error occurred",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=request_id,
    )

    return JSONResponse(status_code=exc.status_code, content=error_content)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Transform Pydantic validation errors into standard error format."""
    request_id = structlog.contextvars.get_contextvars().get("request_id", "unknown")

    details = []
    for err in exc.errors():
        details.append(
            {"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")}
        )

    error_content = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Validation failed for the request parameters.",
            "details": details,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }

    logger.warning("Validation error occurred", details=details, request_id=request_id)

    return JSONResponse(status_code=422, content=error_content)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: log stack trace, return 500 with request_id."""
    request_id = structlog.contextvars.get_contextvars().get("request_id", "unknown")

    error_content = {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected server error occurred.",
            "details": None,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }

    logger.exception("Unhandled server error", request_id=request_id, exc_info=exc)

    return JSONResponse(status_code=500, content=error_content)
