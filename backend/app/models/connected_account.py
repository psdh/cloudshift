from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class CloudProvider(str, enum.Enum):
    """Enum for supported cloud storage providers."""

    ONEDRIVE = "onedrive"
    GOOGLE_DRIVE = "google_drive"

    @classmethod
    def normalize(cls, value: str) -> str:
        """Map any accepted provider alias to its canonical enum value.

        The frontend and older code used "google"; canonical is the enum
        value "google_drive". Raises ValueError for unknown providers.
        """
        if value is None:
            raise ValueError("provider is required")
        canonical = _PROVIDER_ALIASES.get(str(value).strip().lower())
        if canonical is None:
            raise ValueError(f"Unsupported provider: {value!r}")
        return canonical


# Legacy / client provider aliases -> canonical CloudProvider value.
_PROVIDER_ALIASES = {
    "onedrive": CloudProvider.ONEDRIVE.value,
    "google": CloudProvider.GOOGLE_DRIVE.value,
    "google_drive": CloudProvider.GOOGLE_DRIVE.value,
}


class ConnectedAccount(Base):
    """
    ConnectedAccount model for storing OAuth tokens for cloud storage providers.

    Attributes:
        id: Primary key
        user_id: Foreign key to User table
        provider: Cloud storage provider (onedrive, google_drive)
        access_token: Encrypted OAuth access token
        refresh_token: Encrypted OAuth refresh token
        token_expiry: When the access token expires
        account_email: Email address of the connected cloud account
        created_at: Timestamp when account was connected
    """

    __tablename__ = "connected_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(
        Enum(CloudProvider, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )

    # Encrypted tokens (stored as encrypted strings)
    access_token = Column(String(1000), nullable=False)
    refresh_token = Column(String(1000), nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Account info
    account_email = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="connected_accounts")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uix_user_provider"),
    )

    def __repr__(self):
        return f"<ConnectedAccount(id={self.id}, user_id={self.user_id}, provider={self.provider})>"
