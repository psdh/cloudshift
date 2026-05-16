"""Tests for OAuth state CSRF protection (signed, user-bound, expiring)."""

import time

from jose import jwt

from app.core.config import settings
from app.services.oauth import OAuthService


def test_generated_state_validates_for_same_user():
    state = OAuthService.generate_state(user_id=42)
    assert OAuthService.validate_state(state, expected_user_id=42) is True


def test_state_rejected_for_different_user():
    """A state issued for user A must not be accepted when user B completes
    the callback (the core CSRF / account-binding protection)."""
    state = OAuthService.generate_state(user_id=42)
    assert OAuthService.validate_state(state, expected_user_id=99) is False


def test_garbage_and_empty_state_rejected():
    assert OAuthService.validate_state("not-a-token", expected_user_id=1) is False
    assert OAuthService.validate_state("", expected_user_id=1) is False


def test_tampered_state_rejected():
    state = OAuthService.generate_state(user_id=7)
    tampered = state[:-3] + ("abc" if not state.endswith("abc") else "xyz")
    assert OAuthService.validate_state(tampered, expected_user_id=7) is False


def test_expired_state_rejected():
    expired = jwt.encode(
        {
            "sub": "7",
            "purpose": "oauth_state",
            "nonce": "n",
            "exp": int(time.time()) - 5,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert OAuthService.validate_state(expired, expected_user_id=7) is False


def test_token_with_wrong_purpose_rejected():
    """A normal access token must not be usable as an OAuth state."""
    not_a_state = jwt.encode(
        {"sub": "7", "type": "access", "exp": int(time.time()) + 600},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert OAuthService.validate_state(not_a_state, expected_user_id=7) is False
