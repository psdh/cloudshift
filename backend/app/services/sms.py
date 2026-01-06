"""
SMS notification service using Twilio.

This module handles sending SMS notifications for transfer completion and failure.
"""

import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class SMSService:
    """Service for sending SMS notifications via Twilio."""

    def __init__(self):
        """Initialize SMS service with Twilio credentials."""
        self.enabled = False
        self.client = None

        # Check if Twilio is configured
        if not hasattr(settings, 'TWILIO_ACCOUNT_SID') or not settings.TWILIO_ACCOUNT_SID:
            logger.warning("Twilio credentials not configured - SMS service disabled")
            return

        try:
            from twilio.rest import Client
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.from_number = settings.TWILIO_PHONE_NUMBER
            self.enabled = True
            logger.info("SMS service initialized successfully")
        except ImportError:
            logger.error("Twilio package not installed - run: pip install twilio")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {str(e)}")

    def _validate_phone_number(self, phone_number: str) -> bool:
        """
        Validate phone number format.

        Args:
            phone_number: Phone number to validate

        Returns:
            True if valid, False otherwise
        """
        if not phone_number:
            return False

        # Remove common formatting characters
        cleaned = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        # Must start with + and be 10-15 digits
        if not cleaned.startswith("+"):
            return False

        digits = cleaned[1:]
        if not digits.isdigit():
            return False

        if len(digits) < 10 or len(digits) > 15:
            return False

        return True

    async def send_transfer_completion_sms(
        self,
        to_phone: str,
        job_id: int,
        total_files: int,
        files_transferred: int,
        files_failed: int,
        source_provider: str,
        dest_provider: str
    ) -> bool:
        """
        Send SMS notification for transfer completion.

        Args:
            to_phone: Recipient phone number (E.164 format)
            job_id: Transfer job ID
            total_files: Total number of files
            files_transferred: Number of successfully transferred files
            files_failed: Number of failed files
            source_provider: Source provider name
            dest_provider: Destination provider name

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("SMS service not enabled - skipping SMS")
            return False

        # Validate phone number
        if not self._validate_phone_number(to_phone):
            logger.error(f"Invalid phone number format: {to_phone}")
            return False

        try:
            # Create message text
            if files_failed == 0:
                message = (
                    f"CloudShift: Transfer #{job_id} complete! "
                    f"✓ {files_transferred}/{total_files} files transferred from "
                    f"{source_provider.title()} to {dest_provider.title()}."
                )
            else:
                message = (
                    f"CloudShift: Transfer #{job_id} complete with errors. "
                    f"✓ {files_transferred} transferred, ✗ {files_failed} failed. "
                    f"Check dashboard for details."
                )

            # Send SMS via Twilio
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_phone
            )

            logger.info(
                f"SMS sent successfully to {to_phone} for job {job_id}. "
                f"Message SID: {twilio_message.sid}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {str(e)}")
            return False

    async def send_transfer_failure_sms(
        self,
        to_phone: str,
        job_id: int,
        error_reason: str,
        source_provider: str,
        dest_provider: str
    ) -> bool:
        """
        Send SMS notification for transfer failure.

        Args:
            to_phone: Recipient phone number (E.164 format)
            job_id: Transfer job ID
            error_reason: Reason for failure
            source_provider: Source provider name
            dest_provider: Destination provider name

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("SMS service not enabled - skipping SMS")
            return False

        # Validate phone number
        if not self._validate_phone_number(to_phone):
            logger.error(f"Invalid phone number format: {to_phone}")
            return False

        try:
            # Create message text
            # Truncate error reason to keep SMS short
            error_summary = error_reason[:100] + "..." if len(error_reason) > 100 else error_reason

            message = (
                f"CloudShift: Transfer #{job_id} failed. "
                f"{source_provider.title()} → {dest_provider.title()}. "
                f"Error: {error_summary}. Check dashboard for details."
            )

            # Send SMS via Twilio
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_phone
            )

            logger.info(
                f"Failure SMS sent to {to_phone} for job {job_id}. "
                f"Message SID: {twilio_message.sid}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to send failure SMS to {to_phone}: {str(e)}")
            return False


# Global SMS service instance
sms_service = SMSService()
