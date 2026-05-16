"""
Transfer worker tasks: OneDrive -> S3 -> Google Drive.

The pipeline streams: the file is piped chunk-by-chunk from OneDrive into an
S3 multipart upload (computing the MD5 as it goes), then streamed back out of
S3 into a Google Drive resumable upload. At most a few MiB are held in memory
at any time, so files up to the product's 100 GB requirement transfer without
being buffered whole.
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.core.database import worker_session
from app.models.audit_log import AuditAction
from app.models.connected_account import ConnectedAccount
from app.models.transfer import (
    ConflictRecord,
    ConflictResolution,
    ItemStatus,
    JobStatus,
    TransferItem,
    TransferJob,
)
from app.services.audit import AuditService
from app.services.conflict import ConflictDetectionService
from app.services.google_drive import GoogleDriveService
from app.services.onedrive import OneDriveService
from app.services.progress_tracker import progress_tracker
from app.services.s3 import S3Service

logger = logging.getLogger(__name__)


def trigger_notification(job_id: int):
    """Enqueue the completion/failure notification (best-effort)."""
    try:
        from app.services.notifications import send_job_notification

        send_job_notification.delay(job_id)
    except Exception as e:  # broker down must not fail the transfer
        logger.warning(f"Could not enqueue notification for job {job_id}: {e}")


class TransferError(Exception):
    """Raised for unrecoverable transfer errors."""


class _Counter:
    """Mutable byte counter shared with the hashing pass-through generator."""

    __slots__ = ("total",)

    def __init__(self):
        self.total = 0


async def _hashing_passthrough(
    stream: AsyncIterator[bytes], hasher, counter: "_Counter"
) -> AsyncIterator[bytes]:
    """Yield the source stream unchanged while updating `hasher`/`counter`."""
    async for chunk in stream:
        hasher.update(chunk)
        counter.total += len(chunk)
        yield chunk


@celery_app.task(name="app.services.transfer_worker.transfer_single_file", bind=True)
def transfer_single_file(self, item_id: int) -> dict:
    """Transfer a single file: OneDrive -> S3 -> Google Drive (streamed)."""

    async def _transfer():
        async with worker_session() as db:
            item = None
            s3_service = S3Service()
            s3_key = None
            try:
                item = (
                    await db.execute(
                        select(TransferItem).where(TransferItem.id == item_id)
                    )
                ).scalar_one_or_none()
                if not item:
                    raise TransferError(f"Transfer item {item_id} not found")

                job = (
                    await db.execute(
                        select(TransferJob).where(TransferJob.id == item.job_id)
                    )
                ).scalar_one_or_none()
                if not job:
                    raise TransferError(f"Transfer job {item.job_id} not found")

                item.status = ItemStatus.IN_PROGRESS
                item.started_at = datetime.utcnow()
                await db.commit()
                await progress_tracker.update_file_start(
                    job.id, item.source_path, item.size
                )

                source_account = (
                    await db.execute(
                        select(ConnectedAccount).where(
                            ConnectedAccount.user_id == job.user_id,
                            ConnectedAccount.provider == job.source_provider,
                        )
                    )
                ).scalar_one_or_none()
                dest_account = (
                    await db.execute(
                        select(ConnectedAccount).where(
                            ConnectedAccount.user_id == job.user_id,
                            ConnectedAccount.provider == job.dest_provider,
                        )
                    )
                ).scalar_one_or_none()
                if not source_account or not dest_account:
                    raise TransferError("Source or destination account not found")

                dest_folder_id = job.dest_folder_id or "root"
                config = job.config or {}
                strategy = config.get("conflict_strategy", "ask")

                # --- Conflict handling (BEFORE moving any data) ---
                existing = await ConflictDetectionService.check_conflict(
                    dest_account, item.dest_path, dest_folder_id
                )
                if existing:
                    conflict = ConflictRecord(
                        job_id=job.id, item_id=item.id, resolution=None
                    )
                    db.add(conflict)
                    await db.commit()
                    await AuditService.log_action(
                        db=db,
                        action=AuditAction.TRANSFER_CONFLICT_DETECTED,
                        user_id=job.user_id,
                        resource_type="transfer_item",
                        resource_id=str(item.id),
                        details={"job_id": job.id, "file_name": item.dest_path},
                    )

                    if strategy == "ask":
                        # Hold the item and pause the job for user resolution.
                        job.status = JobStatus.PAUSED
                        await db.commit()
                        return {
                            "status": "paused",
                            "item_id": item_id,
                            "conflict_id": conflict.id,
                        }

                    if strategy == "skip_all":
                        item.status = ItemStatus.SKIPPED
                        item.completed_at = datetime.utcnow()
                        conflict.resolution = ConflictResolution.SKIP
                        conflict.resolved_at = datetime.utcnow()
                        await db.commit()
                        await AuditService.log_action(
                            db=db,
                            action=AuditAction.TRANSFER_CONFLICT_RESOLVED,
                            user_id=job.user_id,
                            resource_type="transfer_item",
                            resource_id=str(item.id),
                            details={"resolution": "skip", "file_name": item.dest_path},
                        )
                        await progress_tracker.update_file_complete(
                            job.id, success=True, bytes_transferred=0
                        )
                        return {"status": "skipped", "item_id": item_id}

                    if strategy == "rename_all":
                        existing_files = await GoogleDriveService.list_folder(
                            dest_account, dest_folder_id
                        )
                        new_name = ConflictDetectionService.generate_rename(
                            item.dest_path,
                            [f.name for f in existing_files if f.type == "file"],
                        )
                        item.dest_path = new_name
                        conflict.resolution = ConflictResolution.RENAME
                        conflict.resolved_at = datetime.utcnow()
                        await db.commit()
                        await AuditService.log_action(
                            db=db,
                            action=AuditAction.TRANSFER_CONFLICT_RESOLVED,
                            user_id=job.user_id,
                            resource_type="transfer_item",
                            resource_id=str(item.id),
                            details={"resolution": "rename", "new_name": new_name},
                        )

                    elif strategy == "overwrite_all":
                        # Real overwrite: remove the existing Drive file so the
                        # new upload replaces it (Drive allows same-name files).
                        await GoogleDriveService.delete_file(dest_account, existing.id)
                        conflict.resolution = ConflictResolution.OVERWRITE
                        conflict.resolved_at = datetime.utcnow()
                        await db.commit()
                        await AuditService.log_action(
                            db=db,
                            action=AuditAction.TRANSFER_CONFLICT_RESOLVED,
                            user_id=job.user_id,
                            resource_type="transfer_item",
                            resource_id=str(item.id),
                            details={"resolution": "overwrite", "file_name": item.dest_path},
                        )

                # --- Stream OneDrive -> S3 (multipart, incremental MD5) ---
                s3_key = f"transfers/{job.id}/{item.id}/{item.source_path}"
                hasher = hashlib.md5()
                counter = _Counter()
                src_stream = OneDriveService.download_file(
                    source_account, item.source_file_id
                )
                ok = await s3_service.upload_stream(
                    s3_key, _hashing_passthrough(src_stream, hasher, counter)
                )
                if not ok:
                    raise TransferError("Failed to stage file in S3")
                source_checksum = hasher.hexdigest()
                bytes_seen = counter.total
                if item.size and bytes_seen != item.size:
                    raise TransferError(
                        f"Size mismatch from source: expected {item.size}, got {bytes_seen}"
                    )

                # --- Stream S3 -> Google Drive ---
                uploaded = await GoogleDriveService.upload_file(
                    dest_account,
                    item.dest_path,
                    s3_service.download_stream(s3_key),
                    dest_folder_id,
                    total_size=item.size or bytes_seen,
                )
                expected = item.size or bytes_seen
                if uploaded.size and expected and uploaded.size != expected:
                    raise TransferError(
                        f"Destination size mismatch: expected {expected}, "
                        f"got {uploaded.size}"
                    )

                # Exactly-once: delete the intermediate copy now that the
                # destination upload is confirmed.
                await s3_service.delete_file(s3_key)
                s3_key = None

                item.status = ItemStatus.COMPLETED
                item.completed_at = datetime.utcnow()
                item.error_message = None
                await db.commit()
                await progress_tracker.update_file_complete(
                    job.id, success=True, bytes_transferred=bytes_seen
                )
                return {
                    "status": "success",
                    "item_id": item_id,
                    "checksum": source_checksum,
                    "dest_file_id": uploaded.id,
                }

            except Exception as e:
                logger.error(
                    f"Transfer failed for item {item_id}: {e}", exc_info=True
                )
                if item is not None:
                    item.status = ItemStatus.FAILED
                    item.error_message = str(e)
                    item.completed_at = datetime.utcnow()
                    try:
                        await db.commit()
                        await progress_tracker.update_file_complete(
                            item.job_id, success=False, bytes_transferred=0
                        )
                    except Exception:
                        pass
                if s3_key:  # best-effort cleanup of the partial staged copy
                    try:
                        await s3_service.delete_file(s3_key)
                    except Exception:
                        pass
                raise TransferError(f"Transfer failed: {e}")

    return asyncio.run(_transfer())


@celery_app.task(name="app.services.transfer_worker.transfer_job_orchestrator", bind=True)
def transfer_job_orchestrator(self, job_id: int) -> dict:
    """Queue every outstanding item of a job (resumable, no truncation)."""

    async def _orchestrate():
        async with worker_session() as db:
            try:
                job = (
                    await db.execute(
                        select(TransferJob)
                        .options(selectinload(TransferJob.items))
                        .where(TransferJob.id == job_id)
                    )
                ).scalar_one_or_none()
                if not job:
                    raise TransferError(f"Transfer job {job_id} not found")

                if job.status == JobStatus.PAUSED:
                    return {"status": "paused", "job_id": job_id}

                total_files = len(job.items)
                total_size = sum(i.size or 0 for i in job.items)
                await progress_tracker.initialize_progress(
                    job.id, total_files, total_size
                )

                # Resumable: (re)queue anything not yet finished — PENDING plus
                # IN_PROGRESS items left behind by an interrupted worker.
                outstanding = [
                    i
                    for i in job.items
                    if i.status in (ItemStatus.PENDING, ItemStatus.IN_PROGRESS)
                ]

                if not outstanding:
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.utcnow()
                    await db.commit()
                    trigger_notification(job_id)
                    return {"status": "completed", "job_id": job_id}

                job.status = JobStatus.RUNNING
                if job.started_at is None:
                    job.started_at = datetime.utcnow()
                await db.commit()

                # Enqueue ALL outstanding items. Parallelism is bounded by the
                # Celery worker concurrency, not by truncating the work.
                for item in outstanding:
                    transfer_single_file.delay(item.id)

                logger.info(
                    f"Queued {len(outstanding)} item(s) for job {job_id} "
                    f"({total_files} total)"
                )
                return {
                    "status": "running",
                    "job_id": job_id,
                    "queued": len(outstanding),
                }

            except Exception as e:
                logger.error(
                    f"Orchestration failed for job {job_id}: {e}", exc_info=True
                )
                job = (
                    await db.execute(
                        select(TransferJob).where(TransferJob.id == job_id)
                    )
                ).scalar_one_or_none()
                if job:
                    job.status = JobStatus.FAILED
                    job.completed_at = datetime.utcnow()
                    await db.commit()
                    trigger_notification(job_id)
                raise TransferError(f"Job orchestration failed: {e}")

    return asyncio.run(_orchestrate())
