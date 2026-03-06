"""Custom exceptions and global exception handlers for the application."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# Base exceptions
# ---------------------------------------------------------------------------

class AppException(Exception):
    """Base exception for business logic errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundException(AppException):
    """Raised when a requested entity does not exist."""

    def __init__(self, entity: str, entity_id: str | int) -> None:
        super().__init__(
            message=f"{entity} con id '{entity_id}' no encontrado",
            code="NOT_FOUND",
        )


class ConflictException(AppException):
    """Raised when an operation conflicts with existing state."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="CONFLICT")


class ValidationException(AppException):
    """Raised when business validation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR")


class UnauthorizedException(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "No autorizado") -> None:
        super().__init__(message=message, code="UNAUTHORIZED")


class ForbiddenException(AppException):
    """Raised when the user lacks required permissions."""

    def __init__(self, message: str = "Acceso denegado") -> None:
        super().__init__(message=message, code="FORBIDDEN")


class BadRequestException(AppException):
    """Raised for generic bad-request scenarios."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="BAD_REQUEST")


# ---------------------------------------------------------------------------
# Status code mapping
# ---------------------------------------------------------------------------

_STATUS_MAP: dict[str, int] = {
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "VALIDATION_ERROR": 422,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "BAD_REQUEST": 400,
    "INTERNAL_ERROR": 500,
}


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app instance."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        status_code = _STATUS_MAP.get(exc.code, 500)
        return JSONResponse(
            status_code=status_code,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        import logging
        logger = logging.getLogger("bonapharm")
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "Error interno del servidor",
            },
        )
