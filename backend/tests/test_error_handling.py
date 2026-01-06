"""
Tests for standardized error handling.
"""

import pytest
from app.core.errors import (
    APIError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    RateLimitError,
    InternalServerError,
    create_error_response
)


def test_api_error_creation():
    """Test creating base APIError."""
    error = APIError(
        message="Test error",
        code="TEST_ERROR",
        status_code=500,
        details={"key": "value"}
    )

    assert error.message == "Test error"
    assert error.code == "TEST_ERROR"
    assert error.status_code == 500
    assert error.details == {"key": "value"}


def test_validation_error():
    """Test ValidationError has correct defaults."""
    error = ValidationError("Invalid input")

    assert error.message == "Invalid input"
    assert error.code == "VALIDATION_ERROR"
    assert error.status_code == 400


def test_not_found_error():
    """Test NotFoundError has correct defaults."""
    error = NotFoundError()

    assert error.message == "Resource not found"
    assert error.code == "NOT_FOUND"
    assert error.status_code == 404


def test_unauthorized_error():
    """Test UnauthorizedError has correct defaults."""
    error = UnauthorizedError()

    assert error.message == "Authentication required"
    assert error.code == "UNAUTHORIZED"
    assert error.status_code == 401


def test_forbidden_error():
    """Test ForbiddenError has correct defaults."""
    error = ForbiddenError()

    assert error.message == "Permission denied"
    assert error.code == "FORBIDDEN"
    assert error.status_code == 403


def test_conflict_error():
    """Test ConflictError has correct defaults."""
    error = ConflictError("Resource already exists")

    assert error.message == "Resource already exists"
    assert error.code == "CONFLICT"
    assert error.status_code == 409


def test_rate_limit_error():
    """Test RateLimitError has correct defaults."""
    error = RateLimitError()

    assert error.message == "Rate limit exceeded"
    assert error.code == "RATE_LIMIT_EXCEEDED"
    assert error.status_code == 429


def test_internal_server_error():
    """Test InternalServerError has correct defaults."""
    error = InternalServerError()

    assert error.message == "Internal server error"
    assert error.code == "INTERNAL_SERVER_ERROR"
    assert error.status_code == 500


def test_create_error_response_basic():
    """Test creating basic error response."""
    response = create_error_response(
        error="Test error",
        code="TEST_CODE",
        status_code=400
    )

    assert response["error"] == "Test error"
    assert response["code"] == "TEST_CODE"
    assert response["status_code"] == 400
    assert "details" not in response


def test_create_error_response_with_details():
    """Test creating error response with details."""
    response = create_error_response(
        error="Validation failed",
        code="VALIDATION_ERROR",
        status_code=422,
        details={"field": "email", "issue": "invalid format"}
    )

    assert response["error"] == "Validation failed"
    assert response["code"] == "VALIDATION_ERROR"
    assert response["status_code"] == 422
    assert response["details"] == {"field": "email", "issue": "invalid format"}


def test_error_inheritance():
    """Test that all error classes inherit from APIError."""
    errors = [
        ValidationError("test"),
        NotFoundError(),
        UnauthorizedError(),
        ForbiddenError(),
        ConflictError("test"),
        RateLimitError(),
        InternalServerError()
    ]

    for error in errors:
        assert isinstance(error, APIError)
        assert isinstance(error, Exception)


def test_error_message_customization():
    """Test that error messages can be customized."""
    error = NotFoundError("User with ID 123 not found")

    assert error.message == "User with ID 123 not found"
    assert error.code == "NOT_FOUND"
    assert error.status_code == 404


def test_error_with_custom_details():
    """Test errors with custom detail objects."""
    error = ValidationError(
        "Multiple validation errors",
        details={
            "fields": ["email", "password"],
            "count": 2
        }
    )

    assert error.details["fields"] == ["email", "password"]
    assert error.details["count"] == 2
