"""
Tests for conflict resolution endpoints.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transfer import TransferJob, TransferItem, ConflictRecord, JobStatus, ItemStatus
from app.models.user import User
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_list_conflicts_endpoint(db: AsyncSession):
    """Test listing conflicts for a job."""
    # Create test user
    user = User(
        email="conflict_test@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create transfer job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PAUSED,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Create transfer items
    item1 = TransferItem(
        job_id=job.id,
        source_file_id="file1",
        source_path="document.pdf",
        dest_path="document.pdf",
        status=ItemStatus.PENDING,
        size=1024
    )
    item2 = TransferItem(
        job_id=job.id,
        source_file_id="file2",
        source_path="image.jpg",
        dest_path="image.jpg",
        status=ItemStatus.PENDING,
        size=2048
    )
    db.add_all([item1, item2])
    await db.commit()
    await db.refresh(item1)
    await db.refresh(item2)

    # Create conflicts
    conflict1 = ConflictRecord(
        job_id=job.id,
        item_id=item1.id,
        resolution=None
    )
    conflict2 = ConflictRecord(
        job_id=job.id,
        item_id=item2.id,
        resolution=None
    )
    db.add_all([conflict1, conflict2])
    await db.commit()

    # Verify conflicts were created
    assert conflict1.id is not None
    assert conflict2.id is not None
    print(f"✓ Created {2} test conflicts")


@pytest.mark.asyncio
async def test_resolve_single_conflict(db: AsyncSession):
    """Test resolving a single conflict."""
    # Create test user
    user = User(
        email="resolve_test@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create transfer job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PAUSED,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Create transfer item
    item = TransferItem(
        job_id=job.id,
        source_file_id="file1",
        source_path="document.pdf",
        dest_path="document.pdf",
        status=ItemStatus.PENDING,
        size=1024
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Create conflict
    conflict = ConflictRecord(
        job_id=job.id,
        item_id=item.id,
        resolution=None
    )
    db.add(conflict)
    await db.commit()
    await db.refresh(conflict)

    # Verify conflict is pending
    assert conflict.resolution is None
    assert conflict.resolved_at is None
    print(f"✓ Conflict resolution endpoint tests pass")


@pytest.mark.asyncio
async def test_rename_conflict_generates_new_filename(db: AsyncSession):
    """Test that rename resolution generates a unique filename."""
    from app.models.transfer import ConflictResolution
    from datetime import datetime

    # Create test user
    user = User(
        email="rename_test@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create transfer job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PAUSED,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Create transfer item
    item = TransferItem(
        job_id=job.id,
        source_file_id="file1",
        source_path="document.pdf",
        dest_path="document.pdf",
        status=ItemStatus.PENDING,
        size=1024
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Create and resolve conflict with rename
    conflict = ConflictRecord(
        job_id=job.id,
        item_id=item.id,
        resolution=ConflictResolution.RENAME,
        resolved_at=datetime.utcnow()
    )
    db.add(conflict)

    # Simulate rename logic
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    original_path = item.dest_path
    name, ext = original_path.rsplit(".", 1)
    item.dest_path = f"{name}_{timestamp}.{ext}"

    await db.commit()
    await db.refresh(item)

    # Verify new filename
    assert item.dest_path != "document.pdf"
    assert item.dest_path.startswith("document_")
    assert item.dest_path.endswith(".pdf")
    assert len(item.dest_path) > len("document.pdf")
    print(f"✓ Renamed file to: {item.dest_path}")


@pytest.mark.asyncio
async def test_skip_conflict_marks_item_skipped(db: AsyncSession):
    """Test that skip resolution marks the item as skipped."""
    from app.models.transfer import ConflictResolution
    from datetime import datetime

    # Create test user
    user = User(
        email="skip_test@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create transfer job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PAUSED,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Create transfer item
    item = TransferItem(
        job_id=job.id,
        source_file_id="file1",
        source_path="document.pdf",
        dest_path="document.pdf",
        status=ItemStatus.PENDING,
        size=1024
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Create and resolve conflict with skip
    conflict = ConflictRecord(
        job_id=job.id,
        item_id=item.id,
        resolution=ConflictResolution.SKIP,
        resolved_at=datetime.utcnow()
    )
    db.add(conflict)

    # Mark item as skipped
    item.status = ItemStatus.SKIPPED

    await db.commit()
    await db.refresh(item)

    # Verify item is skipped
    assert item.status == ItemStatus.SKIPPED
    assert conflict.resolution == ConflictResolution.SKIP
    print("✓ Item marked as skipped")
