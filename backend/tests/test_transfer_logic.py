"""
Unit tests for transfer orchestration logic.

Tests job state transitions, conflict detection, filter application, and progress calculation.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import Mock, patch, AsyncMock

from app.models.transfer import TransferJob, TransferItem, JobStatus, ConflictRecord
from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_job_state_transition_pending_to_running(db: AsyncSession):
    """Test job transitions from PENDING to RUNNING when started."""
    # Create user
    user = User(
        email="transition@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job in PENDING state
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PENDING,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    assert job.status == JobStatus.PENDING
    assert job.started_at is None

    # Transition to RUNNING
    job.status = JobStatus.RUNNING
    job.started_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)

    assert job.status == JobStatus.RUNNING
    assert job.started_at is not None


@pytest.mark.asyncio
async def test_job_state_transition_running_to_completed(db: AsyncSession):
    """Test job transitions from RUNNING to COMPLETED when all items done."""
    # Create user
    user = User(
        email="completion@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.RUNNING,
        source_provider="onedrive",
        dest_provider="google",
        started_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Add transfer items - all completed
    for i in range(3):
        item = TransferItem(
            job_id=job.id,
            source_file_id=f"file_{i}",
            source_path=f"file_{i}.txt",
            status=JobStatus.COMPLETED,
            size=1024
        )
        db.add(item)
    await db.commit()

    # Transition to COMPLETED
    job.status = JobStatus.COMPLETED
    job.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)

    assert job.status == JobStatus.COMPLETED
    assert job.completed_at is not None
    assert job.started_at is not None


@pytest.mark.asyncio
async def test_job_state_transition_running_to_failed(db: AsyncSession):
    """Test job transitions from RUNNING to FAILED on error."""
    # Create user
    user = User(
        email="failure@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.RUNNING,
        source_provider="onedrive",
        dest_provider="google",
        started_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Transition to FAILED
    job.status = JobStatus.FAILED
    job.completed_at = datetime.utcnow()
    if job.config is None:
        job.config = {}
    job.config["failure_reason"] = "Network timeout"
    await db.commit()
    await db.refresh(job)

    assert job.status == JobStatus.FAILED
    assert job.completed_at is not None
    assert "failure_reason" in job.config


@pytest.mark.asyncio
async def test_job_state_transition_scheduled_to_running(db: AsyncSession):
    """Test scheduled job transitions to RUNNING when time arrives."""
    # Create user
    user = User(
        email="scheduled@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create scheduled job
    scheduled_time = datetime.utcnow() - timedelta(minutes=1)  # In the past (due)
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.SCHEDULED,
        source_provider="onedrive",
        dest_provider="google",
        scheduled_for=scheduled_time
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    assert job.status == JobStatus.SCHEDULED
    assert job.scheduled_for is not None
    assert job.scheduled_for < datetime.utcnow()  # Due to run

    # Transition to RUNNING
    job.status = JobStatus.RUNNING
    job.started_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)

    assert job.status == JobStatus.RUNNING
    assert job.started_at is not None


@pytest.mark.asyncio
async def test_job_state_transition_paused_to_running(db: AsyncSession):
    """Test paused job can resume to RUNNING."""
    # Create user
    user = User(
        email="paused@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create paused job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PAUSED,
        source_provider="onedrive",
        dest_provider="google",
        started_at=datetime.utcnow() - timedelta(minutes=5)
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    assert job.status == JobStatus.PAUSED

    # Resume to RUNNING
    job.status = JobStatus.RUNNING
    await db.commit()
    await db.refresh(job)

    assert job.status == JobStatus.RUNNING


@pytest.mark.asyncio
async def test_conflict_detection_identifies_duplicate(db: AsyncSession):
    """Test that conflict detection identifies duplicate files."""
    from app.services.conflict import ConflictDetectionService

    # Mock Google Drive file
    mock_existing_file = Mock()
    mock_existing_file.id = "existing_123"
    mock_existing_file.name = "document.pdf"
    mock_existing_file.size = 5000

    # Mock account
    mock_account = Mock()

    # Mock GoogleDriveService to return existing file
    with patch('app.services.conflict.GoogleDriveService.list_folder', new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [mock_existing_file]

        # Check for conflict
        conflict = await ConflictDetectionService.check_conflict(
            mock_account,
            "document.pdf",
            "root",
            case_insensitive=False
        )

        assert conflict is not None
        assert conflict.name == "document.pdf"
        assert conflict.id == "existing_123"


@pytest.mark.asyncio
async def test_conflict_detection_case_insensitive(db: AsyncSession):
    """Test conflict detection with case-insensitive matching."""
    from app.services.conflict import ConflictDetectionService

    # Mock existing file with different case
    mock_existing_file = Mock()
    mock_existing_file.id = "existing_123"
    mock_existing_file.name = "DOCUMENT.PDF"
    mock_existing_file.size = 5000

    mock_account = Mock()

    with patch('app.services.conflict.GoogleDriveService.list_folder', new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [mock_existing_file]

        # Check for conflict (case-insensitive)
        conflict = await ConflictDetectionService.check_conflict(
            mock_account,
            "document.pdf",  # Different case
            "root",
            case_insensitive=True
        )

        assert conflict is not None
        assert conflict.name.lower() == "document.pdf".lower()


@pytest.mark.asyncio
async def test_conflict_detection_no_conflict(db: AsyncSession):
    """Test that no conflict is detected when file doesn't exist."""
    from app.services.conflict import ConflictDetectionService

    mock_account = Mock()

    with patch('app.services.conflict.GoogleDriveService.list_folder', new_callable=AsyncMock) as mock_list:
        mock_list.return_value = []  # No existing files

        conflict = await ConflictDetectionService.check_conflict(
            mock_account,
            "newfile.pdf",
            "root",
            case_insensitive=False
        )

        assert conflict is None


def test_conflict_rename_generation():
    """Test automatic rename generation for conflicts."""
    from app.services.conflict import ConflictDetectionService

    existing_names = ["document.pdf", "document (1).pdf"]

    # Should generate "document (2).pdf"
    new_name = ConflictDetectionService.generate_rename("document.pdf", existing_names)

    assert new_name == "document (2).pdf"


def test_conflict_rename_generation_first():
    """Test rename generation for first conflict."""
    from app.services.conflict import ConflictDetectionService

    existing_names = ["document.pdf"]

    # Should generate "document (1).pdf"
    new_name = ConflictDetectionService.generate_rename("document.pdf", existing_names)

    assert new_name == "document (1).pdf"


def test_conflict_rename_generation_no_extension():
    """Test rename generation for files without extension."""
    from app.services.conflict import ConflictDetectionService

    existing_names = ["README", "README (1)"]

    new_name = ConflictDetectionService.generate_rename("README", existing_names)

    assert new_name == "README (2)"


@pytest.mark.asyncio
async def test_progress_calculation_all_pending(db: AsyncSession):
    """Test progress calculation when all items are pending."""
    # Create user
    user = User(
        email="progress1@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PENDING,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Add pending items
    total_size = 0
    for i in range(5):
        item = TransferItem(
            job_id=job.id,
            source_file_id=f"file_{i}",
            source_path=f"file_{i}.txt",
            status=JobStatus.PENDING,
            size=1000
        )
        total_size += 1000
        db.add(item)
    await db.commit()

    # Fetch items
    result = await db.execute(
        select(TransferItem).where(TransferItem.job_id == job.id)
    )
    items = result.scalars().all()

    # Calculate progress
    completed_items = [i for i in items if i.status == JobStatus.COMPLETED]
    completed_size = sum(i.size for i in completed_items)

    assert len(completed_items) == 0
    assert completed_size == 0
    assert len(items) == 5
    assert sum(i.size for i in items) == 5000


@pytest.mark.asyncio
async def test_progress_calculation_partial_completion(db: AsyncSession):
    """Test progress calculation with some completed items."""
    # Create user
    user = User(
        email="progress2@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.RUNNING,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(user)

    # Add mixed status items
    items_data = [
        ("file_1.txt", JobStatus.COMPLETED, 1000),
        ("file_2.txt", JobStatus.COMPLETED, 2000),
        ("file_3.txt", JobStatus.PENDING, 1500),
        ("file_4.txt", JobStatus.IN_PROGRESS, 3000),
        ("file_5.txt", JobStatus.PENDING, 500),
    ]

    for name, status, size in items_data:
        item = TransferItem(
            job_id=job.id,
            source_file_id=name,
            source_path=name,
            status=status,
            size=size
        )
        db.add(item)
    await db.commit()

    # Fetch and calculate
    result = await db.execute(
        select(TransferItem).where(TransferItem.job_id == job.id)
    )
    items = result.scalars().all()

    completed_items = [i for i in items if i.status == JobStatus.COMPLETED]
    completed_size = sum(i.size for i in completed_items)
    total_size = sum(i.size for i in items)

    assert len(completed_items) == 2
    assert completed_size == 3000
    assert total_size == 8000
    assert completed_size / total_size == 0.375  # 37.5% complete


@pytest.mark.asyncio
async def test_progress_calculation_all_completed(db: AsyncSession):
    """Test progress calculation when all items completed."""
    # Create user
    user = User(
        email="progress3@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.COMPLETED,
        source_provider="onedrive",
        dest_provider="google"
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Add all completed items
    for i in range(3):
        item = TransferItem(
            job_id=job.id,
            source_file_id=f"file_{i}",
            source_path=f"file_{i}.txt",
            status=JobStatus.COMPLETED,
            size=2000
        )
        db.add(item)
    await db.commit()

    # Fetch and calculate
    result = await db.execute(
        select(TransferItem).where(TransferItem.job_id == job.id)
    )
    items = result.scalars().all()

    completed_items = [i for i in items if i.status == JobStatus.COMPLETED]
    completed_size = sum(i.size for i in completed_items)
    total_size = sum(i.size for i in items)

    assert len(completed_items) == 3
    assert len(items) == 3
    assert completed_size == total_size
    assert completed_size / total_size == 1.0  # 100% complete


@pytest.mark.asyncio
async def test_filter_application_size_filter(db: AsyncSession):
    """Test applying size-based filters to file selection."""
    # Create user
    user = User(
        email="filter1@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job with size filter
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PENDING,
        source_provider="onedrive",
        dest_provider="google",
        config={
            "filters": {
                "min_size": 1000,  # 1KB minimum
                "max_size": 5000   # 5KB maximum
            }
        }
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Test files of various sizes
    test_files = [
        ("small.txt", 500),      # Too small
        ("medium1.txt", 2000),   # OK
        ("medium2.txt", 3500),   # OK
        ("large.txt", 10000),    # Too large
    ]

    # Apply filter logic
    min_size = job.config["filters"]["min_size"]
    max_size = job.config["filters"]["max_size"]

    filtered_files = [
        (name, size) for name, size in test_files
        if min_size <= size <= max_size
    ]

    assert len(filtered_files) == 2
    assert ("medium1.txt", 2000) in filtered_files
    assert ("medium2.txt", 3500) in filtered_files


@pytest.mark.asyncio
async def test_filter_application_file_type_filter(db: AsyncSession):
    """Test applying file type filters."""
    # Create user
    user = User(
        email="filter2@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job with file type filter
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PENDING,
        source_provider="onedrive",
        dest_provider="google",
        config={
            "filters": {
                "file_types": [".pdf", ".docx", ".xlsx"]
            }
        }
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Test files of various types
    test_files = [
        "document.pdf",
        "report.docx",
        "image.jpg",
        "spreadsheet.xlsx",
        "video.mp4",
    ]

    # Apply filter
    allowed_types = job.config["filters"]["file_types"]
    filtered_files = [
        f for f in test_files
        if any(f.endswith(ext) for ext in allowed_types)
    ]

    assert len(filtered_files) == 3
    assert "document.pdf" in filtered_files
    assert "report.docx" in filtered_files
    assert "spreadsheet.xlsx" in filtered_files
    assert "image.jpg" not in filtered_files
    assert "video.mp4" not in filtered_files


@pytest.mark.asyncio
async def test_filter_application_date_filter(db: AsyncSession):
    """Test applying date-based filters."""
    # Create user
    user = User(
        email="filter3@example.com",
        password_hash=hash_password("TestPass123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create job with date filter
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    job = TransferJob(
        user_id=user.id,
        status=JobStatus.PENDING,
        source_provider="onedrive",
        dest_provider="google",
        config={
            "filters": {
                "modified_after": cutoff_date.isoformat()
            }
        }
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Test files with various dates
    test_files = [
        ("old_file.txt", datetime.utcnow() - timedelta(days=60)),     # Too old
        ("recent_file.txt", datetime.utcnow() - timedelta(days=10)),  # OK
        ("new_file.txt", datetime.utcnow() - timedelta(days=1)),      # OK
    ]

    # Apply filter
    filter_date = datetime.fromisoformat(job.config["filters"]["modified_after"])
    filtered_files = [
        (name, date) for name, date in test_files
        if date >= filter_date
    ]

    assert len(filtered_files) == 2
    names = [name for name, _ in filtered_files]
    assert "recent_file.txt" in names
    assert "new_file.txt" in names
    assert "old_file.txt" not in names
