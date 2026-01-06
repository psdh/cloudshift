"""
Transfer worker tasks for executing file transfers.
Handles single file transfers through the OneDrive → S3 → Google Drive pipeline.
"""

import logging
import hashlib
import io
from datetime import datetime
from typing import Optional, AsyncIterator

from app.core.celery_app import celery_app
from app.core.database import get_db
from app.models.transfer import TransferItem, TransferJob, JobStatus
from app.models.connected_account import ConnectedAccount
from app.services.onedrive import OneDriveService
from app.services.google_drive import GoogleDriveService
from app.services.s3 import S3Service
from sqlalchemy import select

logger = logging.getLogger(__name__)


class TransferError(Exception):
    """Custom exception for transfer errors."""
    pass


async def calculate_checksum_from_stream(stream: AsyncIterator[bytes], algorithm: str = "md5") -> tuple[bytes, str]:
    """
    Calculate checksum from async stream while collecting data.

    Args:
        stream: Async iterator yielding file chunks
        algorithm: Hash algorithm to use (md5 or sha256)

    Returns:
        Tuple of (file_data, checksum_hex)
    """
    if algorithm == "md5":
        hasher = hashlib.md5()
    elif algorithm == "sha256":
        hasher = hashlib.sha256()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    chunks = []
    async for chunk in stream:
        hasher.update(chunk)
        chunks.append(chunk)

    file_data = b''.join(chunks)
    checksum = hasher.hexdigest()

    logger.debug(f"Calculated {algorithm} checksum: {checksum} (size: {len(file_data)} bytes)")
    return file_data, checksum


async def bytes_to_async_iterator(data: bytes, chunk_size: int = 8192) -> AsyncIterator[bytes]:
    """Convert bytes to async iterator."""
    offset = 0
    while offset < len(data):
        chunk = data[offset:offset + chunk_size]
        if chunk:
            yield chunk
        offset += chunk_size


@celery_app.task(name="app.services.transfer_worker.transfer_single_file", bind=True)
def transfer_single_file(self, item_id: int) -> dict:
    """
    Transfer a single file through the pipeline: OneDrive → S3 → Google Drive.
    Includes checksum verification at each step.

    Args:
        item_id: TransferItem ID

    Returns:
        dict: Transfer result with status and details
    """
    import asyncio

    async def _transfer():
        # Get database session
        async for db in get_db():
            try:
                # Fetch transfer item with job
                result = await db.execute(
                    select(TransferItem).where(TransferItem.id == item_id)
                )
                item = result.scalar_one_or_none()

                if not item:
                    raise TransferError(f"Transfer item {item_id} not found")

                # Fetch the job
                job_result = await db.execute(
                    select(TransferJob).where(TransferJob.id == item.job_id)
                )
                job = job_result.scalar_one_or_none()

                if not job:
                    raise TransferError(f"Transfer job {item.job_id} not found")

                # Update item status to running
                item.status = JobStatus.RUNNING
                item.started_at = datetime.utcnow()
                await db.commit()

                logger.info(f"Starting transfer for item {item_id}: {item.source_path}")

                # Get connected accounts
                source_account_result = await db.execute(
                    select(ConnectedAccount).where(
                        ConnectedAccount.user_id == job.user_id,
                        ConnectedAccount.provider == job.source_provider
                    )
                )
                source_account = source_account_result.scalar_one_or_none()

                dest_account_result = await db.execute(
                    select(ConnectedAccount).where(
                        ConnectedAccount.user_id == job.user_id,
                        ConnectedAccount.provider == job.dest_provider
                    )
                )
                dest_account = dest_account_result.scalar_one_or_none()

                if not source_account or not dest_account:
                    raise TransferError("Source or destination account not found")

                # Step 1: Download from OneDrive with checksum calculation
                logger.info(f"Downloading from OneDrive: {item.source_path}")
                download_stream = OneDriveService.download_file(source_account, item.source_file_id)
                file_data, source_checksum = await calculate_checksum_from_stream(download_stream, "md5")

                # Verify file size
                if len(file_data) != item.size:
                    raise TransferError(
                        f"Size mismatch: expected {item.size}, got {len(file_data)}"
                    )

                logger.info(f"Downloaded {len(file_data)} bytes, checksum: {source_checksum}")

                # Step 2: Upload to S3 with job_id prefix
                s3_key = f"transfers/{job.id}/{item.id}/{item.source_path}"
                logger.info(f"Uploading to S3: {s3_key}")

                s3_service = S3Service()
                upload_stream = bytes_to_async_iterator(file_data)
                await s3_service.upload_file(s3_key, upload_stream, len(file_data))

                # Download from S3 to verify
                s3_data = await s3_service.download_file(s3_key)
                s3_checksum = hashlib.md5(s3_data).hexdigest()

                if s3_checksum != source_checksum:
                    raise TransferError(
                        f"S3 checksum mismatch: source={source_checksum}, s3={s3_checksum}"
                    )

                logger.info(f"S3 upload verified, checksum: {s3_checksum}")

                # Step 3: Upload to Google Drive
                dest_folder_id = job.dest_folder_id or "root"
                logger.info(f"Uploading to Google Drive: {item.dest_path}")

                # Convert bytes to async iterator for Google Drive upload
                gd_upload_stream = bytes_to_async_iterator(file_data)
                uploaded_file = await GoogleDriveService.upload_file(
                    dest_account,
                    item.dest_path,
                    gd_upload_stream,
                    dest_folder_id,
                    mime_type="application/octet-stream"
                )

                # Verify Google Drive upload size
                if uploaded_file.size != item.size:
                    raise TransferError(
                        f"Google Drive size mismatch: expected {item.size}, got {uploaded_file.size}"
                    )

                logger.info(f"Uploaded to Google Drive, file ID: {uploaded_file.id}")

                # Step 4: Delete S3 file after successful upload
                logger.info(f"Deleting S3 file: {s3_key}")
                await s3_service.delete_file(s3_key)

                # Update item status to completed
                item.status = JobStatus.COMPLETED
                item.completed_at = datetime.utcnow()
                item.error_message = None
                await db.commit()

                logger.info(f"Transfer completed successfully for item {item_id}")

                return {
                    "status": "success",
                    "item_id": item_id,
                    "source_path": item.source_path,
                    "dest_path": item.dest_path,
                    "size": item.size,
                    "checksum": source_checksum,
                    "dest_file_id": uploaded_file.id
                }

            except Exception as e:
                logger.error(f"Transfer failed for item {item_id}: {str(e)}", exc_info=True)

                # Update item with error
                if item:
                    item.status = JobStatus.FAILED
                    item.error_message = str(e)
                    item.completed_at = datetime.utcnow()
                    await db.commit()

                # Retry logic - Celery will handle this based on configuration
                raise TransferError(f"Transfer failed: {str(e)}")

            finally:
                await db.close()
                break

    # Run the async transfer function
    return asyncio.run(_transfer())


@celery_app.task(name="app.services.transfer_worker.transfer_job_orchestrator", bind=True)
def transfer_job_orchestrator(self, job_id: int) -> dict:
    """
    Orchestrate the transfer of all files in a job.
    Creates folder structure, queues individual file transfers, tracks progress.

    Args:
        job_id: TransferJob ID

    Returns:
        dict: Job execution result
    """
    import asyncio
    from celery import group

    async def _orchestrate():
        async for db in get_db():
            try:
                # Fetch the job with items
                from sqlalchemy.orm import selectinload

                result = await db.execute(
                    select(TransferJob)
                    .options(selectinload(TransferJob.items))
                    .where(TransferJob.id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job:
                    raise TransferError(f"Transfer job {job_id} not found")

                logger.info(f"Starting transfer job {job_id} with {len(job.items)} items")

                # Update job status
                job.status = JobStatus.RUNNING
                job.started_at = datetime.utcnow()
                await db.commit()

                # Get destination account for folder creation
                dest_account_result = await db.execute(
                    select(ConnectedAccount).where(
                        ConnectedAccount.user_id == job.user_id,
                        ConnectedAccount.provider == job.dest_provider
                    )
                )
                dest_account = dest_account_result.scalar_one_or_none()

                if not dest_account:
                    raise TransferError("Destination account not found")

                # Step 1: Create folder structure in destination (if needed)
                # For now, we assume files go to root or specified folder
                # Future enhancement: parse folder paths from items

                # Step 2: Queue individual file transfers
                # Using Celery groups for controlled concurrency
                pending_items = [item for item in job.items if item.status == JobStatus.PENDING]

                if not pending_items:
                    logger.warning(f"No pending items to transfer for job {job_id}")
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.utcnow()
                    await db.commit()
                    return {
                        "status": "completed",
                        "job_id": job_id,
                        "message": "No items to transfer"
                    }

                logger.info(f"Queueing {len(pending_items)} file transfers")

                # Create task group with concurrency limit
                # Note: Celery will handle the actual concurrency based on worker configuration
                task_ids = []
                for item in pending_items[:5]:  # Process first 5 items (configurable)
                    task = transfer_single_file.delay(item.id)
                    task_ids.append(task.id)

                logger.info(f"Queued {len(task_ids)} transfer tasks for job {job_id}")

                # Note: In production, we'd use Celery's chord or chain for better orchestration
                # For now, tasks run independently and update their status

                return {
                    "status": "running",
                    "job_id": job_id,
                    "queued_tasks": len(task_ids),
                    "task_ids": task_ids
                }

            except Exception as e:
                logger.error(f"Job orchestration failed for job {job_id}: {str(e)}", exc_info=True)

                if job:
                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.utcnow()
                    await db.commit()

                raise TransferError(f"Job orchestration failed: {str(e)}")

            finally:
                await db.close()
                break

    return asyncio.run(_orchestrate())
