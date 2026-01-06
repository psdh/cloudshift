"""
Tests for graceful job failure handling.
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transfer import TransferJob, TransferItem, JobStatus
from app.models.user import User
from app.services.job_failure_handler import JobFailureHandler
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_handle_job_failure_marks_job_as_failed(db: AsyncSession):
    """Test that handle_job_failure marks job as FAILED."""
    # Create test user
    user = User(
        email="failure_test@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create transfer job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.RUNNING,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Create transfer items with mixed statuses
    completed_item = TransferItem(
        job_id=job.id,
        source_file_id="file1",
        source_path="completed.pdf",
        status=JobStatus.COMPLETED,
        size=1024
    )
    pending_item = TransferItem(
        job_id=job.id,
        source_file_id="file2",
        source_path="pending.pdf",
        status=JobStatus.PENDING,
        size=2048
    )
    db.add_all([completed_item, pending_item])
    await db.commit()

    # Handle failure
    handler = JobFailureHandler()
    result = await handler.handle_job_failure(
        db=db,
        job_id=job.id,
        error_message="Test failure",
        preserve_progress=True
    )

    # Verify results
    assert result["success"] is True
    assert result["status"] == "failed"
    assert result["completed_items"] == 1
    assert result["pending_items"] == 1
    assert result["can_retry"] is True

    # Refresh job from database
    await db.refresh(job)

    # Verify job status
    assert job.status == JobStatus.FAILED
    assert job.completed_at is not None
    assert "failure_reason" in job.config
    assert job.config["failure_reason"] == "Test failure"
    assert job.config["can_retry"] is True


@pytest.mark.asyncio
async def test_handle_job_failure_preserves_completed_items(db: AsyncSession):
    """Test that completed items remain completed."""
    # Create test user
    user = User(
        email="preserve_test@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job with completed item
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.RUNNING,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    completed_item = TransferItem(
        job_id=job.id,
        source_file_id="file1",
        source_path="completed.pdf",
        status=JobStatus.COMPLETED,
        size=1024,
        completed_at=datetime.utcnow()
    )
    db.add(completed_item)
    await db.commit()

    # Handle failure with preserve_progress=True
    handler = JobFailureHandler()
    await handler.handle_job_failure(
        db=db,
        job_id=job.id,
        error_message="Test failure",
        preserve_progress=True
    )

    # Refresh item
    await db.refresh(completed_item)

    # Verify completed item is still completed
    assert completed_item.status == JobStatus.COMPLETED
    assert completed_item.completed_at is not None


@pytest.mark.asyncio
async def test_handle_job_failure_marks_pending_as_failed(db: AsyncSession):
    """Test that pending items are marked as failed."""
    # Create test user
    user = User(
        email="pending_test@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job with pending item
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.RUNNING,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    pending_item = TransferItem(
        job_id=job.id,
        source_file_id="file1",
        source_path="pending.pdf",
        status=JobStatus.PENDING,
        size=1024
    )
    db.add(pending_item)
    await db.commit()

    # Handle failure
    handler = JobFailureHandler()
    await handler.handle_job_failure(
        db=db,
        job_id=job.id,
        error_message="Job failed",
        preserve_progress=True
    )

    # Refresh item
    await db.refresh(pending_item)

    # Verify pending item is now failed
    assert pending_item.status == JobStatus.FAILED
    assert pending_item.error_message == "Job failed"
    assert pending_item.completed_at is not None


@pytest.mark.asyncio
async def test_mark_item_failed(db: AsyncSession):
    """Test marking individual item as failed."""
    # Create test user
    user = User(
        email="item_fail_test@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job and item
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.RUNNING,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    item = TransferItem(
        job_id=job.id,
        source_file_id="file1",
        source_path="test.pdf",
        status=JobStatus.IN_PROGRESS,
        size=1024
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Mark item as failed
    handler = JobFailureHandler()
    result = await handler.mark_item_failed(
        db=db,
        item_id=item.id,
        error_message="Transfer timeout"
    )

    # Verify result
    assert result["success"] is True
    assert result["status"] == "failed"
    assert result["error_message"] == "Transfer timeout"

    # Refresh item
    await db.refresh(item)

    # Verify item status
    assert item.status == JobStatus.FAILED
    assert item.error_message == "Transfer timeout"
    assert item.completed_at is not None
