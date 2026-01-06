from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, date

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.transfer import TransferJob, TransferItem, JobStatus, ConflictResolution
from pydantic import BaseModel, Field, field_validator


router = APIRouter(prefix="/api/transfers", tags=["transfers"])


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
