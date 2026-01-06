import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from urllib.parse import urlencode
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.connected_account import ConnectedAccount, CloudProvider
from app.services.encryption import EncryptionService

logger = logging.getLogger(__name__)


class OAuthService:
    """Service for handling OAuth flows with cloud storage providers."""

    # OneDrive OAuth endpoints
    ONEDRIVE_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    ONEDRIVE_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    ONEDRIVE_SCOPES = ["offline_access", "Files.Read.All", "Files.ReadWrite.All", "User.Read"]

    # Google Drive OAuth endpoints
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/userinfo.email"
    ]

    @staticmethod
    def generate_state() -> str:
        """
        Generate a random state parameter for CSRF protection.

        Returns:
            str: Random 32-character state string
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def get_onedrive_auth_url(state: str, redirect_uri: str) -> str:
        """
        Generate OneDrive OAuth authorization URL.

        Args:
            state: CSRF protection state parameter
            redirect_uri: Callback URL for OAuth flow

        Returns:
            str: Authorization URL to redirect user to
        """
        params = {
            "client_id": settings.ONEDRIVE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(OAuthService.ONEDRIVE_SCOPES),
            "state": state,
            "response_mode": "query",
        }
        return f"{OAuthService.ONEDRIVE_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_onedrive_code(
        code: str,
        redirect_uri: str
    ) -> Dict[str, any]:
        """
        Exchange OneDrive authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in authorization request

        Returns:
            Dict with 'access_token', 'refresh_token', 'expires_in'

        Raises:
            httpx.HTTPError: If token exchange fails
        """
        data = {
            "client_id": settings.ONEDRIVE_CLIENT_ID,
            "client_secret": settings.ONEDRIVE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(OAuthService.ONEDRIVE_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_onedrive_user_info(access_token: str) -> Dict[str, any]:
        """
        Fetch OneDrive user information using access token.

        Args:
            access_token: Valid OneDrive access token

        Returns:
            Dict with user info including 'userPrincipalName' (email)

        Raises:
            httpx.HTTPError: If request fails
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def save_connected_account(
        db: AsyncSession,
        user_id: int,
        provider: CloudProvider,
        access_token: str,
        refresh_token: Optional[str],
        expires_in: int,
        account_email: Optional[str]
    ) -> ConnectedAccount:
        """
        Save or update connected account with encrypted tokens.

        Args:
            db: Database session
            user_id: User ID
            provider: Cloud provider enum
            access_token: OAuth access token (will be encrypted)
            refresh_token: OAuth refresh token (will be encrypted)
            expires_in: Token expiration time in seconds
            account_email: Email of the connected cloud account

        Returns:
            ConnectedAccount: Created or updated account
        """
        # Encrypt tokens
        encrypted_access = EncryptionService.encrypt(access_token)
        encrypted_refresh = EncryptionService.encrypt(refresh_token) if refresh_token else None

        # Calculate token expiry
        token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

        # Check if account already exists
        result = await db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.user_id == user_id,
                ConnectedAccount.provider == provider
            )
        )
        existing_account = result.scalar_one_or_none()

        if existing_account:
            # Update existing account
            existing_account.access_token = encrypted_access
            existing_account.refresh_token = encrypted_refresh
            existing_account.token_expiry = token_expiry
            existing_account.account_email = account_email
            account = existing_account
        else:
            # Create new account
            account = ConnectedAccount(
                user_id=user_id,
                provider=provider,
                access_token=encrypted_access,
                refresh_token=encrypted_refresh,
                token_expiry=token_expiry,
                account_email=account_email
            )
            db.add(account)

        await db.commit()
        await db.refresh(account)
        return account

    @staticmethod
    def get_google_auth_url(state: str, redirect_uri: str) -> str:
        """
        Generate Google Drive OAuth authorization URL.

        Args:
            state: CSRF protection state parameter
            redirect_uri: Callback URL for OAuth flow

        Returns:
            str: Authorization URL to redirect user to
        """
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(OAuthService.GOOGLE_SCOPES),
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }
        return f"{OAuthService.GOOGLE_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_google_code(
        code: str,
        redirect_uri: str
    ) -> Dict[str, any]:
        """
        Exchange Google authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in authorization request

        Returns:
            Dict with 'access_token', 'refresh_token', 'expires_in'

        Raises:
            httpx.HTTPError: If token exchange fails
        """
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(OAuthService.GOOGLE_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_google_user_info(access_token: str) -> Dict[str, any]:
        """
        Fetch Google user information using access token.

        Args:
            access_token: Valid Google access token

        Returns:
            Dict with user info including 'email'

        Raises:
            httpx.HTTPError: If request fails
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def refresh_onedrive_token(refresh_token: str) -> Dict[str, any]:
        """
        Refresh OneDrive access token using refresh token.

        Args:
            refresh_token: Valid OneDrive refresh token

        Returns:
            Dict with 'access_token', 'refresh_token', 'expires_in'

        Raises:
            httpx.HTTPError: If token refresh fails
        """
        data = {
            "client_id": settings.ONEDRIVE_CLIENT_ID,
            "client_secret": settings.ONEDRIVE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(OAuthService.ONEDRIVE_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def refresh_google_token(refresh_token: str) -> Dict[str, any]:
        """
        Refresh Google access token using refresh token.

        Args:
            refresh_token: Valid Google refresh token

        Returns:
            Dict with 'access_token', 'expires_in' (may include new 'refresh_token')

        Raises:
            httpx.HTTPError: If token refresh fails
        """
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(OAuthService.GOOGLE_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def is_token_expired(token_expiry: Optional[datetime], buffer_minutes: int = 5) -> bool:
        """
        Check if token is expired or will expire within buffer time.

        Args:
            token_expiry: Token expiration datetime
            buffer_minutes: Minutes before expiry to consider token expired (default 5)

        Returns:
            bool: True if token is expired or will expire soon
        """
        if not token_expiry:
            return True

        # Make token_expiry timezone-aware if it isn't
        if token_expiry.tzinfo is None:
            token_expiry = token_expiry.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        buffer = timedelta(minutes=buffer_minutes)
        return (token_expiry - now) <= buffer

    @staticmethod
    async def get_valid_access_token(
        db: AsyncSession,
        account: ConnectedAccount
    ) -> str:
        """
        Get a valid access token, automatically refreshing if needed.

        Args:
            db: Database session
            account: ConnectedAccount instance

        Returns:
            str: Valid access token (decrypted)

        Raises:
            Exception: If token refresh fails or no refresh token available
        """
        # Check if token needs refresh
        if not OAuthService.is_token_expired(account.token_expiry):
            # Token is still valid, decrypt and return
            access_token = EncryptionService.decrypt(account.access_token)
            if access_token:
                return access_token

        # Token expired or invalid, need to refresh
        if not account.refresh_token:
            logger.error(f"Account {account.id} has no refresh token, cannot refresh")
            raise Exception("No refresh token available")

        # Decrypt refresh token
        refresh_token = EncryptionService.decrypt(account.refresh_token)
        if not refresh_token:
            logger.error(f"Failed to decrypt refresh token for account {account.id}")
            raise Exception("Failed to decrypt refresh token")

        try:
            # Refresh based on provider
            if account.provider == CloudProvider.ONEDRIVE:
                token_response = await OAuthService.refresh_onedrive_token(refresh_token)
            elif account.provider == CloudProvider.GOOGLE_DRIVE:
                token_response = await OAuthService.refresh_google_token(refresh_token)
            else:
                raise Exception(f"Unknown provider: {account.provider}")

            # Extract new tokens
            new_access_token = token_response.get("access_token")
            new_refresh_token = token_response.get("refresh_token", refresh_token)  # Some APIs don't return new refresh token
            expires_in = token_response.get("expires_in", 3600)

            if not new_access_token:
                raise Exception("No access token in refresh response")

            # Update account with new tokens
            account.access_token = EncryptionService.encrypt(new_access_token)
            account.refresh_token = EncryptionService.encrypt(new_refresh_token)
            account.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            await db.commit()
            await db.refresh(account)

            logger.info(f"Successfully refreshed token for account {account.id}")
            return new_access_token

        except httpx.HTTPError as e:
            logger.warning(f"Failed to refresh token for account {account.id}: {str(e)}")
            raise Exception(f"Token refresh failed: {str(e)}")
