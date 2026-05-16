"""
Email notification service using AWS SES.

This module provides email sending functionality for transfer notifications
and other user communications.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via AWS SES."""

    def __init__(self):
        """Initialize AWS SES client."""
        self.ses_client = None
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self.ses_client = boto3.client(
                'ses',
                region_name=settings.AWS_REGION or 'us-east-1',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        else:
            logger.warning("AWS credentials not configured - email service disabled")

    def _format_file_size(self, bytes: int) -> str:
        """
        Format bytes to human-readable size.

        Args:
            bytes: Size in bytes

        Returns:
            Formatted size string (e.g., "1.5 GB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} PB"

    def _format_duration(self, started_at: datetime, completed_at: datetime) -> str:
        """
        Format duration between two timestamps.

        Args:
            started_at: Start timestamp
            completed_at: End timestamp

        Returns:
            Formatted duration string (e.g., "2 hours 15 minutes")
        """
        duration = completed_at - started_at
        hours, remainder = divmod(int(duration.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if not parts and seconds > 0:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        return " ".join(parts) if parts else "less than a second"

    def _generate_completion_email_html(
        self,
        user_name: str,
        job_id: int,
        total_files: int,
        total_size: int,
        files_transferred: int,
        files_failed: int,
        duration: str,
        source_provider: str,
        dest_provider: str
    ) -> str:
        """
        Generate HTML email template for transfer completion.

        Args:
            user_name: User's name or email
            job_id: Transfer job ID
            total_files: Total number of files
            total_size: Total size in bytes
            files_transferred: Number of successfully transferred files
            files_failed: Number of failed files
            duration: Formatted duration string
            source_provider: Source cloud provider
            dest_provider: Destination cloud provider

        Returns:
            HTML email content
        """
        formatted_size = self._format_file_size(total_size)
        success_rate = (files_transferred / total_files * 100) if total_files > 0 else 0
        source_provider = source_provider.capitalize()
        dest_provider = dest_provider.capitalize()

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ background-color: #f9f9f9; padding: 20px; }}
        .summary {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #4CAF50; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
        .stat-label {{ font-size: 12px; color: #666; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
        .warning {{ color: #ff9800; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ Transfer Complete</h1>
        </div>

        <div class="content">
            <p>Hi {user_name},</p>

            <p>Your CloudShift transfer (Job #{job_id}) from <strong>{source_provider}</strong> to <strong>{dest_provider}</strong> has completed successfully!</p>

            <div class="summary">
                <h3>Transfer Summary</h3>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">{files_transferred}</div>
                        <div class="stat-label">Files Transferred</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{formatted_size}</div>
                        <div class="stat-label">Total Size</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{success_rate:.1f}%</div>
                        <div class="stat-label">Success Rate</div>
                    </div>
                </div>

                <p><strong>Duration:</strong> {duration}</p>
                {f'<p class="warning"><strong>Failed Files:</strong> {files_failed}</p>' if files_failed > 0 else ''}
            </div>

            <p>You can view the full details and download a report in the CloudShift dashboard.</p>

            <p style="text-align: center; margin-top: 30px;">
                <a href="{settings.FRONTEND_URL}/transfers/{job_id}"
                   style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
                    View Transfer Details
                </a>
            </p>
        </div>

        <div class="footer">
            <p>This is an automated message from CloudShift.</p>
            <p>&copy; 2026 CloudShift - Cloud File Migration Made Easy</p>
        </div>
    </div>
</body>
</html>
"""

    def _generate_failure_email_html(
        self,
        user_name: str,
        job_id: int,
        total_files: int,
        files_attempted: int,
        files_failed: int,
        error_message: str,
        source_provider: str,
        dest_provider: str
    ) -> str:
        """
        Generate HTML email template for transfer failure.

        Args:
            user_name: User's name or email
            job_id: Transfer job ID
            total_files: Total number of files
            files_attempted: Number of files attempted
            files_failed: Number of failed files
            error_message: Main error message
            source_provider: Source cloud provider
            dest_provider: Destination cloud provider

        Returns:
            HTML email content
        """
        source_provider = source_provider.capitalize()
        dest_provider = dest_provider.capitalize()

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; }}
        .content {{ background-color: #f9f9f9; padding: 20px; }}
        .error-box {{ background-color: #ffebee; padding: 15px; margin: 15px 0; border-left: 4px solid #f44336; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #f44336; }}
        .stat-label {{ font-size: 12px; color: #666; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✗ Transfer Failed</h1>
        </div>

        <div class="content">
            <p>Hi {user_name},</p>

            <p>Unfortunately, your CloudShift transfer (Job #{job_id}) from <strong>{source_provider}</strong> to <strong>{dest_provider}</strong> has failed.</p>

            <div class="error-box">
                <h3>Error Details</h3>
                <p><strong>Error:</strong> {error_message}</p>

                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">{total_files}</div>
                        <div class="stat-label">Total Files</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{files_attempted}</div>
                        <div class="stat-label">Attempted</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{files_failed}</div>
                        <div class="stat-label">Failed</div>
                    </div>
                </div>
            </div>

            <p><strong>What to do next:</strong></p>
            <ul>
                <li>Check the error details in your dashboard</li>
                <li>Verify your cloud account connections are still valid</li>
                <li>You can retry the transfer from where it left off</li>
            </ul>

            <p style="text-align: center; margin-top: 30px;">
                <a href="{settings.FRONTEND_URL}/transfers/{job_id}"
                   style="background-color: #f44336; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">
                    View Transfer Details & Retry
                </a>
            </p>
        </div>

        <div class="footer">
            <p>This is an automated message from CloudShift.</p>
            <p>&copy; 2026 CloudShift - Cloud File Migration Made Easy</p>
        </div>
    </div>
</body>
</html>
"""

    async def send_transfer_completion_email(
        self,
        to_email: str,
        job_id: int,
        total_files: int,
        total_size: int,
        files_transferred: int,
        files_failed: int,
        started_at: datetime,
        completed_at: datetime,
        source_provider: str,
        dest_provider: str
    ) -> bool:
        """
        Send transfer completion notification email.

        Args:
            to_email: Recipient email address
            job_id: Transfer job ID
            total_files: Total number of files
            total_size: Total size in bytes
            files_transferred: Number of successfully transferred files
            files_failed: Number of failed files
            started_at: Transfer start timestamp
            completed_at: Transfer completion timestamp
            source_provider: Source cloud provider name
            dest_provider: Destination cloud provider name

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.ses_client:
            logger.error("Cannot send email - SES client not configured")
            return False

        try:
            # Format duration
            duration = self._format_duration(started_at, completed_at)

            # Generate email content
            html_body = self._generate_completion_email_html(
                user_name=to_email.split('@')[0],
                job_id=job_id,
                total_files=total_files,
                total_size=total_size,
                files_transferred=files_transferred,
                files_failed=files_failed,
                duration=duration,
                source_provider=source_provider.capitalize(),
                dest_provider=dest_provider.capitalize()
            )

            # Send email via SES
            response = self.ses_client.send_email(
                Source=settings.SES_FROM_EMAIL or "noreply@cloudshift.com",
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {
                        'Data': f'CloudShift Transfer Complete - Job #{job_id}',
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': html_body,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )

            message_id = response.get('MessageId')
            logger.info(f"Sent completion email to {to_email} for job {job_id} (MessageId: {message_id})")
            return True

        except ClientError as e:
            logger.error(
                f"Failed to send completion email to {to_email} for job {job_id}: {e.response['Error']['Message']}",
                exc_info=True
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending completion email to {to_email} for job {job_id}: {str(e)}",
                exc_info=True
            )
            return False

    async def send_transfer_failure_email(
        self,
        to_email: str,
        job_id: int,
        total_files: int,
        files_attempted: int,
        files_failed: int,
        error_message: str,
        source_provider: str,
        dest_provider: str
    ) -> bool:
        """
        Send transfer failure notification email.

        Args:
            to_email: Recipient email address
            job_id: Transfer job ID
            total_files: Total number of files
            files_attempted: Number of files attempted
            files_failed: Number of failed files
            error_message: Main error message
            source_provider: Source cloud provider name
            dest_provider: Destination cloud provider name

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.ses_client:
            logger.error("Cannot send email - SES client not configured")
            return False

        try:
            # Generate email content
            html_body = self._generate_failure_email_html(
                user_name=to_email.split('@')[0],
                job_id=job_id,
                total_files=total_files,
                files_attempted=files_attempted,
                files_failed=files_failed,
                error_message=error_message,
                source_provider=source_provider.capitalize(),
                dest_provider=dest_provider.capitalize()
            )

            # Send email via SES
            response = self.ses_client.send_email(
                Source=settings.SES_FROM_EMAIL or "noreply@cloudshift.com",
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {
                        'Data': f'CloudShift Transfer Failed - Job #{job_id}',
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': html_body,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )

            message_id = response.get('MessageId')
            logger.info(f"Sent failure email to {to_email} for job {job_id} (MessageId: {message_id})")
            return True

        except ClientError as e:
            logger.error(
                f"Failed to send failure email to {to_email} for job {job_id}: {e.response['Error']['Message']}",
                exc_info=True
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending failure email to {to_email} for job {job_id}: {str(e)}",
                exc_info=True
            )
            return False


# Global email service instance
email_service = EmailService()
