from typing import Any, Dict, Optional

class AppException(Exception):
    """Base application exception for all domain-specific errors."""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."
    details: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if message is not None:
            self.message = message
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Exception raised for authentication failures (HTTP 401)."""
    status_code = 401
    error_code = "INVALID_CREDENTIALS"
    message = "Authentication failed."


class AuthorizationError(AppException):
    """Exception raised for unauthorized access (HTTP 403)."""
    status_code = 403
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class NotFoundError(AppException):
    """Exception raised when a resource is not found (HTTP 404)."""
    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"
    message = "The requested resource was not found."


class ConflictError(AppException):
    """Exception raised for data conflicts, e.g., duplicates (HTTP 409)."""
    status_code = 409
    error_code = "CONFLICT"
    message = "A conflict occurred with the current state of the resource."


class ValidationError(AppException):
    """Exception raised for business validation failures (HTTP 422)."""
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Validation failed for the request parameters."


class RateLimitError(AppException):
    """Exception raised when API rate limit is exceeded (HTTP 429)."""
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Rate limit exceeded. Please try again later."


class InternalError(AppException):
    """Exception raised for unexpected internal errors (HTTP 500)."""
    status_code = 500
    error_code = "INTERNAL_ERROR"
    message = "An internal server error occurred."
