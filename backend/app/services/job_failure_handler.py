"""
Graceful job failure handling service.

This module handles unrecoverable job failures with proper cleanup,
progress preservation, and user notifications.
"""

import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transfer import TransferJob, TransferItem, JobStatus
from app.services.s3 import S3Service
from app.services.notifications import send_job_notification

logger = logging.getLogger(__name__)


class JobFailureHandler:
    """Service for handling job failures gracefully."""

    def __init__(self):
        """Initialize failure handler."""
        self.s3_service = S3Service()

    async def handle_job_failure(
        self,
        db: AsyncSession,
        job_id: int,
        error_message: str,
        preserve_progress: bool = True
    ) -> dict:
        """
        Handle a job failure with proper cleanup and notifications.

        This method:
        1. Marks job as FAILED
        2. Preserves completed file progress
        3. Cleans up S3 intermediate files
        4. Triggers user notification
        5. Ensures job can be retried later

        Args:
            db: Database session
            job_id: Transfer job ID
            error_message: Error message describing the failure
            preserve_progress: Whether to preserve completed files (default: True)

        Returns:
            dict: Summary of failure handling actions
        """
        try:
            # Fetch job with items
            result = await db.execute(
                select(TransferJob).where(TransferJob.id == job_id)
            )
            job = result.scalar_one_or_none()

            if not job:
                logger.error(f"Job {job_id} not found for failure handling")
                return {
                    "success": False,
                    "error": "Job not found"
                }

            # Fetch transfer items
            items_result = await db.execute(
                select(TransferItem).where(TransferItem.job_id == job_id)
            )
            items = items_result.scalars().all()

            # Count progress
            completed_items = [item for item in items if item.status == JobStatus.COMPLETED]
            failed_items = [item for item in items if item.status == JobStatus.FAILED]
            pending_items = [
                item for item in items
                if item.status in [JobStatus.PENDING, JobStatus.IN_PROGRESS]
            ]

            logger.info(
                f"Handling failure for job {job_id}: "
                f"{len(completed_items)} completed, "
                f"{len(failed_items)} failed, "
                f"{len(pending_items)} pending"
            )

            # Mark job as failed
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()

            # Store error message in job config if not already set
            if job.config is None:
                job.config = {}
            job.config["failure_reason"] = error_message
            job.config["failed_at"] = datetime.utcnow().isoformat()
            job.config["can_retry"] = True

            if preserve_progress:
                # Completed files stay completed (already done, just logging)
                logger.info(
                    f"Preserving progress: {len(completed_items)} completed files will not be re-transferred on retry"
                )
            else:
                # Reset all items to pending for full retry
                for item in completed_items:
                    item.status = JobStatus.PENDING
                logger.info(f"Reset {len(completed_items)} completed items to pending for full retry")

            # Mark pending items as failed
            for item in pending_items:
                if not item.error_message:
                    item.error_message = error_message
                item.status = JobStatus.FAILED
                item.completed_at = datetime.utcnow()

            await db.commit()

            # Clean up S3 intermediate files
            s3_cleanup_count = await self._cleanup_s3_files(job_id, items)

            # Trigger notification asynchronously
            # Import here to avoid circular dependency
            from app.services.transfer_worker import trigger_notification
            trigger_notification(job_id)

            logger.info(
                f"Job {job_id} failure handled: "
                f"preserved {len(completed_items)} completed files, "
                f"cleaned up {s3_cleanup_count} S3 files"
            )

            return {
                "success": True,
                "job_id": job_id,
                "status": "failed",
                "completed_items": len(completed_items),
                "failed_items": len(failed_items),
                "pending_items": len(pending_items),
                "s3_files_cleaned": s3_cleanup_count,
                "can_retry": True,
                "error_message": error_message
            }

        except Exception as e:
            logger.error(
                f"Error handling job failure for job {job_id}: {str(e)}",
                exc_info=True
            )
            return {
                "success": False,
                "job_id": job_id,
                "error": str(e)
            }

    async def _cleanup_s3_files(self, job_id: int, items: list) -> int:
        """
        Clean up S3 intermediate files for a failed job.

        Args:
            job_id: Transfer job ID
            items: List of transfer items

        Returns:
            Number of S3 files cleaned up
        """
        cleanup_count = 0

        for item in items:
            # Only clean up files that are in pending or failed state
            # (completed files should have already been cleaned up)
            if item.status in [JobStatus.PENDING, JobStatus.FAILED, JobStatus.IN_PROGRESS]:
                s3_key = f"transfers/{job_id}/{item.id}/{item.source_path}"

                try:
                    # Check if file exists before trying to delete
                    if await self.s3_service.file_exists(s3_key):
                        await self.s3_service.delete_file(s3_key)
                        cleanup_count += 1
                        logger.debug(f"Deleted S3 file: {s3_key}")
                except Exception as e:
                    # Log but don't fail - S3 cleanup is best-effort
                    logger.warning(f"Failed to clean up S3 file {s3_key}: {str(e)}")

        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} S3 intermediate files for job {job_id}")

        return cleanup_count

    async def mark_item_failed(
        self,
        db: AsyncSession,
        item_id: int,
        error_message: str,
        max_retries: int = 3
    ) -> dict:
        """
        Mark a transfer item as failed after max retries.

        Args:
            db: Database session
            item_id: Transfer item ID
            error_message: Error message
            max_retries: Maximum number of retries before permanent failure

        Returns:
            dict: Summary of action taken
        """
        try:
            result = await db.execute(
                select(TransferItem).where(TransferItem.id == item_id)
            )
            item = result.scalar_one_or_none()

            if not item:
                logger.error(f"Item {item_id} not found for failure marking")
                return {
                    "success": False,
                    "error": "Item not found"
                }

            # Mark item as failed
            item.status = JobStatus.FAILED
            item.error_message = error_message
            item.completed_at = datetime.utcnow()

            await db.commit()

            logger.info(f"Marked item {item_id} as failed: {error_message}")

            return {
                "success": True,
                "item_id": item_id,
                "status": "failed",
                "error_message": error_message
            }

        except Exception as e:
            logger.error(
                f"Error marking item {item_id} as failed: {str(e)}",
                exc_info=True
            )
            return {
                "success": False,
                "item_id": item_id,
                "error": str(e)
            }


# Global failure handler instance
job_failure_handler = JobFailureHandler()
