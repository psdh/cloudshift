import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from urllib.parse import urlencode
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.connected_account import ConnectedAccount, CloudProvider
from app.services.encryption import EncryptionService


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
