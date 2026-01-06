from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
import enum

from app.core.database import Base


class JobStatus(str, enum.Enum):
    """Enum for transfer job status."""

    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class ItemStatus(str, enum.Enum):
    """Enum for transfer item status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConflictResolution(str, enum.Enum):
    """Enum for conflict resolution strategy."""

    ASK = "ask"
    SKIP = "skip"
    RENAME = "rename"
    OVERWRITE = "overwrite"


class TransferJob(Base):
    """
    TransferJob model for managing file transfer jobs.

    Attributes:
        id: Primary key
        user_id: Foreign key to User table
        status: Job status (draft, pending, running, completed, etc.)
        source_provider: Source cloud provider
        dest_provider: Destination cloud provider
        source_folder_id: Source folder ID (provider-specific)
        dest_folder_id: Destination folder ID (provider-specific)
        config: JSON configuration (filters, conflict strategy, etc.)
        created_at: When job was created
        started_at: When job execution started
        completed_at: When job completed or failed
        scheduled_for: When job is scheduled to run (optional)
    """

    __tablename__ = "transfer_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Job status
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.DRAFT, index=True)

    # Source and destination
    source_provider = Column(String(50), nullable=False)
    dest_provider = Column(String(50), nullable=False)
    source_folder_id = Column(String(500), nullable=True)
    dest_folder_id = Column(String(500), nullable=True)

    # Configuration (filters, conflict handling, etc.)
    config = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="transfer_jobs")
    items = relationship("TransferItem", back_populates="job", cascade="all, delete-orphan")
    conflicts = relationship("ConflictRecord", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TransferJob(id={self.id}, user_id={self.user_id}, status={self.status})>"


class TransferItem(Base):
    """
    TransferItem model for tracking individual files in a transfer job.

    Attributes:
        id: Primary key
        job_id: Foreign key to TransferJob
        source_file_id: File ID in source provider
        source_path: File path in source
        dest_path: File path in destination
        status: Item status (pending, in_progress, completed, failed, skipped)
        size: File size in bytes
        error_message: Error message if transfer failed
        started_at: When item transfer started
        completed_at: When item transfer completed
    """

    __tablename__ = "transfer_items"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("transfer_jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # File information
    source_file_id = Column(String(500), nullable=False)
    source_path = Column(Text, nullable=False)
    dest_path = Column(Text, nullable=True)

    # Transfer status
    status = Column(Enum(ItemStatus), nullable=False, default=ItemStatus.PENDING, index=True)
    size = Column(BigInteger, nullable=True)  # File size in bytes
    error_message = Column(Text, nullable=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    job = relationship("TransferJob", back_populates="items")

    def __repr__(self):
        return f"<TransferItem(id={self.id}, job_id={self.job_id}, status={self.status})>"


class ConflictRecord(Base):
    """
    ConflictRecord model for tracking file conflicts during transfer.

    Attributes:
        id: Primary key
        job_id: Foreign key to TransferJob
        item_id: Foreign key to TransferItem
        resolution: How the conflict was/should be resolved (skip, rename, overwrite)
        resolved_at: When conflict was resolved
    """

    __tablename__ = "conflict_records"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("transfer_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("transfer_items.id", ondelete="CASCADE"), nullable=False, index=True)

    # Resolution
    resolution = Column(Enum(ConflictResolution), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    job = relationship("TransferJob", back_populates="conflicts")
    item = relationship("TransferItem", backref="conflicts")

    def __repr__(self):
        return f"<ConflictRecord(id={self.id}, job_id={self.job_id}, resolution={self.resolution})>"
