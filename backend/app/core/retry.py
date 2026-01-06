"""
Retry logic with exponential backoff for cloud API calls.

This module provides decorators and utilities for handling transient failures
in cloud provider API calls with intelligent retry strategies.
"""

import logging
import time
import asyncio
from typing import Callable, TypeVar, Optional, List, Type
from functools import wraps
import httpx
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryableError(Exception):
    """Base exception for errors that should be retried."""
    pass


class PermanentError(Exception):
    """Exception for errors that should not be retried."""
    pass


def is_transient_error(error: Exception) -> bool:
    """
    Determine if an error is transient and should be retried.

    Transient errors include:
    - Network timeouts
    - Connection errors
    - HTTP 429 (rate limit)
    - HTTP 5xx (server errors)
    - Temporary service unavailability

    Args:
        error: Exception to check

    Returns:
        True if error is transient, False otherwise
    """
    # Check for httpx errors (used by async HTTP clients)
    if isinstance(error, httpx.TimeoutException):
        return True
    if isinstance(error, httpx.ConnectError):
        return True
    if isinstance(error, httpx.NetworkError):
        return True

    # Check for requests errors (used by some sync clients)
    if isinstance(error, Timeout):
        return True
    if isinstance(error, ConnectionError):
        return True

    # Check for HTTP status codes in httpx responses
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        # Rate limits and server errors are transient
        if status_code == 429:  # Too Many Requests
            return True
        if status_code >= 500:  # Server errors
            return True
        # Client errors (4xx) except 429 are permanent
        return False

    # Check error message for common transient indicators
    error_str = str(error).lower()
    transient_indicators = [
        'timeout',
        'timed out',
        'connection',
        'temporary',
        'unavailable',
        'service unavailable',
        'rate limit',
        'throttle',
        'too many requests'
    ]

    for indicator in transient_indicators:
        if indicator in error_str:
            return True

    # Default to not retrying unknown errors
    return False


def is_permanent_error(error: Exception) -> bool:
    """
    Determine if an error is permanent and should not be retried.

    Permanent errors include:
    - HTTP 404 (not found)
    - HTTP 403 (forbidden)
    - HTTP 401 (unauthorized)
    - HTTP 400 (bad request)
    - Authentication/authorization failures

    Args:
        error: Exception to check

    Returns:
        True if error is permanent, False otherwise
    """
    # Check for httpx HTTP errors
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        # Client errors that shouldn't be retried
        if status_code in [400, 401, 403, 404, 409]:
            return True
        return False

    # Check error message for permanent error indicators
    error_str = str(error).lower()
    permanent_indicators = [
        'not found',
        'forbidden',
        'unauthorized',
        'invalid',
        'bad request',
        'authentication failed',
        'permission denied'
    ]

    for indicator in permanent_indicators:
        if indicator in error_str:
            return True

    return False


def calculate_backoff_delay(attempt: int, base_delay: float = 1.0) -> float:
    """
    Calculate exponential backoff delay for retry attempt.

    Uses exponential backoff: delay = base_delay * (2 ** attempt)
    For base_delay=1.0: attempt 0=1s, attempt 1=2s, attempt 2=4s

    Args:
        attempt: Retry attempt number (0-indexed)
        base_delay: Base delay in seconds

    Returns:
        Delay in seconds
    """
    return base_delay * (2 ** attempt)


def retry_on_transient_error(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: Optional[List[Type[Exception]]] = None
):
    """
    Decorator for retrying synchronous functions on transient errors.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay for exponential backoff in seconds (default: 1.0)
        exceptions: List of exception types to catch (default: all exceptions)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_transient_error(max_retries=3, base_delay=1.0)
        def call_api():
            response = requests.get("https://api.example.com/data")
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_error = e

                    # Check if we should retry this exception type
                    if exceptions and not isinstance(e, tuple(exceptions)):
                        raise

                    # Don't retry permanent errors
                    if is_permanent_error(e):
                        logger.warning(
                            f"{func.__name__} failed with permanent error: {str(e)}"
                        )
                        raise

                    # Don't retry if this was the last attempt
                    if attempt >= max_retries:
                        break

                    # Only retry transient errors
                    if not is_transient_error(e):
                        raise

                    # Calculate backoff delay
                    delay = calculate_backoff_delay(attempt, base_delay)

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                        f"Retrying in {delay}s..."
                    )

                    time.sleep(delay)

            # All retries exhausted
            logger.error(
                f"{func.__name__} failed after {max_retries + 1} attempts: {str(last_error)}"
            )
            raise last_error

        return wrapper
    return decorator


def async_retry_on_transient_error(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: Optional[List[Type[Exception]]] = None
):
    """
    Decorator for retrying async functions on transient errors.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay for exponential backoff in seconds (default: 1.0)
        exceptions: List of exception types to catch (default: all exceptions)

    Returns:
        Decorated async function with retry logic

    Example:
        @async_retry_on_transient_error(max_retries=3, base_delay=1.0)
        async def call_api():
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com/data")
                response.raise_for_status()
                return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_error = e

                    # Check if we should retry this exception type
                    if exceptions and not isinstance(e, tuple(exceptions)):
                        raise

                    # Don't retry permanent errors
                    if is_permanent_error(e):
                        logger.warning(
                            f"{func.__name__} failed with permanent error: {str(e)}"
                        )
                        raise

                    # Don't retry if this was the last attempt
                    if attempt >= max_retries:
                        break

                    # Only retry transient errors
                    if not is_transient_error(e):
                        raise

                    # Calculate backoff delay
                    delay = calculate_backoff_delay(attempt, base_delay)

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                        f"Retrying in {delay}s..."
                    )

                    await asyncio.sleep(delay)

            # All retries exhausted
            logger.error(
                f"{func.__name__} failed after {max_retries + 1} attempts: {str(last_error)}"
            )
            raise last_error

        return wrapper
    return decorator
