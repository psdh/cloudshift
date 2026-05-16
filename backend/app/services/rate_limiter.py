"""
Rate limiting service for cloud API providers.

This module implements rate limit detection, backoff, and request queuing
to avoid hitting provider limits and ensure graceful degradation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import httpx

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for cloud API providers.

    Tracks rate limit state per provider and implements:
    - Automatic backoff on 429 responses
    - Retry-After header parsing
    - Global rate limit tracking
    - Request queuing when near limits
    """

    def __init__(self):
        """Initialize rate limiter."""
        # Provider -> datetime when rate limit expires
        self._rate_limit_until: Dict[str, datetime] = {}

        # Provider -> number of recent requests
        self._request_counts: Dict[str, int] = {}

        # Provider -> last reset time
        self._last_reset: Dict[str, datetime] = {}

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Configuration
        self._warning_threshold = 0.8  # Warn at 80% of limit
        self._request_window = 60  # 60 second window
        self._max_requests_per_minute = {
            "onedrive": 100,       # Conservative limit
            "google_drive": 100    # Conservative limit
        }

    async def check_rate_limit(self, provider: str) -> bool:
        """
        Check if provider is currently rate limited.

        Args:
            provider: Provider name (onedrive, google)

        Returns:
            True if rate limited, False otherwise
        """
        async with self._lock:
            if provider not in self._rate_limit_until:
                return False

            limit_until = self._rate_limit_until[provider]

            if datetime.utcnow() >= limit_until:
                # Rate limit expired
                del self._rate_limit_until[provider]
                logger.info(f"Rate limit expired for {provider}")
                return False

            # Still rate limited
            remaining = (limit_until - datetime.utcnow()).total_seconds()
            logger.warning(f"{provider} is rate limited for {remaining:.1f} more seconds")
            return True

    async def wait_if_rate_limited(self, provider: str):
        """
        Wait if provider is currently rate limited.

        Args:
            provider: Provider name (onedrive, google)
        """
        async with self._lock:
            if provider not in self._rate_limit_until:
                return

            limit_until = self._rate_limit_until[provider]
            now = datetime.utcnow()

            if now >= limit_until:
                # Rate limit expired
                del self._rate_limit_until[provider]
                return

            # Wait until rate limit expires
            wait_seconds = (limit_until - now).total_seconds()
            logger.info(f"Waiting {wait_seconds:.1f}s for {provider} rate limit to expire")

        # Release lock while waiting
        await asyncio.sleep(wait_seconds)

    async def record_request(self, provider: str):
        """
        Record a request for rate limit tracking.

        Args:
            provider: Provider name (onedrive, google)
        """
        async with self._lock:
            now = datetime.utcnow()

            # Reset counter if window expired
            if provider not in self._last_reset or \
               (now - self._last_reset[provider]).total_seconds() >= self._request_window:
                self._request_counts[provider] = 0
                self._last_reset[provider] = now

            # Increment counter
            self._request_counts[provider] = self._request_counts.get(provider, 0) + 1

            # Check if approaching limit
            max_requests = self._max_requests_per_minute.get(provider, 100)
            current_count = self._request_counts[provider]

            if current_count >= max_requests * self._warning_threshold:
                logger.warning(
                    f"{provider} at {current_count}/{max_requests} requests per minute "
                    f"({current_count/max_requests*100:.1f}% of limit)"
                )

    async def handle_rate_limit_response(
        self,
        provider: str,
        response: httpx.Response,
        default_backoff: int = 60
    ):
        """
        Handle a rate limit response (429).

        Args:
            provider: Provider name (onedrive, google)
            response: HTTP response object
            default_backoff: Default backoff in seconds if no Retry-After header
        """
        # Parse Retry-After header
        retry_after = self._parse_retry_after(response)
        backoff_seconds = retry_after or default_backoff

        async with self._lock:
            limit_until = datetime.utcnow() + timedelta(seconds=backoff_seconds)
            self._rate_limit_until[provider] = limit_until

            logger.error(
                f"Rate limit hit for {provider}. "
                f"Backing off for {backoff_seconds}s until {limit_until.isoformat()}"
            )

            # Log to audit if available
            try:
                from app.services.audit import AuditService
                from app.models.audit_log import AuditAction
                from app.core.database import get_async_session

                async with get_async_session() as db:
                    await AuditService.log_action(
                        db=db,
                        action=AuditAction.SYSTEM_ERROR,
                        user_id=None,
                        resource_type="rate_limit",
                        resource_id=provider,
                        details={
                            "provider": provider,
                            "backoff_seconds": backoff_seconds,
                            "retry_after_header": retry_after,
                            "limit_until": limit_until.isoformat()
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to log rate limit event: {str(e)}")

    def _parse_retry_after(self, response: httpx.Response) -> Optional[int]:
        """
        Parse Retry-After header from response.

        Args:
            response: HTTP response object

        Returns:
            Number of seconds to wait, or None if header not present
        """
        retry_after = response.headers.get("Retry-After")

        if not retry_after:
            return None

        # Try parsing as integer (seconds)
        try:
            return int(retry_after)
        except ValueError:
            pass

        # Try parsing as HTTP date
        try:
            from email.utils import parsedate_to_datetime
            from datetime import timezone
            retry_time = parsedate_to_datetime(retry_after)
            # Make current time timezone-aware for comparison
            now = datetime.now(timezone.utc)
            delta = retry_time - now
            return max(int(delta.total_seconds()), 0)
        except Exception as e:
            logger.warning(f"Failed to parse Retry-After header '{retry_after}': {str(e)}")
            return None

    async def get_rate_limit_status(self, provider: str) -> dict:
        """
        Get current rate limit status for a provider.

        Args:
            provider: Provider name (onedrive, google)

        Returns:
            dict with status information
        """
        async with self._lock:
            is_limited = provider in self._rate_limit_until

            status = {
                "provider": provider,
                "is_rate_limited": is_limited,
                "requests_this_window": self._request_counts.get(provider, 0),
                "max_requests_per_minute": self._max_requests_per_minute.get(provider, 100)
            }

            if is_limited:
                limit_until = self._rate_limit_until[provider]
                remaining = (limit_until - datetime.utcnow()).total_seconds()
                status["rate_limit_expires_in_seconds"] = max(remaining, 0)
                status["rate_limit_expires_at"] = limit_until.isoformat()

            return status


# Global rate limiter instance
rate_limiter = RateLimiter()
