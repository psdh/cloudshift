from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import datetime, timedelta, date
from io import StringIO
import csv

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.audit_log import AuditLog, AuditAction
from pydantic import BaseModel


router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


# Response schemas
class AuditLogResponse(BaseModel):
    """Response schema for a single audit log entry."""

    id: int
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class PaginatedAuditLogsResponse(BaseModel):
    """Response schema for paginated audit logs."""

    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=PaginatedAuditLogsResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[date] = Query(None, description="Filter logs from this date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter logs until this date (inclusive)"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List audit logs for the current user with pagination and filtering.

    Enforces 30-day retention - only returns logs from the last 30 days.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        action: Filter by action type (e.g., 'login', 'transfer_created')
        start_date: Filter logs from this date (inclusive)
        end_date: Filter logs until this date (inclusive)
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        PaginatedAuditLogsResponse: Paginated list of audit logs
    """
    # Enforce 30-day retention
    retention_cutoff = datetime.utcnow() - timedelta(days=30)

    # Build query filters
    filters = [
        AuditLog.user_id == user_id,
        AuditLog.created_at >= retention_cutoff
    ]

    # Add action filter if provided
    if action:
        # Validate action type
        try:
            action_enum = AuditAction(action)
            filters.append(AuditLog.action == action_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type: {action}"
            )

    # Add date range filters
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        filters.append(AuditLog.created_at >= start_datetime)

    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        filters.append(AuditLog.created_at <= end_datetime)

    # Count total matching logs
    count_query = select(func.count(AuditLog.id)).where(and_(*filters))
    result = await db.execute(count_query)
    total = result.scalar()

    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size

    # Fetch paginated logs
    query = (
        select(AuditLog)
        .where(and_(*filters))
        .order_by(AuditLog.created_at.desc())
        .limit(page_size)
        .offset(offset)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    # Convert to response format
    log_responses = [
        AuditLogResponse(
            id=log.id,
            action=log.action.value,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            created_at=log.created_at.isoformat()
        )
        for log in logs
    ]

    return PaginatedAuditLogsResponse(
        logs=log_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/export")
async def export_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[date] = Query(None, description="Filter logs from this date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter logs until this date (inclusive)"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Export audit logs for the current user as CSV.

    Enforces 30-day retention - only exports logs from the last 30 days.

    Args:
        action: Filter by action type (e.g., 'login', 'transfer_created')
        start_date: Filter logs from this date (inclusive)
        end_date: Filter logs until this date (inclusive)
        user_id: Current user ID from JWT token
        db: Database session

    Returns:
        CSV file with audit logs
    """
    from fastapi.responses import StreamingResponse

    # Enforce 30-day retention
    retention_cutoff = datetime.utcnow() - timedelta(days=30)

    # Build query filters
    filters = [
        AuditLog.user_id == user_id,
        AuditLog.created_at >= retention_cutoff
    ]

    # Add action filter if provided
    if action:
        # Validate action type
        try:
            action_enum = AuditAction(action)
            filters.append(AuditLog.action == action_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type: {action}"
            )

    # Add date range filters
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        filters.append(AuditLog.created_at >= start_datetime)

    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        filters.append(AuditLog.created_at <= end_datetime)

    # Fetch all matching logs
    query = (
        select(AuditLog)
        .where(and_(*filters))
        .order_by(AuditLog.created_at.desc())
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    # Generate CSV
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "ID",
        "Action",
        "Resource Type",
        "Resource ID",
        "Details",
        "IP Address",
        "User Agent",
        "Created At"
    ])

    # Write data rows
    for log in logs:
        writer.writerow([
            log.id,
            log.action.value,
            log.resource_type or "",
            log.resource_id or "",
            str(log.details) if log.details else "",
            log.ip_address or "",
            log.user_agent or "",
            log.created_at.isoformat()
        ])

    # Return CSV response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )
