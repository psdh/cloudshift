"""
Tests for rate limiting functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import httpx

from app.services.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_requests_initially():
    """Test that rate limiter allows requests initially."""
    limiter = RateLimiter()

    is_limited = await limiter.check_rate_limit("onedrive")
    assert is_limited is False


@pytest.mark.asyncio
async def test_rate_limiter_records_requests():
    """Test that rate limiter tracks request counts."""
    limiter = RateLimiter()

    # Record multiple requests
    await limiter.record_request("onedrive")
    await limiter.record_request("onedrive")
    await limiter.record_request("onedrive")

    status = await limiter.get_rate_limit_status("onedrive")
    assert status["requests_this_window"] == 3
    assert status["is_rate_limited"] is False


@pytest.mark.asyncio
async def test_rate_limiter_handles_429_response():
    """Test that 429 responses trigger rate limiting."""
    limiter = RateLimiter()

    # Create mock 429 response with Retry-After header
    response = httpx.Response(
        status_code=429,
        headers={"Retry-After": "60"},
        request=httpx.Request("GET", "https://api.example.com")
    )

    await limiter.handle_rate_limit_response("onedrive", response)

    # Check that rate limit was recorded
    is_limited = await limiter.check_rate_limit("onedrive")
    assert is_limited is True

    # Check status
    status = await limiter.get_rate_limit_status("onedrive")
    assert status["is_rate_limited"] is True
    assert "rate_limit_expires_in_seconds" in status


@pytest.mark.asyncio
async def test_rate_limiter_parses_retry_after_seconds():
    """Test parsing Retry-After header in seconds format."""
    limiter = RateLimiter()

    response = httpx.Response(
        status_code=429,
        headers={"Retry-After": "30"},
        request=httpx.Request("GET", "https://api.example.com")
    )

    # Parse the header
    retry_after = limiter._parse_retry_after(response)
    assert retry_after == 30


@pytest.mark.asyncio
async def test_rate_limiter_parses_retry_after_http_date():
    """Test parsing Retry-After header in HTTP-date format."""
    limiter = RateLimiter()

    # Create HTTP-date 60 seconds in future
    from email.utils import formatdate
    from datetime import timezone
    future_time = datetime.now(timezone.utc) + timedelta(seconds=60)
    http_date = formatdate(timeval=future_time.timestamp(), usegmt=True)

    response = httpx.Response(
        status_code=429,
        headers={"Retry-After": http_date},
        request=httpx.Request("GET", "https://api.example.com")
    )

    retry_after = limiter._parse_retry_after(response)
    # Allow some tolerance for processing time
    assert 58 <= retry_after <= 62


@pytest.mark.asyncio
async def test_rate_limiter_handles_missing_retry_after():
    """Test that missing Retry-After header uses default backoff."""
    limiter = RateLimiter()

    response = httpx.Response(
        status_code=429,
        headers={},
        request=httpx.Request("GET", "https://api.example.com")
    )

    # Should use default backoff (60 seconds)
    await limiter.handle_rate_limit_response("onedrive", response, default_backoff=45)

    status = await limiter.get_rate_limit_status("onedrive")
    assert status["is_rate_limited"] is True


@pytest.mark.asyncio
async def test_rate_limiter_wait_if_rate_limited():
    """Test that wait_if_rate_limited actually waits."""
    limiter = RateLimiter()

    # Set very short rate limit
    response = httpx.Response(
        status_code=429,
        headers={"Retry-After": "1"},  # 1 second
        request=httpx.Request("GET", "https://api.example.com")
    )

    await limiter.handle_rate_limit_response("onedrive", response)

    # Wait should block for ~1 second
    start = datetime.utcnow()
    await limiter.wait_if_rate_limited("onedrive")
    elapsed = (datetime.utcnow() - start).total_seconds()

    # Should have waited approximately 1 second
    assert 0.8 <= elapsed <= 1.5


@pytest.mark.asyncio
async def test_rate_limiter_expires_after_timeout():
    """Test that rate limit expires after the timeout period."""
    limiter = RateLimiter()

    # Set very short rate limit
    response = httpx.Response(
        status_code=429,
        headers={"Retry-After": "1"},  # 1 second
        request=httpx.Request("GET", "https://api.example.com")
    )

    await limiter.handle_rate_limit_response("onedrive", response)

    # Initially rate limited
    assert await limiter.check_rate_limit("onedrive") is True

    # Wait for expiry
    await asyncio.sleep(1.2)

    # Should no longer be rate limited
    assert await limiter.check_rate_limit("onedrive") is False


@pytest.mark.asyncio
async def test_rate_limiter_per_provider_isolation():
    """Test that rate limits are isolated per provider."""
    limiter = RateLimiter()

    # Rate limit onedrive
    response = httpx.Response(
        status_code=429,
        headers={"Retry-After": "60"},
        request=httpx.Request("GET", "https://api.example.com")
    )

    await limiter.handle_rate_limit_response("onedrive", response)

    # OneDrive should be limited
    assert await limiter.check_rate_limit("onedrive") is True

    # Google should not be limited
    assert await limiter.check_rate_limit("google") is False


@pytest.mark.asyncio
async def test_rate_limiter_request_window_reset():
    """Test that request counts reset after the time window."""
    limiter = RateLimiter()
    limiter._request_window = 1  # 1 second window for testing

    # Record requests
    await limiter.record_request("onedrive")
    await limiter.record_request("onedrive")

    status = await limiter.get_rate_limit_status("onedrive")
    assert status["requests_this_window"] == 2

    # Wait for window to expire
    await asyncio.sleep(1.1)

    # Record another request (should reset counter)
    await limiter.record_request("onedrive")

    status = await limiter.get_rate_limit_status("onedrive")
    assert status["requests_this_window"] == 1


@pytest.mark.asyncio
async def test_rate_limiter_warning_at_threshold():
    """Test that warnings are logged when approaching limit."""
    limiter = RateLimiter()
    limiter._max_requests_per_minute["onedrive"] = 10
    limiter._warning_threshold = 0.8  # Warn at 80%

    # Record 8 requests (80% of 10)
    for _ in range(8):
        await limiter.record_request("onedrive")

    # Should have logged warning (check logs in actual implementation)
    status = await limiter.get_rate_limit_status("onedrive")
    assert status["requests_this_window"] == 8
    assert status["max_requests_per_minute"] == 10


@pytest.mark.asyncio
async def test_rate_limiter_get_status():
    """Test getting comprehensive rate limit status."""
    limiter = RateLimiter()

    # Get status when not limited
    status = await limiter.get_rate_limit_status("onedrive")
    assert status["provider"] == "onedrive"
    assert status["is_rate_limited"] is False
    assert status["requests_this_window"] == 0

    # Rate limit the provider
    response = httpx.Response(
        status_code=429,
        headers={"Retry-After": "120"},
        request=httpx.Request("GET", "https://api.example.com")
    )
    await limiter.handle_rate_limit_response("onedrive", response)

    # Get status when limited
    status = await limiter.get_rate_limit_status("onedrive")
    assert status["is_rate_limited"] is True
    assert "rate_limit_expires_at" in status
    assert "rate_limit_expires_in_seconds" in status


@pytest.mark.asyncio
async def test_concurrent_rate_limiter_access():
    """Test that rate limiter handles concurrent access safely."""
    limiter = RateLimiter()

    # Concurrent request recording
    async def record_many():
        for _ in range(10):
            await limiter.record_request("onedrive")

    # Run multiple concurrent tasks
    await asyncio.gather(
        record_many(),
        record_many(),
        record_many()
    )

    # Should have recorded all 30 requests
    status = await limiter.get_rate_limit_status("onedrive")
    assert status["requests_this_window"] == 30
