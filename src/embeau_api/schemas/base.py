"""Base schemas for API responses."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
    )


class ErrorDetail(BaseModel):
    """Error detail schema."""

    code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    success: bool
    data: T | None = None
    error: ErrorDetail | None = None

    @classmethod
    def ok(cls, data: T) -> "ApiResponse[T]":
        """Create a successful response."""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, code: str, message: str) -> "ApiResponse[Any]":
        """Create an error response."""
        return cls(success=False, error=ErrorDetail(code=code, message=message))


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    success: bool = True
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
