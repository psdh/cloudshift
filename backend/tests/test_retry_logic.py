"""
Tests for retry logic with exponential backoff.
"""

import pytest
import time
from unittest.mock import Mock, patch
import httpx
from requests.exceptions import Timeout, ConnectionError

from app.core.retry import (
    is_transient_error,
    is_permanent_error,
    calculate_backoff_delay,
    retry_on_transient_error,
    async_retry_on_transient_error
)


def test_calculate_backoff_delay():
    """Test exponential backoff delay calculation."""
    assert calculate_backoff_delay(0, 1.0) == 1.0
    assert calculate_backoff_delay(1, 1.0) == 2.0
    assert calculate_backoff_delay(2, 1.0) == 4.0
    assert calculate_backoff_delay(3, 1.0) == 8.0

    # Test with different base delay
    assert calculate_backoff_delay(0, 2.0) == 2.0
    assert calculate_backoff_delay(1, 2.0) == 4.0


def test_is_transient_error_httpx_timeout():
    """Test that httpx timeout errors are identified as transient."""
    error = httpx.TimeoutException("Request timed out")
    assert is_transient_error(error) is True


def test_is_transient_error_httpx_connect():
    """Test that httpx connection errors are identified as transient."""
    error = httpx.ConnectError("Connection failed")
    assert is_transient_error(error) is True


def test_is_transient_error_requests_timeout():
    """Test that requests timeout errors are identified as transient."""
    error = Timeout("Request timed out")
    assert is_transient_error(error) is True


def test_is_transient_error_requests_connection():
    """Test that requests connection errors are identified as transient."""
    error = ConnectionError("Connection failed")
    assert is_transient_error(error) is True


def test_is_transient_error_rate_limit():
    """Test that rate limit errors (429) are identified as transient."""
    response = Mock()
    response.status_code = 429
    error = httpx.HTTPStatusError("Too many requests", request=Mock(), response=response)
    assert is_transient_error(error) is True


def test_is_transient_error_server_error():
    """Test that server errors (5xx) are identified as transient."""
    response = Mock()
    response.status_code = 500
    error = httpx.HTTPStatusError("Internal server error", request=Mock(), response=response)
    assert is_transient_error(error) is True

    response.status_code = 503
    error = httpx.HTTPStatusError("Service unavailable", request=Mock(), response=response)
    assert is_transient_error(error) is True


def test_is_permanent_error_not_found():
    """Test that 404 errors are identified as permanent."""
    response = Mock()
    response.status_code = 404
    error = httpx.HTTPStatusError("Not found", request=Mock(), response=response)
    assert is_permanent_error(error) is True


def test_is_permanent_error_forbidden():
    """Test that 403 errors are identified as permanent."""
    response = Mock()
    response.status_code = 403
    error = httpx.HTTPStatusError("Forbidden", request=Mock(), response=response)
    assert is_permanent_error(error) is True


def test_is_permanent_error_unauthorized():
    """Test that 401 errors are identified as permanent."""
    response = Mock()
    response.status_code = 401
    error = httpx.HTTPStatusError("Unauthorized", request=Mock(), response=response)
    assert is_permanent_error(error) is True


def test_retry_on_transient_error_success():
    """Test that function succeeds without retries when no error."""
    mock_func = Mock(return_value="success")
    decorated = retry_on_transient_error(max_retries=3)(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 1


def test_retry_on_transient_error_succeeds_after_retry():
    """Test that function succeeds after transient failure."""
    mock_func = Mock(side_effect=[
        Timeout("Timed out"),
        "success"
    ])
    decorated = retry_on_transient_error(max_retries=3, base_delay=0.1)(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 2


def test_retry_on_transient_error_exhausts_retries():
    """Test that function raises error after max retries."""
    mock_func = Mock(side_effect=Timeout("Timed out"))
    decorated = retry_on_transient_error(max_retries=2, base_delay=0.1)(mock_func)

    with pytest.raises(Timeout):
        decorated()

    # Should try initial + 2 retries = 3 times
    assert mock_func.call_count == 3


def test_retry_on_transient_error_permanent_error():
    """Test that permanent errors are not retried."""
    response = Mock()
    response.status_code = 404
    error = httpx.HTTPStatusError("Not found", request=Mock(), response=response)

    mock_func = Mock(side_effect=error)
    decorated = retry_on_transient_error(max_retries=3)(mock_func)

    with pytest.raises(httpx.HTTPStatusError):
        decorated()

    # Should only try once (no retries for permanent errors)
    assert mock_func.call_count == 1


@pytest.mark.asyncio
async def test_async_retry_on_transient_error_success():
    """Test async retry decorator with successful call."""
    async def mock_func():
        return "success"

    decorated = async_retry_on_transient_error(max_retries=3)(mock_func)
    result = await decorated()

    assert result == "success"


@pytest.mark.asyncio
async def test_async_retry_on_transient_error_succeeds_after_retry():
    """Test async retry decorator succeeds after transient failure."""
    call_count = 0

    async def mock_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Timeout("Timed out")
        return "success"

    decorated = async_retry_on_transient_error(max_retries=3, base_delay=0.1)(mock_func)
    result = await decorated()

    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_async_retry_on_transient_error_exhausts_retries():
    """Test async retry decorator exhausts retries."""
    async def mock_func():
        raise Timeout("Timed out")

    decorated = async_retry_on_transient_error(max_retries=2, base_delay=0.1)(mock_func)

    with pytest.raises(Timeout):
        await decorated()


def test_retry_backoff_timing():
    """Test that retry backoff delays are applied correctly."""
    start_time = time.time()

    mock_func = Mock(side_effect=[
        Timeout("Error 1"),
        Timeout("Error 2"),
        "success"
    ])
    decorated = retry_on_transient_error(max_retries=3, base_delay=0.1)(mock_func)

    result = decorated()

    elapsed_time = time.time() - start_time

    # Should have delays of 0.1s and 0.2s = 0.3s total
    # Allow some tolerance for execution time
    assert elapsed_time >= 0.3
    assert elapsed_time < 0.5
    assert result == "success"
