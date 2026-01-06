from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """
    User model for authentication and profile management.

    Attributes:
        id: Primary key
        email: User's email address (unique)
        password_hash: Bcrypt hashed password
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        email_notifications: Whether user wants email notifications
        sms_notifications: Whether user wants SMS notifications
        phone_number: User's phone number for SMS notifications (optional)
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Notification preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    sms_notifications = Column(Boolean, default=False, nullable=False)
    phone_number = Column(String(20), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
