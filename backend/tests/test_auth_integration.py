"""
Integration tests for authentication endpoints.

Tests the full authentication flow including registration, login, and token refresh.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import Mock
from pydantic import ValidationError

from app.models.user import User
from app.core.security import hash_password, verify_password, decode_token
from app.schemas.user import UserRegister, UserLogin, TokenRefresh


@pytest.mark.asyncio
async def test_register_valid_user(db: AsyncSession):
    """Test successful user registration with valid data."""
    from app.api.auth import register

    # Create mock request object
    mock_request = Mock()
    mock_request.client.host = "127.0.0.1"

    # Create registration request
    request = UserRegister(
        email="newuser@example.com",
        password="StrongPass123!",
        confirm_password="StrongPass123!"
    )

    # Register user
    response = await register(request, mock_request, db)

    # Verify response
    assert response.email == "newuser@example.com"
    assert response.id is not None
    assert not hasattr(response, 'password')  # Password should not be in response

    # Verify user in database
    result = await db.execute(
        select(User).where(User.email == "newuser@example.com")
    )
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == "newuser@example.com"
    assert verify_password("StrongPass123!", user.password_hash)


@pytest.mark.asyncio
async def test_register_duplicate_email(db: AsyncSession):
    """Test that registration fails with duplicate email."""
    from app.api.auth import register

    # Create mock request object
    mock_request = Mock()
    mock_request.client.host = "127.0.0.1"

    # Create first user
    user1 = User(
        email="duplicate@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user1)
    await db.commit()

    # Try to register with same email
    request = UserRegister(
        email="duplicate@example.com",
        password="DifferentPass123!",
        confirm_password="DifferentPass123!"
    )

    with pytest.raises(HTTPException) as exc_info:
        await register(request, mock_request, db)

    assert exc_info.value.status_code == 400
    assert "already registered" in exc_info.value.detail.lower()


def test_register_weak_passwords():
    """Test that registration fails with weak passwords at schema validation level."""
    # Test various weak passwords - should fail at Pydantic validation
    weak_passwords = [
        ("short", "short"),  # Too short
        ("nouppercase123", "nouppercase123"),  # No uppercase
        ("NOLOWERCASE123", "NOLOWERCASE123"),  # No lowercase
        ("NoDigits", "NoDigits"),  # No digits
    ]

    for weak_pass, confirm in weak_passwords:
        with pytest.raises(ValidationError):
            UserRegister(
                email=f"user_{weak_pass}@example.com",
                password=weak_pass,
                confirm_password=confirm
            )


def test_register_password_mismatch():
    """Test that registration fails when passwords don't match."""
    with pytest.raises(ValidationError):
        UserRegister(
            email="test@example.com",
            password="StrongPass123!",
            confirm_password="DifferentPass123!"
        )


@pytest.mark.asyncio
async def test_login_valid_credentials(db: AsyncSession):
    """Test successful login with valid credentials."""
    from app.api.auth import login

    # Create mock request object
    mock_request = Mock()
    mock_request.client.host = "127.0.0.1"

    # Create user
    password = "TestPass123!"
    user = User(
        email="logintest@example.com",
        password_hash=hash_password(password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Login
    request = UserLogin(
        email="logintest@example.com",
        password=password
    )

    response = await login(request, mock_request, db)

    # Verify response contains tokens
    assert response.access_token is not None
    assert response.refresh_token is not None
    assert response.token_type == "bearer"

    # Verify access token payload
    payload = decode_token(response.access_token)
    assert payload is not None
    assert payload["sub"] == str(user.id)
    assert payload["email"] == user.email
    assert payload["type"] == "access"
    assert "exp" in payload

    # Verify refresh token payload
    refresh_payload = decode_token(response.refresh_token)
    assert refresh_payload is not None
    assert refresh_payload["sub"] == str(user.id)
    assert refresh_payload["type"] == "refresh"


@pytest.mark.asyncio
async def test_login_wrong_password(db: AsyncSession):
    """Test that login fails with wrong password."""
    from app.api.auth import login

    # Create mock request object
    mock_request = Mock()
    mock_request.client.host = "127.0.0.1"

    # Create user
    user = User(
        email="wrongpass@example.com",
        password_hash=hash_password("CorrectPass123!")
    )
    db.add(user)
    await db.commit()

    # Try to login with wrong password
    request = UserLogin(
        email="wrongpass@example.com",
        password="WrongPass123!"
    )

    with pytest.raises(HTTPException) as exc_info:
        await login(request, mock_request, db)

    assert exc_info.value.status_code == 401
    assert "incorrect" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_login_unknown_email(db: AsyncSession):
    """Test that login fails with unknown email."""
    from app.api.auth import login

    # Create mock request object
    mock_request = Mock()
    mock_request.client.host = "127.0.0.1"

    # Try to login with non-existent email
    request = UserLogin(
        email="doesnotexist@example.com",
        password="SomePass123!"
    )

    with pytest.raises(HTTPException) as exc_info:
        await login(request, mock_request, db)

    assert exc_info.value.status_code == 401
    assert "incorrect" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_token_refresh_valid(db: AsyncSession):
    """Test successful token refresh with valid refresh token."""
    from app.api.auth import refresh_token
    from app.core.security import create_refresh_token

    # Create user
    user = User(
        email="refreshtest@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create refresh token
    refresh_tok = create_refresh_token({"sub": str(user.id)})

    # Refresh access token
    request = TokenRefresh(refresh_token=refresh_tok)
    response = await refresh_token(request, db)

    # Verify new access token
    assert response.access_token is not None
    assert response.token_type == "bearer"

    # Verify new access token payload
    payload = decode_token(response.access_token)
    assert payload is not None
    assert payload["sub"] == str(user.id)
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_token_refresh_invalid_token(db: AsyncSession):
    """Test that token refresh fails with invalid token."""
    from app.api.auth import refresh_token

    # Try to refresh with invalid token
    request = TokenRefresh(refresh_token="invalid.token.here")

    with pytest.raises(HTTPException) as exc_info:
        await refresh_token(request, db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh_access_token_not_allowed(db: AsyncSession):
    """Test that using an access token for refresh is rejected."""
    from app.api.auth import refresh_token
    from app.core.security import create_access_token

    # Create user
    user = User(
        email="tokentype@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Try to use access token for refresh (should fail)
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    request = TokenRefresh(refresh_token=access_token)

    with pytest.raises(HTTPException) as exc_info:
        await refresh_token(request, db)

    assert exc_info.value.status_code == 401
    assert "token type" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_token_refresh_nonexistent_user(db: AsyncSession):
    """Test that token refresh fails if user no longer exists."""
    from app.api.auth import refresh_token
    from app.core.security import create_refresh_token

    # Create refresh token for non-existent user
    refresh_tok = create_refresh_token({"sub": "99999"})
    request = TokenRefresh(refresh_token=refresh_tok)

    with pytest.raises(HTTPException) as exc_info:
        await refresh_token(request, db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_full_auth_flow(db: AsyncSession):
    """Test complete authentication flow: register -> login -> refresh."""
    from app.api.auth import register, login, refresh_token

    # Create mock request object
    mock_request = Mock()
    mock_request.client.host = "127.0.0.1"

    # Step 1: Register
    register_request = UserRegister(
        email="fullflow@example.com",
        password="TestPass123!",
        confirm_password="TestPass123!"
    )
    register_response = await register(register_request, mock_request, db)
    assert register_response.email == "fullflow@example.com"

    # Step 2: Login
    login_request = UserLogin(
        email="fullflow@example.com",
        password="TestPass123!"
    )
    login_response = await login(login_request, mock_request, db)
    assert login_response.access_token is not None
    assert login_response.refresh_token is not None

    # Verify access token works
    access_payload = decode_token(login_response.access_token)
    assert access_payload is not None
    assert access_payload["email"] == "fullflow@example.com"

    # Step 3: Refresh token
    refresh_request = TokenRefresh(refresh_token=login_response.refresh_token)
    refresh_response = await refresh_token(refresh_request, db)
    assert refresh_response.access_token is not None

    # Verify new access token is different but valid
    assert refresh_response.access_token != login_response.access_token
    new_payload = decode_token(refresh_response.access_token)
    assert new_payload is not None
    assert new_payload["sub"] == access_payload["sub"]
