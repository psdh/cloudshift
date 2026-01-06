import pytest
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "TestPassword123"
    hashed = hash_password(password)

    # Verify hash is different from password
    assert hashed != password

    # Verify password matches hash
    assert verify_password(password, hashed) is True

    # Verify wrong password doesn't match
    assert verify_password("WrongPassword123", hashed) is False


def test_password_hash_is_unique():
    """Test that same password generates different hashes."""
    password = "TestPassword123"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    # Same password should generate different hashes (salt)
    assert hash1 != hash2

    # But both should verify correctly
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_create_access_token():
    """Test access token creation and decoding."""
    data = {"sub": "123", "email": "test@example.com"}
    token = create_access_token(data)

    # Verify token is a string
    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify payload
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "123"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_create_refresh_token():
    """Test refresh token creation and decoding."""
    data = {"sub": "123"}
    token = create_refresh_token(data)

    # Verify token is a string
    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify payload
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "123"
    assert payload["type"] == "refresh"
    assert "exp" in payload


def test_decode_invalid_token():
    """Test decoding invalid token."""
    invalid_token = "invalid.token.here"
    payload = decode_token(invalid_token)
    assert payload is None


def test_token_types_are_different():
    """Test that access and refresh tokens have different types."""
    data = {"sub": "123"}
    access_token = create_access_token(data)
    refresh_token = create_refresh_token(data)

    access_payload = decode_token(access_token)
    refresh_payload = decode_token(refresh_token)

    assert access_payload["type"] == "access"
    assert refresh_payload["type"] == "refresh"
