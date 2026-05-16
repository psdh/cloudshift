import logging
import secrets
from typing import Optional

from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    # Application
    APP_NAME: str = "CloudShift"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: Optional[str] = None

    # Redis
    REDIS_URL: Optional[str] = None

    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None

    # OAuth - OneDrive
    ONEDRIVE_CLIENT_ID: Optional[str] = None
    ONEDRIVE_CLIENT_SECRET: Optional[str] = None

    # OAuth - Google Drive
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # JWT — no default secret is shipped; see _require_secrets below.
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption key for OAuth tokens at rest (32-byte url-safe base64 Fernet key).
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # No default is shipped; see _require_secrets below.
    ENCRYPTION_KEY: Optional[str] = None

    # Notifications
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # Email (AWS SES)
    SES_FROM_EMAIL: Optional[str] = None

    # Frontend URL (for email links)
    FRONTEND_URL: str = "http://localhost:3000"

    @model_validator(mode="after")
    def _require_secrets(self):
        """Fail fast in production if security secrets are unset.

        No secret is shipped as a code default (a committed key is equivalent
        to no key). In DEBUG an ephemeral key is generated so local/test runs
        work; in production a missing secret raises at startup.
        """
        if not self.JWT_SECRET_KEY:
            if self.DEBUG:
                self.JWT_SECRET_KEY = secrets.token_urlsafe(64)
                logger.warning(
                    "JWT_SECRET_KEY not set; generated an ephemeral DEBUG key. "
                    "Set JWT_SECRET_KEY before production."
                )
            else:
                raise ValueError("JWT_SECRET_KEY must be set (no default is provided).")

        if not self.ENCRYPTION_KEY:
            if self.DEBUG:
                self.ENCRYPTION_KEY = Fernet.generate_key().decode()
                logger.warning(
                    "ENCRYPTION_KEY not set; generated an ephemeral DEBUG key. "
                    "Tokens encrypted now will not be decryptable after restart. "
                    "Set ENCRYPTION_KEY before production."
                )
            else:
                raise ValueError("ENCRYPTION_KEY must be set (no default is provided).")
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
