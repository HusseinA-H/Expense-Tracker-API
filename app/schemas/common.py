from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for paginated resource responses."""

    items: List[T]
    total: int
    page: int
    size: int
    pages: int


class ErrorDetails(BaseModel):
    """Schema representing structured error details."""

    loc: Optional[List[Any]] = None
    msg: Optional[str] = None
    type: Optional[str] = None


class ErrorResponseContent(BaseModel):
    """Schema representing error response body content."""

    code: str
    message: str
    details: Optional[Any] = None
    request_id: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Standardized error wrapper schema."""

    error: ErrorResponseContent
