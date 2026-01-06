from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from typing import Optional, Dict, Any
import logging

from app.models.audit_log import AuditLog, AuditAction

logger = logging.getLogger(__name__)


class AuditService:
    """Service for creating audit log entries."""

    @staticmethod
    async def log_action(
        db: AsyncSession,
        action: AuditAction,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            db: Database session
            action: Action type (AuditAction enum)
            user_id: User ID (optional for system events)
            resource_type: Type of resource (e.g., 'transfer', 'account')
            resource_id: ID of the resource
            details: Additional context as dictionary
            ip_address: IP address (auto-extracted from request if not provided)
            user_agent: User agent string (auto-extracted from request if not provided)
            request: FastAPI request object (for auto-extraction)

        Returns:
            AuditLog: Created audit log entry
        """
        # Auto-extract IP and user agent from request if provided
        if request:
            if not ip_address:
                # Try to get real IP from X-Forwarded-For header first (for proxies)
                forwarded_for = request.headers.get("X-Forwarded-For")
                if forwarded_for:
                    ip_address = forwarded_for.split(",")[0].strip()
                else:
                    # Fall back to client host
                    ip_address = request.client.host if request.client else None

            if not user_agent:
                user_agent = request.headers.get("User-Agent")

        # Create audit log entry
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

        try:
            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)
            logger.debug(f"Audit log created: {action.value} by user {user_id}")
            return audit_log
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            await db.rollback()
            # Don't raise - audit logging failures shouldn't break the application
            return audit_log

    @staticmethod
    async def log_login(
        db: AsyncSession,
        user_id: int,
        request: Optional[Request] = None,
        success: bool = True
    ) -> Optional[AuditLog]:
        """Log a login attempt."""
        return await AuditService.log_action(
            db=db,
            action=AuditAction.LOGIN,
            user_id=user_id,
            resource_type="user",
            resource_id=str(user_id),
            details={"success": success},
            request=request
        )

    @staticmethod
    async def log_logout(
        db: AsyncSession,
        user_id: int,
        request: Optional[Request] = None
    ) -> Optional[AuditLog]:
        """Log a logout action."""
        return await AuditService.log_action(
            db=db,
            action=AuditAction.LOGOUT,
            user_id=user_id,
            resource_type="user",
            resource_id=str(user_id),
            request=request
        )

    @staticmethod
    async def log_register(
        db: AsyncSession,
        user_id: int,
        email: str,
        request: Optional[Request] = None
    ) -> Optional[AuditLog]:
        """Log a user registration."""
        return await AuditService.log_action(
            db=db,
            action=AuditAction.REGISTER,
            user_id=user_id,
            resource_type="user",
            resource_id=str(user_id),
            details={"email": email},
            request=request
        )

    @staticmethod
    async def log_transfer_created(
        db: AsyncSession,
        user_id: int,
        transfer_id: int,
        source_provider: str,
        dest_provider: str,
        request: Optional[Request] = None
    ) -> Optional[AuditLog]:
        """Log transfer job creation."""
        return await AuditService.log_action(
            db=db,
            action=AuditAction.TRANSFER_CREATED,
            user_id=user_id,
            resource_type="transfer",
            resource_id=str(transfer_id),
            details={
                "source_provider": source_provider,
                "dest_provider": dest_provider
            },
            request=request
        )

    @staticmethod
    async def log_transfer_started(
        db: AsyncSession,
        user_id: int,
        transfer_id: int,
        request: Optional[Request] = None
    ) -> Optional[AuditLog]:
        """Log transfer job start."""
        return await AuditService.log_action(
            db=db,
            action=AuditAction.TRANSFER_STARTED,
            user_id=user_id,
            resource_type="transfer",
            resource_id=str(transfer_id),
            request=request
        )

    @staticmethod
    async def log_transfer_completed(
        db: AsyncSession,
        user_id: int,
        transfer_id: int,
        total_files: int,
        total_size: int,
        request: Optional[Request] = None
    ) -> Optional[AuditLog]:
        """Log transfer job completion."""
        return await AuditService.log_action(
            db=db,
            action=AuditAction.TRANSFER_COMPLETED,
            user_id=user_id,
            resource_type="transfer",
            resource_id=str(transfer_id),
            details={
                "total_files": total_files,
                "total_size": total_size
            },
            request=request
        )

    @staticmethod
    async def log_account_connected(
        db: AsyncSession,
        user_id: int,
        provider: str,
        account_email: str,
        request: Optional[Request] = None
    ) -> Optional[AuditLog]:
        """Log cloud account connection."""
        return await AuditService.log_action(
            db=db,
            action=AuditAction.ACCOUNT_CONNECTED,
            user_id=user_id,
            resource_type="account",
            resource_id=provider,
            details={
                "provider": provider,
                "account_email": account_email
            },
            request=request
        )

    @staticmethod
    async def log_account_disconnected(
        db: AsyncSession,
        user_id: int,
        provider: str,
        request: Optional[Request] = None
    ) -> Optional[AuditLog]:
        """Log cloud account disconnection."""
        return await AuditService.log_action(
            db=db,
            action=AuditAction.ACCOUNT_DISCONNECTED,
            user_id=user_id,
            resource_type="account",
            resource_id=provider,
            details={"provider": provider},
            request=request
        )

    @staticmethod
    async def log_config_updated(
        db: AsyncSession,
        user_id: int,
        transfer_id: int,
        config_changes: Dict[str, Any],
        request: Optional[Request] = None
    ) -> Optional[AuditLog]:
        """Log transfer configuration update."""
        return await AuditService.log_action(
            db=db,
            action=AuditAction.CONFIG_UPDATED,
            user_id=user_id,
            resource_type="transfer",
            resource_id=str(transfer_id),
            details={"changes": config_changes},
            request=request
        )
