import pytest
from app.core.security import hash_password, verify_password


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
