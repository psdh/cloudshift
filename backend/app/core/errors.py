"""
Standardized error handling for CloudShift API.

This module provides consistent error responses across all endpoints,
including proper HTTP status codes, user-friendly messages, and logging.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback

logger = logging.getLogger(__name__)


class APIError(Exception):
    """
    Base exception class for API errors.

    All custom API exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class NotFoundError(APIError):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details
        )


class UnauthorizedError(APIError):
    """Raised when authentication is required but not provided."""

    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
            details=details
        )


class ForbiddenError(APIError):
    """Raised when user lacks permission for the requested operation."""

    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            details=details
        )


class ConflictError(APIError):
    """Raised when request conflicts with current state."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details=details
        )


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details
        )


class InternalServerError(APIError):
    """Raised for internal server errors."""

    def __init__(self, message: str = "Internal server error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INTERNAL_SERVER_ERROR",
            status_code=500,
            details=details
        )


def create_error_response(
    error: str,
    code: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        error: User-friendly error message
        code: Error code for programmatic handling
        status_code: HTTP status code
        details: Optional additional error details

    Returns:
        Dictionary with standardized error format
    """
    response = {
        "error": error,
        "code": code,
        "status_code": status_code
    }

    if details:
        response["details"] = details

    return response


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Handler for APIError exceptions.

    Args:
        request: FastAPI request object
        exc: APIError exception

    Returns:
        JSONResponse with standardized error format
    """
    # Log error details
    logger.error(
        f"API Error: {exc.code} - {exc.message}",
        extra={
            "code": exc.code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error=exc.message,
            code=exc.code,
            status_code=exc.status_code,
            details=exc.details if exc.details else None
        )
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handler for FastAPI HTTPException.

    Args:
        request: FastAPI request object
        exc: HTTPException

    Returns:
        JSONResponse with standardized error format
    """
    # Map HTTP status codes to error codes
    code_mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR"
    }

    code = code_mapping.get(exc.status_code, "UNKNOWN_ERROR")

    # Log non-client errors (5xx)
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error=str(exc.detail),
            code=code,
            status_code=exc.status_code
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for Pydantic validation errors.

    Args:
        request: FastAPI request object
        exc: RequestValidationError

    Returns:
        JSONResponse with standardized error format including validation details
    """
    # Extract validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        f"Validation error on {request.url.path}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors
        }
    )

    return JSONResponse(
        status_code=422,
        content=create_error_response(
            error="Validation error",
            code="VALIDATION_ERROR",
            status_code=422,
            details={"validation_errors": errors}
        )
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler for unhandled exceptions.

    Logs full stack trace and returns generic error to user.

    Args:
        request: FastAPI request object
        exc: Any unhandled exception

    Returns:
        JSONResponse with generic error message (no sensitive details)
    """
    # Log full exception with stack trace
    logger.error(
        f"Unhandled exception on {request.url.path}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True  # Include full stack trace in logs
    )

    # Return generic error message (don't expose internal details)
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            error="An unexpected error occurred. Please try again later.",
            code="INTERNAL_SERVER_ERROR",
            status_code=500
        )
    )


def register_error_handlers(app):
    """
    Register all error handlers with the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
