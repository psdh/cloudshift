from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
import enum

from app.core.database import Base


class AuditAction(str, enum.Enum):
    """Enum for audit log actions."""

    # Authentication actions
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    TOKEN_REFRESH = "token_refresh"

    # Transfer actions
    TRANSFER_CREATED = "transfer_created"
    TRANSFER_STARTED = "transfer_started"
    TRANSFER_COMPLETED = "transfer_completed"
    TRANSFER_FAILED = "transfer_failed"
    TRANSFER_CANCELLED = "transfer_cancelled"
    TRANSFER_DELETED = "transfer_deleted"

    # Conflict resolution
    CONFLICT_RESOLVED = "conflict_resolved"
    TRANSFER_CONFLICT_DETECTED = "transfer_conflict_detected"
    TRANSFER_CONFLICT_RESOLVED = "transfer_conflict_resolved"

    # System
    SYSTEM_ERROR = "system_error"

    # Account management
    ACCOUNT_CONNECTED = "account_connected"
    ACCOUNT_DISCONNECTED = "account_disconnected"

    # Settings
    SETTINGS_CHANGED = "settings_changed"
    CONFIG_UPDATED = "config_updated"


class AuditLog(Base):
    """
    AuditLog model for tracking user actions and system events.

    Attributes:
        id: Primary key
        user_id: Foreign key to User table (nullable for system events)
        action: Action type (enum)
        resource_type: Type of resource affected (e.g., 'transfer', 'account')
        resource_id: ID of the affected resource
        details: JSON field with additional context
        ip_address: IP address of the request
        user_agent: User agent string from the request
        created_at: Timestamp when action occurred
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action details
    action = Column(Enum(AuditAction), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)

    # Additional context
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("User", backref="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action})>"
