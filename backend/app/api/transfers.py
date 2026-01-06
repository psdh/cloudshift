from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from collections import defaultdict
import logging
import asyncio
import json

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.transfer import TransferJob, TransferItem, JobStatus, ConflictResolution, ConflictRecord, ItemStatus
from app.models.connected_account import ConnectedAccount
from app.services.onedrive import OneDriveService
from app.services.google_drive import GoogleDriveService
from app.services.conflict import ConflictDetectionService
from app.services.s3 import S3Service
from app.services.transfer_worker import transfer_single_file
from app.services.progress_tracker import progress_tracker
from pydantic import BaseModel, Field, field_validator


router = APIRouter(prefix="/api/transfers", tags=["transfers"])

logger = logging.getLogger(__name__)


class CreateTransferRequest(BaseModel):
    """Request schema for creating a transfer job."""

    source_provider: str
    dest_provider: str
    source_folder_id: Optional[str] = None
    dest_folder_id: Optional[str] = None
    config: Optional[dict] = None


class TransferJobSummary(BaseModel):
    """Response schema for transfer job in list."""

    id: int
    status: str
    source_provider: str
    dest_provider: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    scheduled_for: Optional[str]
    total_items: int
    completed_items: int
    failed_items: int

    class Config:
        from_attributes = True


class TransferJobDetail(BaseModel):
    """Response schema for detailed transfer job."""

    id: int
    status: str
    source_provider: str
    dest_provider: str
    source_folder_id: Optional[str]
    dest_folder_id: Optional[str]
    config: Optional[dict]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    scheduled_for: Optional[str]

    class Config:
        from_attributes = True


class PaginatedTransfersResponse(BaseModel):
    """Response schema for paginated transfer list."""

    items: List[TransferJobSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class DateRangeFilter(BaseModel):
    """Date range filter for files."""

    start_date: Optional[date] = None
    end_date: Optional[date] = None


class TransferConfigUpdate(BaseModel):
    """Request schema for updating transfer configuration."""

    file_types: Optional[List[str]] = Field(None, description="List of file extensions to include (e.g., ['.pdf', '.docx'])")
    date_range: Optional[DateRangeFilter] = None
    folder_include: Optional[List[str]] = Field(None, description="Folder patterns to include")
    folder_exclude: Optional[List[str]] = Field(None, description="Folder patterns to exclude")
    conflict_strategy: Optional[str] = Field(None, description="Conflict resolution strategy: ask, skip_all, rename_all, or overwrite_all")

    @field_validator("conflict_strategy")
    @classmethod
    def validate_conflict_strategy(cls, v: Optional[str]) -> Optional[str]:
        """Validate conflict strategy is one of the allowed values."""
        if v is None:
            return v

        valid_strategies = ["ask", "skip_all", "rename_all", "overwrite_all"]
        if v not in valid_strategies:
            raise ValueError(f"conflict_strategy must be one of: {', '.join(valid_strategies)}")
        return v


@router.post("", response_model=TransferJobDetail, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    transfer_data: CreateTransferRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new transfer job.

    Args:
        transfer_data: Transfer job creation data
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        TransferJobDetail: Created transfer job
    """
    # Create new transfer job
    transfer_job = TransferJob(
        user_id=user_id,
        status=JobStatus.DRAFT,
        source_provider=transfer_data.source_provider,
        dest_provider=transfer_data.dest_provider,
        source_folder_id=transfer_data.source_folder_id,
        dest_folder_id=transfer_data.dest_folder_id,
        config=transfer_data.config or {}
    )

    db.add(transfer_job)
    await db.commit()
    await db.refresh(transfer_job)

    return TransferJobDetail(
        id=transfer_job.id,
        status=transfer_job.status.value,
        source_provider=transfer_job.source_provider,
        dest_provider=transfer_job.dest_provider,
        source_folder_id=transfer_job.source_folder_id,
        dest_folder_id=transfer_job.dest_folder_id,
        config=transfer_job.config,
        created_at=transfer_job.created_at.isoformat(),
        started_at=transfer_job.started_at.isoformat() if transfer_job.started_at else None,
        completed_at=transfer_job.completed_at.isoformat() if transfer_job.completed_at else None,
        scheduled_for=transfer_job.scheduled_for.isoformat() if transfer_job.scheduled_for else None
    )


@router.get("", response_model=PaginatedTransfersResponse)
async def list_transfers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List all transfer jobs for the current user with pagination.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        PaginatedTransfersResponse: Paginated list of transfer jobs
    """
    # Calculate offset
    offset = (page - 1) * page_size

    # Get total count
    count_query = select(func.count(TransferJob.id)).where(TransferJob.user_id == user_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated jobs
    jobs_query = (
        select(TransferJob)
        .where(TransferJob.user_id == user_id)
        .options(selectinload(TransferJob.items))
        .order_by(TransferJob.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(jobs_query)
    jobs = result.scalars().all()

    # Format response with item counts
    items = []
    for job in jobs:
        total_items = len(job.items)
        completed_items = sum(1 for item in job.items if item.status.value == "completed")
        failed_items = sum(1 for item in job.items if item.status.value == "failed")

        items.append(
            TransferJobSummary(
                id=job.id,
                status=job.status.value,
                source_provider=job.source_provider,
                dest_provider=job.dest_provider,
                created_at=job.created_at.isoformat(),
                started_at=job.started_at.isoformat() if job.started_at else None,
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                scheduled_for=job.scheduled_for.isoformat() if job.scheduled_for else None,
                total_items=total_items,
                completed_items=completed_items,
                failed_items=failed_items
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return PaginatedTransfersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{job_id}", response_model=TransferJobDetail)
async def get_transfer(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific transfer job.

    Args:
        job_id: Transfer job ID
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        TransferJobDetail: Transfer job details

    Raises:
        HTTPException 404: If job not found or user doesn't own it
    """
    # Fetch the job
    result = await db.execute(
        select(TransferJob).where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    return TransferJobDetail(
        id=job.id,
        status=job.status.value,
        source_provider=job.source_provider,
        dest_provider=job.dest_provider,
        source_folder_id=job.source_folder_id,
        dest_folder_id=job.dest_folder_id,
        config=job.config,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        scheduled_for=job.scheduled_for.isoformat() if job.scheduled_for else None
    )


@router.post("/{job_id}/cancel")
async def cancel_transfer(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a pending or running transfer job.

    Args:
        job_id: Transfer job ID
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        Dict with success message

    Raises:
        HTTPException 404: If job not found
        HTTPException 400: If job cannot be cancelled
    """
    # Fetch the job
    result = await db.execute(
        select(TransferJob).where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    # Check if job can be cancelled
    cancellable_statuses = [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.SCHEDULED, JobStatus.PAUSED]
    if job.status not in cancellable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status '{job.status.value}'"
        )

    # Update job status
    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.utcnow()

    await db.commit()

    return {
        "success": True,
        "message": "Transfer job cancelled successfully",
        "job_id": job_id
    }


@router.delete("/{job_id}")
async def delete_transfer(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a completed transfer job and its logs.

    Args:
        job_id: Transfer job ID
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        Dict with success message

    Raises:
        HTTPException 404: If job not found
        HTTPException 400: If job is still running
    """
    # Fetch the job
    result = await db.execute(
        select(TransferJob).where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    # Check if job can be deleted (not running)
    if job.status in [JobStatus.RUNNING, JobStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete running or pending job. Cancel it first."
        )

    # Delete the job (cascade will delete items and conflicts)
    await db.delete(job)
    await db.commit()

    return {
        "success": True,
        "message": "Transfer job deleted successfully",
        "job_id": job_id
    }


@router.patch("/{job_id}/config", response_model=TransferJobDetail)
async def update_transfer_config(
    job_id: int,
    config_update: TransferConfigUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update transfer job configuration (filters, conflict handling).

    Can only update jobs in DRAFT or PENDING status.

    Args:
        job_id: Transfer job ID
        config_update: Configuration updates
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        TransferJobDetail: Updated transfer job

    Raises:
        HTTPException 404: If job not found
        HTTPException 400: If job status doesn't allow updates
    """
    # Fetch the job
    result = await db.execute(
        select(TransferJob).where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    # Check if job can be configured
    if job.status not in [JobStatus.DRAFT, JobStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update configuration for job with status '{job.status.value}'"
        )

    # Get existing config or initialize
    current_config = job.config or {}

    # Update config with provided values
    if config_update.file_types is not None:
        current_config["file_types"] = config_update.file_types

    if config_update.date_range is not None:
        current_config["date_range"] = {
            "start_date": config_update.date_range.start_date.isoformat() if config_update.date_range.start_date else None,
            "end_date": config_update.date_range.end_date.isoformat() if config_update.date_range.end_date else None
        }

    if config_update.folder_include is not None:
        current_config["folder_include"] = config_update.folder_include

    if config_update.folder_exclude is not None:
        current_config["folder_exclude"] = config_update.folder_exclude

    if config_update.conflict_strategy is not None:
        current_config["conflict_strategy"] = config_update.conflict_strategy

    # Update job config
    job.config = current_config
    await db.commit()
    await db.refresh(job)

    return TransferJobDetail(
        id=job.id,
        status=job.status.value,
        source_provider=job.source_provider,
        dest_provider=job.dest_provider,
        source_folder_id=job.source_folder_id,
        dest_folder_id=job.dest_folder_id,
        config=job.config,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        scheduled_for=job.scheduled_for.isoformat() if job.scheduled_for else None
    )


class AnalysisResponse(BaseModel):
    """Response schema for file analysis."""

    total_files: int
    total_size: int
    folder_count: int
    file_type_breakdown: Dict[str, int]
    potential_conflicts: int
    items_created: int


class DryRunFileInfo(BaseModel):
    """Information about a file in dry run."""

    source_name: str
    source_path: str
    dest_path: str
    size: int
    has_conflict: bool
    conflict_resolution: Optional[str] = None


class DryRunResponse(BaseModel):
    """Response schema for dry run."""

    files_to_transfer: List[DryRunFileInfo]
    folders_to_create: List[str]
    total_files: int
    total_size: int
    conflicts: int
    estimated_time_minutes: int


@router.post("/{job_id}/analyze", response_model=AnalysisResponse)
async def analyze_transfer(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze source files and create transfer items.

    Args:
        job_id: Transfer job ID
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        AnalysisResponse: Analysis results

    Raises:
        HTTPException 404: If job not found
        HTTPException 400: If job already analyzed or wrong status
    """
    # Fetch the job
    result = await db.execute(
        select(TransferJob).where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    # Check if job is in valid state for analysis
    if job.status not in [JobStatus.DRAFT, JobStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot analyze job with status '{job.status.value}'"
        )

    # Get source account
    source_result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.provider == job.source_provider
        )
    )
    source_account = source_result.scalar_one_or_none()

    if not source_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source account not connected: {job.source_provider}"
        )

    # Get destination account
    dest_result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.provider == job.dest_provider
        )
    )
    dest_account = dest_result.scalar_one_or_none()

    if not dest_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Destination account not connected: {job.dest_provider}"
        )

    # Delete any existing transfer items
    await db.execute(
        delete(TransferItem).where(TransferItem.job_id == job_id)
    )
    await db.commit()

    # List source files
    source_folder_id = job.source_folder_id or "root"
    if job.source_provider == "onedrive":
        files = await OneDriveService.list_folder(source_account, source_folder_id)
    else:
        files = await GoogleDriveService.list_folder(source_account, source_folder_id)

    # Apply filters from config
    config = job.config or {}
    filtered_files = []
    folder_count = 0

    for file in files:
        # Skip folders (count them separately)
        if file.type == "folder":
            folder_count += 1
            continue

        # Apply file type filter
        if config.get("file_types"):
            file_ext = file.name.split(".")[-1].lower() if "." in file.name else ""
            if file_ext not in [ft.lower() for ft in config["file_types"]]:
                continue

        # Apply date range filter
        if config.get("date_range") and file.modified_at:
            start_date = config["date_range"].get("start_date")
            end_date = config["date_range"].get("end_date")

            if start_date:
                start_dt = datetime.fromisoformat(start_date)
                if file.modified_at < start_dt:
                    continue

            if end_date:
                end_dt = datetime.fromisoformat(end_date)
                if file.modified_at > end_dt:
                    continue

        filtered_files.append(file)

    # Check for conflicts
    file_names = [f.name for f in filtered_files]
    dest_folder_id = job.dest_folder_id or "root"
    conflicts = await ConflictDetectionService.check_conflicts_batch(
        dest_account, file_names, dest_folder_id, case_insensitive=False
    )
    conflict_count = sum(1 for v in conflicts.values() if v is not None)

    # Create transfer items
    file_type_breakdown = defaultdict(int)
    total_size = 0
    items_created = 0

    for file in filtered_files:
        # Get file extension for breakdown
        file_ext = file.name.split(".")[-1].lower() if "." in file.name else "none"
        file_type_breakdown[file_ext] += 1
        total_size += file.size

        # Create transfer item
        item = TransferItem(
            job_id=job_id,
            source_file_id=file.id,
            source_path=file.name,
            dest_path=file.name,
            status=JobStatus.PENDING,
            size=file.size
        )
        db.add(item)
        items_created += 1

    await db.commit()

    # Update job status
    job.status = JobStatus.PENDING
    await db.commit()

    return AnalysisResponse(
        total_files=len(filtered_files),
        total_size=total_size,
        folder_count=folder_count,
        file_type_breakdown=dict(file_type_breakdown),
        potential_conflicts=conflict_count,
        items_created=items_created
    )


@router.post("/{job_id}/dry-run", response_model=DryRunResponse)
async def dry_run_transfer(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform a dry run to preview the transfer without modifying files.

    Args:
        job_id: Transfer job ID
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        DryRunResponse: Detailed preview of transfer

    Raises:
        HTTPException 404: If job not found
        HTTPException 400: If no items to transfer
    """
    # Fetch the job with items
    result = await db.execute(
        select(TransferJob)
        .options(selectinload(TransferJob.items))
        .where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    if not job.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No items to transfer. Run /analyze first."
        )

    # Get destination account for conflict checking
    dest_result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.provider == job.dest_provider
        )
    )
    dest_account = dest_result.scalar_one_or_none()

    if not dest_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Destination account not connected: {job.dest_provider}"
        )

    # Analyze each item
    files_to_transfer = []
    folders_to_create = set()
    total_size = 0
    conflict_count = 0

    dest_folder_id = job.dest_folder_id or "root"
    config = job.config or {}
    conflict_strategy = config.get("conflict_strategy", "ask")

    for item in job.items:
        # Check for conflicts
        has_conflict = await ConflictDetectionService.check_conflict(
            dest_account, item.dest_path, dest_folder_id, case_insensitive=False
        )

        # Determine conflict resolution
        conflict_resolution = None
        if has_conflict:
            conflict_count += 1
            if conflict_strategy == "skip_all":
                conflict_resolution = "skip"
            elif conflict_strategy == "rename_all":
                conflict_resolution = "rename"
            elif conflict_strategy == "overwrite_all":
                conflict_resolution = "overwrite"
            else:
                conflict_resolution = "ask"

        files_to_transfer.append(
            DryRunFileInfo(
                source_name=item.source_path,
                source_path=item.source_path,
                dest_path=item.dest_path,
                size=item.size,
                has_conflict=has_conflict is not None,
                conflict_resolution=conflict_resolution
            )
        )

        total_size += item.size

    # Calculate estimated time (rough estimate: 1MB per second)
    estimated_seconds = total_size / (1024 * 1024)  # Convert bytes to MB
    estimated_minutes = max(1, int(estimated_seconds / 60))

    return DryRunResponse(
        files_to_transfer=files_to_transfer,
        folders_to_create=list(folders_to_create),
        total_files=len(files_to_transfer),
        total_size=total_size,
        conflicts=conflict_count,
        estimated_time_minutes=estimated_minutes
    )


class ResumeResponse(BaseModel):
    """Response schema for resume transfer."""

    job_id: int
    items_to_retry: int
    completed_items: int
    s3_files_cleaned: int
    task_ids: List[str]


class ProgressResponse(BaseModel):
    """Response schema for transfer progress."""

    job_id: int
    total_files: int
    total_size: int
    files_completed: int
    files_failed: int
    bytes_transferred: int
    current_file: Optional[str]
    current_file_bytes: int
    current_file_total: int
    percent_complete: float
    started_at: str
    last_update: str


@router.post("/{job_id}/resume", response_model=ResumeResponse)
async def resume_transfer(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Resume a failed or paused transfer job.

    Skips completed items, re-queues failed/pending items, and cleans up partial S3 files.

    Args:
        job_id: Transfer job ID
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        ResumeResponse: Resume operation results

    Raises:
        HTTPException 404: If job not found
        HTTPException 400: If job cannot be resumed
    """
    # Fetch the job with items
    result = await db.execute(
        select(TransferJob)
        .options(selectinload(TransferJob.items))
        .where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    # Check if job can be resumed
    resumable_statuses = [JobStatus.FAILED, JobStatus.PAUSED, JobStatus.CANCELLED]
    if job.status not in resumable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resume job with status '{job.status.value}'. Only FAILED, PAUSED, or CANCELLED jobs can be resumed."
        )

    # Separate items by status
    completed_items = [item for item in job.items if item.status == JobStatus.COMPLETED]
    items_to_retry = [
        item for item in job.items
        if item.status in [JobStatus.FAILED, JobStatus.PENDING, JobStatus.RUNNING]
    ]

    if not items_to_retry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No items to retry. All items are already completed."
        )

    # Clean up partial S3 files from previous attempts
    s3_service = S3Service()
    s3_files_cleaned = 0

    for item in items_to_retry:
        s3_key = f"transfers/{job.id}/{item.id}/{item.source_path}"
        try:
            # Check if partial file exists
            if await s3_service.file_exists(s3_key):
                await s3_service.delete_file(s3_key)
                s3_files_cleaned += 1
        except Exception as e:
            # Log but don't fail - S3 cleanup is best-effort
            logger.warning(f"Failed to clean up S3 file {s3_key}: {str(e)}")

    # Reset items to pending status
    for item in items_to_retry:
        item.status = JobStatus.PENDING
        item.started_at = None
        item.completed_at = None
        item.error_message = None

    # Update job status
    job.status = JobStatus.RUNNING
    job.started_at = datetime.utcnow()
    job.completed_at = None

    await db.commit()

    # Queue transfer tasks
    task_ids = []
    for item in items_to_retry[:5]:  # Process first 5 items (configurable)
        task = transfer_single_file.delay(item.id)
        task_ids.append(task.id)

    logger.info(f"Resumed job {job_id}: {len(items_to_retry)} items to retry, {len(completed_items)} already completed")

    return ResumeResponse(
        job_id=job_id,
        items_to_retry=len(items_to_retry),
        completed_items=len(completed_items),
        s3_files_cleaned=s3_files_cleaned,
        task_ids=task_ids
    )


@router.get("/{job_id}/progress", response_model=ProgressResponse)
async def get_transfer_progress(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time progress for a transfer job.

    Args:
        job_id: Transfer job ID
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        ProgressResponse: Current progress data

    Raises:
        HTTPException 404: If job not found or no progress data
        HTTPException 403: If user doesn't own the job
    """
    # Verify job ownership
    result = await db.execute(
        select(TransferJob).where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    # Get progress from Redis
    progress = await progress_tracker.get_progress(job_id)

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No progress data available. Job may not have started yet."
        )

    # Calculate percent complete
    if progress["total_size"] > 0:
        percent_complete = (progress["bytes_transferred"] / progress["total_size"]) * 100
    else:
        percent_complete = 0.0

    return ProgressResponse(
        job_id=progress["job_id"],
        total_files=progress["total_files"],
        total_size=progress["total_size"],
        files_completed=progress["files_completed"],
        files_failed=progress["files_failed"],
        bytes_transferred=progress["bytes_transferred"],
        current_file=progress.get("current_file"),
        current_file_bytes=progress.get("current_file_bytes", 0),
        current_file_total=progress.get("current_file_total", 0),
        percent_complete=round(percent_complete, 2),
        started_at=progress["started_at"],
        last_update=progress["last_update"]
    )


@router.get("/{job_id}/progress/stream")
async def stream_transfer_progress(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Stream real-time progress updates for a transfer job using Server-Sent Events (SSE).

    Clients subscribe to this endpoint to receive continuous progress updates.
    The stream automatically closes when the job completes or fails.

    Args:
        job_id: Transfer job ID
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        StreamingResponse: SSE stream of progress updates

    Raises:
        HTTPException 404: If job not found
        HTTPException 403: If user doesn't own the job
    """
    # Verify job ownership
    result = await db.execute(
        select(TransferJob).where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    async def event_generator():
        """
        Generate SSE events with progress updates.

        Sends progress updates every 2 seconds and automatically closes
        the stream when the job reaches a terminal state.
        """
        last_update = None

        try:
            while True:
                # Get current progress from Redis
                progress = await progress_tracker.get_progress(job_id)

                if progress:
                    # Calculate percent complete
                    if progress["total_size"] > 0:
                        percent_complete = (progress["bytes_transferred"] / progress["total_size"]) * 100
                    else:
                        percent_complete = 0.0

                    # Only send if data has changed or it's the first update
                    current_update = progress.get("last_update")
                    if current_update != last_update or last_update is None:
                        last_update = current_update

                        # Format progress data
                        progress_data = {
                            "job_id": progress["job_id"],
                            "total_files": progress["total_files"],
                            "total_size": progress["total_size"],
                            "files_completed": progress["files_completed"],
                            "files_failed": progress["files_failed"],
                            "bytes_transferred": progress["bytes_transferred"],
                            "current_file": progress.get("current_file"),
                            "current_file_bytes": progress.get("current_file_bytes", 0),
                            "current_file_total": progress.get("current_file_total", 0),
                            "percent_complete": round(percent_complete, 2),
                            "started_at": progress["started_at"],
                            "last_update": progress["last_update"]
                        }

                        # Send SSE event
                        yield f"data: {json.dumps(progress_data)}\n\n"

                # Check if job has reached a terminal state
                result = await db.execute(
                    select(TransferJob.status).where(TransferJob.id == job_id)
                )
                current_status = result.scalar_one_or_none()

                if current_status:
                    terminal_statuses = [
                        JobStatus.COMPLETED,
                        JobStatus.FAILED,
                        JobStatus.CANCELLED
                    ]

                    if current_status in terminal_statuses:
                        # Send completion event
                        completion_data = {
                            "event": "complete",
                            "job_id": job_id,
                            "status": current_status.value,
                            "message": f"Transfer job {current_status.value}"
                        }
                        yield f"data: {json.dumps(completion_data)}\n\n"
                        logger.info(f"Job {job_id} reached terminal status {current_status.value}, closing SSE stream")
                        break

                # Wait before next update (2 seconds for responsive updates)
                await asyncio.sleep(2)

        except asyncio.CancelledError:
            # Client disconnected
            logger.info(f"SSE stream cancelled for job {job_id} (client disconnected)")
            raise
        except Exception as e:
            # Log error and send error event
            logger.error(f"Error in SSE stream for job {job_id}: {str(e)}")
            error_data = {
                "event": "error",
                "job_id": job_id,
                "message": "An error occurred while streaming progress"
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering in nginx
        }
    )


class ConflictInfo(BaseModel):
    """Information about a file conflict."""

    id: int
    item_id: int
    source_path: str
    dest_path: str
    source_size: int
    dest_file_exists: bool
    resolution: Optional[str] = None
    resolved_at: Optional[str] = None

    class Config:
        from_attributes = True


class ConflictListResponse(BaseModel):
    """Response schema for listing conflicts."""

    conflicts: List[ConflictInfo]
    total_conflicts: int
    pending_conflicts: int
    resolved_conflicts: int


class ResolveConflictRequest(BaseModel):
    """Request schema for resolving a conflict."""

    resolution: str  # skip, rename, or overwrite

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        """Validate resolution is one of the allowed values."""
        valid_resolutions = ["skip", "rename", "overwrite"]
        if v not in valid_resolutions:
            raise ValueError(f"resolution must be one of: {', '.join(valid_resolutions)}")
        return v


class ResolveAllConflictsRequest(BaseModel):
    """Request schema for resolving all conflicts."""

    resolution: str  # skip, rename, or overwrite

    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        """Validate resolution is one of the allowed values."""
        valid_resolutions = ["skip", "rename", "overwrite"]
        if v not in valid_resolutions:
            raise ValueError(f"resolution must be one of: {', '.join(valid_resolutions)}")
        return v


@router.get("/{job_id}/conflicts", response_model=ConflictListResponse)
async def list_conflicts(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List all conflicts for a transfer job.

    Args:
        job_id: Transfer job ID
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        ConflictListResponse: List of conflicts with details

    Raises:
        HTTPException 404: If job not found
        HTTPException 403: If user doesn't own the job
    """
    # Verify job ownership
    result = await db.execute(
        select(TransferJob).where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    # Fetch conflicts with related item data
    conflicts_result = await db.execute(
        select(ConflictRecord)
        .options(selectinload(ConflictRecord.item))
        .where(ConflictRecord.job_id == job_id)
        .order_by(ConflictRecord.id)
    )
    conflicts = conflicts_result.scalars().all()

    # Format conflict information
    conflict_list = []
    pending_count = 0
    resolved_count = 0

    for conflict in conflicts:
        if conflict.resolution is None:
            pending_count += 1
        else:
            resolved_count += 1

        conflict_list.append(
            ConflictInfo(
                id=conflict.id,
                item_id=conflict.item_id,
                source_path=conflict.item.source_path,
                dest_path=conflict.item.dest_path or conflict.item.source_path,
                source_size=conflict.item.size or 0,
                dest_file_exists=True,  # Conflict means file exists
                resolution=conflict.resolution.value if conflict.resolution else None,
                resolved_at=conflict.resolved_at.isoformat() if conflict.resolved_at else None
            )
        )

    return ConflictListResponse(
        conflicts=conflict_list,
        total_conflicts=len(conflict_list),
        pending_conflicts=pending_count,
        resolved_conflicts=resolved_count
    )


@router.post("/{job_id}/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    job_id: int,
    conflict_id: int,
    resolve_request: ResolveConflictRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve a single conflict.

    Args:
        job_id: Transfer job ID
        conflict_id: Conflict record ID
        resolve_request: Resolution details
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        Dict with success message and updated conflict

    Raises:
        HTTPException 404: If job or conflict not found
        HTTPException 403: If user doesn't own the job
        HTTPException 400: If conflict already resolved
    """
    # Verify job ownership
    result = await db.execute(
        select(TransferJob).where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    # Fetch the conflict
    conflict_result = await db.execute(
        select(ConflictRecord)
        .options(selectinload(ConflictRecord.item))
        .where(
            ConflictRecord.id == conflict_id,
            ConflictRecord.job_id == job_id
        )
    )
    conflict = conflict_result.scalar_one_or_none()

    if not conflict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conflict not found"
        )

    if conflict.resolution is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflict already resolved"
        )

    # Apply resolution
    resolution_enum = ConflictResolution(resolve_request.resolution)
    conflict.resolution = resolution_enum
    conflict.resolved_at = datetime.utcnow()

    # Update transfer item based on resolution
    if resolution_enum == ConflictResolution.SKIP:
        conflict.item.status = ItemStatus.SKIPPED
    elif resolution_enum == ConflictResolution.RENAME:
        # Generate new filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        original_path = conflict.item.dest_path or conflict.item.source_path
        # Split into name and extension
        if "." in original_path:
            name, ext = original_path.rsplit(".", 1)
            conflict.item.dest_path = f"{name}_{timestamp}.{ext}"
        else:
            conflict.item.dest_path = f"{original_path}_{timestamp}"
    elif resolution_enum == ConflictResolution.OVERWRITE:
        # Item will overwrite existing file
        pass

    await db.commit()
    await db.refresh(conflict)

    logger.info(f"Resolved conflict {conflict_id} for job {job_id} with resolution: {resolve_request.resolution}")

    return {
        "success": True,
        "message": f"Conflict resolved with {resolve_request.resolution}",
        "conflict_id": conflict_id,
        "resolution": resolve_request.resolution,
        "new_dest_path": conflict.item.dest_path
    }


@router.post("/{job_id}/conflicts/resolve-all")
async def resolve_all_conflicts(
    job_id: int,
    resolve_request: ResolveAllConflictsRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve all pending conflicts for a transfer job with the same resolution.

    Args:
        job_id: Transfer job ID
        resolve_request: Resolution to apply to all conflicts
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        Dict with success message and count of resolved conflicts

    Raises:
        HTTPException 404: If job not found
        HTTPException 403: If user doesn't own the job
        HTTPException 400: If no pending conflicts
    """
    # Verify job ownership
    result = await db.execute(
        select(TransferJob).where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    # Fetch all pending conflicts
    conflicts_result = await db.execute(
        select(ConflictRecord)
        .options(selectinload(ConflictRecord.item))
        .where(
            ConflictRecord.job_id == job_id,
            ConflictRecord.resolution.is_(None)
        )
    )
    pending_conflicts = conflicts_result.scalars().all()

    if not pending_conflicts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending conflicts to resolve"
        )

    # Apply resolution to all conflicts
    resolution_enum = ConflictResolution(resolve_request.resolution)
    resolved_count = 0

    for conflict in pending_conflicts:
        conflict.resolution = resolution_enum
        conflict.resolved_at = datetime.utcnow()

        # Update transfer item based on resolution
        if resolution_enum == ConflictResolution.SKIP:
            conflict.item.status = ItemStatus.SKIPPED
        elif resolution_enum == ConflictResolution.RENAME:
            # Generate new filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            original_path = conflict.item.dest_path or conflict.item.source_path
            # Split into name and extension
            if "." in original_path:
                name, ext = original_path.rsplit(".", 1)
                conflict.item.dest_path = f"{name}_{timestamp}.{ext}"
            else:
                conflict.item.dest_path = f"{original_path}_{timestamp}"
        elif resolution_enum == ConflictResolution.OVERWRITE:
            # Item will overwrite existing file
            pass

        resolved_count += 1

    await db.commit()

    # If job was paused due to conflicts and all are now resolved, resume it
    if job.status == JobStatus.PAUSED:
        job.status = JobStatus.RUNNING
        await db.commit()
        logger.info(f"Resumed job {job_id} after resolving all conflicts")

    logger.info(f"Resolved {resolved_count} conflicts for job {job_id} with resolution: {resolve_request.resolution}")

    return {
        "success": True,
        "message": f"Resolved {resolved_count} conflicts with {resolve_request.resolution}",
        "job_id": job_id,
        "conflicts_resolved": resolved_count,
        "resolution": resolve_request.resolution,
        "job_resumed": job.status == JobStatus.RUNNING
    }


class ScheduleTransferRequest(BaseModel):
    """Request schema for scheduling a transfer."""

    scheduled_for: datetime

    @field_validator("scheduled_for")
    @classmethod
    def validate_scheduled_time(cls, v: datetime) -> datetime:
        """Validate that scheduled time is in the future."""
        # Ensure datetime is timezone-aware
        if v.tzinfo is None:
            raise ValueError("scheduled_for must include timezone information")

        # Convert to UTC for comparison
        now_utc = datetime.now(v.tzinfo).astimezone()
        v_utc = v.astimezone()

        if v_utc <= now_utc:
            raise ValueError("scheduled_for must be in the future")

        return v


class ScheduleTransferResponse(BaseModel):
    """Response schema for scheduling a transfer."""

    job_id: int
    scheduled_for: str
    status: str
    message: str


@router.post("/{job_id}/schedule", response_model=ScheduleTransferResponse)
async def schedule_transfer(
    job_id: int,
    schedule_request: ScheduleTransferRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Schedule a transfer job for future execution.

    Args:
        job_id: Transfer job ID
        schedule_request: Schedule details with scheduled_for datetime
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        ScheduleTransferResponse: Scheduling confirmation

    Raises:
        HTTPException 404: If job not found
        HTTPException 403: If user doesn't own the job
        HTTPException 400: If job cannot be scheduled (wrong status or no items)
    """
    # Verify job ownership
    result = await db.execute(
        select(TransferJob)
        .options(selectinload(TransferJob.items))
        .where(
            TransferJob.id == job_id,
            TransferJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer job not found"
        )

    # Check if job can be scheduled
    schedulable_statuses = [JobStatus.DRAFT, JobStatus.PENDING]
    if job.status not in schedulable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot schedule job with status '{job.status.value}'. Only DRAFT or PENDING jobs can be scheduled."
        )

    # Verify job has items to transfer
    if not job.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule job with no items. Run analysis first."
        )

    # Convert scheduled time to UTC for storage
    scheduled_utc = schedule_request.scheduled_for.astimezone()

    # Update job with scheduled time and status
    job.scheduled_for = scheduled_utc.replace(tzinfo=None)  # Store as naive UTC
    job.status = JobStatus.SCHEDULED

    await db.commit()
    await db.refresh(job)

    logger.info(f"Scheduled job {job_id} for execution at {scheduled_utc.isoformat()}")

    return ScheduleTransferResponse(
        job_id=job_id,
        scheduled_for=scheduled_utc.isoformat(),
        status=job.status.value,
        message=f"Transfer scheduled for {scheduled_utc.isoformat()}"
    )
