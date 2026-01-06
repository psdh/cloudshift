"""
Notification service for transfer job events.

This module provides Celery tasks for sending notifications
when transfer jobs complete or fail.
"""

import logging
from datetime import datetime
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.database import get_async_session
from app.models.transfer import TransferJob, TransferItem, JobStatus
from app.models.user import User
from app.services.email import email_service
from app.services.sms import sms_service
from app.services.audit import AuditService

audit_service = AuditService()

logger = logging.getLogger(__name__)


@celery_app.task(name="app.services.notifications.send_job_notification")
def send_job_notification(job_id: int):
    """
    Send notification for a completed or failed transfer job.

    This task is called asynchronously when a job completes (success or failure).
    It respects user notification preferences and sends appropriate emails.

    Args:
        job_id: Transfer job ID

    Returns:
        dict: Summary of notifications sent
    """
    import asyncio

    logger.info(f"Sending notification for job {job_id}")

    # Run async task in sync context
    result = asyncio.run(_send_job_notification_async(job_id))

    return result


async def _send_job_notification_async(job_id: int):
    """
    Async implementation of job notification sender.

    Args:
        job_id: Transfer job ID

    Returns:
        dict: Summary with notification results
    """
    async with get_async_session() as db:
        try:
            # Fetch job with user and items
            result = await db.execute(
                select(TransferJob).where(TransferJob.id == job_id)
            )
            job = result.scalar_one_or_none()

            if not job:
                logger.error(f"Job {job_id} not found for notification")
                return {
                    "success": False,
                    "error": "Job not found"
                }

            # Fetch user
            user_result = await db.execute(
                select(User).where(User.id == job.user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                logger.error(f"User {job.user_id} not found for job {job_id}")
                return {
                    "success": False,
                    "error": "User not found"
                }

            # Check if user wants any notifications
            if not user.email_notifications and not user.sms_notifications:
                logger.info(f"User {user.id} has all notifications disabled, skipping")
                return {
                    "success": True,
                    "skipped": "notifications_disabled"
                }

            # Fetch transfer items for stats
            items_result = await db.execute(
                select(TransferItem).where(TransferItem.job_id == job_id)
            )
            items = items_result.scalars().all()

            total_files = len(items)
            files_completed = sum(1 for item in items if item.status.value == "completed")
            files_failed = sum(1 for item in items if item.status.value == "failed")
            total_size = sum(item.size or 0 for item in items)

            # Determine notification type based on job status
            email_sent = False
            sms_sent = False

            if job.status == JobStatus.COMPLETED:
                # Send completion email if enabled
                if user.email_notifications:
                    email_sent = await email_service.send_transfer_completion_email(
                        to_email=user.email,
                        job_id=job.id,
                        total_files=total_files,
                        total_size=total_size,
                        files_transferred=files_completed,
                        files_failed=files_failed,
                        started_at=job.started_at or job.created_at,
                        completed_at=job.completed_at or datetime.utcnow(),
                        source_provider=job.source_provider,
                        dest_provider=job.dest_provider
                    )

                # Send completion SMS if enabled
                if user.sms_notifications and user.phone_number:
                    sms_sent = await sms_service.send_transfer_completion_sms(
                        to_phone=user.phone_number,
                        job_id=job.id,
                        total_files=total_files,
                        files_transferred=files_completed,
                        files_failed=files_failed,
                        source_provider=job.source_provider,
                        dest_provider=job.dest_provider
                    )

                notification_type = "transfer_completed"

            elif job.status == JobStatus.FAILED:
                # Get error message from first failed item or use generic message
                error_message = "Transfer failed due to an error"
                for item in items:
                    if item.error_message:
                        error_message = item.error_message
                        break

                # Send failure email if enabled
                if user.email_notifications:
                    email_sent = await email_service.send_transfer_failure_email(
                        to_email=user.email,
                        job_id=job.id,
                        total_files=total_files,
                        files_attempted=files_completed + files_failed,
                        files_failed=files_failed,
                        error_message=error_message,
                        source_provider=job.source_provider,
                        dest_provider=job.dest_provider
                    )

                # Send failure SMS if enabled
                if user.sms_notifications and user.phone_number:
                    sms_sent = await sms_service.send_transfer_failure_sms(
                        to_phone=user.phone_number,
                        job_id=job.id,
                        error_reason=error_message,
                        source_provider=job.source_provider,
                        dest_provider=job.dest_provider
                    )

                notification_type = "transfer_failed"

            else:
                logger.warning(
                    f"Job {job_id} has unexpected status {job.status.value} for notification"
                )
                return {
                    "success": False,
                    "error": f"Unexpected job status: {job.status.value}"
                }

            # Log notification in audit log
            if email_sent or sms_sent:
                notification_channels = []
                if email_sent:
                    notification_channels.append("email")
                if sms_sent:
                    notification_channels.append("sms")

                await audit_service.log_action(
                    db=db,
                    user_id=user.id,
                    action=notification_type,
                    resource_type="transfer_job",
                    resource_id=job.id,
                    details={
                        "notification_channels": notification_channels,
                        "email": user.email if email_sent else None,
                        "phone": user.phone_number if sms_sent else None,
                        "files_completed": files_completed,
                        "files_failed": files_failed
                    }
                )

            logger.info(
                f"Notification sent for job {job_id}: "
                f"email={email_sent}, sms={sms_sent}, type={notification_type}"
            )

            return {
                "success": True,
                "job_id": job_id,
                "notification_type": notification_type,
                "email_sent": email_sent,
                "sms_sent": sms_sent,
                "recipient_email": user.email if email_sent else None,
                "recipient_phone": user.phone_number if sms_sent else None
            }

        except Exception as e:
            logger.error(
                f"Error sending notification for job {job_id}: {str(e)}",
                exc_info=True
            )
            return {
                "success": False,
                "job_id": job_id,
                "error": str(e)
            }
