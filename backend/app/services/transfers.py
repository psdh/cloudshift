"""
Transfer service tasks for Celery.

This module contains Celery tasks for transfer job management,
including scheduled transfer execution.
"""

import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import get_async_session
from app.models.transfer import TransferJob, JobStatus
from app.services.transfer_worker import transfer_job_orchestrator

logger = logging.getLogger(__name__)


@celery_app.task(name="app.services.transfers.check_scheduled_transfers")
def check_scheduled_transfers():
    """
    Periodic task to check for scheduled transfers that are due to start.

    This task runs every minute via Celery Beat and:
    1. Finds jobs where scheduled_for <= now and status = 'scheduled'
    2. Starts the transfer orchestrator for each due job
    3. Updates job status to 'running'
    4. Handles timezone correctly (stores and compares in UTC)

    Returns:
        dict: Summary of jobs started
    """
    import asyncio

    logger.info("Checking for scheduled transfers...")

    # Run async task in sync context
    result = asyncio.run(_check_scheduled_transfers_async())

    return result


async def _check_scheduled_transfers_async():
    """
    Async implementation of scheduled transfer checker.

    Returns:
        dict: Summary with count of jobs started and their IDs
    """
    async with get_async_session() as db:
        try:
            # Get current time in UTC
            now_utc = datetime.utcnow()

            # Find jobs that are due to start
            result = await db.execute(
                select(TransferJob).where(
                    TransferJob.status == JobStatus.SCHEDULED,
                    TransferJob.scheduled_for <= now_utc
                )
            )
            due_jobs = result.scalars().all()

            if not due_jobs:
                logger.debug("No scheduled transfers due for execution")
                return {
                    "jobs_started": 0,
                    "job_ids": []
                }

            started_job_ids = []

            for job in due_jobs:
                try:
                    # Update job status to running
                    job.status = JobStatus.RUNNING
                    job.started_at = now_utc

                    # Commit the status change before starting the job
                    await db.commit()

                    # Start the transfer job orchestrator (Celery task)
                    transfer_job_orchestrator.delay(job.id)

                    started_job_ids.append(job.id)
                    logger.info(
                        f"Started scheduled transfer job {job.id} "
                        f"(was scheduled for {job.scheduled_for.isoformat()})"
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to start scheduled job {job.id}: {str(e)}",
                        exc_info=True
                    )
                    # Mark job as failed
                    job.status = JobStatus.FAILED
                    job.completed_at = now_utc
                    await db.commit()

            return {
                "jobs_started": len(started_job_ids),
                "job_ids": started_job_ids,
                "timestamp": now_utc.isoformat()
            }

        except Exception as e:
            logger.error(
                f"Error in check_scheduled_transfers: {str(e)}",
                exc_info=True
            )
            return {
                "jobs_started": 0,
                "job_ids": [],
                "error": str(e)
            }
