"""Shared Pydantic schemas: pagination, generic response wrappers."""

from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list response."""
    items: list[T]
    total: int
    skip: int
    limit: int


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


class SuccessResponse(BaseModel):
    """Generic success response for actions."""
    success: bool = True
    message: str = ""


class ErrorResponse(BaseModel):
    """Standard error envelope."""
    error: str
    message: str


class TimestampMixin(BaseModel):
    """Mixin that adds created_at / updated_at fields."""
    created_at: datetime
    updated_at: datetime
